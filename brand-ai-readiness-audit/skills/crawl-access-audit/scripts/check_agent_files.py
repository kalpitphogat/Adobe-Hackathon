#!/usr/bin/env python3
"""Stage reach: agent-facing files (llms.txt, markdown negotiation).

This file is where we most visibly disagree with the rest of the field. Nearly
every AI-readiness tool reports a missing llms.txt as a high-severity defect. We
report it as LOW, and only on sites where an agent-facing surface is plausibly
useful at all, and we put the reasoning in the finding text so the reader can
check it rather than take our word for it.

Every claim in that finding text is sourced. Nothing here is asserted without a
primary source that was actually read.
"""

from __future__ import annotations

from bundle import action, finding, threshold

CHECKS = [
    {"id": "reach.agent.llms_txt_absent", "stage": "reach", "category": "discoverability",
     "tier": "core", "default_severity": "low", "skill": "crawl-access-audit"},
]

# Archetypes where an agent-facing text surface is plausibly worth maintaining.
AGENT_FACING = {"docs", "developer-platform"}


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    findings: list[dict] = []
    skipped: list[dict] = []
    proactive: list[dict] = []

    archetype = (profile or {}).get("archetype", "other")
    llms = b.probes.get("llms_txt") or {}
    status = llms.get("status")
    present = status is not None and 200 <= status < 300

    surface = threshold(profile, "surface_llms_txt", archetype in AGENT_FACING)

    if present:
        skipped.append({
            "check_id": "reach.agent.llms_txt_absent",
            "reason": f"llms.txt is present at {llms.get('url')} (HTTP {status}).",
            "confidence_effect": "not applicable",
        })
    elif not surface:
        # SUPPRESS: the dominant false positive in this field.
        skipped.append({
            "check_id": "reach.agent.llms_txt_absent",
            "reason": (
                f"llms.txt is absent (HTTP {status}), but this site is classified as "
                f"'{archetype}', not a documentation or developer-platform site. We do not "
                f"surface a missing llms.txt outside those archetypes, because no primary source "
                f"establishes a retrieval benefit and reporting it would spend the reader's "
                f"attention on a file that has not been shown to do anything."
            ),
            "confidence_effect": "suppressed by design",
        })
    else:
        findings.append(finding(
            check_id="reach.agent.llms_txt_absent",
            title="No llms.txt — reported at LOW severity, deliberately, and here is why",
            severity="low", confidence="confirmed", stage="reach",
            category="discoverability", scope="site",
            evidence=(
                f"{b.origin}/llms.txt returned HTTP {status}. This site is classified as "
                f"'{archetype}', an archetype where an agent-facing text surface is plausibly "
                f"useful, which is the only reason this appears at all.\n\n"
                f"Why we score this LOW when most audit tools score it HIGH: Google Search "
                f"Central states plainly that \"You don't need to create new machine readable "
                f"files, AI text files, markup, or Markdown to appear in Google Search (including "
                f"its generative AI capabilities), as Google Search itself doesn't use them\", and "
                f"that maintaining such files \"will neither harm nor help your site's visibility "
                f"or rankings in Google Search, as Google Search ignores them\". No major "
                f"assistant provider has publicly committed to consuming llms.txt at answer time. "
                f"SE Ranking's analysis of nearly 300,000 domains found that only 10.13% had an "
                f"llms.txt file, and reported no measurable citation benefit.\n\n"
                f"So this is a cheap, low-risk thing to add for agent consumers of your docs. It "
                f"is not a fix for AI visibility, and any tool that tells you it is has not "
                f"checked."
            ),
            affected_urls=[b.origin + "/llms.txt"],
            action=action(
                summary=(
                    "Optionally publish an llms.txt index of your documentation. Do this for the "
                    "convenience of agent users, not in expectation of a ranking or citation effect."
                ),
                effort="low",
                mechanism=(
                    "A curated plain-text index gives an agent already reading your docs a shorter "
                    "path to the right page; it does not influence whether retrieval systems find "
                    "the site in the first place."
                ),
                source=(
                    "Google Search Central, Optimizing your website for generative AI features "
                    "(developers.google.com/search/docs/fundamentals/ai-optimization-guide); "
                    "SE Ranking, llms.txt study of ~300,000 domains, November 2025"
                ),
                patch=_llms_patch(b, profile),
                verification=f"curl -sI {b.origin}/llms.txt | head -1  # expect HTTP 200",
            ),
        ))

    # Markdown negotiation is a proactive recommendation, never a defect.
    md = b.probes.get("markdown_negotiation") or {}
    md_status = md.get("accept_text_markdown_status")
    if md_status is not None and not (md.get("content_type") or "").startswith("text/markdown"):
        if archetype in AGENT_FACING:
            proactive.append({
                "id": "PROACTIVE",
                "check_id": "reach.agent.no_markdown_negotiation",
                "title": "Consider serving a Markdown representation of documentation pages",
                "rationale": (
                    f"A request for {b.origin}/ with Accept: text/markdown returned "
                    f"content-type {md.get('content_type') or 'none'}. Agents that consume "
                    f"documentation handle Markdown with less loss than HTML, because there is no "
                    f"navigation chrome to strip. This is an ergonomics improvement for agent "
                    f"readers, with no evidence of a retrieval or ranking effect, which is why it "
                    f"is a recommendation and not a finding."
                ),
                "applies_to_archetype": sorted(AGENT_FACING),
                "suggested_action": action(
                    summary="Serve .md alongside .html for documentation routes, or honour Accept: text/markdown.",
                    effort="medium",
                    mechanism=(
                        "Markdown carries the document structure without the navigation and "
                        "styling wrapper, so an agent extracting a fact has less to discard."
                    ),
                    source="No primary source claims a retrieval benefit; offered on ergonomics grounds only.",
                    patch="# Route /docs/<slug>.md to the same content rendered as Markdown.",
                    verification=f"curl -sH 'Accept: text/markdown' -I {b.origin}/ | grep -i content-type",
                ),
            })

    return findings, skipped, proactive


def _llms_patch(b, profile) -> str:
    """Build an llms.txt from pages we actually observed. No invented URLs."""
    pages = [p for p in b.html_pages() if b.page_type(p, profile) in ("docs", "article", "home")]
    pages.sort(key=lambda p: p["url"])
    site = b.site or "__FILL_IN__:site_name"
    home = next((p for p in b.html_pages() if p["url"].rstrip("/") == b.origin.rstrip("/")), None)
    summary = (home or {}).get("meta_description") or "__FILL_IN__:one_line_site_summary"
    lines = [f"# {site}", "", f"> {summary}", "", "## Documentation", ""]
    for page in pages[:20]:
        title = page.get("title") or "__FILL_IN__:page_title"
        lines.append(f"- [{title}]({page['url']})")
    return "\n".join(lines) + "\n"
