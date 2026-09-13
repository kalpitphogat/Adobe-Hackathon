#!/usr/bin/env python3
"""Crawler-trap guards, URL hygiene, soft-404 probing and crawl sampling.

Naive crawlers die in three places, and all three are handled here:

  1. Infinite crawlable space. Faceted navigation, calendar widgets and
     page-builder pagination generate unbounded distinct URLs that all render
     roughly the same page. We refuse them by pattern before fetching.
  2. Servers that answer 200 for URLs that cannot exist. A site like that has
     no bottom; every 404 becomes a new page to crawl. We detect it after the
     crawl with probe URLs and compare against a known-good 404 body.
  3. Malformed hrefs. Street addresses, bare emails and phone numbers pasted
     into href attributes become phantom URLs that inflate a report with
     findings about pages that were never real. We classify and drop them, and
     report them separately as a link-hygiene observation.

Standard library only. Nothing here performs I/O; callers do the fetching.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
import urllib.parse
from dataclasses import dataclass

__all__ = [
    "normalise_url",
    "classify_href",
    "trap_reason",
    "probe_urls",
    "is_soft_404",
    "stratified_sample",
    "HrefClass",
]

# Query parameters that generate combinatorial URL space without new content.
FACET_PARAMS = frozenset(
    {
        "filter", "filters", "facet", "refine", "refinement", "sort", "sortby", "orderby", "order",
        "colour", "color", "size", "brand", "price", "price_min", "price_max", "min_price", "max_price",
        "rating", "availability", "view", "layout", "display", "columns", "per_page", "perpage",
        "limit", "offset", "start", "from", "cursor", "sid", "sessionid", "session_id", "phpsessid",
        "replytocom", "share", "print", "amp",
    }
)

TRACKING_PARAM_RE = re.compile(r"^(utm_|ga_|gclid|fbclid|msclkid|mc_|ref|referrer|source)", re.I)

# Path prefixes and fragments that are never a content page.
NON_PAGE_PATTERNS = [
    (re.compile(r"/feed/?$|/rss/?$|/atom/?$|/feed\.xml$", re.I), "feed_endpoint"),
    (re.compile(r"/wp-json/|/wp-admin/|/wp-includes/|/xmlrpc\.php", re.I), "wordpress_infrastructure"),
    (re.compile(r"/wp-content/uploads/", re.I), "uploads_directory"),
    (re.compile(r"[?&]wc-ajax=", re.I), "woocommerce_ajax"),
    (re.compile(r"[?&]add-to-cart=", re.I), "cart_mutation_endpoint"),
    (re.compile(r"/cart/?$|/checkout|/basket/?$|/order-received", re.I), "cart_or_checkout"),
    (re.compile(r"/wishlist|/compare/?$", re.I), "session_scoped_list"),
    (re.compile(r"/(login|signin|sign-in|logout|signout|register|my-account|account/)", re.I), "authenticated_area"),
    (re.compile(r"/admin(/|$)|/administrator(/|$)|/cpanel", re.I), "admin_area"),
    (re.compile(r"/cgi-bin/|/\.git/|/\.env$", re.I), "non_page_path"),
    (re.compile(r"/(20\d{2})/(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/?$", re.I), "date_archive_leaf"),
    (re.compile(r"/tag/|/tags/|/author/|/category/page/", re.I), "taxonomy_pagination"),
    (re.compile(r"/search/?$|[?&](q|s|query|keyword)=", re.I), "search_results"),
]

NON_HTML_EXT = frozenset(
    """.jpg .jpeg .png .gif .webp .avif .svg .ico .bmp .tiff
       .css .js .mjs .map .json .xml .txt .csv .tsv
       .pdf .doc .docx .xls .xlsx .ppt .pptx .odt .rtf
       .zip .gz .tar .rar .7z .dmg .exe .msi .apk
       .mp3 .mp4 .avi .mov .wmv .webm .ogg .wav .m4a
       .woff .woff2 .ttf .eot .otf""".split()
)

MAX_PATH_DEPTH = 8
MAX_QUERY_PARAMS = 3
MAX_PAGINATION = 3

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[+()\d][\d\s()+.-]{6,}$")
# A street address pasted into href: commas plus spaces plus no scheme.
ADDRESS_RE = re.compile(r"^[^/:?#]*[,]\s*\S+.*$")


@dataclass(frozen=True)
class HrefClass:
    kind: str  # internal | external | malformed | non_http | fragment
    url: str | None
    reason: str | None = None


def normalise_url(href: str, base: str) -> str | None:
    """Resolve and canonicalise a URL for de-duplication.

    Drops the fragment, strips tracking parameters, lowercases scheme and host,
    removes a default port, collapses `.` and `..`, and sorts remaining query
    parameters so that two orderings of the same query are one URL.
    """
    try:
        joined = urllib.parse.urljoin(base, href.strip())
        parts = urllib.parse.urlsplit(joined)
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https"):
        return None

    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if not host:
        return None
    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        host = f"{host}:{port}"

    path = posixpath.normpath(parts.path or "/")
    if parts.path.endswith("/") and not path.endswith("/"):
        path += "/"
    if not path.startswith("/"):
        path = "/" + path

    kept = []
    for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True):
        if TRACKING_PARAM_RE.match(key):
            continue
        kept.append((key, value))
    query = urllib.parse.urlencode(sorted(kept))

    return urllib.parse.urlunsplit((scheme, host, path, query, ""))


def classify_href(href: str, base: str, origin_host: str) -> HrefClass:
    """Sort one raw href into internal, external, malformed, non-http or fragment.

    Malformed hrefs are the interesting case: a street address or bare email in
    an href is a real authoring defect, but treating it as a URL would invent a
    page that does not exist and pollute every downstream count.
    """
    raw = (href or "").strip()
    if not raw or raw == "#":
        return HrefClass("fragment", None, "empty or bare fragment")
    if raw.startswith("#"):
        return HrefClass("fragment", None, "in-page anchor")

    lowered = raw.lower()
    for scheme in ("javascript:", "data:", "vbscript:", "about:"):
        if lowered.startswith(scheme):
            return HrefClass("non_http", None, f"{scheme.rstrip(':')} scheme")
    if lowered.startswith(("mailto:", "tel:", "sms:", "callto:", "ftp:", "file:")):
        return HrefClass("non_http", None, f"{lowered.split(':', 1)[0]} scheme")

    if "://" not in raw and not raw.startswith("/"):
        if EMAIL_RE.match(raw):
            return HrefClass("malformed", None, "bare email address in href, missing mailto:")
        if PHONE_RE.match(raw):
            return HrefClass("malformed", None, "bare phone number in href, missing tel:")
        if " " in raw and ADDRESS_RE.match(raw) and "." not in raw.split(",")[0]:
            return HrefClass("malformed", None, "plain text (looks like a postal address) in href")

    url = normalise_url(raw, base)
    if url is None:
        return HrefClass("malformed", None, "href does not resolve to an http(s) URL")
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host == origin_host or host.endswith("." + origin_host):
        return HrefClass("internal", url)
    return HrefClass("external", url)


def trap_reason(url: str) -> str | None:
    """Return the trap rule this URL trips, or None if it is safe to fetch."""
    parts = urllib.parse.urlsplit(url)
    path = parts.path or "/"
    lowered_path = path.lower()

    ext = posixpath.splitext(lowered_path)[1]
    if ext in NON_HTML_EXT:
        return f"non_html_extension:{ext}"

    segments = [s for s in path.split("/") if s]
    if len(segments) > MAX_PATH_DEPTH:
        return f"excessive_depth:{len(segments)}"

    lowered_segments = [s.lower() for s in segments]
    for i in range(len(lowered_segments) - 1):
        if lowered_segments[i] == lowered_segments[i + 1]:
            return f"repeating_segment:/{lowered_segments[i]}/{lowered_segments[i]}/"
    for seg in set(lowered_segments):
        if lowered_segments.count(seg) >= 3:
            return f"repeating_segment:{seg} appears {lowered_segments.count(seg)} times"

    m = re.search(r"/page/(\d+)", lowered_path)
    if m and int(m.group(1)) > MAX_PAGINATION:
        return f"deep_pagination:/page/{m.group(1)}"

    for pattern, label in NON_PAGE_PATTERNS:
        if pattern.search(url):
            return label

    params = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    if len(params) > MAX_QUERY_PARAMS:
        return f"excessive_query_params:{len(params)}"
    for key, value in params:
        if key.lower() in FACET_PARAMS:
            if key.lower() in ("page", "paged", "p") and value.isdigit() and int(value) <= MAX_PAGINATION:
                continue
            return f"faceted_param:{key}"
    for key, value in params:
        if key.lower() in ("page", "paged", "p") and value.isdigit() and int(value) > MAX_PAGINATION:
            return f"deep_pagination:{key}={value}"

    return None


def probe_urls(origin: str, count: int = 3) -> list[str]:
    """Deterministic URLs that cannot legitimately exist.

    Derived from a hash of the origin so they are stable across runs (a random
    probe would break byte-identical determinism) but unlikely to collide with
    a real path.
    """
    digest = hashlib.sha256(origin.encode("utf-8")).hexdigest()
    out = []
    for i in range(count):
        token = digest[i * 8 : i * 8 + 8]
        out.append(urllib.parse.urljoin(origin, f"/audit-probe-{token}-does-not-exist/"))
    return out


def is_soft_404(probe_status: int, probe_body: str, known_404_body: str | None) -> tuple[bool, str]:
    """Decide whether a 200 for an impossible URL is a genuine soft 404.

    A site that serves a styled "not found" page with status 200 is a real
    finding: it creates unbounded crawlable space. But a site whose probe body
    is byte-identical to its real 404 body is only using the wrong status code,
    which is a lesser problem, so we say so rather than overstating it.
    """
    if probe_status != 200:
        return False, f"probe returned {probe_status}, which is correct"
    if known_404_body is not None and probe_body.strip() == known_404_body.strip():
        return True, "probe body is identical to the real 404 body; only the status code is wrong"
    return True, "probe URL returned 200 with content, creating unbounded crawlable space"


def stratified_sample(
    candidates: list[dict],
    cap: int,
    min_types_for_stratification: int = 3,
    max_share: float = 0.4,
) -> tuple[list[dict], str]:
    """Choose which discovered URLs to crawl.

    Two strategies, and which one ran is returned so it can be recorded in the
    evidence bundle:

      * Stratified, when at least `min_types_for_stratification` distinct
        provisional page types are present. Round-robins across types and caps
        any single type at `max_share` of the budget, so a site with 400 blog
        posts and 6 product pages does not produce an audit of 25 blog posts.

      * Prominence, otherwise. A cap of 40% cannot bind on a single-archetype
        site, so stratifying a 25-page blog would starve it of nothing and add
        nondeterminism for no gain. Instead we sort by crawl depth ascending
        then inbound internal link count descending, which surfaces the pages
        the site itself treats as important.

    Ordering is fully deterministic: every sort ends with the URL as tiebreak.
    """
    if not candidates:
        return [], "empty"

    types = {c.get("provisional_type") or "unknown" for c in candidates}
    if len(types) >= min_types_for_stratification:
        buckets: dict[str, list[dict]] = {}
        for c in candidates:
            buckets.setdefault(c.get("provisional_type") or "unknown", []).append(c)
        for key in buckets:
            buckets[key].sort(key=lambda c: (c.get("depth", 99), -c.get("inlinks", 0), c["url"]))

        per_type_cap = max(1, int(cap * max_share))
        selected: list[dict] = []
        order = sorted(buckets)
        cursor = {k: 0 for k in order}
        while len(selected) < cap:
            progressed = False
            for key in order:
                if len(selected) >= cap:
                    break
                idx = cursor[key]
                if idx >= len(buckets[key]) or idx >= per_type_cap:
                    continue
                selected.append(buckets[key][idx])
                cursor[key] += 1
                progressed = True
            if not progressed:
                break
        # If per-type caps left budget unspent, backfill by prominence.
        if len(selected) < cap:
            chosen = {c["url"] for c in selected}
            rest = [c for c in candidates if c["url"] not in chosen]
            rest.sort(key=lambda c: (c.get("depth", 99), -c.get("inlinks", 0), c["url"]))
            selected.extend(rest[: cap - len(selected)])
        selected.sort(key=lambda c: c["url"])
        return selected, f"stratified:{len(types)}_types"

    ordered = sorted(candidates, key=lambda c: (c.get("depth", 99), -c.get("inlinks", 0), c["url"]))
    selected = ordered[:cap]
    selected.sort(key=lambda c: c["url"])
    return selected, f"prominence:{len(types)}_type"
