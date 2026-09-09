#!/usr/bin/env python3
"""Build the shared evidence bundle. The only component that touches the network.

Every other skill in this marketplace reads the bundle this script writes and
performs no I/O of its own. That is what keeps six audit skills from disagreeing
about what the site served, and what keeps the whole audit inside the runtime
budget: one crawl, one render pass, many readers.

Usage
-----
  collect.py https://example.com --out ./evidence
  collect.py https://example.com --out ./evidence --probe-bot-ua
  collect.py --offline-root tests/fixtures/site_a --out ./evidence
  collect.py https://example.com --out ./evidence --import-page /=saved.html

Exit codes (the CLI contract every audit skill script shares)
  0  a bundle was written, whatever it contains
  1  internal error, no bundle written
  2  output path unusable
  3  precondition unmet (bad arguments)

A seed that does not resolve, 404s, serves a PDF, or is blanket-disallowed by
robots.txt is NOT an error. Each produces a bundle recording exactly what was
observed, with `status` set to partial or no_content_available. The audit says
what it could not see rather than failing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dom  # noqa: E402
import traps  # noqa: E402
from fetch import AUDITOR_TOKEN, DEFAULT_UA, FetchResult, Fetcher, Hop, median  # noqa: E402
from politeness import HostThrottle, parse_robots  # noqa: E402
from render import build_renderer  # noqa: E402

COLLECTOR_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"

# Bots we probe for edge reachability, only with --probe-bot-ua. Classification
# lives in crawl-access-audit/references/ai-bots.json; this list is only the
# subset we would send a single HEAD as.
PROBE_BOTS = [
    "OAI-SearchBot/1.0 (+https://openai.com/searchbot)",
    "PerplexityBot/1.0 (+https://perplexity.ai/perplexitybot)",
    "Claude-SearchBot/1.0 (+https://www.anthropic.com/claude-searchbot)",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "Bingbot/2.0 (+http://www.bing.com/bingbot.htm)",
]

# Which page types get the render budget first. Home and the commercial pages
# carry the most auditable signal; utility pages carry the least.
RENDER_PRIORITY = (
    "home", "product", "pricing", "article", "docs", "category",
    "contact", "about", "other", "utility",
)

CHALLENGE_MARKERS = (
    "just a moment",
    "checking your browser",
    "enable javascript and cookies to continue",
    "attention required",
    "ddos protection by",
    "access denied",
    "request blocked",
)


# --------------------------------------------------------------- transports


class LiveTransport:
    """Real HTTP. Honours robots.txt as a hard constraint on our own crawl."""

    kind = "live"

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    def get(self, url: str, method: str = "GET", extra_headers=None, follow_cross_host=False) -> FetchResult:
        return self.fetcher.fetch(
            url, method=method, extra_headers=extra_headers, follow_cross_host=follow_cross_host
        )

    def sample_ttfb(self, url: str, n: int = 3) -> list:
        return self.fetcher.sample_ttfb(url, n)


class OfflineTransport:
    """Serves a fixture directory as if it were a site.

    Used by tests/run_offline.py, which additionally blocks the socket module so
    that any accidental live call fails loudly rather than passing silently.
    """

    kind = "offline"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        meta = json.loads((self.root / "_meta.json").read_text(encoding="utf-8"))
        self.origin = meta["origin"].rstrip("/")
        self.routes = meta.get("routes", {})
        self.default_status = meta.get("default_status", 404)
        self.not_found_file = meta.get("not_found_file")
        self.fixed_ttfb = meta.get("ttfb_ms", [120.0, 130.0, 125.0])

    def _route_of(self, url: str) -> str:
        if url.startswith(self.origin):
            rest = url[len(self.origin) :]
            return rest or "/"
        parts = urllib.parse.urlsplit(url)
        return (parts.path or "/") + (("?" + parts.query) if parts.query else "")

    def get(self, url: str, method: str = "GET", extra_headers=None, follow_cross_host=False) -> FetchResult:
        route = self._route_of(url)
        spec = self.routes.get(route)
        result = FetchResult(url=url, final_url=url, method=method)
        result.ttfb_ms = float(self.fixed_ttfb[0])

        if spec is None:
            result.status = self.default_status
            result.headers = {"content-type": "text/html; charset=utf-8"}
            if self.not_found_file and method == "GET":
                path = self.root / self.not_found_file
                if path.exists():
                    result.body = path.read_bytes()
            return result

        if "redirect_to" in spec:
            target = urllib.parse.urljoin(self.origin + "/", spec["redirect_to"])
            result.status = spec.get("status", 301)
            result.headers = {"location": target, "content-type": "text/html"}
            result.final_url = target
            # Record the hop so FetchResult.cross_host_redirect can see it, the
            # same way the live transport would.
            result.hops = [Hop(url=url, status=result.status, location=target)]
            return result

        if spec.get("error"):
            result.error = spec["error"]
            result.status = None
            return result

        result.status = spec.get("status", 200)
        headers = {"content-type": spec.get("content_type", "text/html; charset=utf-8")}
        headers.update({k.lower(): v for k, v in (spec.get("headers") or {}).items()})
        result.headers = headers
        if method == "GET" and spec.get("file"):
            path = self.root / spec["file"]
            if path.exists():
                result.body = path.read_bytes()
        elif method == "GET" and "body" in spec:
            result.body = spec["body"].encode("utf-8")
        return result

    def sample_ttfb(self, url: str, n: int = 3) -> list:
        return [float(v) for v in self.fixed_ttfb[:n]]


# ------------------------------------------------------------------ helpers


MIN_FREE_BYTES = 64 * 1024 * 1024


def check_free_space(target: Path, minimum: int = MIN_FREE_BYTES) -> str | None:
    """Return an error string if the filesystem is too full to write safely.

    A disk that fills mid-write leaves a truncated file behind. For an evidence
    bundle that is merely annoying; for a checked-in golden it is poison, because
    the corrupt file silently becomes the reference every later test validates
    against. We refuse to start rather than write half a bundle.
    """
    try:
        usage = shutil.disk_usage(target if target.exists() else target.parent)
    except OSError as exc:
        return f"cannot stat filesystem for {target}: {exc}"
    if usage.free < minimum:
        return (
            f"only {usage.free / 1048576:.1f} MiB free at {target}; "
            f"{minimum / 1048576:.0f} MiB required. Refusing to write a bundle that "
            f"could be truncated."
        )
    return None


def atomic_write(path: Path, data: str | bytes) -> None:
    """Write a file so that a partial file is impossible, not merely unlikely.

    Write to a temporary file in the SAME directory (so os.replace is a rename
    within one filesystem and therefore atomic), flush, fsync, then replace. A
    crash or a full disk leaves either the old file or the new one, never a
    half-written one.

    Deliberately duplicated in emit_report.py and tests/run_offline.py rather
    than shared: no script in this marketplace may import from a sibling skill
    folder, because every skill folder has to be liftable and runnable alone.
    See references/skill-cli-contract.md.
    """
    payload = data.encode("utf-8") if isinstance(data, str) else data
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def utc_now_iso() -> str:
    """Timestamp for this run. Honours SOURCE_DATE_EPOCH so tests are reproducible."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        try:
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(epoch)))
        except (ValueError, OSError):
            pass
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def slug_for(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    raw = (parts.path or "/") + (("?" + parts.query) if parts.query else "")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower() or "index"
    return slug[:80]


def provisional_page_type(url: str, doc: dom.Document | None = None) -> str:
    """Cheap URL-shaped guess, used only to stratify the crawl sample.

    The real classification is site-profile-classifier's job and runs later
    against full page evidence. This exists because sampling has to happen
    before we have that evidence.
    """
    path = (urllib.parse.urlsplit(url).path or "/").lower().rstrip("/")
    if path in ("", "/"):
        return "home"
    segments = [s for s in path.split("/") if s]
    joined = "/" + "/".join(segments)
    rules = [
        (r"/(contact|contact-us|get-in-touch|support)$", "contact"),
        (r"/(about|about-us|team|company|our-story)", "about"),
        (r"/(pricing|plans|price)$", "pricing"),
        (r"/(blog|news|article|post|insights|resources)/.+", "article"),
        (r"/(blog|news|insights|resources)$", "category"),
        (r"/(docs|documentation|guide|guides|reference|api|manual)", "docs"),
        (r"/(product|products|item|p|shop|store)/.+", "product"),
        (r"/(product|products|shop|store|collections|category)$", "category"),
        (r"/(login|signin|register|cart|checkout|account|404|search)", "utility"),
        (r"/(privacy|terms|legal|cookie|imprint|gdpr)", "utility"),
    ]
    for pattern, label in rules:
        if re.search(pattern, joined):
            return label
    if doc is not None and doc.wordcount > 400:
        return "article"
    return "other"


def informative_image(img: dict) -> bool:
    """Is this image carrying content, or is it chrome or decoration?"""
    if img.get("role") == "presentation":
        return False
    if img.get("in_chrome"):
        return False
    if not img.get("in_main", True):
        return False
    w, h = img.get("width") or 0, img.get("height") or 0
    if w and h and (w < 100 or h < 100):
        return False
    src = (img.get("src") or "").lower()
    if any(t in src for t in ("icon", "sprite", "logo", "avatar", "spacer", "pixel", "badge")):
        return False
    # Thumbnails and previews restate a link that already carries its own text,
    # so they add no fact a reader could otherwise miss. On one live aggregator
    # 53 of 83 flagged images were post thumbnails.
    if any(t in src for t in ("thumb", "thumbnail", "preview", "_small", "-small", "placeholder")):
        return False
    return True


# ---------------------------------------------------------------- collector


class Collector:
    def __init__(self, args) -> None:
        self.args = args
        self.started = time.perf_counter()
        self.audited_at = utc_now_iso()
        self.degraded: list[dict] = []
        self.notes: list[str] = []
        self.throttle = HostThrottle(default_delay=args.delay)

        if args.offline_root:
            root = Path(args.offline_root)
            self.transport = OfflineTransport(root)
            self.seed = args.seed or (self.transport.origin + "/")
            self.renderer = build_renderer(offline_root=root, enable=not args.no_render)
        else:
            fetcher = Fetcher(
                user_agent=args.user_agent,
                timeout=args.timeout,
                throttle=self.throttle,
                max_retries=args.max_retries,
            )
            self.transport = LiveTransport(fetcher)
            self.seed = args.seed
            self.renderer = build_renderer(offline_root=None, enable=not args.no_render)

        if not getattr(self.renderer, "available", False):
            self.degrade(
                "rendered_dom",
                getattr(self.renderer, "reason", "renderer unavailable"),
                ["read.render.raw_text_gap", "read.render.nav_links_js_only", "act.perf.above_fold_weight"],
                "read.render.empty_spa_shell drops from critical/confirmed to high/likely",
            )

        self.origin = self._origin_of(self.seed)
        self.status = "complete"
        self.pages: list[dict] = []
        self.headers: dict[str, dict] = {}
        self.robots_text = ""
        self.robots_status: int | None = None
        self.robots = None
        self.sitemap_info: dict = {}
        self.probes: dict = {}
        self.skipped_robots: list[str] = []
        self.skipped_traps: list[dict] = []
        self.malformed_hrefs: list[dict] = []
        self.render_pairs: dict[str, dict] = {}
        self.sample_strategy = "not_run"

    # ------------------------------------------------------------- utils

    @staticmethod
    def _origin_of(url: str) -> str:
        parts = urllib.parse.urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}"

    def degrade(self, capability: str, reason: str, affects: list[str], effect: str) -> None:
        self.degraded.append(
            {
                "capability": capability,
                "reason": reason,
                "affects": sorted(affects),
                "confidence_effect": effect,
            }
        )

    def elapsed(self) -> float:
        return time.perf_counter() - self.started

    def out_of_time(self) -> bool:
        return self.args.time_budget > 0 and self.elapsed() > self.args.time_budget

    def record_headers(self, result: FetchResult) -> None:
        self.headers[result.url] = {
            "url": result.url,
            "final_url": result.final_url,
            "status": result.status,
            "method": result.method,
            "hops": [asdict(h) for h in result.hops],
            "headers": dict(sorted((result.headers or {}).items())),
            "tls": {"valid": result.tls_error is None, "error": result.tls_error},
            "error": result.error,
            "ttfb_ms": round(result.ttfb_ms, 1) if result.ttfb_ms is not None else None,
        }

    # --------------------------------------------------------- preflight

    def preflight(self) -> str | None:
        """Validate the seed. Returns a terminal status, or None to keep going."""
        result = self.transport.get(self.seed, follow_cross_host=False)
        self.record_headers(result)

        if result.status is None:
            self.notes.append(f"seed did not resolve: {result.error}")
            self.degrade(
                "site_content",
                f"seed URL unreachable: {result.error}",
                ["all"],
                "no page evidence could be collected",
            )
            return "no_content_available"

        if 300 <= result.status < 400 and result.cross_host_redirect:
            new_origin = self._origin_of(result.final_url)
            self.notes.append(
                f"seed redirected off-domain from {self.origin} to {new_origin}; "
                f"re-anchoring the audit origin to the final host"
            )
            self.origin = new_origin
            self.seed = result.final_url
            result = self.transport.get(self.seed, follow_cross_host=False)
            self.record_headers(result)
            self.status = "partial"

        if result.status is not None and result.status >= 400:
            self.notes.append(f"seed returned HTTP {result.status}")
            self.degrade(
                "site_content",
                f"seed URL returned HTTP {result.status}",
                ["all"],
                "no page evidence could be collected from the seed",
            )
            return "no_content_available"

        if result.body and not result.is_html:
            self.notes.append(
                f"seed content-type is {result.content_type or 'unknown'}, not HTML; "
                f"this auditor assesses HTML pages"
            )
            self.degrade(
                "site_content",
                f"seed served {result.content_type or 'an unknown content type'} rather than HTML",
                ["all"],
                "no HTML page evidence could be collected",
            )
            return "no_content_available"

        return None

    # ------------------------------------------------------------ robots

    def load_robots(self) -> None:
        url = urllib.parse.urljoin(self.origin + "/", "/robots.txt")
        result = self.transport.get(url)
        self.record_headers(result)
        self.robots_status = result.status
        self.robots_text = result.text() if result.body else ""
        self.robots = parse_robots(self.robots_text, status=result.status)

    def may_fetch(self, url: str) -> bool:
        """robots.txt is a hard constraint on our own crawling, not advice."""
        if self.robots is None:
            return True
        decision = self.robots.decide(self.args.user_agent, url)
        if not decision.allowed:
            self.skipped_robots.append(url)
        return decision.allowed

    # ----------------------------------------------------------- sitemap

    def load_sitemaps(self) -> None:
        candidates = list(self.robots.sitemaps) if self.robots else []
        default = urllib.parse.urljoin(self.origin + "/", "/sitemap.xml")
        if default not in candidates:
            candidates.append(default)

        fetched = []
        entries: list[dict] = []
        seen: set[str] = set()
        queue = list(candidates)
        while queue and len(fetched) < 5:
            sm_url = queue.pop(0)
            if sm_url in seen:
                continue
            seen.add(sm_url)
            result = self.transport.get(sm_url)
            self.record_headers(result)
            record = {"url": sm_url, "status": result.status, "type": None, "parse_error": None, "count": 0}
            text = result.text() if result.body else ""
            if result.status == 200 and text.strip():
                if "<sitemapindex" in text:
                    record["type"] = "index"
                    children = re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.I | re.S)
                    record["count"] = len(children)
                    queue.extend(c.strip() for c in children[:5])
                elif "<urlset" in text:
                    record["type"] = "urlset"
                    for block in re.findall(r"<url>(.*?)</url>", text, re.I | re.S):
                        loc = re.search(r"<loc>\s*(.*?)\s*</loc>", block, re.I | re.S)
                        lastmod = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", block, re.I | re.S)
                        if loc:
                            entries.append(
                                {"loc": loc.group(1).strip(), "lastmod": lastmod.group(1).strip() if lastmod else None}
                            )
                    record["count"] = len(entries)
                else:
                    record["parse_error"] = "body is not a sitemap (no <urlset> or <sitemapindex>)"
            elif result.status == 200:
                record["parse_error"] = "empty body"
            fetched.append(record)

        entries.sort(key=lambda e: e["loc"])
        lastmods = {e["lastmod"] for e in entries if e["lastmod"]}
        self.sitemap_info = {
            "declared_in_robots": sorted(self.robots.sitemaps) if self.robots else [],
            "fetched": fetched,
            "entries": entries,
            "coverage": {
                "listed": len(entries),
                "lastmod_present": sum(1 for e in entries if e["lastmod"]),
                "lastmod_distinct_values": len(lastmods),
            },
        }

    # ------------------------------------------------------------- crawl

    def discover(self) -> list[dict]:
        """Seed the frontier from the sitemap and the homepage link graph."""
        origin_host = (urllib.parse.urlsplit(self.origin).hostname or "").lower()
        frontier: dict[str, dict] = {}

        def consider(url: str, depth: int) -> None:
            normalised = traps.normalise_url(url, self.origin + "/")
            if not normalised:
                return
            host = (urllib.parse.urlsplit(normalised).hostname or "").lower()
            if host != origin_host and not host.endswith("." + origin_host):
                return
            reason = traps.trap_reason(normalised)
            if reason:
                self.skipped_traps.append({"url": normalised, "rule": reason})
                return
            row = frontier.setdefault(
                normalised, {"url": normalised, "depth": depth, "inlinks": 0, "provisional_type": None}
            )
            row["depth"] = min(row["depth"], depth)

        consider(self.seed, 0)
        for entry in self.sitemap_info.get("entries", []):
            consider(entry["loc"], 1)

        home = self.transport.get(self.seed)
        self.record_headers(home)
        if home.ok and home.is_html:
            doc = dom.parse_html(home.text(), self.seed)
            for link in doc.links:
                klass = traps.classify_href(link["href"], self.seed, origin_host)
                if klass.kind == "malformed":
                    self.malformed_hrefs.append(
                        {"source": self.seed, "href": link["href"][:200], "reason": klass.reason}
                    )
                elif klass.kind == "internal" and klass.url:
                    consider(klass.url, 1)
                    if klass.url in frontier:
                        frontier[klass.url]["inlinks"] += 1

        for row in frontier.values():
            row["provisional_type"] = provisional_page_type(row["url"])

        self.skipped_traps.sort(key=lambda r: r["url"])
        self.malformed_hrefs.sort(key=lambda r: (r["source"], r["href"]))
        return sorted(frontier.values(), key=lambda r: r["url"])

    def crawl(self, selected: list[dict]) -> None:
        allowed = [row for row in selected if self.may_fetch(row["url"])]
        origin_host = (urllib.parse.urlsplit(self.origin).hostname or "").lower()

        def work(row: dict) -> dict | None:
            if self.out_of_time():
                return None
            result = self.transport.get(row["url"])
            return self._page_record(row, result, origin_host)

        workers = max(1, self.args.workers)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for record in pool.map(work, allowed):
                if record is not None:
                    self.pages.append(record)

        self.pages.sort(key=lambda p: p["url"])
        if len(self.pages) < len(allowed):
            self.status = "partial"
            self.notes.append(
                f"time budget reached after {len(self.pages)} of {len(allowed)} pages; "
                f"the audit continues with what was collected"
            )

    def _page_record(self, row: dict, result: FetchResult, origin_host: str) -> dict:
        self.record_headers(result)
        record = {
            "url": row["url"],
            "status": result.status,
            "content_type": result.content_type,
            "bytes": len(result.body),
            "ttfb_ms": [round(result.ttfb_ms, 1)] if result.ttfb_ms is not None else [],
            "error": result.error,
            "redirect_chain": [asdict(h) for h in result.hops],
            "rendered_available": False,
            "rendered_html_path": None,
            "raw_html_path": None,
        }
        if not (result.ok and result.is_html and result.body):
            record.update(
                {
                    "title": "", "meta_description": None, "wordcount": 0, "main_wordcount": 0,
                    "text": "", "main_text": "", "headings": {}, "links": {}, "images": [],
                    "forms": [], "markup": {}, "meta_robots": None, "x_robots_tag": None,
                    "canonical": None, "dates": {}, "page_type": "unfetchable",
                    "page_type_confidence": 0.0, "spa_signals": {},
                }
            )
            return record

        doc = dom.parse_html(result.text(), row["url"])
        slug = slug_for(row["url"])
        record["raw_html_path"] = f"render_pairs/{slug}.raw.html"
        self.render_pairs[row["url"]] = {"slug": slug, "raw": result.text(), "rendered": None}

        internal, external, nofollow = [], [], []
        for link in doc.links:
            klass = traps.classify_href(link["href"], row["url"], origin_host)
            if klass.kind == "malformed":
                self.malformed_hrefs.append(
                    {"source": row["url"], "href": link["href"][:200], "reason": klass.reason}
                )
                continue
            if klass.url is None:
                continue
            if "nofollow" in (link.get("rel") or ""):
                nofollow.append(klass.url)
            if klass.kind == "internal":
                internal.append(klass.url)
            elif klass.kind == "external":
                external.append(klass.url)

        sitemap_lastmod = next(
            (e["lastmod"] for e in self.sitemap_info.get("entries", []) if e["loc"] == row["url"]), None
        )

        record.update(
            {
                "title": doc.title,
                "meta_description": doc.meta.get("description"),
                "wordcount": doc.wordcount,
                "main_wordcount": doc.main_wordcount,
                "main_selector": doc.main_selector,
                "text": doc.text,
                "main_text": doc.main_text,
                "boilerplate_ratio": round(doc.boilerplate_ratio, 3),
                "headings": {k: v for k, v in sorted(doc.headings.items())},
                "links": {
                    "internal": sorted(set(internal)),
                    "external": sorted(set(external)),
                    "nofollow": sorted(set(nofollow)),
                    "internal_in_main": sorted(
                        {
                            traps.classify_href(l["href"], row["url"], origin_host).url
                            for l in doc.links
                            if l["in_main"]
                            and traps.classify_href(l["href"], row["url"], origin_host).kind == "internal"
                        }
                        - {None}
                    ),
                },
                # Anchor text, not just target URLs: the engagement checks reason
                # about what a button SAYS, which a URL list cannot answer.
                "anchors": [
                    {
                        "text": link["text"],
                        "href": link["href"],
                        "in_main": link["in_main"],
                        "in_chrome": link["in_chrome"],
                    }
                    for link in doc.links
                    if link["text"]
                ][:200],
                "images": [
                    {**img, "informative": informative_image(img)} for img in doc.images
                ],
                "forms": doc.forms,
                "markup": {
                    "jsonld": doc.jsonld,
                    "microdata": doc.microdata,
                    "rdfa": doc.rdfa,
                    "opengraph": {k: v for k, v in sorted(doc.opengraph.items())},
                    "parse_errors": doc.jsonld_errors,
                },
                "meta_robots": doc.meta_robots,
                "x_robots_tag": (result.headers or {}).get("x-robots-tag"),
                "canonical": doc.canonical,
                "dates": {
                    "http_last_modified": (result.headers or {}).get("last-modified"),
                    "sitemap_lastmod": sitemap_lastmod,
                    "schema_published": None,
                    "schema_modified": None,
                    "visible": None,
                },
                "page_type": provisional_page_type(row["url"], doc),
                "page_type_confidence": 0.0,
                "spa_signals": doc.spa_shell_signals,
                "looks_like_spa_shell": doc.looks_like_spa_shell,
                "noscript_wordcount": doc.noscript_wordcount,
            }
        )
        return record

    # ------------------------------------------------------------ render

    def render_pass(self) -> None:
        if not getattr(self.renderer, "available", False):
            return
        html_pages = [p for p in self.pages if p["status"] == 200 and p["wordcount"] >= 0 and p["raw_html_path"]]
        by_type: dict[str, list[dict]] = {}
        for page in html_pages:
            by_type.setdefault(page["page_type"], []).append(page)
        picked: list[dict] = []
        # Render budget goes to the page types that carry the most auditable
        # signal first. Alphabetical round-robin would spend it on /about while
        # skipping /pricing. Ordering is fixed, so selection stays deterministic.
        order = sorted(by_type, key=lambda t: (RENDER_PRIORITY.index(t) if t in RENDER_PRIORITY else len(RENDER_PRIORITY), t))
        while len(picked) < self.args.render and any(by_type[k] for k in order):
            for key in order:
                if not by_type[key] or len(picked) >= self.args.render:
                    continue
                picked.append(by_type[key].pop(0))
        for page in picked:
            if self.out_of_time():
                break
            outcome = self.renderer.render(page["url"])
            if outcome.ok:
                slug = self.render_pairs[page["url"]]["slug"]
                self.render_pairs[page["url"]]["rendered"] = outcome.html
                page["rendered_available"] = True
                page["rendered_html_path"] = f"render_pairs/{slug}.rendered.html"
                rendered_doc = dom.parse_html(outcome.html, page["url"])
                page["rendered_wordcount"] = rendered_doc.wordcount
                page["rendered_main_wordcount"] = rendered_doc.main_wordcount
                page["rendered_internal_link_count"] = len(
                    {
                        traps.classify_href(
                            l["href"], page["url"], (urllib.parse.urlsplit(self.origin).hostname or "").lower()
                        ).url
                        for l in rendered_doc.links
                    }
                    - {None}
                )
                page["rendered_text"] = rendered_doc.text
                page["rendered_main_text"] = rendered_doc.main_text
            else:
                page["render_error"] = outcome.error
        self.renderer.close()

    # ------------------------------------------------------------ probes

    def probe(self) -> None:
        origin_slash = self.origin + "/"
        real_404 = None
        probes = traps.probe_urls(origin_slash)
        soft: list[dict] = []

        known = self.transport.get(urllib.parse.urljoin(origin_slash, "/this-page-should-not-exist-404"))
        self.record_headers(known)
        if known.status == 404:
            real_404 = known.text()

        for probe_url in probes:
            if self.out_of_time():
                break
            result = self.transport.get(probe_url)
            self.record_headers(result)
            body = result.text() if result.body else ""
            hit, why = traps.is_soft_404(result.status or 0, body, real_404)
            soft.append(
                {
                    "probe_url": probe_url,
                    "status": result.status,
                    "wordcount": dom.wordcount(dom.parse_html(body).text) if body else 0,
                    "is_soft_404": hit,
                    "verdict": why,
                }
            )

        llms = self.transport.get(urllib.parse.urljoin(origin_slash, "/llms.txt"))
        self.record_headers(llms)
        md_head = self.transport.get(
            origin_slash, method="HEAD", extra_headers={"Accept": "text/markdown"}
        )

        bot_reach = {"enabled": False, "reason": "--probe-bot-ua not set", "results": []}
        if self.args.probe_bot_ua:
            bot_reach = self._probe_bots(origin_slash)

        self.probes = {
            "soft_404": soft,
            "real_404_sample": {
                "url": known.url,
                "status": known.status,
                "wordcount": dom.wordcount(dom.parse_html(known.text()).text) if known.body else 0,
            },
            "llms_txt": {
                "url": urllib.parse.urljoin(origin_slash, "/llms.txt"),
                "status": llms.status,
                "bytes": len(llms.body),
            },
            "markdown_negotiation": {
                "accept_text_markdown_status": md_head.status,
                "content_type": md_head.content_type,
            },
            "bot_reach": bot_reach,
            "ttfb_samples_ms": self.transport.sample_ttfb(self.seed, self.args.ttfb_samples),
        }

    def _probe_bots(self, origin_slash: str) -> dict:
        """One HEAD per bot, homepage only, auditor token appended to the UA.

        Off by default. The token is always present so the site owner can see in
        their logs that this was an audit probe and not the real crawler. We do
        not silently impersonate.
        """
        results = []
        baseline = self.transport.get(origin_slash, method="HEAD")
        for bot in PROBE_BOTS:
            if self.out_of_time():
                break
            ua = f"{bot} {AUDITOR_TOKEN}"
            result = self.transport.get(origin_slash, method="GET", extra_headers={"User-Agent": ua})
            body = result.text()[:4000].lower() if result.body else ""
            challenged = any(marker in body for marker in CHALLENGE_MARKERS)
            results.append(
                {
                    "bot": bot.split("/")[0],
                    "user_agent_sent": ua,
                    "status": result.status,
                    "challenged": challenged,
                    "server": (result.headers or {}).get("server"),
                    "wordcount": dom.wordcount(dom.parse_html(result.text()).text) if result.body else 0,
                }
            )
        results.sort(key=lambda r: r["bot"])
        return {
            "enabled": True,
            "reason": None,
            "method": "one GET per bot, homepage only, auditor token appended to the user agent",
            "baseline_status": baseline.status,
            "results": results,
        }

    # ------------------------------------------------------------- write

    def write(self, out: Path) -> None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "render_pairs").mkdir(exist_ok=True)
        (out / "headers").mkdir(exist_ok=True)

        atomic_write(out / "robots.txt", self.robots_text)

        for url, pair in sorted(self.render_pairs.items()):
            atomic_write(out / "render_pairs" / f"{pair['slug']}.raw.html", pair["raw"])
            if pair["rendered"] is not None:
                atomic_write(
                    out / "render_pairs" / f"{pair['slug']}.rendered.html", pair["rendered"]
                )

        for url, record in sorted(self.headers.items()):
            atomic_write(
                out / "headers" / f"{slug_for(url)}.json",
                json.dumps(record, indent=2, sort_keys=True),
            )

        atomic_write(
            out / "pages.jsonl",
            "".join(json.dumps(page, sort_keys=True) + "\n" for page in self.pages),
        )

        atomic_write(out / "sitemap.json", json.dumps(self.sitemap_info, indent=2, sort_keys=True))
        atomic_write(out / "probes.json", json.dumps(self.probes, indent=2, sort_keys=True))

        meta = {
            "schema_version": SCHEMA_VERSION,
            "audited_at": self.audited_at,
            "seed_url": self.args.seed or self.seed,
            "resolved_origin": self.origin,
            "status": self.status,
            "notes": self.notes,
            "tool_versions": {
                "python": sys.version.split()[0],
                "collector": COLLECTOR_VERSION,
                "renderer": getattr(self.renderer, "name", "none"),
                "transport": self.transport.kind,
            },
            "crawl": {
                "pages_requested": self.args.max_pages,
                "pages_fetched": len(self.pages),
                "pages_rendered": sum(1 for p in self.pages if p.get("rendered_available")),
                "workers": self.args.workers,
                "per_host_delay_s": self.args.delay,
                "sample_strategy": self.sample_strategy,
                "robots_respected": True,
                "robots_status": self.robots_status,
                "urls_skipped_by_robots": sorted(set(self.skipped_robots)),
                "urls_skipped_by_traps": self.skipped_traps,
                "malformed_hrefs": self.malformed_hrefs,
            },
            "degraded_capabilities": sorted(self.degraded, key=lambda d: d["capability"]),
            "elapsed_s": None if os.environ.get("SOURCE_DATE_EPOCH") else round(self.elapsed(), 2),
        }
        atomic_write(out / "meta.json", json.dumps(meta, indent=2, sort_keys=True))

    # --------------------------------------------------------------- run

    def run(self, out: Path) -> int:
        terminal = self.preflight()
        if terminal is not None:
            self.status = terminal
            self.load_robots()
            self.probes = {
                "soft_404": [], "real_404_sample": {}, "llms_txt": {},
                "markdown_negotiation": {}, "bot_reach": {"enabled": False, "reason": "seed unusable", "results": []},
                "ttfb_samples_ms": [],
            }
            self.sitemap_info = {"declared_in_robots": [], "fetched": [], "entries": [], "coverage": {}}
            self.write(out)
            return 0

        self.load_robots()

        if self.robots is not None and not self.robots.allows(self.args.user_agent, self.seed):
            self.status = "no_content_available"
            self.notes.append(
                "robots.txt disallows this auditor from fetching the seed URL. "
                "robots.txt is a hard constraint on our own crawling, so no page "
                "content was fetched. The robots policy itself is still reported."
            )
            self.degrade(
                "site_content",
                "robots.txt disallows crawling; no content could be lawfully fetched",
                ["all page-level checks"],
                "no page evidence exists, so no page-level check may fire",
            )
            self.skipped_robots.append(self.seed)
            self.load_sitemaps()
            self.probes = {
                "soft_404": [], "real_404_sample": {}, "llms_txt": {},
                "markdown_negotiation": {},
                "bot_reach": {"enabled": False, "reason": "crawling disallowed by robots.txt", "results": []},
                "ttfb_samples_ms": [],
            }
            self.write(out)
            return 0

        self.load_sitemaps()
        candidates = self.discover()
        selected, strategy = traps.stratified_sample(candidates, cap=self.args.max_pages)
        self.sample_strategy = strategy
        self.crawl(selected)
        self.render_pass()
        self.probe()

        if not any(p["status"] == 200 for p in self.pages):
            self.status = "no_content_available"
        elif self.degraded or self.skipped_robots:
            self.status = "partial" if self.status == "complete" else self.status

        self.write(out)
        return 0


# ------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="collect.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("seed", nargs="?", help="seed URL, e.g. https://example.com")
    p.add_argument("--out", required=True, help="evidence bundle directory to write")
    p.add_argument("--offline-root", help="serve a fixture directory instead of the network")
    p.add_argument("--max-pages", type=int, default=25)
    p.add_argument("--workers", type=int, default=5)
    p.add_argument("--delay", type=float, default=0.4, help="per-host politeness delay in seconds")
    p.add_argument("--render", type=int, default=6, help="how many pages to render")
    p.add_argument("--no-render", action="store_true")
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--ttfb-samples", type=int, default=3)
    p.add_argument("--time-budget", type=float, default=0, help="seconds; 0 disables")
    p.add_argument("--user-agent", default=DEFAULT_UA)
    p.add_argument(
        "--probe-bot-ua",
        action="store_true",
        help="opt in to one request per AI bot user agent against the homepage only",
    )
    p.add_argument("--dry-run", action="store_true", help="print the plan and exit without fetching")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.seed and not args.offline_root:
        print("error: provide a seed URL or --offline-root", file=sys.stderr)
        return 3
    if args.seed and not re.match(r"^https?://", args.seed):
        print(f"error: seed must be an http(s) URL, got {args.seed!r}", file=sys.stderr)
        return 3

    out = Path(args.out)
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot write to {out}: {exc}", file=sys.stderr)
        return 2

    if "onedrive" in str(out.resolve()).lower():
        print(
            f"error: refusing to write the evidence bundle to a cloud-synced path: {out.resolve()}. "
            f"A sync client rewriting files mid-run corrupts the bundle and breaks determinism. "
            f"Choose an --out path outside OneDrive.",
            file=sys.stderr,
        )
        return 2

    space_error = check_free_space(out)
    if space_error:
        print(f"error: {space_error}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(
            json.dumps(
                {
                    "would_collect": args.seed or f"offline:{args.offline_root}",
                    "out": str(out),
                    "max_pages": args.max_pages,
                    "workers": args.workers,
                    "per_host_delay_s": args.delay,
                    "render": 0 if args.no_render else args.render,
                    "probe_bot_ua": args.probe_bot_ua,
                    "writes_to_target_site": False,
                },
                indent=2,
            )
        )
        return 0

    try:
        collector = Collector(args)
        code = collector.run(out)
    except Exception as exc:  # noqa: BLE001 - report the failure, do not traceback at a grader
        print(f"internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "bundle": str(out),
                "status": collector.status,
                "pages_fetched": len(collector.pages),
                "pages_rendered": sum(1 for p in collector.pages if p.get("rendered_available")),
                "degraded_capabilities": [d["capability"] for d in collector.degraded],
            },
            indent=2,
        )
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
