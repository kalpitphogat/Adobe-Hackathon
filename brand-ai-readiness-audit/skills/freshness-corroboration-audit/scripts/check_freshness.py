#!/usr/bin/env python3
"""freshness-corroboration-audit: is the content current and cross-verifiable?
Round-2 appendix D: machines trust facts that are fresh and agreed-upon across the
web, and get confused by name collisions. Usage: check_freshness.py <cache_dir>"""
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "audit-orchestrator", "scripts")))
import auditlib as A  # noqa: E402

SKILL = "freshness-corroboration-audit"
NOW = datetime.date.today()


def run(cache_dir):
    meta = A.load_meta(cache_dir)
    pages = [p for p in meta["pages"] if p["status"] == 200]
    findings = []
    if not pages:
        return findings

    # 1. Stale copyright / dates
    stale_years = []
    for p in pages:
        text = A.read_page(cache_dir, p, "text") or ""
        for m in re.finditer(r"(?:©|copyright|&copy;)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", text, re.I):
            yr = int(m.group(1))
            if yr < NOW.year - 1 and yr > 2000:
                stale_years.append((p["url"], yr))
                break
    if stale_years:
        oldest = min(y for _, y in stale_years)
        findings.append(A.finding(
            "Stale copyright / last-updated year",
            "medium",
            f"{len(stale_years)} page(s) show a copyright year of {oldest} or earlier "
            f"(current year {NOW.year}), e.g. {stale_years[0][0]} ({stale_years[0][1]}).",
            "Update the footer year and surface a visible 'last updated' date on time-sensitive "
            "pages. Stale dates signal abandonment and lower an assistant's trust in the facts.",
            "medium", "freshness", checked=len(pages)))

    # 2. No machine-readable dates on article-like pages
    dated, article_like = 0, 0
    for p in pages:
        html = A.read_page(cache_dir, p, "html") or ""
        low = html.lower()
        is_article = ("article" in low and ("datepublished" in low or "<time" in low
                                            or "/blog/" in p["url"].lower() or "/news/" in p["url"].lower()
                                            or "/article" in p["url"].lower()))
        if "/blog/" in p["url"].lower() or "/news/" in p["url"].lower() or "/article" in p["url"].lower():
            article_like += 1
            if "datepublished" in low or "datemodified" in low or "<time" in low:
                dated += 1
    if article_like and dated == 0:
        findings.append(A.finding(
            "Article/blog pages have no machine-readable publish date",
            "medium",
            f"{article_like} article-like page(s) expose no <time>, datePublished, or dateModified.",
            "Add datePublished/dateModified (in Article JSON-LD and a visible <time> element) so "
            "assistants can judge recency and prefer current sources.",
            "medium", "freshness", checked=article_like))

    # 3. Entity-collision / disambiguation risk
    home = pages[0]
    home_html = A.read_page(cache_dir, home, "html") or ""
    low = home_html.lower()
    has_sameas = "sameas" in low
    has_about = any(k in low for k in ["about", "who we are", "what we do"])
    if not has_sameas:
        findings.append(A.finding(
            "Weak entity corroboration (identity lives only on this site)",
            "medium",
            "Homepage declares no sameAs/external identity links; the brand's facts are not tied "
            "to independent, agreeing sources.",
            "Establish and link consistent profiles across independent sources (Wikidata, "
            "LinkedIn, industry directories, press) and reference them via sameAs. Agreement "
            "across unrelated sources is what makes a fact trusted and repeated.",
            "medium", "corroboration"))
    if not has_about:
        findings.append(A.finding(
            "No clear identity/‘about’ statement to distinguish the brand",
            "low",
            "Homepage text lacks an explicit about/who-we-are statement.",
            "State plainly who the brand is, what it does, and what makes it distinct, so systems "
            "don't confuse it with similarly named entities.",
            "low", "corroboration"))

    # 4. Unqualified superlative claims with no attribution (fragile single-source facts)
    superlatives = 0
    for p in pages[:6]:
        text = A.read_page(cache_dir, p, "text") or ""
        superlatives += len(re.findall(r"\b(?:best|#1|number one|world'?s leading|award-winning|"
                                       r"top-rated|fastest|most trusted)\b", text, re.I))
    if superlatives >= 3:
        findings.append(A.finding(
            "Unattributed superlative claims",
            "low",
            f"Found ~{superlatives} superlative marketing claims (e.g. 'best', '#1', "
            "'world-leading') without visible third-party attribution across sampled pages.",
            "Back strong claims with attributable evidence (named awards, cited rankings, dated "
            "sources). Unverifiable single-source claims are discounted and rarely repeated by assistants.",
            "low", "corroboration", checked=min(6, len(pages))))

    return findings


if __name__ == "__main__":
    A.emit(SKILL, run(sys.argv[1]))
