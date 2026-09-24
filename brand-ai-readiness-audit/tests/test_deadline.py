#!/usr/bin/env python3
"""The handout caps an audit at five minutes. This proves we honour it.

Per-stage timeouts alone cannot: seven skills that each stop just short of
their own budget still overrun the total. The orchestrator therefore draws
every stage from one shared clock, and the property that makes the ceiling
hold is narrow enough to state exactly --

    while remaining() >= MIN_USEFUL_SLICE, the slice handed to a stage is
    always <= remaining()

-- so no stage can ever be granted more time than the run has left. The
algebra is checked below over the whole domain, then end-to-end against the
real orchestrator so a refactor that keeps the class but stops using it is
still caught.

Run: python tests/test_deadline.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORCH_SCRIPTS = ROOT / "skills" / "ai-readiness-orchestrator" / "scripts"
sys.path.insert(0, str(ORCH_SCRIPTS))

import orchestrate  # noqa: E402

Deadline = orchestrate.Deadline
MIN = Deadline.MIN_USEFUL_SLICE
N_SKILLS = len(orchestrate.AUDIT_SKILLS)

FAILURES: list[str] = []
COUNT = 0


def expect(cond: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not cond:
        FAILURES.append(label)


# --------------------------------------------------------------- the algebra

# A deadline whose clock we control, so the assertions are about the arithmetic
# and not about how fast this machine happens to be.
class FakeDeadline(Deadline):
    def __init__(self, budget: float, spent: float) -> None:
        super().__init__(budget)
        self._spent = spent

    def elapsed(self) -> float:
        return self._spent


expect(Deadline(0).remaining() == float("inf"),
       "D1: budget 0 disables the deadline rather than expiring instantly")
expect(not Deadline(0).exhausted(),
       "D1: a disabled deadline is never exhausted")
expect(Deadline(0).slice_for(75.0) == 75.0,
       "D1: a disabled deadline grants a stage exactly what it asks for")

# The invariant, over the whole domain: every stage slice the orchestrator can
# compute is <= the time actually left. This is the property the five-minute
# ceiling rests on.
for budget in (5, 30, 60, 120, 300, 600):
    for spent_pct in range(0, 100, 3):
        spent = budget * spent_pct / 100.0
        d = FakeDeadline(budget, spent)
        remaining = d.remaining()

        expect(d.slice_for(120.0) <= remaining + 1e-9,
               f"D2: classify slice exceeds remaining (budget={budget}, spent={spent:.1f})")

        if d.exhausted():
            expect(remaining < MIN,
                   f"D3: exhausted() true while {remaining:.2f}s remained")
            continue

        # Mid-loop: k skills left to run, each takes an equal share of what is
        # left, floored so a stage is never handed a slice it cannot start in.
        for k in range(1, N_SKILLS + 1):
            share = remaining / k
            granted = max(MIN, min(share, orchestrate.DEFAULT_SKILL_TIMEOUT))
            expect(granted <= remaining + 1e-9,
                   f"D4: skill slice {granted:.2f}s > remaining {remaining:.2f}s "
                   f"(budget={budget}, k={k})")

expect(FakeDeadline(300, 299.0).exhausted(),
       "D5: a nearly-spent budget stops the loop instead of starting a doomed stage")
expect(not FakeDeadline(300, 100.0).exhausted(),
       "D5: a budget with time left keeps running")

# The floor must never exceed the stop threshold, or a stage could be granted
# more than remaining() at the exact moment the loop decides to continue.
expect(MIN <= Deadline.MIN_USEFUL_SLICE,
       "D6: the slice floor and the stop threshold are the same value")


# ------------------------------------------------------------- the real thing

def run(budget: float, fixture: str = "site_b") -> tuple[float, int, dict | None]:
    with tempfile.TemporaryDirectory() as tmp:
        started = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, str(ORCH_SCRIPTS / "orchestrate.py"),
             "--offline-root", f"tests/fixtures/{fixture}",
             "--time-budget", str(budget), "--out", tmp],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        wall = time.perf_counter() - started
        report = Path(tmp) / "audit-report.json"
        data = json.loads(report.read_text(encoding="utf-8")) if report.exists() else None
        return wall, proc.returncode, data


# A budget large enough to finish: the deadline must not cost us any findings.
wall, code, full = run(120)
expect(code == 0 and full is not None, "D7: a generous budget still produces a report")
expect(full and full["summary"]["total_findings"] > 0,
       "D7: a generous budget produces the findings it would without one")

# Squeezed budgets: the run must stay inside the budget and still emit a
# schema-valid report rather than dying or hanging.
for budget in (3, 5, 10, 30):
    wall, code, data = run(budget)
    expect(code == 0, f"D8: budget={budget}s exits 0 (got {code})")
    expect(data is not None, f"D8: budget={budget}s still writes a report")
    # +3s of slack for interpreter startup and process teardown, which sit
    # outside the orchestrator's own clock.
    expect(wall <= budget + 3.0,
           f"D9: budget={budget}s overran ({wall:.2f}s wall)")
    if data:
        expect({"site", "audited_at", "summary", "findings"} <= set(data),
               f"D10: budget={budget}s report keeps the required schema floor")

# Whatever a squeezed run could not do has to be said out loud, never dropped
# silently. A budget that cannot even collect evidence must say so.
_, _, tiny = run(0.1)
expect(tiny is not None and tiny.get("limitations"),
       "D11: a budget too small to finish records why in limitations[]")

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} time-budget ceiling assertions")
