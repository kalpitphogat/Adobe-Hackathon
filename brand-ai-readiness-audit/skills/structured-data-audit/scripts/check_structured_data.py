#!/usr/bin/env python3
"""structured-data-audit: can a machine pick out the specific fact?
Checks JSON-LD/schema.org coverage & validity, core metadata (title/description/OG),
heading structure, and entity clarity (sameAs). Usage: check_structured_data.py <cache_dir>"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "structured-data-audit"


def extract_ldjson(html):
    """Return (valid_objs, n_blocks, n_invalid)."""
    blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                        html, re.I | re.S)
    objs, invalid = [], 0
    for b in blocks:
        try:
            data = json.loads(b.strip())
            objs.extend(data if isinstance(data, list) else [data])
        except Exception:
            invalid += 1
    return objs, len(blocks), invalid


def types_of(objs):
    t = []
    for o in objs:
        if isinstance(o, dict):
            v = o.get("@type")
            if isinstance(v, list):
                t.extend(v)
            elif v:
                t.append(v)
            if "@graph" in o and isinstance(o["@graph"], list):
                t.extend(types_of(o["@graph"]))
    return [str(x) for x in t]


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = [p for p in meta["pages"] if p["status"] == 200]
    findings = []
    if not pages:
        return findings

    total = len(pages)
    with_schema, invalid_pages, all_types = 0, [], []
    missing_desc, missing_og, no_h1, multi_h1, missing_title = [], [], [], [], []

    for p in pages:
        html = A.read_page(cache_dir, p, "html") or ""
        objs, nblocks, ninvalid = extract_ldjson(html)
        if nblocks:
            with_schema += 1
        if ninvalid:
            invalid_pages.append(p["url"])
        all_types.extend(types_of(objs))

        low = html.lower()
        if not re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'][^"\']{20,}', low):
            missing_desc.append(p["url"])
        if 'property="og:' not in low and "property='og:" not in low:
            missing_og.append(p["url"])
        if not p.get("title"):
            missing_title.append(p["url"])
        if p.get("n_h1", 0) == 0:
            no_h1.append(p["url"])
        elif p.get("n_h1", 0) > 1:
            multi_h1.append(p["url"])

    # 1. structured data coverage
    if with_schema == 0:
        findings.append(A.finding(
            "No structured data (JSON-LD / schema.org) anywhere",
            "high",
            f"Crawled {total} pages; 0/{total} contain any schema.org markup.",
            "Add JSON-LD to every page: Organization + WebSite on the homepage, and the right "
            "type per page (Product/Offer, Article, FAQPage, BreadcrumbList, LocalBusiness). "
            "See references/schema-templates.md for paste-ready snippets.",
            "high", "structured-data", checked=total))
    elif with_schema < total:
        findings.append(A.finding(
            "Structured data is missing on some pages",
            "medium",
            f"{with_schema}/{total} pages carry JSON-LD; {total - with_schema} do not.",
            "Extend JSON-LD to the uncovered page types so every important fact is machine-readable.",
            "medium", "structured-data", checked=total))

    # 2. invalid JSON-LD
    if invalid_pages:
        findings.append(A.finding(
            "Invalid JSON-LD that fails to parse",
            "high",
            f"{len(invalid_pages)}/{total} pages contain a ld+json block that is not valid JSON: "
            f"{', '.join(invalid_pages[:4])}.",
            "Fix the JSON syntax; a block that does not parse is ignored entirely, so the markup "
            "delivers zero benefit.",
            "high", "structured-data", checked=total))

    # 3. homepage entity identity (Organization + sameAs)
    home = pages[0]
    home_html = A.read_page(cache_dir, home, "html") or ""
    home_objs, _, _ = extract_ldjson(home_html)
    home_types = set(types_of(home_objs))
    if not (home_types & {"Organization", "LocalBusiness", "Corporation", "WebSite"}):
        findings.append(A.finding(
            "Homepage lacks an Organization/WebSite identity in structured data",
            "high",
            f"Homepage JSON-LD @types found: {sorted(home_types) or 'none'}.",
            "Add Organization (name, url, logo, sameAs) and WebSite JSON-LD to the homepage so "
            "assistants can identify the brand as a distinct entity.",
            "high", "structured-data"))
    else:
        has_sameas = any(isinstance(o, dict) and o.get("sameAs") for o in home_objs)
        if not has_sameas:
            findings.append(A.finding(
                "No sameAs links to disambiguate the brand entity",
                "medium",
                "Organization/WebSite markup is present but declares no sameAs profiles.",
                "Add sameAs URLs (Wikipedia/Wikidata, LinkedIn, Crunchbase, official socials) so "
                "assistants can resolve name collisions and merge signals to the right entity.",
                "medium", "structured-data"))

    # 4. metadata basics
    if missing_title:
        findings.append(A.finding(
            "Pages missing a <title>",
            "high",
            f"{len(missing_title)}/{total} pages have an empty or absent <title>: "
            f"{', '.join(missing_title[:4])}.",
            "Give every page a unique, descriptive <title>; it is the primary label engines and "
            "assistants use to name the page.",
            "high", "structured-data", checked=total))
    if len(missing_desc) == total:
        findings.append(A.finding(
            "No meta descriptions",
            "medium",
            f"0/{total} pages have a meaningful meta description (>=20 chars).",
            "Write a unique meta description per page summarizing the key fact; it is a common "
            "quotable snippet source.",
            "medium", "structured-data", checked=total))
    if len(missing_og) == total:
        findings.append(A.finding(
            "No Open Graph metadata",
            "low",
            f"0/{total} pages declare Open Graph (og:*) tags.",
            "Add og:title/og:description/og:image/og:url so shared and cited links render with "
            "correct titles and previews.",
            "low", "structured-data", checked=total))
    if no_h1:
        findings.append(A.finding(
            "Pages with no H1 heading",
            "medium",
            f"{len(no_h1)}/{total} pages have no <h1>: {', '.join(no_h1[:4])}.",
            "Add a single clear H1 stating what the page is about; headings give machines the "
            "topical spine of the page.",
            "medium", "structured-data", checked=total))
    if multi_h1:
        findings.append(A.finding(
            "Pages with multiple H1 headings",
            "low",
            f"{len(multi_h1)}/{total} pages have more than one <h1>: {', '.join(multi_h1[:4])}.",
            "Use exactly one H1 per page and nest sub-topics under H2/H3 for an unambiguous outline.",
            "low", "structured-data", checked=total))

    # 4b. Title length outside the useful range (truncated or too thin to be descriptive)
    bad_title_len = [p["url"] for p in pages
                     if p.get("title") and not (10 <= len(p["title"]) <= 65)]
    if bad_title_len:
        findings.append(A.finding(
            "Page titles outside the useful length range",
            "low",
            f"{len(bad_title_len)}/{total} pages have a <title> shorter than 10 or longer than "
            f"65 characters: {', '.join(bad_title_len[:4])}.",
            "Aim for descriptive ~10-60 character titles; very short titles under-describe the "
            "page and very long ones get truncated in results and citations.",
            "low", "structured-data", checked=total))

    # 4c. Broken heading hierarchy (a level is skipped, e.g. H1 -> H3)
    skipped = []
    for p in pages:
        levels = p.get("heading_levels") or []
        prev = 0
        for lvl in levels:
            if prev and lvl > prev + 1:
                skipped.append(p["url"])
                break
            prev = lvl
    if skipped:
        findings.append(A.finding(
            "Skipped heading levels break the document outline",
            "low",
            f"{len(skipped)}/{total} pages jump more than one heading level (e.g. H1 -> H3), "
            f"e.g. {', '.join(skipped[:4])}.",
            "Use headings in order (H1 -> H2 -> H3) without skipping levels so machines can "
            "reconstruct a correct topical outline of the page.",
            "low", "structured-data", checked=total))

    # 5. duplicate titles / descriptions across pages
    if total >= 3:
        titles = {}
        for p in pages:
            t = (p.get("title") or "").strip().lower()
            if t:
                titles.setdefault(t, []).append(p["url"])
        dup_titles = {t: us for t, us in titles.items() if len(us) > 1}
        if dup_titles:
            worst = max(dup_titles.values(), key=len)
            findings.append(A.finding(
                "Duplicate page titles across the site",
                "medium",
                f"{sum(len(u) for u in dup_titles.values())} pages share {len(dup_titles)} "
                f"repeated <title>(s); e.g. {len(worst)} pages titled "
                f"\"{[t for t, u in dup_titles.items() if u == worst][0][:60]}\".",
                "Give every page a unique, descriptive title. Duplicate titles make pages "
                "indistinguishable to engines and assistants and cause the wrong page to be cited.",
                "medium", "structured-data", checked=total))

        descs = {}
        for p in pages:
            html = A.read_page(cache_dir, p, "html") or ""
            m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']{20,})',
                          html, re.I)
            if m:
                descs.setdefault(m.group(1).strip().lower(), []).append(p["url"])
        dup_desc = {d: us for d, us in descs.items() if len(us) > 1}
        if dup_desc:
            findings.append(A.finding(
                "Duplicate meta descriptions across the site",
                "low",
                f"{sum(len(u) for u in dup_desc.values())} pages share {len(dup_desc)} "
                "repeated meta description(s).",
                "Write a unique meta description per page; duplicates dilute the snippet signal "
                "and are often ignored.",
                "low", "structured-data", checked=total))

    return findings


if __name__ == "__main__":
    A.emit(SKILL, run(sys.argv[1]))
