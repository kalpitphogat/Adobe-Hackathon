#!/usr/bin/env python3
"""crawl-access-audit: can an (AI) crawler get in and index the site?
Reads the shared cache and emits findings. Usage: check_access.py <cache_dir>"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "crawl-access-audit"


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = meta["pages"]
    findings = []
    robots = meta["robots"]

    # 1. robots.txt presence
    if not robots["present"]:
        findings.append(A.finding(
            "No robots.txt found",
            "low",
            f"GET {meta['site']}/robots.txt returned status {robots['status']}.",
            "Add a robots.txt that allows crawling and points to your sitemap; absence "
            "forces every crawler to guess and slows discovery.",
            "low", "crawl-access"))

    # 2. AI crawlers blocked
    blocked_bots = [b for b, s in robots.get("ai_bots", {}).items() if s == "blocked"]
    if blocked_bots:
        key = [b for b in blocked_bots if b in ("GPTBot", "OAI-SearchBot", "ClaudeBot",
                                                "PerplexityBot", "Google-Extended")]
        sev = "critical" if key else "high"
        findings.append(A.finding(
            "AI assistant crawlers are blocked in robots.txt",
            sev,
            f"robots.txt disallows: {', '.join(blocked_bots)}. These are the fetchers "
            "AI assistants use to find and cite pages.",
            "If you want the brand cited by AI assistants, allow these user-agents "
            "(GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended) for public content.",
            sev, "crawl-access", checked=len(robots.get("ai_bots", {}))))

    # 3. sitemap
    if not meta["sitemaps"]:
        findings.append(A.finding(
            "No XML sitemap discovered",
            "medium",
            "No sitemap referenced in robots.txt and /sitemap.xml did not return a valid urlset.",
            "Publish an XML sitemap and reference it in robots.txt so crawlers can find "
            "every page without relying on internal-link discovery.",
            "medium", "crawl-access"))

    # 4. per-page blocking / noindex / status
    noindex_pages, blocked_pages, err_pages = [], [], []
    for p in pages:
        xrt = (p.get("x_robots_tag") or "").lower()
        if "noindex" in xrt:
            noindex_pages.append(p["url"])
        if p.get("robots_blocked"):
            blocked_pages.append(p["url"])
        if p["status"] and p["status"] >= 400:
            err_pages.append(f"{p['url']} ({p['status']})")

    # meta robots noindex needs the raw HTML
    meta_noindex = []
    for p in pages:
        html = A.read_page(cache_dir, p, "html") or ""
        low = html.lower()
        if 'name="robots"' in low and "noindex" in low.split('name="robots"', 1)[1][:200]:
            meta_noindex.append(p["url"])
    noindex_pages = sorted(set(noindex_pages) | set(meta_noindex))

    if noindex_pages:
        home_hit = any(u.rstrip("/") == meta["site"] for u in noindex_pages)
        sev = "critical" if home_hit else "high"
        findings.append(A.finding(
            "Pages carry a noindex directive",
            sev,
            f"{len(noindex_pages)}/{len(pages)} crawled pages set noindex "
            f"(meta robots or X-Robots-Tag): {', '.join(noindex_pages[:5])}.",
            "Remove noindex from pages you want found and cited. noindex tells every "
            "engine and assistant to exclude the page entirely.",
            sev, "crawl-access", checked=len(pages)))

    if blocked_pages:
        findings.append(A.finding(
            "Crawlable content is disallowed by robots.txt",
            "high",
            f"{len(blocked_pages)}/{len(pages)} sampled URLs are Disallow'd for the default "
            f"user-agent: {', '.join(blocked_pages[:5])}.",
            "Relax robots.txt Disallow rules for public pages you want indexed and cited.",
            "high", "crawl-access", checked=len(pages)))

    if err_pages:
        findings.append(A.finding(
            "Pages return error status codes",
            "high",
            f"{len(err_pages)} sampled URL(s) returned 4xx/5xx: {', '.join(err_pages[:5])}.",
            "Fix broken URLs (or 301 them to live equivalents). Error pages cannot be "
            "indexed and waste crawl budget.",
            "high", "crawl-access", checked=len(pages)))

    # 5. canonical hygiene
    no_canonical = [p["url"] for p in pages if p["status"] == 200 and not p.get("canonical")]
    if no_canonical and len(no_canonical) == len([p for p in pages if p["status"] == 200]):
        findings.append(A.finding(
            "No canonical URLs declared",
            "low",
            f"0/{len(no_canonical)} successful pages declare rel=canonical.",
            "Add a self-referential rel=canonical to each page to consolidate duplicate/"
            "parameterized URLs onto one authoritative address.",
            "low", "crawl-access", checked=len(no_canonical)))

    # 6. HTTPS
    if meta["site"].startswith("http://"):
        findings.append(A.finding(
            "Site is served over HTTP, not HTTPS",
            "high",
            f"Base URL resolved to {meta['site']}.",
            "Serve everything over HTTPS with a valid certificate; insecure origins are "
            "down-ranked and distrusted by crawlers and assistants.",
            "high", "crawl-access"))

    return findings


if __name__ == "__main__":
    A.emit(SKILL, run(sys.argv[1]))
