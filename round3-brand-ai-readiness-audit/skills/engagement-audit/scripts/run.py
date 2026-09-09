#!/usr/bin/env python3
"""engagement-audit entry point. Stage: act.

One question: does a visitor who arrives stay and act?

Composes the five check modules in this folder and emits one JSON object per
ai-readiness-orchestrator/references/skill-cli-contract.md. Reads only the
evidence bundle; performs no network I/O.

Gate Rule 0b is enforced here as well as in the orchestrator. Engagement is not
causally downstream of reach, so a robots.txt block never touches these
findings; but it IS evidentially downstream of read, so a page whose content was
never observed produces no engagement findings at all rather than findings at
reduced confidence. See gating.py.

  python run.py --bundle ./evidence [--profile ./profile.json]

Exit codes: 0 ran, 3 precondition unmet, 1 internal error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blockers  # noqa: E402
import context_retention  # noqa: E402
import cta_friction  # noqa: E402
import form_friction  # noqa: E402
import orientation  # noqa: E402
from bundle import emit, load  # noqa: E402
from gating import RULE_0B_SUPPRESSIBLE, Rule0b  # noqa: E402

MODULES = (orientation, cta_friction, form_friction, context_retention, blockers)
SKILL = "engagement-audit"
STAGE = "act"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="run.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--bundle", required=True, help="evidence bundle directory")
    parser.add_argument("--profile", help="site profile JSON from site-profile-classifier")
    args = parser.parse_args(argv)

    b, profile = load(args.bundle, args.profile)

    findings: list[dict] = []
    skipped: list[dict] = []
    proactive: list[dict] = []
    limitations: list[dict] = []

    try:
        for module in MODULES:
            f, s, p = module.run(b, profile)
            findings.extend(f)
            skipped.extend(s)
            # Every module returns the same Rule 0b limitation; keep one copy.
            for item in p:
                if item not in limitations and "reason" in item:
                    limitations.append(item)
                elif item not in proactive and "rationale" in item:
                    proactive.append(item)
    except Exception as exc:  # noqa: BLE001
        print(f"internal error in {SKILL}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    # Safety net: no act finding may survive on a page we never observed, no
    # matter which module produced it. Each module already applies Rule 0b, so
    # this should never remove anything; it exists because a future check that
    # forgets to consult the gate would otherwise report unevidenced findings.
    gate = Rule0b(b)
    unobserved = {p["url"] for p in gate.unobserved}
    kept = []
    for f in findings:
        urls = set(f.get("affected_urls") or [])
        if f["check_id"] in RULE_0B_SUPPRESSIBLE and urls and urls <= unobserved:
            skipped.append({
                "check_id": f["check_id"],
                "reason": (
                    f"suppressed by the Rule 0b safety net: every affected URL "
                    f"({', '.join(sorted(urls))}) is an unobserved shell."
                ),
                "confidence_effect": "suppressed entirely",
            })
            continue
        kept.append(f)

    return emit({
        "skill": SKILL,
        "stage": STAGE,
        "checks_run": [c["id"] for m in MODULES for c in getattr(m, "CHECKS", [])],
        "checks_skipped": skipped,
        "findings": kept,
        "proactive_recommendations": proactive,
        "limitations": limitations,
    })


if __name__ == "__main__":
    sys.exit(main())
