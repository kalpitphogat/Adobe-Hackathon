#!/usr/bin/env python3
"""structured-data-audit: can a machine pick out the specific fact?

Mechanism 3 of the chain - identify important facts. The question this skill asks
is never "is best practice X present?" but "are this page's important facts
expressed in a form a machine can extract, given what the page is for?".

Structured data is recommended only where a relevant schema type exists for the
page's role. Missing markup on a page whose facts are already plain, readable
HTML is an opportunity, not a defect. Usage: check_structured_data.py <cache_dir>
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "structured-data-audit"

# The only schema types this audit will ever recommend, keyed by the page role
# that makes them relevant. A role with no entry gets no schema recommendation:
# recommending Product markup for a documentation page is worse than silence.
ROLE_SCHEMA = {
    "homepage":      ("Organization and WebSite", {"organization", "website", "localbusiness",
                                                   "corporation", "person", "ngo",
                                                   "educationalorganization",
                                                   "governmentorganization"}),
    "article":       ("Article (or NewsArticle/BlogPosting)", {"article", "newsarticle",
                                                               "blogposting", "report",
                                                               "liveblogposting"}),
    "product":       ("Product with Offer, or Service", {"product", "offer", "aggregateoffer",
                                                         "service", "softwareapplication",
                                                         "course"}),
    "contact":       ("ContactPage with the organisation's contact points",
                      {"contactpage", "organization", "localbusiness"}),
    "documentation": ("TechArticle or HowTo", {"techarticle", "howto", "apireference",
                                               "faqpage", "article"}),
}


def extract_ldjson(html):
    """Return (objects, n_blocks, n_invalid) for the page's ld+json blocks."""
    blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                        html, re.I | re.S)
    objs, invalid = [], 0
    for b in blocks:
        if not b.strip():
            continue
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
            for key in ("@graph", "mainEntity", "itemListElement"):
                sub = o.get(key)
                if isinstance(sub, list):
                    t.extend(types_of(sub))
                elif isinstance(sub, dict):
                    t.extend(types_of([sub]))
    return [str(x) for x in t]


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = A.html_pages(meta)
    findings, skips = [], []
    non_html = A.non_html_resources(meta)
    if non_html:
        skips.append(A.skipped(
            "structured data, title and heading checks on non-HTML resources",
            f"{len(non_html)} crawled resource(s) are not HTML documents; schema.org markup, "
            "<title> and heading structure are not meaningful for them."))
    if not pages:
        skips.append(A.skipped("all structured-data checks",
                               "no HTML page was retrieved in this crawl"))
        return findings, skips

    total = len(pages)
    invalid_pages, per_page = [], []
    for p in pages:
        html = A.read_page(cache_dir, p, "html") or ""
        objs, nblocks, ninvalid = extract_ldjson(html)
        if ninvalid:
            invalid_pages.append(p["url"])
        per_page.append((p, objs, nblocks, {t.lower() for t in types_of(objs)}))

    # ---- 1. invalid JSON-LD ------------------------------------------------ #
    # A block that does not parse is silently ignored by every consumer, so the
    # site believes it has markup that in fact delivers nothing. This is a real
    # defect regardless of page role.
    if invalid_pages:
        # Scope-proportional: a broken block on most of the sample is a template
        # defect; on one page it is a page defect. Both are real; they are not
        # equally loud.
        widespread = len(invalid_pages) * 2 >= total
        sev = "high" if widespread else "medium"
        findings.append(A.finding(
            "JSON-LD blocks that fail to parse",
            sev,
            f"{len(invalid_pages)}/{total} sampled HTML pages contain an "
            "application/ld+json block that is not valid JSON: "
            + ", ".join(invalid_pages[:4]) + ".",
            "Consumers discard a block that does not parse, so the markup the site is "
            "publishing delivers none of its intended benefit"
            + (" - and the same template appears to be affected across the sample."
               if widespread else " on the pages listed."),
            "Fix the JSON syntax in the listed blocks and re-validate them with a "
            "structured-data testing tool.",
            sev, "structured-data", checked=total, confidence="high", material=True,
            mechanism="identify-facts", dedup_key="structured-data:invalid-jsonld"))

    # ---- 2. relevant schema missing, by role ------------------------------- #
    # Only pages whose role has a genuinely applicable schema type are considered,
    # and only pages whose role was classified with confidence.
    # The homepage is excluded here: its entity markup is assessed once, by the
    # dedicated identity check below, so it is never reported twice.
    def schema_candidate(p):
        return (A.role_of(p) in ROLE_SCHEMA and A.role_of(p) != "homepage"
                and A.role_confident(p))

    gaps = {}
    for p, objs, nblocks, tset in per_page:
        if not schema_candidate(p):
            continue
        label, accepted = ROLE_SCHEMA[A.role_of(p)]
        if not (tset & accepted):
            gaps.setdefault(A.role_of(p), []).append(p["url"])
    if gaps:
        considered = sum(1 for p, _, _, _ in per_page if schema_candidate(p))
        lines = []
        for role in sorted(gaps):
            label = ROLE_SCHEMA[role][0]
            lines.append(f"{len(gaps[role])} {role} page(s) with no {label} markup "
                         f"(e.g. {gaps[role][0]})")
        n_gap = sum(len(v) for v in gaps.values())
        findings.append(A.finding(
            "Pages lack the schema.org type that matches their role",
            "medium",
            f"{n_gap}/{considered} sampled pages whose role was classified with confidence "
            "carry no matching schema.org type: " + "; ".join(lines) + ".",
            "Structured data is one of the ways a machine attributes a fact to an entity. "
            "Its absence does not make the facts unreadable, but it leaves the extraction to "
            "inference from prose. Only the types listed above are relevant to these roles.",
            "Add the matching JSON-LD per role: " + "; ".join(
                f"{role} -> {ROLE_SCHEMA[role][0]}" for role in sorted(gaps)) + ".",
            "medium", "structured-data", checked=considered,
            finding_type="improvement", confidence="high",
            mechanism="identify-facts", dedup_key="structured-data:role-schema-gap",
            thin_html_sensitive=True))

    unclassified = [p for p, _, _, _ in per_page if not A.role_confident(p)]
    if unclassified:
        skips.append(A.skipped(
            "role-specific schema recommendation",
            f"{len(unclassified)}/{total} sampled pages could not be assigned a page role "
            "with confidence, so no schema type was recommended for them."))

    # ---- 3. homepage entity identity --------------------------------------- #
    home = A.homepage_of(meta)
    if home is not None:
        entry = next((e for e in per_page if e[0]["url"] == home["url"]), None)
        home_objs = entry[1] if entry else []
        home_types = entry[3] if entry else set()
        ident = {"organization", "localbusiness", "corporation", "website", "person",
                 "ngo", "educationalorganization", "governmentorganization"}
        if not (home_types & ident):
            findings.append(A.finding(
                "Homepage declares no Organization or WebSite entity in structured data",
                "medium",
                "Homepage JSON-LD @types found: "
                + (", ".join(sorted(home_types)) if home_types else "none") + ".",
                "Without an explicit entity node, a machine must infer the brand's identity "
                "from prose and the domain name. That inference usually succeeds for a "
                "well-known brand and is least reliable for names that collide with others.",
                "Add Organization JSON-LD to the homepage with name, url and logo, plus a "
                "WebSite node. Do not add unrelated types.",
                "medium", "structured-data", checked=1, checked_unit="homepage",
                finding_type="improvement", confidence="high", page_role="homepage",
                mechanism="identify-facts", dedup_key="structured-data:no-entity"))
        else:
            has_sameas = any(isinstance(o, dict) and o.get("sameAs") for o in home_objs)
            if not has_sameas:
                findings.append(A.finding(
                    "No sameAs relationships declared in homepage structured data",
                    "low",
                    "The homepage declares "
                    + ", ".join(sorted(home_types & ident))
                    + " markup, and no sameAs property was found in it.",
                    "sameAs is how a page states which external profiles refer to the same "
                    "entity. Its absence says nothing about whether external sources exist; "
                    "this audit checked the homepage markup only.",
                    "Add sameAs URLs to the Organization node pointing at profiles you "
                    "control or that already describe the brand, such as Wikidata, LinkedIn "
                    "or the official social accounts.",
                    "low", "structured-data", checked=1, checked_unit="homepage",
                    finding_type="improvement", confidence="high", page_role="homepage",
                    mechanism="corroborate", dedup_key="structured-data:entity-sameas",
                    not_verified="whether external sources describing this brand exist; "
                                 "no external source was queried"))

    # ---- 4. <title> -------------------------------------------------------- #
    missing_title = [p["url"] for p in pages if not (p.get("title") or "").strip()]
    if missing_title:
        # Scope-proportional: the homepage or most of the sample is a site-level
        # problem; one deep page is a page-level one.
        home_hit = any(A.is_homepage_url(meta.get("site", ""), u) for u in missing_title)
        widespread = len(missing_title) * 2 >= total
        sev = "high" if (home_hit or widespread) else "medium"
        findings.append(A.finding(
            "HTML pages with no <title>",
            sev,
            f"{len(missing_title)}/{total} sampled HTML pages have an empty or absent "
            "<title> element: " + ", ".join(missing_title[:4]) + ".",
            "The title is the primary label engines and assistants use to name a page, and "
            "there is no fallback that carries the same weight."
            + (" The homepage is among them." if home_hit else ""),
            "Give each listed page a unique <title> that names the page and the brand.",
            sev, "structured-data", checked=total, confidence="high", material=True,
            mechanism="identify-facts", dedup_key="structured-data:missing-title",
            thin_html_sensitive=True))

    # Length guidance is presentation advice, never a significant AI-readiness
    # defect, so it stays a low-priority improvement.
    bad_len = [p["url"] for p in pages
               if (p.get("title") or "").strip() and not (10 <= len(p["title"].strip()) <= 65)]
    if bad_len and len(bad_len) >= max(2, total // 2):
        findings.append(A.finding(
            "Page titles fall outside the range that displays without truncation",
            "low",
            f"{len(bad_len)}/{total} sampled pages have a <title> shorter than 10 or longer "
            f"than 65 characters, e.g. {', '.join(bad_len[:3])}.",
            "Very long titles are truncated in result listings and very short ones "
            "under-describe the page. This affects presentation, not whether the page can "
            "be read or indexed.",
            "Aim for roughly 10-65 characters that name the page and the brand.",
            "low", "structured-data", checked=total, finding_type="improvement",
            confidence="high", mechanism="identify-facts",
            dedup_key="structured-data:title-length"))

    # ---- 5. duplicate titles ----------------------------------------------- #
    if total >= 3:
        # Two URLs serving byte-identical content (for example / and /index.html)
        # share a title because they are the same document. That is a duplicate-URL
        # question for the canonical check, not a titling problem, so such groups
        # are excluded here rather than reported twice.
        titles = {}
        for p in pages:
            t = (p.get("title") or "").strip().lower()
            if t:
                titles.setdefault(t, []).append(p)
        dup = {}
        same_content_groups = 0
        for t, ps in titles.items():
            if len(ps) < 2:
                continue
            bodies = {(A.read_page(cache_dir, q, "text") or "").strip() for q in ps}
            if len(bodies) == 1:
                same_content_groups += 1
                continue
            dup[t] = [q["url"] for q in ps]
        if same_content_groups:
            skips.append(A.skipped(
                "duplicate <title> check on identical documents",
                f"{same_content_groups} title group(s) were excluded because every URL in "
                "them returned identical content, which is a duplicate-URL question rather "
                "than a titling one."))
        if dup:
            worst_title = max(dup, key=lambda t: len(dup[t]))
            findings.append(A.finding(
                "Distinct pages share the same <title>",
                "medium",
                f"{sum(len(u) for u in dup.values())}/{total} sampled pages share "
                f"{len(dup)} repeated title(s); the most repeated is "
                f"\"{worst_title[:60]}\" on {len(dup[worst_title])} pages.",
                "Pages that carry the same label are hard to tell apart when a machine "
                "chooses which one to cite for a specific question.",
                "Give each page a title naming its own subject rather than only the site.",
                "medium", "structured-data", checked=total, confidence="high", material=True,
                mechanism="identify-facts", dedup_key="structured-data:duplicate-titles"))

    # ---- 6. meta description ----------------------------------------------- #
    no_desc = [p["url"] for p in pages if len((p.get("meta_description") or "").strip()) < 20]
    if len(no_desc) == total:
        findings.append(A.finding(
            "No page in the sample declares a meta description",
            "low",
            f"0/{total} sampled HTML pages declare a meta description of 20 characters or more.",
            "A meta description is a publisher-supplied summary that some surfaces display. "
            "Engines frequently substitute their own snippet, and this audit did not measure "
            "whether any assistant treats it as a fact source for this site.",
            "Write a one-sentence description per page summarising what the page answers.",
            "low", "structured-data", checked=total, finding_type="improvement",
            confidence="high", mechanism="identify-facts",
            dedup_key="structured-data:no-meta-description",
            not_verified="whether assistants use this site's meta descriptions as a fact source"))

    # ---- 7. Open Graph ----------------------------------------------------- #
    no_og = [p["url"] for p in pages if not p.get("og_keys")]
    if len(no_og) == total:
        findings.append(A.finding(
            "No Open Graph metadata in the sample",
            "low",
            f"0/{total} sampled HTML pages declare any og:* property.",
            "Open Graph controls how a link renders when it is shared or cited. Its absence "
            "affects link presentation, not indexability.",
            "Add og:title, og:description, og:url and og:image to the main page templates.",
            "low", "structured-data", checked=total, finding_type="improvement",
            confidence="high", mechanism="identify-facts",
            dedup_key="structured-data:no-opengraph"))

    # ---- 8. H1 -------------------------------------------------------------- #
    # A missing H1 matters only where the page has substantial content AND no
    # other machine-readable topical identity (title, schema type). "Exactly one
    # H1" is not treated as a universal requirement.
    weak_identity = []
    for p, objs, nblocks, tset in per_page:
        if A.role_of(p) in ("resource", "authentication", "utility"):
            continue
        if p.get("text_len", 0) < 600:
            continue
        if p.get("n_h1", 0) > 0:
            continue
        if (p.get("title") or "").strip() or tset:
            continue           # the page already has a machine-readable identity
        weak_identity.append(p["url"])
    considered_h1 = [p for p, _, _, _ in per_page
                     if A.role_of(p) not in ("resource", "authentication", "utility")
                     and p.get("text_len", 0) >= 600]
    if weak_identity:
        findings.append(A.finding(
            "Content pages state their topic in neither an H1, a title, nor structured data",
            "medium",
            f"{len(weak_identity)}/{len(considered_h1)} sampled content pages (600+ characters "
            "of body text) have no <h1>, no <title> and no schema.org type: "
            + ", ".join(weak_identity[:4]) + ".",
            "With all three absent there is no explicit statement of what the page is about, "
            "so a machine must infer the topic entirely from body prose.",
            "Add an H1 naming the page's subject, and a matching <title>.",
            "medium", "structured-data", checked=len(considered_h1), confidence="high",
            material=True, mechanism="identify-facts",
            dedup_key="structured-data:no-topical-identity", thin_html_sensitive=True))

    no_h1_only = [p["url"] for p in considered_h1 if p.get("n_h1", 0) == 0
                  and p["url"] not in weak_identity]
    if no_h1_only and len(no_h1_only) >= max(2, len(considered_h1) // 2):
        findings.append(A.finding(
            "Content pages have no H1, relying on the title alone for topic",
            "low",
            f"{len(no_h1_only)}/{len(considered_h1)} sampled content pages have no <h1> but do "
            f"declare a <title> or a schema.org type, e.g. {', '.join(no_h1_only[:3])}.",
            "The topic is still machine-readable through the title or markup, so this is a "
            "structural improvement rather than a discoverability defect.",
            "Add an H1 that matches each page's title, so the on-page outline starts at the "
            "page's own subject.",
            "low", "structured-data", checked=len(considered_h1), finding_type="improvement",
            confidence="high", mechanism="identify-facts",
            dedup_key="structured-data:no-h1", thin_html_sensitive=True))

    # ---- 9. skipped heading levels ----------------------------------------- #
    skipped_levels = []
    for p in pages:
        prev = 0
        for lvl in (p.get("heading_levels") or []):
            if prev and lvl > prev + 1:
                skipped_levels.append(p["url"])
                break
            prev = lvl
    if skipped_levels and len(skipped_levels) >= max(2, total // 2):
        findings.append(A.finding(
            "Heading levels are skipped, so the document outline has gaps",
            "low",
            f"{len(skipped_levels)}/{total} sampled pages jump more than one heading level "
            f"(for example H1 straight to H3), e.g. {', '.join(skipped_levels[:3])}.",
            "A parser reconstructing the outline sees sections at an unintended depth. "
            "The text itself remains fully readable.",
            "Use heading levels in sequence so each section nests one level below its parent.",
            "low", "structured-data", checked=total, finding_type="improvement",
            confidence="medium", mechanism="identify-facts",
            dedup_key="structured-data:skipped-headings"))

    return findings, skips


if __name__ == "__main__":
    f, s = run(sys.argv[1])
    A.emit(SKILL, f, s)
