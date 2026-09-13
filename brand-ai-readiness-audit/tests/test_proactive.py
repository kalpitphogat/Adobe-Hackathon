#!/usr/bin/env python3
"""Beyond-defect recommendations: relevant to the archetype, silent otherwise.

The handout asks for suggestions that "go beyond the detected problems --
proactive improvements that would strengthen discoverability or engagement even
where no explicit defect was found". The trap is that generic advice is easy to
emit and worth nothing: "add structured data" to a site that already has it
reads as padding and costs credibility.

So every recommendation here is gated twice -- on the archetype it is relevant
to, and on the absence of the defect that would make it redundant. A site with
the defect gets a finding, which is specific and actionable; a site without it
gets the recommendation. Never both, and never neither.

Run: python tests/test_proactive.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "ai-readiness-orchestrator" / "scripts"))

import orchestrate as orch  # noqa: E402

FAILURES: list[str] = []
COUNT = 0


def expect(cond: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not cond:
        FAILURES.append(label)


def recs(archetype: str, fired: list[str] | None = None) -> list[dict]:
    findings = [{"check_id": c} for c in (fired or [])]
    return orch.build_proactive({"archetype": archetype}, findings, [])


# Every archetype the classifier can assign, and the defect that makes its
# recommendation redundant.
GATED = {
    "docs": "extract.sd.absent_on_eligible_page",
    "developer-platform": "extract.sd.absent_on_eligible_page",
    "e-commerce": "extract.sd.required_props_missing",
    "publisher": "trust.authorship.unattributed",
    "local-business": "trust.entity.nap_inconsistent",
}

for archetype, blocking_check in GATED.items():
    clean = recs(archetype)
    expect(len(clean) >= 1, f"P1: {archetype} gets at least one beyond-defect recommendation")

    blocked = recs(archetype, [blocking_check])
    expect(len(blocked) < len(clean),
           f"P2: {archetype} withholds its recommendation when {blocking_check} already fired")

# saas-marketing is ungated on purpose: a comparison page is a gap in coverage,
# not a repair of any check, so no finding can make it redundant.
expect(len(recs("saas-marketing")) >= 1, "P3: saas-marketing gets a recommendation")
expect(len(recs("saas-marketing", list(GATED.values()))) >= 1,
       "P3: the saas-marketing recommendation is a coverage gap, so no finding suppresses it")

# An unclassified site gets nothing rather than generic filler. This is the
# assertion that keeps the whole mechanism honest.
expect(recs("other") == [],
       "P4: an unclassified site gets no archetype advice rather than generic advice")

# Every recommendation has to be actionable to the same standard as a finding:
# a reader must be able to see what to do, why it works, and how to check it.
seen_titles: set[str] = set()
for archetype in list(GATED) + ["saas-marketing"]:
    for rec in recs(archetype):
        where = f"{archetype}/{rec.get('title', '?')[:40]}"
        expect(bool(rec.get("title")), f"P5: {where} has a title")
        expect(bool(rec.get("rationale")), f"P5: {where} says why it matters")
        expect(archetype in (rec.get("applies_to_archetype") or []),
               f"P5: {where} declares the archetype it applies to")

        action = rec.get("suggested_action") or {}
        for field in ("summary", "priority", "effort", "mechanism", "verification"):
            expect(bool(action.get(field)), f"P6: {where} suggested_action has {field}")

        # Beyond-defect advice must never outrank a real defect in the queue.
        expect(action.get("priority") == "low",
               f"P7: {where} is prioritised below every actual finding")

        # A patch a reader is meant to paste must mark what they have to supply,
        # or they paste a placeholder into production.
        patch = action.get("patch")
        if patch:
            expect("__FILL_IN__" in patch,
                   f"P8: {where} marks the values the reader must supply")

        seen_titles.add(rec["title"])

expect(len(seen_titles) == len(set(seen_titles)),
       "P9: no two archetypes emit the same recommendation text")

# Recommendations collected from the audit skills pass through untouched.
carried = {"title": "from a skill", "rationale": "r", "suggested_action": {"summary": "s"}}
expect(carried in orch.build_proactive({"archetype": "other"}, [], [carried]),
       "P10: recommendations emitted by the audit skills are preserved, not replaced")

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} beyond-defect recommendation assertions")
