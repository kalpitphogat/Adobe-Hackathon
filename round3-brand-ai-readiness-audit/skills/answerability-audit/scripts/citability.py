#!/usr/bin/env python3
"""Stage extract: does the page carry the evidence markers that make it quotable?

Grounded in Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan and Deshpande,
"GEO: Generative Engine Optimization", KDD 2024 (arXiv:2311.09735). The paper
formalises optimisation for generative engines, builds GEO-bench over 10,000
queries, and tests nine content rewrites; the ones that reliably increased a
page's visibility in synthesised answers were citing sources, adding statistics
and adding quotations, reported as up to a 40% relative improvement in their
setup, while keyword stuffing did not help.

We report the ABSENCE of all three together, at LOW severity, because the paper
measures a relative visibility effect in a benchmark, not a defect in the page.
A page can be excellent without statistics. Reporting this as high severity
would overstate what the evidence supports.
"""

from __future__ import annotations

import re

from bundle import action, finding, threshold
from retrievability_sim import derive_entity, tokens

CHECKS = [
    {"id": "extract.ans.no_evidence_markers", "stage": "extract", "category": "discoverability",
     "tier": "core", "default_severity": "low", "skill": "answerability-audit"},
]

# Page types where citations and statistics are not the idiom.
NOT_IDIOMATIC = {"product", "contact", "utility", "category", "home"}

STATISTIC = re.compile(
    r"(\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s?%"
    r"|\b\d+(?:\.\d+)?\s?(?:x|times)\b"
    r"|\b\d{2,}(?:,\d{3})*\s+(?:customers|users|companies|teams|people|hours|minutes|seconds|days))",
    re.I,
)
QUOTATION = re.compile(r"[“\"][^”\"]{40,}[”\"]")
CITATION_TEXT = re.compile(
    r"\b(according to|as reported by|research by|a study (by|from)|per the|source:)\b", re.I
)


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []
    min_words = threshold(profile, "evidence_markers_min_words", 400)

    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        text = b.observed_text(page)
        words = len(tokens(text))

        if page_type in NOT_IDIOMATIC:
            continue
        if words < min_words:
            skipped.append({
                "check_id": "extract.ans.no_evidence_markers",
                "reason": (
                    f"{page['url']}: {words} words, below the {min_words}-word floor for this "
                    f"archetype. A short page is not expected to carry statistics or citations."
                ),
                "confidence_effect": "suppressed by threshold",
            })
            continue

        stats = STATISTIC.findall(text)
        quotes = QUOTATION.findall(text)
        cites_text = CITATION_TEXT.findall(text)
        external = (page.get("links") or {}).get("external") or []
        # An external link inside main content reads as a source reference.
        cites = len(cites_text) + len([a for a in (page.get("anchors") or [])
                                       if a.get("in_main") and a.get("href", "").startswith("http")])

        if stats or quotes or cites:
            continue

        entity = derive_entity(b, page)
        findings.append(finding(
            check_id="extract.ans.no_evidence_markers",
            title="This page makes claims with no statistic, quotation or source behind them",
            severity="low", confidence="confirmed", stage="extract",
            category="discoverability", scope="url",
            evidence=(
                f"{page['url']} ({words} words, page type {page_type}) contains 0 statistics, "
                f"0 block quotations of 40 characters or more, 0 attribution phrases such as "
                f"\"according to\", and 0 outbound source links in its main content. "
                f"Aggarwal et al. (GEO, KDD 2024, arXiv:2311.09735) found that adding citations, "
                f"statistics and quotations reliably increased how prominently a page was used in "
                f"synthesised answers, by up to 40% relative in their benchmark, while keyword "
                f"stuffing did not. Reported at LOW severity because that is a measured relative "
                f"improvement, not a defect: this page is not broken without them."
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="Support the page's main claims with a specific number and a named source.",
                effort="medium",
                mechanism=(
                    "A specific, attributed number is directly quotable and independently "
                    "checkable, which makes the passage more useful to reproduce than an "
                    "unsupported assertion of the same claim."
                ),
                source=(
                    "Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan, Deshpande, "
                    "GEO: Generative Engine Optimization, KDD 2024, arXiv:2311.09735"
                ),
                patch=(
                    f"<!-- Before: an unsupported claim -->\n"
                    f"<p>{entity or '__FILL_IN__:subject'} is fast and reliable.</p>\n\n"
                    f"<!-- After: the same claim with a statistic and an inline source -->\n"
                    f"<p>{entity or '__FILL_IN__:subject'} __FILL_IN__:claim, cutting "
                    f"__FILL_IN__:metric from __FILL_IN__:before to __FILL_IN__:after "
                    f"(<a href=\"__FILL_IN__:source_url\">__FILL_IN__:source_name</a>, "
                    f"__FILL_IN__:year).</p>"
                ),
                verification=(
                    f"curl -s {page['url']} | sed -e 's/<[^>]*>//g' | grep -cE "
                    f"'[0-9]+%|according to'"
                ),
            ),
        ))

    return findings, skipped, []
