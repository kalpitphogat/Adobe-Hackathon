#!/usr/bin/env python3
"""Stage act: is there an action, is it legible, and is there exactly one?"""

from __future__ import annotations

import re

from bundle import action, finding, typed_threshold, threshold
from gating import Rule0b
from orientation import ctas

CHECKS = [
    {"id": "act.cta.absent_for_page_type", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "high", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
    {"id": "act.cta.ambiguous_primary_label", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
    {"id": "act.cta.competing_primaries", "stage": "act", "category": "engagement",
     "tier": "core", "default_severity": "medium", "skill": "engagement-audit",
     "rule_0b_suppressible": True},
]

# Page types where an explicit call to action is expected.
# "other" removed: it is the bucket for pages we could not classify, and
# demanding a call to action from a page whose purpose is unknown asserts more
# than we know. It fired high severity on an interactive tool page.
CTA_EXPECTED = {"home", "product", "pricing", "contact"}

# Labels that name no object. "Submit" tells the visitor nothing about what
# happens next; "Start free trial" does.
AMBIGUOUS = re.compile(
    r"^\s*(submit|send|click here|click|continue|next|go|ok|learn more|read more|more|"
    r"find out more|discover|explore|here|view|see more|details)\s*$", re.I
)

# Controls whose wording is fixed by law or convention and must not be flagged.
LEGALLY_FIXED = re.compile(r"^\s*(accept|accept all|reject|reject all|decline|agree|i agree|manage preferences)\s*$", re.I)


def run(b, profile) -> tuple[list[dict], list[dict], list[dict]]:
    gate = Rule0b(b)
    findings: list[dict] = []
    skipped: list[dict] = []

    for page in b.html_pages():
        page_type = b.page_type(page, profile)
        found = ctas(page)
        forms = [f for f in (page.get("forms") or []) if f.get("field_count")]

        # -------------------------------------------------------- absent
        if page_type in CTA_EXPECTED:
            if not gate.page_allowed("act.cta.absent_for_page_type", page):
                skipped.append(_skip("act.cta.absent_for_page_type", page))
            elif not found and not forms:
                anchors = page.get("anchors") or []
                findings.append(finding(
                    check_id="act.cta.absent_for_page_type",
                    title=f"This {page_type} page offers the visitor nothing to do",
                    severity="high", confidence="likely", stage="act",
                    category="engagement", scope="url",
                    evidence=(
                        f"{page['url']} is a {page_type} page, a type that normally exists to "
                        f"produce an action. It contains {len(anchors)} links and "
                        f"{len(page.get('forms') or [])} form(s), and none of them reads as an "
                        f"action: no link text matches an action verb (sign up, start, book, "
                        f"request, contact, buy, download, subscribe, try) and no form has an "
                        f"input field. Link text present: "
                        f"{', '.join(repr(a['text'][:28]) for a in anchors[:6]) or '(none)'}."
                    ),
                    affected_urls=[page["url"]],
                    action=action(
                        summary="Add one clear primary action naming what the visitor gets.",
                        effort="low",
                        mechanism=(
                            "A page with no action leaves the visitor to invent a next step; most "
                            "invent leaving."
                        ),
                        source="references/cro-frameworks.md",
                        patch='<a class="cta-primary" href="__FILL_IN__:destination">__FILL_IN__:verb_plus_object</a>',
                        verification=f"Open {page['url']}: is there one obvious thing to click?",
                    ),
                ))

        if not found:
            continue

        # ------------------------------------------------------ ambiguous
        primary = found[0]
        if not gate.page_allowed("act.cta.ambiguous_primary_label", page):
            skipped.append(_skip("act.cta.ambiguous_primary_label", page))
        elif LEGALLY_FIXED.match(primary["text"]):
            skipped.append({
                "check_id": "act.cta.ambiguous_primary_label",
                "reason": (
                    f"{page['url']}: the most prominent control is {primary['text']!r}, a consent "
                    f"control whose wording is fixed by convention or law."
                ),
                "confidence_effect": "suppressed by design",
            })
        elif AMBIGUOUS.match(primary["text"]):
            findings.append(finding(
                check_id="act.cta.ambiguous_primary_label",
                title=f"The main action is labelled {primary['text']!r}, which names no outcome",
                severity="medium", confidence="confirmed", stage="act",
                category="engagement", scope="url",
                evidence=(
                    f"{page['url']}: the most prominent action is {primary['text']!r} pointing at "
                    f"{primary['href']!r}. The label carries a verb but no object, so it does not "
                    f"say what the visitor gets by clicking. Other actions on the page: "
                    f"{', '.join(repr(c['text'][:26]) for c in found[1:4]) or '(none)'}."
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Relabel with a verb and its object.",
                    effort="low",
                    mechanism=(
                        "A label that names the outcome lets the visitor evaluate the click before "
                        "making it, which removes the hesitation a bare verb creates."
                    ),
                    source="references/cro-frameworks.md",
                    patch=(
                        f'<!-- was: <a href="{primary["href"]}">{primary["text"]}</a> -->\n'
                        f'<a href="{primary["href"]}">__FILL_IN__:verb_plus_what_they_get</a>'
                    ),
                    verification="Read the label alone, out of context: is it clear what happens next?",
                ),
            ))

        # ---------------------------------------------------- competing
        if not gate.page_allowed("act.cta.competing_primaries", page):
            continue
        prominent = [c for c in found if c["in_main"] and not c["in_chrome"]]
        distinct = []
        seen = set()
        for c in prominent:
            key = c["text"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            distinct.append(c)
        limit = threshold(profile, "competing_primary_ctas_max", 3)
        if len(distinct) > limit:
            findings.append(finding(
                check_id="act.cta.competing_primaries",
                title=f"{len(distinct)} distinct primary actions compete on one page",
                severity="medium", confidence="likely", stage="act",
                category="engagement", scope="url",
                evidence=(
                    f"{page['url']} presents {len(distinct)} distinct action labels in the main "
                    f"content, above a threshold of {limit} for this site type: "
                    f"{', '.join(repr(c['text'][:30]) for c in distinct[:8])}. Repeats of the same "
                    f"label were counted once, and navigation and footer chrome were excluded."
                ),
                affected_urls=[page["url"]],
                action=action(
                    summary="Choose one primary action; demote the rest to secondary styling.",
                    effort="low",
                    mechanism=(
                        "When several actions are presented as equally important the visitor has "
                        "to rank them, and the extra decision costs more conversions than the "
                        "extra options gain."
                    ),
                    source="references/cro-frameworks.md",
                    patch=(
                        f'<a class="cta-primary" href="{distinct[0]["href"]}">{distinct[0]["text"]}</a>\n'
                        + "\n".join(
                            f'<a class="cta-secondary" href="{c["href"]}">{c["text"]}</a>'
                            for c in distinct[1:4]
                        )
                    ),
                    verification=f"Open {page['url']}: squint at the first screen; is one action obviously dominant?",
                ),
            ))

    limitation = gate.limitation()
    return findings, skipped, ([limitation] if limitation else [])


def _skip(check_id: str, page: dict) -> dict:
    return {
        "check_id": check_id,
        "reason": (
            f"{page['url']} serves an unhydrated shell with no rendered DOM, so visible content "
            f"was never observed. Suppressed entirely under gate Rule 0b."
        ),
        "confidence_effect": "suppressed entirely",
    }
