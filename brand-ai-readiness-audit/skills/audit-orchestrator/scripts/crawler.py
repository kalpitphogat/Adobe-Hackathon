#!/usr/bin/env python3
"""
Crawl a site politely and build the shared cache the sub-audits read.

  python crawler.py <site> <cache_dir> [--max-pages N] [--render]

Respects robots.txt (a disallowed URL is recorded, never requested), stays
on-host, samples up to --max-pages resources, honours any Crawl-delay, and
optionally renders each page with Playwright to enable the static-vs-rendered
fact-gap check. Read-only: GET/HEAD only, no forms, no auth, no state change.

Every fetched resource is classified (HTML / XML / JSON / image / PDF / other)
and, when it is HTML, given a page role. Sub-audits filter on that metadata so
HTML-only checks never run against a sitemap or an API endpoint.
"""
import argparse
import collections
import json
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auditlib as A  # noqa: E402

# User-agents we report allow/deny status for, split by what blocking one actually
# costs. Presence in either list is not a claim that a given assistant uses a given
# agent; it is how the operators document them.
#
# CITATION_FETCHERS are documented as fetching pages so an assistant can answer or
# cite. Blocking them is what removes a site from those answers.
CITATION_FETCHERS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot",
                     "Claude-Web", "anthropic-ai", "PerplexityBot", "Google-Extended",
                     "Applebot-Extended"]
# BULK_CRAWLERS gather corpora rather than serve a live query. Blocking them is a
# common and deliberate licensing choice with no effect on being cited at query time.
BULK_CRAWLERS = ["CCBot", "Bytespider"]
AI_BOTS = CITATION_FETCHERS + BULK_CRAWLERS

GPTBOT_UA = "Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122 Safari/537.36")

# Bounds for the homepage broken-link sweep, so one slow host cannot consume the
# whole runtime budget.
LINK_SWEEP_MAX = 15
LINK_SWEEP_BUDGET_S = 45
LINK_SWEEP_TIMEOUT_S = 8

# <link rel> values a browser actually fetches. Everything else (profile,
# canonical, alternate, author, pingback, EditURI, ...) is metadata, not a load.
FETCHED_LINK_REL = re.compile(
    r"\b(?:stylesheet|icon|apple-touch-icon|mask-icon|manifest|preload"
    r"|modulepreload|prefetch)\b", re.IGNORECASE)

PRICE_RE = re.compile(r"(?:[$€£¥]\s?\d|(?:\d+(?:[.,]\d{2})?)\s?"
                      r"(?:USD|EUR|GBP|INR)\b|\bper month\b|\b/mo\b)", re.I)


def discover_sitemaps(site, robots_txt, max_urls):
    """Return (sitemap_urls_found, page_urls, notes) from robots.txt + /sitemap.xml.

    A sitemap index is followed one level so nested sitemaps still yield URLs.
    Sitemaps are a discovery mechanism here; they are never added to the page
    sample as if they were content pages.
    """
    candidates = []
    for line in (robots_txt or "").splitlines():
        if line.lower().startswith("sitemap:"):
            # The directive is meant to be an absolute URL, but sites publish
            # relative ones; resolve against the site root rather than crashing.
            candidates.append(A.absolutize(site + "/", line.split(":", 1)[1].strip()))
    from_robots = list(dict.fromkeys(candidates))
    candidates.append(site + "/sitemap.xml")

    urls, sitemaps, notes = [], [], []
    queue = list(dict.fromkeys(candidates))
    seen_sm = set()
    while queue and len(urls) < max_urls and len(seen_sm) < 6:
        sm = queue.pop(0)
        if sm in seen_sm:
            continue
        seen_sm.add(sm)
        r = A.fetch(sm)
        body = r["body"] or ""
        if r["status"] != 200:
            continue
        if "<sitemapindex" in body:
            sitemaps.append(sm)
            nested = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)[:5]
            queue.extend(nested)
            notes.append(f"{sm} is a sitemap index ({len(nested)} nested sitemaps sampled)")
        elif "<urlset" in body:
            sitemaps.append(sm)
            for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body):
                # <loc> should be absolute; absolutize against the sitemap's own
                # URL so a relative entry still resolves instead of being dropped.
                urls.append(A.absolutize(sm, loc.strip()))
    return sitemaps, urls[:max_urls], {"from_robots": from_robots, "notes": notes}


def _find_chromium():
    """Locate a Chromium executable: explicit env var, or scan PLAYWRIGHT_BROWSERS_PATH."""
    exe = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if exe and os.path.exists(exe):
        return exe
    import glob
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    for pat in ("chromium-*/chrome-linux/chrome",
                "chromium_headless_shell-*/chrome-linux/headless_shell"):
        hits = sorted(glob.glob(os.path.join(base, pat))) if base else []
        if hits:
            return hits[-1]
    return None


def try_render(url):
    """Return rendered visible text via Playwright, or None if unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    try:
        with sync_playwright() as pw:
            exe = _find_chromium()
            launch = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if exe:
                launch["executable_path"] = exe
            browser = pw.chromium.launch(**launch)
            try:
                page = browser.new_page(user_agent=A.DEFAULT_UA)
                page.goto(url, wait_until="networkidle", timeout=20000)
                return page.evaluate("() => document.body ? document.body.innerText : ''")
            finally:
                browser.close()  # always close, even if goto()/evaluate() raised
    except Exception:
        return None


def ldjson_types(parsed):
    """schema.org @type values declared on the page, flattened."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            v = o.get("@type")
            if isinstance(v, list):
                out.extend(str(x) for x in v)
            elif v:
                out.append(str(v))
            for key in ("@graph", "mainEntity", "itemListElement"):
                sub = o.get(key)
                if isinstance(sub, list):
                    for s in sub:
                        walk(s)
                elif isinstance(sub, dict):
                    walk(sub)
        elif isinstance(o, list):
            for s in o:
                walk(s)

    for block in parsed.ldjson:
        try:
            walk(json.loads(block.strip()))
        except Exception:
            continue
    return out


def build_record(site, url, r, parsed, cls, robots_blocked=False):
    """Assemble the per-resource metadata record every sub-audit reads."""
    body = r.get("body") or ""
    internal = external = 0
    for href in parsed.links:
        absu = A.absolutize(url, href)
        if absu.startswith(("mailto:", "tel:", "javascript:")):
            continue
        if A.same_host(site, absu):
            internal += 1
        elif absu.startswith("http"):
            external += 1

    text = parsed.visible_text
    text_len = len(text)
    link_text_ratio = round(parsed.link_text_len / text_len, 3) if text_len else None
    heading_texts = [t for _, t in parsed.headings]
    schema_types = ldjson_types(parsed) if cls["is_html"] else []

    # Mixed content = insecure SUB-RESOURCES the browser actually loads on a secure
    # page. Two things are deliberately NOT counted: an <a href="http://"> to
    # another site, which is an ordinary outbound link; and a <link> whose rel is
    # metadata rather than a fetch - rel="profile" carries an RDFa vocabulary
    # identifier, not a resource, and counting it flagged every page of a site that
    # loads nothing insecurely at all.
    mixed = 0
    if site.startswith("https://") and body:
        mixed = len(re.findall(
            r"<(?:script|img|iframe|source|track|embed|audio|video)\b[^>]*\bsrc\s*=\s*"
            r"[\"']http://", body, re.I))
        for lm in re.finditer(r"<link\b[^>]*>", body, re.I):
            tag = lm.group(0)
            if not re.search(r"\bhref\s*=\s*[\"']http://", tag, re.I):
                continue
            rel_m = re.search(r"\brel\s*=\s*[\"']([^\"']*)", tag, re.I)
            if FETCHED_LINK_REL.search(rel_m.group(1) if rel_m else ""):
                mixed += 1

    rec = {
        "url": url,
        "final_url": r.get("final_url") or url,
        "slug": A.slug(url),
        "status": r.get("status"),
        "error": r.get("error"),
        "bytes": r.get("bytes", 0),
        "truncated": r.get("truncated", False),
        "elapsed_ms": r.get("elapsed_ms", 0),
        "robots_blocked": robots_blocked,
        "content_type": (r.get("headers") or {}).get("content-type", ""),
        "x_robots_tag": (r.get("headers") or {}).get("x-robots-tag", ""),
        # resource classification
        "resource_kind": cls["resource_kind"],
        "is_html": cls["is_html"],
        "useful_for_page_audit": cls["useful_for_page_audit"],
        "classification_basis": cls["classification_basis"],
    }

    if not cls["is_html"]:
        if cls["resource_kind"] == "offsite_redirect":
            rec["redirected_to"] = r.get("final_url")
        # Non-HTML resources get no page-level metrics at all: recording zeros for
        # H1s or viewport on an XML sitemap is exactly how a sitemap turns into a
        # fake page defect.
        rec["page_role"] = "resource"
        rec["page_role_confidence"] = "high"
        rec["page_role_basis"] = f"non-HTML resource ({cls['resource_kind']})"
        return rec

    rec.update({
        "title": parsed.title.strip(),
        "canonical": parsed.canonical,
        "html_lang": parsed.html_lang,
        "has_viewport": parsed.has_viewport,
        "meta_description": parsed.meta_description,
        "meta_robots": parsed.meta_robots,
        "og_keys": sorted(set(parsed.og_keys)),
        "n_headings": len(parsed.headings),
        "n_h1": sum(1 for lvl, _ in parsed.headings if lvl == 1),
        "heading_levels": [lvl for lvl, _ in parsed.headings],
        "headings": heading_texts[:40],
        "n_question_headings": sum(1 for _, t in parsed.headings if t.strip().endswith("?")),
        "n_links": len(parsed.links),
        "n_internal_links": internal,
        "n_external_links": external,
        "nav_link_count": parsed.nav_link_count,
        "link_text_ratio": link_text_ratio,
        "n_imgs": len(parsed.imgs),
        "n_imgs_no_alt": sum(1 for im in parsed.imgs if im.get("alt") is None),
        "n_imgs_empty_alt": sum(1 for im in parsed.imgs
                                if (im.get("alt") or "").strip() == "" and im.get("alt") is not None),
        # An image is treated as potentially informational only when it sits in
        # the content area, is not marked decorative, and is not icon-sized.
        "n_content_imgs": sum(1 for im in parsed.imgs
                              if im.get("in_content") and not im.get("role_presentation")
                              and not ((im.get("w") or 999) <= 64 and (im.get("h") or 999) <= 64)),
        "n_content_imgs_no_alt": sum(1 for im in parsed.imgs
                                     if im.get("in_content") and not im.get("role_presentation")
                                     and not ((im.get("w") or 999) <= 64 and (im.get("h") or 999) <= 64)
                                     and im.get("alt") is None),
        "n_ldjson_blocks": len(parsed.ldjson),
        "schema_types": sorted(set(schema_types)),
        "text_len": text_len,
        "n_mixed_content": mixed,
        "n_lists_content": parsed.n_lists_content,
        "n_lists_total": parsed.n_lists_total,
        "n_tables": parsed.n_tables,
        "n_iframes": parsed.n_iframes,
        "n_forms": parsed.n_forms,
        "n_inputs": parsed.n_inputs,
        "n_password_inputs": parsed.n_password_inputs,
        "n_buttons": parsed.n_buttons,
        "n_selects": parsed.n_selects,
        "n_mailto": parsed.n_mailto,
        "n_tel": parsed.n_tel,
        "n_time_elements": parsed.n_time_elements,
        "time_datetimes": parsed.time_datetimes[:10],
        "n_code_blocks": parsed.n_code_blocks,
        "has_header": parsed.has_header,
        "has_footer": parsed.has_footer,
        "has_nav": parsed.has_nav,
        "has_main": parsed.has_main,
        "media": parsed.media[:10],
        # hidden-content evidence, split so UI chrome is not mistaken for cloaking
        "hidden_text_len": parsed.hidden_text_len,
        "hidden_ui_text_len": parsed.hidden_ui_text_len,
        "n_hidden_blocks": parsed.n_hidden_blocks,
        "n_hidden_ui_blocks": parsed.n_hidden_ui_blocks,
        "has_price": bool(PRICE_RE.search(text[:20000])),
    })

    role, conf = A.classify_page_role({
        "url": url, "site": site, "title": rec["title"], "headings": heading_texts,
        "text_len": text_len, "schema_types": rec["schema_types"],
        "n_forms": rec["n_forms"], "n_password_inputs": rec["n_password_inputs"],
        "n_inputs": rec["n_inputs"], "n_buttons": rec["n_buttons"],
        "n_selects": rec["n_selects"], "n_links": rec["n_links"],
        "link_text_ratio": link_text_ratio, "n_time_elements": rec["n_time_elements"],
        "n_code_blocks": rec["n_code_blocks"], "has_price": rec["has_price"],
        "n_mailto": rec["n_mailto"], "n_tel": rec["n_tel"],
    })
    rec["page_role"] = role
    rec["page_role_confidence"] = conf
    return rec


def blocked_record(site, url):
    cls = A.classify_resource(robots_blocked=True)
    return {
        "url": url, "final_url": url, "slug": A.slug(url), "status": None,
        "error": "robots_disallow", "bytes": 0, "truncated": False, "elapsed_ms": 0,
        "robots_blocked": True, "content_type": "", "x_robots_tag": "",
        "resource_kind": cls["resource_kind"], "is_html": False,
        "useful_for_page_audit": False,
        "classification_basis": cls["classification_basis"],
        "page_role": "resource", "page_role_confidence": "high",
        "page_role_basis": "disallowed by robots.txt; never requested",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("cache_dir")
    ap.add_argument("--max-pages", type=int, default=12)
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()

    max_pages = max(1, min(args.max_pages, 100))   # hard bound: never an infinite crawl
    requested_site = A.normalize_site(args.site)
    site = requested_site
    os.makedirs(os.path.join(args.cache_dir, "pages"), exist_ok=True)

    # ---- follow a site-level move ------------------------------------------ #
    # A brand that has changed domain answers its old address with an off-host
    # redirect. Auditing the old host would yield one redirect record and nothing
    # else, so the audit re-bases on where the site actually lives now and records
    # the move. Everything after this point - robots.txt included - is fetched
    # from the resolved host.
    site_moved_to = None
    home_probe = A.fetch(site + "/")
    final = home_probe.get("final_url") or ""
    if home_probe["status"] and home_probe["status"] < 400 and final             and not A.same_host(site, final):
        parts = urllib.parse.urlparse(final)
        if parts.scheme in ("http", "https") and parts.netloc:
            site_moved_to = f"{parts.scheme}://{parts.netloc}"
            site = A.normalize_site(site_moved_to)
    host = urllib.parse.urlparse(site).netloc

    # ---- robots.txt -------------------------------------------------------- #
    robots = A.fetch(site + "/robots.txt")
    robots_txt = robots["body"] if robots["status"] == 200 else ""
    rp = A.Robots(robots_txt)

    crawl_delay = A.MIN_DELAY_S
    try:
        cd = rp.crawl_delay(A.DEFAULT_UA)
        if cd:
            crawl_delay = max(A.MIN_DELAY_S, min(float(cd), 5.0))
    except Exception:
        pass

    def allowed(url, ua=A.DEFAULT_UA):
        if not robots_txt:
            return True
        try:
            return rp.can_fetch(ua, url)
        except Exception:
            return True

    # Per-bot allow/deny. Records both whether the site ROOT is reachable and the
    # Disallow patterns that apply, so the access audit can say what is blocked
    # rather than only that something is.
    ai_bot_status, ai_bot_blocked_paths, ai_bot_path_rules = {}, {}, {}
    for bot in AI_BOTS:
        root_ok = (not robots_txt) or rp.can_fetch(bot, site + "/")
        ai_bot_status[bot] = "allowed" if root_ok else "blocked"
        if not root_ok:
            ai_bot_blocked_paths[bot] = ["/"]
        elif robots_txt:
            patterns = rp.disallowed_prefixes(bot)
            if patterns:
                # The root is reachable but some paths are not. Recorded as
                # context; a partial restriction is not a site-level block.
                ai_bot_path_rules[bot] = patterns

    llms = A.fetch(site + "/llms.txt")
    llms_txt = {"present": llms["status"] == 200 and "<html" not in llms["body"][:500].lower(),
                "status": llms["status"]}

    # ---- edge reachability probe ------------------------------------------ #
    # robots.txt may allow an AI crawler while a WAF/CDN still refuses its
    # User-Agent. Probe twice and require a refusal STATUS, not merely an error,
    # so one transient timeout cannot manufacture a critical finding.
    ai_probe = A.fetch(site + "/", ua=GPTBOT_UA)
    ref_probe = A.fetch(site + "/", ua=BROWSER_UA)
    refusal = (401, 403, 406, 429, 451)
    edge_blocked = ref_probe["status"] == 200 and ai_probe["status"] in refusal
    if ref_probe["status"] == 200 and ai_probe["status"] is None:
        # retry once before concluding anything from a network-level failure
        ai_probe = A.fetch(site + "/", ua=GPTBOT_UA)
        edge_blocked = ai_probe["status"] in refusal
    ai_bot_reachability = {
        "ua": "GPTBot",
        "ai_status": ai_probe["status"],
        "ai_error": ai_probe["error"],
        "reference_status": ref_probe["status"],
        "blocked": bool(edge_blocked),
        "inconclusive": ref_probe["status"] == 200 and ai_probe["status"] is None,
    }

    # ---- sitemap discovery ------------------------------------------------- #
    sitemaps, sm_urls, sm_info = discover_sitemaps(site, robots_txt, max_pages * 4)

    # ---- BFS crawl --------------------------------------------------------- #
    queue = collections.deque([site + "/"])
    for u in [u for u in sm_urls if A.same_host(site, u)]:
        queue.append(u)

    seen, pages, homepage_links = set(), [], []
    fetch_errors = []
    while queue and len(pages) < max_pages:
        url = queue.popleft().split("#")[0]
        if url in seen or not url.startswith("http") or not A.same_host(site, url):
            continue
        seen.add(url)

        if not allowed(url):
            # Respect robots.txt: never request a disallowed URL. Record it as
            # blocked - that is what crawl-access-audit reports on.
            pages.append(blocked_record(site, url))
            continue

        r = A.fetch(url, delay=crawl_delay)
        if r["error"] and r["status"] is None:
            fetch_errors.append({"url": url, "error": r["error"][:200]})
        # A response answered by a different host is that host's content, not this
        # site's page. Blanking the body is not enough: it must also stop being
        # classified as an HTML page, or it surfaces as a page with no title and
        # no viewport.
        offsite = bool(r["final_url"]) and not A.same_host(site, r["final_url"])
        if offsite:
            r = {**r, "body": "", "bytes": 0}

        cls = A.classify_resource(r["status"], (r["headers"] or {}).get("content-type", ""),
                                  url, r["body"], r["error"], offsite_redirect=offsite)
        parsed = A.parse_html(r["body"]) if (cls["is_html"] and r["body"]) else A.parse_html("")
        rec = build_record(site, url, r, parsed, cls)

        sl = rec["slug"]
        if r["body"]:
            with open(os.path.join(args.cache_dir, "pages", sl + ".html"), "w",
                      encoding="utf-8") as f:
                f.write(r["body"])
        if cls["is_html"]:
            with open(os.path.join(args.cache_dir, "pages", sl + ".txt"), "w",
                      encoding="utf-8") as f:
                f.write(parsed.visible_text)

        if args.render and cls["is_html"] and r["status"] == 200:
            rendered = try_render(url)
            rec["rendered"] = rendered is not None
            if rendered is not None:
                rec["rendered_len"] = len(rendered)
                with open(os.path.join(args.cache_dir, "pages", sl + ".rendered.txt"), "w",
                          encoding="utf-8") as f:
                    f.write(rendered)

        pages.append(rec)

        # Homepage links feed the broken-link sweep; early pages broaden the sample.
        if cls["is_html"] and r["body"]:
            is_home = A.is_homepage_url(site, url)
            if is_home:
                for href in parsed.links:
                    nu = A.absolutize(url, href).split("#")[0]
                    if A.same_host(site, nu) and nu.startswith("http"):
                        homepage_links.append(nu)
            if len(pages) <= 3:
                for href in parsed.links:
                    nu = A.absolutize(url, href).split("#")[0]
                    if A.same_host(site, nu) and nu not in seen and nu.startswith("http"):
                        queue.append(nu)

    # ---- bounded broken-internal-link sweep -------------------------------- #
    # Bounded twice over: at most LINK_SWEEP_MAX URLs, and a wall-clock budget for
    # the whole sweep. A host that is slow to answer HEAD could otherwise stack
    # fifteen timeouts and push a single site past the runtime budget on its own.
    link_check, sweep_truncated = [], False
    sweep_deadline = time.time() + LINK_SWEEP_BUDGET_S
    candidates = list(dict.fromkeys(homepage_links))[:LINK_SWEEP_MAX]
    for lu in candidates:
        if time.time() > sweep_deadline:
            sweep_truncated = True
            break
        if not allowed(lu):
            continue
        hr = A.fetch(lu, method="HEAD", delay=crawl_delay, timeout=LINK_SWEEP_TIMEOUT_S)
        st, err = hr["status"], hr["error"]
        if st is None or st >= 400:      # some servers reject HEAD; confirm with GET
            hr = A.fetch(lu, method="GET", delay=crawl_delay, timeout=LINK_SWEEP_TIMEOUT_S)
            st, err = hr["status"], hr["error"]
        link_check.append({"url": lu, "status": st,
                           "error": None if st else (err or "")[:120]})

    # How much of what we actually sampled each AI user-agent may fetch. A site can
    # allow the root while disallowing the content beneath it, which a root-only
    # check would miss entirely. Uses the URLs already discovered - no extra requests.
    sampled_urls = [p["url"] for p in pages]
    ai_bot_sample_access = {}
    if robots_txt and sampled_urls:
        for bot in AI_BOTS:
            allowed_n = sum(1 for u in sampled_urls if rp.can_fetch(bot, u))
            ai_bot_sample_access[bot] = {"allowed": allowed_n, "sampled": len(sampled_urls)}

    html_count = sum(1 for p in pages if p.get("is_html"))
    reachable = sum(1 for p in pages if p.get("status"))
    if html_count:
        crawl_status = "ok" if len(pages) >= min(3, max_pages) else "partial"
    elif reachable:
        crawl_status = "partial"          # something responded, but no HTML page
    else:
        crawl_status = "failed"

    meta = {
        "site": site,
        "host": host,
        "requested_site": requested_site,
        "site_moved_to": site_moved_to,
        "crawl_status": crawl_status,
        "max_pages": max_pages,
        "crawl_delay_s": crawl_delay,
        "robots": {
            "present": robots["status"] == 200,
            "status": robots["status"],
            "text": robots_txt[:20000],
            "ai_bots": ai_bot_status,
            "ai_bot_blocked_paths": ai_bot_blocked_paths,
            "ai_bot_path_rules": ai_bot_path_rules,
            "ai_bot_sample_access": ai_bot_sample_access,
            "citation_fetchers": CITATION_FETCHERS,
            "bulk_crawlers": BULK_CRAWLERS,
        },
        "llms_txt": llms_txt,
        "ai_bot_reachability": ai_bot_reachability,
        "sitemaps": sitemaps,
        "sitemap_info": sm_info,
        "sitemap_url_count": len(sm_urls),
        "link_check": link_check,
        "link_check_truncated": sweep_truncated,
        "link_check_candidates": len(candidates),
        "fetch_errors": fetch_errors,
        "render_enabled": args.render,
        "render_available": any(p.get("rendered") for p in pages),
        "pages": pages,
        "pages_crawled": len(pages),
        "html_pages": html_count,
        "non_html_resources": len(pages) - html_count,
        "resource_kinds": {k: sum(1 for p in pages if p.get("resource_kind") == k)
                           for k in sorted({p.get("resource_kind", "other") for p in pages})},
        "page_roles": A.role_histogram([p for p in pages if p.get("is_html")]),
    }
    with open(os.path.join(args.cache_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"crawled {len(pages)} resources ({html_count} HTML) -> {args.cache_dir} "
          f"[{crawl_status}]", file=sys.stderr)


if __name__ == "__main__":
    main()
