#!/usr/bin/env python3
"""
Crawl a site politely and build the shared cache the sub-audits read.

  python crawler.py <site> <cache_dir> [--max-pages N] [--render]

Respects robots.txt, stays on-host, samples up to --max-pages pages (default 12),
and optionally renders each page with Playwright (headless Chromium) to enable the
static-vs-rendered fact-gap check. Read-only: GET only, no forms, no auth.
"""
import argparse
import collections
import json
import os
import re
import sys
import urllib.parse
import urllib.robotparser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auditlib as A  # noqa: E402


def discover_from_sitemap(site, robots_txt):
    """Return (sitemap_urls_found, page_urls) from sitemap.xml if reachable."""
    candidates = []
    for line in (robots_txt or "").splitlines():
        if line.lower().startswith("sitemap:"):
            candidates.append(line.split(":", 1)[1].strip())
    candidates.append(site + "/sitemap.xml")
    urls, sitemaps = [], []
    for sm in dict.fromkeys(candidates):
        r = A.fetch(sm)
        if r["status"] == 200 and ("<urlset" in r["body"] or "<sitemapindex" in r["body"]):
            sitemaps.append(sm)
            import re
            for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r["body"]):
                urls.append(loc.strip())
    return sitemaps, urls


def _find_chromium():
    """Locate a Chromium executable: explicit env var, or scan PLAYWRIGHT_BROWSERS_PATH."""
    exe = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if exe and os.path.exists(exe):
        return exe
    import glob
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    for pat in ("chromium-*/chrome-linux/chrome", "chromium_headless_shell-*/chrome-linux/headless_shell"):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("cache_dir")
    ap.add_argument("--max-pages", type=int, default=12)
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()

    site = A.normalize_site(args.site)
    host = urllib.parse.urlparse(site).netloc
    os.makedirs(os.path.join(args.cache_dir, "pages"), exist_ok=True)

    # robots.txt
    robots = A.fetch(site + "/robots.txt")
    robots_txt = robots["body"] if robots["status"] == 200 else ""
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots_txt.splitlines())

    def allowed(url, ua=A.DEFAULT_UA):
        if not robots_txt:
            return True
        try:
            return rp.can_fetch(ua, url)
        except Exception:
            return True

    # AI crawler directives (explicit allow/deny per bot)
    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-Web",
               "anthropic-ai", "PerplexityBot", "Google-Extended", "Applebot-Extended",
               "CCBot", "Bytespider"]
    ai_bot_status = {}
    for bot in ai_bots:
        rp_bot = urllib.robotparser.RobotFileParser()
        rp_bot.parse(robots_txt.splitlines())
        ai_bot_status[bot] = "allowed" if (not robots_txt or rp_bot.can_fetch(bot, site + "/")) else "blocked"

    # llms.txt discovery (emerging convention for AI-assistant guidance)
    llms = A.fetch(site + "/llms.txt")
    llms_txt = {"present": llms["status"] == 200 and "<html" not in llms["body"][:500].lower(),
                "status": llms["status"]}

    # Edge/CDN reachability: robots.txt may allow an AI crawler, but a WAF/CDN can still
    # block its User-Agent at the edge (403/challenge). Probe the homepage as GPTBot and
    # compare to a normal browser UA.
    GPTBOT_UA = "Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)"
    BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
    ai_probe = A.fetch(site + "/", ua=GPTBOT_UA)
    ref_probe = A.fetch(site + "/", ua=BROWSER_UA)
    ai_bot_reachability = {
        "ua": "GPTBot",
        "ai_status": ai_probe["status"],
        "reference_status": ref_probe["status"],
        # blocked = a normal browser is served but the AI bot UA is refused at the edge
        "blocked": ref_probe["status"] == 200
                   and (ai_probe["status"] in (401, 403, 406, 429, 451) or ai_probe["error"] is not None),
    }

    # sitemap discovery
    sitemaps, sm_urls = discover_from_sitemap(site, robots_txt)

    # Seed BFS from homepage; supplement with sitemap URLs
    queue = collections.deque([site + "/"])
    seen = set()
    seeded = [u for u in sm_urls if A.same_host(site, u)][:args.max_pages * 3]
    for u in seeded:
        queue.append(u)

    pages = []
    homepage_links = []
    while queue and len(pages) < args.max_pages:
        url = queue.popleft()
        url = url.split("#")[0]
        if url in seen:
            continue
        seen.add(url)
        if not A.same_host(site, url):
            continue
        blocked = not allowed(url)
        sl = A.slug(url)
        if blocked:
            # Respect robots.txt: never fetch a disallowed URL. Record it as blocked
            # (that is what crawl-access-audit reports on) without requesting the body.
            pages.append({
                "url": url, "slug": sl, "status": None, "error": "robots_disallow",
                "bytes": 0, "elapsed_ms": 0, "robots_blocked": True,
                "content_type": "", "x_robots_tag": "", "title": "", "canonical": None,
                "html_lang": None, "has_viewport": False, "n_headings": 0, "n_h1": 0,
                "n_links": 0, "n_imgs": 0, "n_imgs_no_alt": 0, "n_ldjson_blocks": 0,
                "text_len": 0, "n_mixed_content": 0,
                "heading_levels": [], "n_question_headings": 0, "n_lists": 0, "n_tables": 0,
            })
            continue
        r = A.fetch(url)
        # If the response redirected off-host, don't treat its body as this site's content.
        if r["final_url"] and not A.same_host(site, r["final_url"]):
            r = {**r, "body": "", "bytes": 0}
        parsed = A.parse_html(r["body"]) if r["body"] else A.parse_html("")
        rec = {
            "url": url,
            "slug": sl,
            "status": r["status"],
            "error": r["error"],
            "bytes": r["bytes"],
            "elapsed_ms": r["elapsed_ms"],
            "robots_blocked": blocked,
            "content_type": r["headers"].get("content-type", ""),
            "x_robots_tag": r["headers"].get("x-robots-tag", ""),
            "title": parsed.title.strip(),
            "canonical": parsed.canonical,
            "html_lang": parsed.html_lang,
            "has_viewport": parsed.has_viewport,
            "n_headings": len(parsed.headings),
            "n_h1": sum(1 for lvl, _ in parsed.headings if lvl == 1),
            "n_links": len(parsed.links),
            "n_imgs": len(parsed.imgs),
            "n_imgs_no_alt": sum(1 for im in parsed.imgs if not (im.get("alt") or "").strip()),
            "n_ldjson_blocks": len(parsed.ldjson),
            "text_len": len(parsed.visible_text),
            # mixed content: http:// sub-resources referenced from an https page
            "n_mixed_content": (len(re.findall(r'(?:src|href)=["\']http://', r["body"]))
                                if site.startswith("https://") and r["body"] else 0),
            # answer-formatting / chunkability signals
            "heading_levels": [lvl for lvl, _ in parsed.headings],
            "n_question_headings": sum(1 for _, t in parsed.headings if t.strip().endswith("?")),
            "n_lists": len(re.findall(r"<(?:ul|ol)\b", r["body"], re.I)) if r["body"] else 0,
            "n_tables": len(re.findall(r"<table\b", r["body"], re.I)) if r["body"] else 0,
        }
        # persist raw html + extracted text
        if r["body"]:
            with open(os.path.join(args.cache_dir, "pages", sl + ".html"), "w", encoding="utf-8") as f:
                f.write(r["body"])
        with open(os.path.join(args.cache_dir, "pages", sl + ".txt"), "w", encoding="utf-8") as f:
            f.write(parsed.visible_text)

        # optional render
        if args.render and r["status"] == 200:
            rendered = try_render(url)
            if rendered is not None:
                rec["rendered"] = True
                rec["rendered_len"] = len(rendered)
                with open(os.path.join(args.cache_dir, "pages", sl + ".rendered.txt"), "w", encoding="utf-8") as f:
                    f.write(rendered)
            else:
                rec["rendered"] = False
        pages.append(rec)

        # capture homepage links for a broken-link sweep (first page only)
        if len(pages) == 1 and r["body"]:
            for href in parsed.links:
                nu = A.absolutize(url, href).split("#")[0]
                if A.same_host(site, nu) and nu.startswith("http"):
                    homepage_links.append(nu)

        # enqueue internal links from homepage & early pages to broaden the sample
        if len(pages) <= 3 and r["body"]:
            for href in parsed.links:
                nu = A.absolutize(url, href).split("#")[0]
                if A.same_host(site, nu) and nu not in seen and nu.startswith("http"):
                    queue.append(nu)

    # Bounded broken-internal-link sweep: HEAD up to 15 distinct homepage links.
    link_check = []
    for lu in list(dict.fromkeys(homepage_links))[:15]:
        hr = A.fetch(lu, method="HEAD")
        st = hr["status"]
        if st is None or st >= 400:  # retry once with GET (some servers reject HEAD)
            hr = A.fetch(lu, method="GET")
            st = hr["status"]
        link_check.append({"url": lu, "status": st})

    meta = {
        "site": site,
        "host": host,
        "robots": {
            "present": robots["status"] == 200,
            "status": robots["status"],
            "text": robots_txt[:20000],
            "ai_bots": ai_bot_status,
        },
        "llms_txt": llms_txt,
        "ai_bot_reachability": ai_bot_reachability,
        "sitemaps": sitemaps,
        "sitemap_url_count": len(sm_urls),
        "link_check": link_check,
        "render_enabled": args.render,
        "render_available": any(p.get("rendered") for p in pages),
        "pages": pages,
        "pages_crawled": len(pages),
    }
    with open(os.path.join(args.cache_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"crawled {len(pages)} pages -> {args.cache_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
