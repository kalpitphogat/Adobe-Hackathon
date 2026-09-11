#!/usr/bin/env python3
"""Stage read: can a crawler read the page without executing JavaScript?

Two paths, and the difference between them is the honest boundary of the
zero-dependency tier:

  raw_text_gap      quantified diff of raw versus rendered text. Needs a
                    renderer, so it is ENRICHMENT. When no rendered DOM exists
                    it does not fire at all - it becomes a limitation.
  empty_spa_shell   static signature of an unhydrated mount point. Needs no
                    browser, so it is CORE, and it is how a zero-install run
                    still reports a render-stage problem. It fires at high /
                    likely instead of critical / confirmed, because without a
                    render we cannot quantify what is missing.

The shell signature is deliberately conservative: all four signals must agree.
A false positive here caps the site's whole discoverability report under gate
Rule 2 and suppresses 14 engagement checks under Rule 0b, so the cost of being
wrong is unusually high.
"""

from __future__ import annotations

from bundle import action, finding, threshold

CHECKS = [
    {"id": "read.render.raw_text_gap", "stage": "read", "category": "discoverability",
     "tier": "enrichment", "default_severity": "critical", "skill": "render-gap-audit"},
    {"id": "read.render.empty_spa_shell", "stage": "read", "category": "discoverability",
     "tier": "core", "default_severity": "critical", "skill": "render-gap-audit"},
    {"id": "read.render.nav_links_js_only", "stage": "read", "category": "discoverability",
     "tier": "enrichment", "default_severity": "high", "skill": "render-gap-audit"},
]


def _first_sentences(text: str, n: int = 3) -> list[str]:
    import re

    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 40]
    return parts[:n]


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []

    renderer_missing = "rendered_dom" in b.degraded_capabilities()
    rendered_pages = [p for p in b.html_pages() if p.get("rendered_available")]

    min_rendered = threshold(profile, "render_gap_min_rendered_words", 200)
    max_ratio = threshold(profile, "render_gap_raw_ratio_max", 0.3)

    # ------------------------------------------------------- raw_text_gap
    if not rendered_pages:
        skipped.append({
            "check_id": "read.render.raw_text_gap",
            "reason": (
                "no page has a rendered DOM, so the raw-versus-rendered difference cannot be "
                "measured. This check requires a headless browser and is in the ENRICHMENT tier. "
                + ("The renderer was unavailable: "
                   + "; ".join(d["reason"] for d in b.degraded if d["capability"] == "rendered_dom")
                   if renderer_missing else "")
            ),
            "confidence_effect": "not assessed",
        })
        skipped.append({
            "check_id": "read.render.nav_links_js_only",
            "reason": "no rendered DOM, so the raw and rendered link graphs cannot be compared.",
            "confidence_effect": "not assessed",
        })
    else:
        gapped = []
        for page in rendered_pages:
            raw_words = page.get("main_wordcount") or 0
            rendered_words = page.get("rendered_main_wordcount") or page.get("rendered_wordcount") or 0
            if rendered_words < min_rendered:
                continue
            ratio = raw_words / rendered_words if rendered_words else 0.0
            if ratio >= max_ratio:
                continue
            raw_text = page.get("main_text") or ""
            rendered_text = page.get("rendered_text") or ""
            only_rendered = [
                s for s in _first_sentences(rendered_text, 8) if s[:60] not in raw_text
            ][:3]
            gapped.append((page, raw_words, rendered_words, ratio, only_rendered))

        for page, raw_words, rendered_words, ratio, quotes in gapped:
            quoted = " ".join(f'"{q[:120]}"' for q in quotes) or "(no clean sentence boundary to quote)"
            findings.append(finding(
                check_id="read.render.raw_text_gap",
                title=f"Most of this page's text only exists after JavaScript runs",
                severity="critical", confidence="confirmed", stage="read",
                category="discoverability", scope="url",
                evidence=(
                    f"{page['url']}: raw HTML main content is {raw_words} words, the rendered DOM "
                    f"is {rendered_words} words, so a crawler that does not execute JavaScript "
                    f"sees {ratio:.0%} of the content. Present only after rendering: {quoted}"
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Server-render or pre-render the main content so it is present in the initial HTML response.",
                    effort="high",
                    mechanism=(
                        "Retrieval crawlers fetch and parse the HTML response; content assembled "
                        "later by client-side JavaScript is not in that response, so the fact "
                        "cannot be extracted even though a human sees it."
                    ),
                    source="Handout appendix, How machines read a page",
                    patch=(
                        "# Framework-level change, not a markup patch. Options in rough order of effort:\n"
                        "#   1. Enable server-side rendering or static generation for this route.\n"
                        "#   2. Pre-render this route at build time if its content is not per-user.\n"
                        "#   3. As a stopgap, inline the key facts into the initial HTML, including\n"
                        "#      inside <noscript>, so a non-executing reader still receives them."
                    ),
                    verification=(
                        f"curl -s {page['url']} | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w\n"
                        f"# expect close to {rendered_words}, currently about {raw_words}"
                    ),
                ),
            ))

        # ---------------------------------------------- nav_links_js_only
        for page in rendered_pages:
            raw_links = len((page.get("links") or {}).get("internal", []))
            rendered_links = page.get("rendered_internal_link_count") or 0
            if rendered_links < 5 or raw_links >= rendered_links * 0.6:
                continue
            findings.append(finding(
                check_id="read.render.nav_links_js_only",
                title="The internal link graph only exists after JavaScript runs",
                severity="high", confidence="confirmed", stage="read",
                category="discoverability", scope="url",
                evidence=(
                    f"{page['url']}: the raw HTML contains {raw_links} internal links, the "
                    f"rendered DOM contains {rendered_links}. A crawler that does not execute "
                    f"JavaScript has {rendered_links - raw_links} fewer paths onward from this "
                    f"page, so pages reachable only through those links may never be discovered."
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Emit navigation and listing links as real <a href> elements in the initial HTML.",
                    effort="medium",
                    mechanism=(
                        "Crawl discovery follows anchors in the served HTML; a link that only "
                        "exists after hydration is not a link the crawler can follow."
                    ),
                    source="Handout appendix, How search visibility works",
                    patch=(
                        "<!-- Render navigation server-side. A router link must still emit an href: -->\n"
                        '<a href="/products/widget">Widget</a>\n'
                        "<!-- not: <div onclick=\"navigate(...)\">Widget</div> -->"
                    ),
                    verification=f"curl -s {page['url']} | grep -o 'href=\"/[^\"]*\"' | sort -u | wc -l",
                ),
            ))

    # ---------------------------------------------------- empty_spa_shell
    shells = [p for p in b.html_pages() if p.get("looks_like_spa_shell")]
    for page in shells:
        signals = page.get("spa_signals") or {}
        # SUPPRESS: a shell whose content we DID render is a render-gap finding,
        # not a shell finding; raw_text_gap above covers it with better evidence.
        if page.get("rendered_available"):
            skipped.append({
                "check_id": "read.render.empty_spa_shell",
                "reason": (
                    f"{page['url']} is an unhydrated shell in raw HTML, but a rendered DOM was "
                    f"captured, so read.render.raw_text_gap reports it with a quantified gap "
                    f"instead."
                ),
                "confidence_effect": "deduped into raw_text_gap",
            })
            continue
        core_only = "rendered_dom" in b.degraded_capabilities()
        findings.append(finding(
            check_id="read.render.empty_spa_shell",
            title="The served HTML is an empty application shell with no content",
            severity="high" if core_only else "critical",
            confidence="likely" if core_only else "confirmed",
            stage="read", category="discoverability", scope="url",
            evidence=(
                f"{page['url']} serves {signals.get('body_wordcount', 0)} words of body text. "
                f"The framework mount point {signals.get('framework_root')} contains "
                f"{signals.get('framework_root_wordcount', 0)} words, "
                f"{len(signals.get('bundle_scripts') or [])} JavaScript bundle(s) are loaded "
                f"({', '.join((signals.get('bundle_scripts') or [])[:2])}), and the <noscript> "
                f"fallback carries {signals.get('noscript_wordcount', 0)} words. A crawler that "
                f"does not execute JavaScript receives an empty page."
                + (
                    " No renderer was available, so this is reported at high/likely rather than "
                    "critical/confirmed: we can see the shell signature but cannot measure what "
                    "the visitor would have seen."
                    if core_only else ""
                )
            ),
            affected_urls=[page["url"]],
            action=action(
                summary="Server-render or pre-render this route so the initial HTML response carries the content.",
                effort="high",
                mechanism=(
                    "The mount point is empty in the served HTML, so every downstream signal - "
                    "structured data, headings, facts - is absent at the moment the crawler reads "
                    "the page."
                ),
                source="Handout appendix, How machines read a page",
                patch=(
                    "# Enable SSR or static generation for this route.\n"
                    "# Minimum viable stopgap: put the page's key facts in the initial HTML.\n"
                    "<noscript>\n"
                    "  <h1>__FILL_IN__:page_h1</h1>\n"
                    "  <p>__FILL_IN__:one_paragraph_summary_of_this_page</p>\n"
                    "</noscript>"
                ),
                verification=(
                    f"curl -s {page['url']} | sed -e 's/<[^>]*>//g' | tr -s '[:space:]' ' ' | wc -w\n"
                    f"# currently about {signals.get('body_wordcount', 0)}; expect the real content length"
                ),
            ),
        ))

    return findings, skipped, []
