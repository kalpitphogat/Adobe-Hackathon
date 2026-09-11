#!/usr/bin/env python3
"""crawl-access-audit: can an (AI) crawler reach and index the site?

Mechanism 1 of the chain - reach the content. Every check here is about access,
not content quality. Checks that only make sense for an HTML page are applied
only to HTML pages; XML sitemaps and other resources are reported as what they
are. Usage: check_access.py <cache_dir>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
# pyrefly: ignore [missing-import]
import auditlib as A  # noqa: E402  - sys.path must be modified before this import

SKILL = "crawl-access-audit"

NOINDEX_TOKENS = ("noindex", "none")


def has_noindex(value):
    v = (value or "").lower()
    return any(tok in v for tok in NOINDEX_TOKENS)


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    all_res = meta.get("pages", [])
    pages = A.html_pages(meta)
    non_html = A.non_html_resources(meta)
    findings, skips = [], []
    robots = meta.get("robots", {})
    site = meta.get("site", "")

    # ---- 1. robots.txt presence ------------------------------------------- #
    if not robots.get("present"):
        findings.append(A.finding(
            "No robots.txt published",
            "low",
            f"GET {site}/robots.txt returned status {robots.get('status')}.",
            "Without robots.txt a crawler has no declared policy and no sitemap pointer, "
            "so it discovers pages only by following links. This slows discovery; it does "
            "not block it.",
            "Publish a robots.txt that allows public content and names your sitemap.",
            "low", "crawl-access", finding_type="improvement", confidence="high",
            mechanism="reach", dedup_key="crawl-access:no-robots"))

    # ---- 2. AI crawler restrictions --------------------------------------- #
    # Report exactly which user-agents are disallowed and whether public content
    # is demonstrably affected. A restriction may be deliberate editorial policy,
    # so it is never automatically critical.
    blocked_bots = sorted(b for b, st in robots.get("ai_bots", {}).items() if st == "blocked")
    if blocked_bots:
        total_bots = len(robots.get("ai_bots", {}))
        fetchers = set(robots.get("citation_fetchers") or [])
        bulk = set(robots.get("bulk_crawlers") or [])
        blocked_fetchers = sorted(b for b in blocked_bots if b in fetchers)
        blocked_bulk = sorted(b for b in blocked_bots if b in bulk)

        # Severity follows what is actually lost. Blocking the agents documented as
        # fetching pages to answer a query is what removes a site from those
        # answers; blocking a bulk corpus crawler is a licensing choice with no
        # effect on being cited at query time, and is not reported as a defect.
        if fetchers and len(blocked_fetchers) * 2 >= len(fetchers):
            sev, ftype, material = "high", "defect", True
        elif blocked_fetchers:
            sev, ftype, material = "medium", "defect", False
        else:
            sev, ftype, material = "low", "improvement", False

        groups = []
        if blocked_fetchers:
            groups.append(f"{len(blocked_fetchers)}/{len(fetchers)} documented "
                          f"citation fetchers ({', '.join(blocked_fetchers)})")
        if blocked_bulk:
            groups.append(f"{len(blocked_bulk)}/{len(bulk)} bulk corpus crawlers "
                          f"({', '.join(blocked_bulk)})")

        if blocked_fetchers:
            interp = ("Assistants that honour these user-agents cannot fetch the site's "
                      "pages to cite them. This may be a deliberate content-licensing "
                      "decision, in which case the finding is expected rather than a "
                      "defect. Being listed here is not a claim that every assistant uses "
                      "every one of these agents.")
            action = ("Decide the policy explicitly. If citation by AI assistants is "
                      f"wanted, allow {', '.join(blocked_fetchers[:4])} for the public "
                      "sections while keeping any Disallow rules for private or "
                      "parameterised paths.")
        else:
            interp = ("Only bulk corpus crawlers are disallowed. Those gather training and "
                      "index corpora rather than fetching a page to answer a live query, so "
                      "this does not by itself stop an assistant citing the site. It is a "
                      "content-licensing position, not an access defect.")
            action = ("No action is needed for citation. Keep this rule if the intent is to "
                      f"withhold content from bulk corpora ({', '.join(blocked_bulk)}), and "
                      "confirm the citation fetchers remain allowed.")

        findings.append(A.finding(
            "robots.txt disallows AI-related crawlers from the site root",
            sev,
            "robots.txt returns Disallow for the site root to "
            + "; ".join(groups)
            + f". {len(pages)} HTML page(s) were sampled behind that policy.",
            interp, action, sev, "crawl-access",
            checked=total_bots, checked_unit="AI-related user-agents",
            finding_type=ftype, confidence="high", material=material,
            mechanism="reach", dedup_key="crawl-access:ai-bots-blocked"))

    # A site can allow the root to an AI crawler while disallowing the content
    # beneath it. A root-only check would report nothing at all, so the rules are
    # also evaluated against the URLs the crawl actually discovered.
    access = robots.get("ai_bot_sample_access", {}) or {}
    starved = sorted(b for b, a in access.items()
                     if b not in blocked_bots and a.get("sampled")
                     and a["allowed"] <= a["sampled"] // 2)
    if starved:
        a0 = access[starved[0]]
        findings.append(A.finding(
            "AI-assistant crawlers are allowed the site root but disallowed most content",
            "high",
            f"{len(starved)} AI-assistant user-agent(s) can fetch the site root but are "
            f"Disallow'd from at least half of the {a0['sampled']} URLs this crawl "
            "discovered: "
            + ", ".join(f"{b} ({access[b]['allowed']}/{access[b]['sampled']} reachable)"
                        for b in starved[:4]) + ".",
            "Permission at the root is not permission to the pages. These agents can reach "
            "the entry point but not most of what the crawl found beneath it, so the "
            "content itself stays unfetchable to them.",
            "Narrow the Disallow rules covering these user-agents to the paths that "
            "genuinely should stay out of an index, rather than the content sections.",
            "high", "crawl-access", checked=a0["sampled"],
            checked_unit="URLs discovered by this crawl",
            confidence="high", material=True,
            mechanism="reach", dedup_key="crawl-access:ai-bots-content-blocked"))

    # ---- 3. sitemap ------------------------------------------------------- #
    if not meta.get("sitemaps"):
        findings.append(A.finding(
            "No XML sitemap discovered at the conventional locations",
            "low",
            f"No sitemap was returned from robots.txt Sitemap: directives or {site}/sitemap.xml.",
            "Crawlers must then rely on internal links to find pages, which reaches deep or "
            "poorly-linked pages more slowly. A sitemap may still exist at a non-standard path "
            "this audit did not try.",
            "Publish an XML sitemap and reference it from robots.txt with a Sitemap: line.",
            "low", "crawl-access", finding_type="improvement", confidence="medium",
            mechanism="reach", dedup_key="crawl-access:no-sitemap"))

    # ---- 4. noindex ------------------------------------------------------- #
    # Only an HTML page the brand plausibly wants discovered can be a noindex
    # defect. A sitemap or API response carrying X-Robots-Tag: noindex is normal
    # and is reported separately as context, not as a page defect.
    noindex_html, noindex_other = [], []
    for p in all_res:
        src = []
        if has_noindex(p.get("x_robots_tag")):
            src.append("X-Robots-Tag")
        if p.get("is_html") and has_noindex(p.get("meta_robots")):
            src.append("meta robots")
        if not src:
            continue
        entry = (p["url"], "+".join(src), p.get("page_role", "resource"))
        (noindex_html if p.get("is_html") else noindex_other).append(entry)

    if noindex_html:
        roles = {r for _, _, r in noindex_html}
        home_hit = any(A.is_homepage_url(site, u) for u, _, _ in noindex_html)
        # Material when a page a brand would want found is excluded: the homepage,
        # or any content-bearing role. Utility and authentication pages are
        # routinely and correctly noindexed.
        content_roles = roles - {"authentication", "utility", "resource", "unknown"}
        material = home_hit or bool(content_roles)
        sev = "critical" if home_hit else ("high" if content_roles else "low")
        findings.append(A.finding(
            "HTML pages carry a noindex directive",
            sev,
            f"{len(noindex_html)}/{len(pages)} sampled HTML pages set noindex: "
            + "; ".join(f"{u} [{src}, role={role}]" for u, src, role in noindex_html[:5]) + ".",
            "noindex instructs search engines and assistant crawlers to exclude the page "
            "entirely, so its facts cannot be indexed or cited"
            + (" - and this includes the homepage." if home_hit else
               " for the roles listed above."),
            "Remove noindex from the public pages listed above that are intended to be "
            "discoverable. Keep it on genuinely private, duplicate or staging URLs.",
            sev, "crawl-access", checked=len(pages), confidence="high", material=material,
            mechanism="reach", dedup_key="crawl-access:noindex-html"))

    if noindex_other and not noindex_html:
        skips.append(A.skipped(
            "noindex (page-level)",
            f"{len(noindex_other)} non-HTML resource(s) carry noindex "
            f"(e.g. {noindex_other[0][0]}); this is normal for sitemaps and API responses "
            "and is not treated as a page defect."))

    # ---- 5. robots-disallowed sampled URLs -------------------------------- #
    blocked_pages = [p["url"] for p in all_res if p.get("robots_blocked")]
    if blocked_pages:
        findings.append(A.finding(
            "Sampled URLs are disallowed by robots.txt for the default crawler",
            "medium",
            f"{len(blocked_pages)}/{len(all_res)} URLs discovered during the crawl are "
            f"Disallow'd and were therefore never requested: {', '.join(blocked_pages[:5])}.",
            "A disallowed URL cannot be fetched by any compliant crawler. Whether that is a "
            "problem depends on whether these paths hold public content; this audit did not "
            "fetch them, so it cannot judge their contents.",
            "Review the Disallow rules covering these paths and narrow them to the URLs that "
            "genuinely should stay out of an index.",
            "medium", "crawl-access", checked=len(all_res),
            checked_unit="crawled URLs", confidence="medium",
            mechanism="reach", dedup_key="crawl-access:robots-disallow",
            not_verified="what these URLs contain, since robots.txt was respected"))

    # ---- 6. error statuses ------------------------------------------------ #
    err_pages = [(p["url"], p["status"]) for p in all_res
                 if p.get("status") and p["status"] >= 400]
    if err_pages:
        server_err = [u for u, s in err_pages if s >= 500]
        findings.append(A.finding(
            "Sampled URLs return 4xx/5xx status codes",
            "high" if server_err else "medium",
            f"{len(err_pages)}/{len(all_res)} sampled URLs returned an error status: "
            + ", ".join(f"{u} ({s})" for u, s in err_pages[:5]) + ".",
            "An error response carries no indexable content. 5xx responses additionally "
            "suggest the origin is failing rather than the URL simply being retired.",
            "Restore the 5xx URLs, and redirect retired 4xx URLs to their live equivalents "
            "so link equity and crawl paths are preserved.",
            "high" if server_err else "medium", "crawl-access", checked=len(all_res),
            checked_unit="crawled URLs", confidence="high", material=bool(server_err),
            mechanism="reach", dedup_key="crawl-access:error-status"))

    # ---- 7. canonical ------------------------------------------------------ #
    # Missing canonical only matters where there is actual URL ambiguity to
    # resolve. Otherwise it is a hygiene improvement, not a defect.
    ok_html = [p for p in pages if p.get("status") == 200]
    no_canonical = [p for p in ok_html if not p.get("canonical")]
    if no_canonical and len(no_canonical) == len(ok_html) and ok_html:
        ambiguous = [p["url"] for p in no_canonical if "?" in p["url"]]
        findings.append(A.finding(
            "No rel=canonical declared on the sampled pages",
            "medium" if ambiguous else "low",
            f"0/{len(ok_html)} sampled HTML pages declare a rel=canonical link."
            + (f" {len(ambiguous)} of them are parameterised URLs, e.g. {ambiguous[0]}."
               if ambiguous else " No parameterised or duplicate URLs were observed in the sample."),
            "A canonical resolves which address is authoritative when the same content is "
            "reachable at several URLs."
            + (" Parameterised URLs were observed here, so that ambiguity is present."
               if ambiguous else
               " No such ambiguity was observed in this sample, so this is hygiene rather "
               "than an active problem."),
            "Add a self-referential rel=canonical to each page"
            + (", starting with the parameterised URLs listed above." if ambiguous else "."),
            "medium" if ambiguous else "low", "crawl-access", checked=len(ok_html),
            finding_type="defect" if ambiguous else "improvement",
            confidence="high" if ambiguous else "medium",
            mechanism="reach", dedup_key="crawl-access:no-canonical"))

    # ---- 8. HTTPS ---------------------------------------------------------- #
    if site.startswith("http://"):
        findings.append(A.finding(
            "Site is served over HTTP, not HTTPS",
            "high",
            f"The audited base URL resolved to {site}.",
            "Browsers mark insecure origins, and crawlers treat them as lower quality.",
            "Serve every URL over HTTPS with a valid certificate and redirect HTTP to HTTPS.",
            "high", "crawl-access", confidence="high", material=True,
            mechanism="reach", dedup_key="crawl-access:no-https"))

    # ---- 9. broken internal links ----------------------------------------- #
    checks = meta.get("link_check", [])
    broken = [lc for lc in checks if lc.get("status") and lc["status"] >= 400]
    unreachable = [lc for lc in checks if not lc.get("status")]
    if broken:
        findings.append(A.finding(
            "Homepage links to internal URLs that return an error",
            "medium",
            f"{len(broken)}/{len(checks)} internal links sampled from the homepage returned "
            "4xx/5xx: "
            + ", ".join(f"{lc['url']} ({lc['status']})" for lc in broken[:5]) + ".",
            "These are paths a crawler would follow from the homepage, so the destination "
            "pages are unreachable through them.",
            "Repair the destination pages, or point the homepage links at their live "
            "equivalents.",
            "medium", "crawl-access", checked=len(checks),
            checked_unit="homepage links sampled", confidence="high", material=True,
            mechanism="reach", dedup_key="crawl-access:broken-links"))
    if unreachable and not broken:
        skips.append(A.skipped(
            "broken internal links",
            f"{len(unreachable)}/{len(checks)} homepage links produced no HTTP response "
            "(network error or timeout); this audit cannot tell a broken link from a "
            "transient failure, so no finding was raised."))
    if meta.get("link_check_truncated"):
        skips.append(A.skipped(
            "broken internal links (remaining candidates)",
            f"the link sweep hit its wall-clock budget after {len(checks)} of "
            f"{meta.get('link_check_candidates', '?')} candidate homepage links; the rest "
            "were not checked, so this finding's scope is those checked, not all links."))

    # ---- 10. mixed content ------------------------------------------------- #
    mixed = [(p["url"], p.get("n_mixed_content", 0)) for p in pages
             if p.get("n_mixed_content", 0) > 0]
    if mixed:
        findings.append(A.finding(
            "Secure pages reference insecure sub-resources",
            "medium",
            f"{len(mixed)}/{len(pages)} sampled HTML pages load scripts, images, stylesheets "
            "or frames over http:// from an https:// page: "
            + ", ".join(f"{u} ({n})" for u, n in mixed[:4]) + ".",
            "Browsers block or downgrade these sub-resources, which can break layout or "
            "functionality for visitors. Outbound http:// anchor links were excluded from "
            "this count.",
            "Load every sub-resource over https, or use protocol-relative/upgraded URLs.",
            "medium", "crawl-access", checked=len(pages), confidence="high", material=True,
            mechanism="reach", dedup_key="crawl-access:mixed-content"))

    # ---- 11. edge/CDN block ------------------------------------------------ #
    rb = meta.get("ai_bot_reachability", {})
    if rb.get("blocked"):
        findings.append(A.finding(
            "AI crawler user-agent is refused at the edge, independently of robots.txt",
            "critical",
            f"The homepage returned HTTP {rb.get('reference_status')} to a normal browser "
            f"user-agent but HTTP {rb.get('ai_status')} to the {rb.get('ua')} user-agent, "
            "on two separate requests.",
            "A CDN/WAF rule is refusing the crawler regardless of what robots.txt permits, "
            "so the homepage cannot be fetched by that agent at all.",
            "Allow-list the AI-assistant user-agents at the CDN/WAF layer (Cloudflare, Akamai, "
            "Fastly, Vercel). robots.txt permission has no effect while the edge returns "
            f"{rb.get('ai_status')}.",
            "critical", "crawl-access", checked=1, checked_unit="homepage probes (two UAs)",
            confidence="high", material=True,
            mechanism="reach", dedup_key="crawl-access:edge-block"))
    elif rb.get("inconclusive"):
        skips.append(A.skipped(
            "edge/CDN AI-crawler reachability",
            f"The {rb.get('ua')} probe produced no HTTP response after a retry "
            f"({rb.get('ai_error')}), while the browser probe succeeded. A network failure "
            "cannot be distinguished from an edge block, so no finding was raised."))

    # ---- 12. llms.txt ------------------------------------------------------ #
    if not meta.get("llms_txt", {}).get("present"):
        findings.append(A.finding(
            "No llms.txt guidance file present",
            "low",
            f"GET {site}/llms.txt returned status {meta.get('llms_txt', {}).get('status')}.",
            "llms.txt is an emerging, non-universal convention for pointing AI assistants at "
            "a site's most quotable pages. It is not consumed by every assistant and its "
            "absence blocks nothing.",
            "Optionally publish an llms.txt listing your most important pages in plain "
            "markdown, as a low-cost, forward-looking signal.",
            "low", "crawl-access", finding_type="improvement", confidence="high",
            mechanism="reach", dedup_key="crawl-access:no-llms-txt"))

    if non_html:
        kinds = {}
        for p in non_html:
            kinds[p.get("resource_kind", "other")] = kinds.get(p.get("resource_kind", "other"), 0) + 1
        skips.append(A.skipped(
            "HTML page checks on non-HTML resources",
            f"{len(non_html)} crawled resource(s) are not HTML documents and were excluded "
            "from every page-level check.",
            resource_kinds=kinds))

    return findings, skips


if __name__ == "__main__":
    f, s = run(sys.argv[1])
    A.emit(SKILL, f, s)
