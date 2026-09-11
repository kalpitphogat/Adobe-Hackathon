#!/usr/bin/env python3
"""freshness-corroboration-audit: are the facts current, and is the entity
identifiable beyond this one site?

Mechanism 4 of the chain - are the facts fresh and corroborated. This skill is
strict about what it may claim. It checks the site's own markup and text; it does
not query external sources. Therefore it never concludes that a brand lacks
external corroboration - only that the site does or does not declare any.

Usage: check_freshness.py <cache_dir>
"""
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "freshness-corroboration-audit"
NOW = datetime.date.today()

COPYRIGHT = re.compile(r"(?:©|\(c\)|copyright|&copy;)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", re.I)
SUPERLATIVE = re.compile(
    r"\b(?:#1|number one|world'?s (?:leading|best)|award-winning|top-rated|"
    r"most trusted|industry-leading)\b", re.I)


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = A.html_pages(meta)
    findings, skips = [], []

    non_html = A.non_html_resources(meta)
    if non_html:
        skips.append(A.skipped(
            "freshness and corroboration checks on non-HTML resources",
            f"{len(non_html)} crawled resource(s) are not HTML documents; copyright lines, "
            "publish dates and entity markup are page-level properties."))
    if not pages:
        skips.append(A.skipped("all freshness checks",
                               "no HTML page was retrieved in this crawl"))
        return findings, skips

    # ---- 1. stale copyright ------------------------------------------------- #
    stale = []
    for p in pages:
        text = A.read_page(cache_dir, p, "text") or ""
        years = [int(m) for m in COPYRIGHT.findall(text) if 2000 < int(m) <= NOW.year + 1]
        if years and max(years) < NOW.year - 1:
            stale.append((p["url"], max(years)))
    if stale:
        oldest = min(y for _, y in stale)
        findings.append(A.finding(
            "Copyright year in page text is more than one year out of date",
            "low",
            f"{len(stale)}/{len(pages)} sampled pages show a most-recent copyright year of "
            f"{oldest} or earlier against the current year {NOW.year}, e.g. "
            + ", ".join(f"{u} ({y})" for u, y in stale[:3]) + ".",
            "A visibly old copyright line is one of several signals a reader may use to judge "
            "whether a site is maintained. It says nothing directly about whether the content "
            "itself is current, which this audit did not assess.",
            "Render the footer year from the current date rather than a hard-coded value, and "
            "surface a real last-reviewed date on pages whose facts change.",
            "low", "freshness", checked=len(pages), finding_type="improvement",
            confidence="high", mechanism="freshness", dedup_key="freshness:stale-copyright",
            not_verified="whether the page content itself is out of date"))

    # ---- 2. article publish dates -------------------------------------------- #
    # Only pages confidently classified as articles; a URL containing "/blog" is
    # not on its own treated as an article.
    articles = [p for p in pages if A.role_of(p) == "article" and A.role_confident(p)]
    if articles:
        undated = []
        for p in articles:
            html = (A.read_page(cache_dir, p, "html") or "").lower()
            has_date = (p.get("n_time_elements", 0) > 0
                        or "datepublished" in html or "datemodified" in html
                        or "article:published_time" in html)
            if not has_date:
                undated.append(p["url"])
        if undated:
            findings.append(A.finding(
                "Article pages expose no machine-readable publication date",
                "medium",
                f"{len(undated)}/{len(articles)} sampled pages classified as articles declare "
                "no <time> element, no datePublished or dateModified property and no "
                "article:published_time meta tag: " + ", ".join(undated[:4]) + ".",
                "Recency is one of the inputs used when choosing between sources that make "
                "competing claims. Without a declared date, a consumer cannot place these "
                "pages on a timeline except by guessing from the text.",
                "Emit datePublished and dateModified in the Article JSON-LD on these pages, "
                "and show the same date to readers in a <time datetime=\"...\"> element.",
                "medium", "freshness", checked=len(articles), confidence="high", material=True,
                mechanism="freshness", dedup_key="freshness:undated-articles"))
    else:
        skips.append(A.skipped(
            "article publication dates",
            "no sampled page was confidently classified as an article, so no page was "
            "assessed for a publication date."))

    # ---- 3. entity corroboration -------------------------------------------- #
    # Reports exactly what was inspected. Absence of sameAs is never reported as
    # absence of external corroboration: no external source was queried.
    home = A.homepage_of(meta)
    if home is not None:
        home_html = A.read_page(cache_dir, home, "html") or ""
        has_sameas = '"sameas"' in home_html.lower()
        if not has_sameas:
            findings.append(A.finding(
                "No sameAs relationships detected in homepage structured data",
                "low",
                "The homepage's server HTML was searched for a sameAs property in its "
                "structured data, and none was found.",
                "sameAs is how a page asserts which external profiles refer to the same "
                "entity. This audit inspected the homepage markup only. It did not query "
                "Wikidata, search engines, social platforms or any other external source, so "
                "it makes no claim about whether such sources exist, agree, or describe this "
                "brand at all.",
                "If the brand has authoritative external profiles, list them in the "
                "Organization node's sameAs array so the connection is stated rather than "
                "left to be inferred.",
                "low", "corroboration", checked=1, checked_unit="homepage",
                finding_type="improvement",
                confidence="high", page_role="homepage", mechanism="corroborate",
                dedup_key="corroboration:entity-sameas",
                not_verified="whether external sources describing this brand exist or agree; "
                             "no external source was queried by this audit"))

    # ---- 4. unattributed superlatives ---------------------------------------- #
    sample = pages[:6]
    hits = []
    for p in sample:
        text = A.read_page(cache_dir, p, "text") or ""
        found = SUPERLATIVE.findall(text)
        if found:
            hits.append((p["url"], len(found)))
    n_claims = sum(n for _, n in hits)
    if n_claims >= 3:
        findings.append(A.finding(
            "Superlative claims appear without a named source",
            "low",
            f"{n_claims} superlative marketing phrase(s) such as \"#1\", \"world-leading\" or "
            f"\"award-winning\" were found across {len(hits)}/{len(sample)} sampled pages, "
            "e.g. " + ", ".join(f"{u} ({n})" for u, n in hits[:3]) + ".",
            "Whether each claim is attributed nearby was not determined; the audit matched the "
            "phrases, not their context. Claims that carry a named award, ranking or date are "
            "easier for a reader to verify than ones that do not.",
            "Where these claims are backed by a specific award, ranking or study, name it and "
            "date it next to the claim, and link the source.",
            "low", "corroboration", checked=len(sample), finding_type="improvement",
            confidence="low", mechanism="corroborate",
            dedup_key="corroboration:unattributed-claims",
            not_verified="whether each claim is attributed in its surrounding context"))

    return findings, skips


if __name__ == "__main__":
    f, s = run(sys.argv[1])
    A.emit(SKILL, f, s)
