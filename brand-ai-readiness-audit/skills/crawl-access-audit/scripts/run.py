#!/usr/bin/env python3
"""crawl-access-audit entry point. Stage: reach.

One question: can an AI crawler get in at all?

Composes the four check modules in this folder and emits one JSON object per
ai-readiness-orchestrator/references/skill-cli-contract.md. Reads only the
evidence bundle; performs no network I/O.

  python run.py --bundle ./evidence [--profile ./profile.json]

Exit codes: 0 ran, 3 precondition unmet, 1 internal error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_agent_files  # noqa: E402
import check_edge_reach  # noqa: E402
import check_indexability  # noqa: E402
import check_robots  # noqa: E402
from bundle import emit, load  # noqa: E402

MODULES = (check_robots, check_edge_reach, check_indexability, check_agent_files)
SKILL = "crawl-access-audit"
STAGE = "reach"


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
            proactive.extend(p)
            limitations.extend(getattr(module, "LIMITATIONS", []))
    except Exception as exc:  # noqa: BLE001
        print(f"internal error in {SKILL}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if b.meta.get("status") == "no_content_available":
        limitations.append({
            "scope": "site",
            "reason": (
                "No page content was collected, so only origin-level policy could be assessed. "
                + "; ".join(b.meta.get("notes", []))
            ),
            "checks_not_run": sorted(
                c["id"] for m in MODULES for c in getattr(m, "CHECKS", [])
                if c["id"] not in {f["check_id"] for f in findings}
            ),
            "confidence_effect": "page-level reach checks were not assessed",
        })

    return emit({
        "skill": SKILL,
        "stage": STAGE,
        "checks_run": [c["id"] for m in MODULES for c in getattr(m, "CHECKS", [])],
        "checks_skipped": skipped,
        "findings": findings,
        "proactive_recommendations": proactive,
        "limitations": limitations,
    })


if __name__ == "__main__":
    sys.exit(main())
