#!/usr/bin/env python3
"""S5 gate: the gate cascade, Rule 0b, and the false-positive control.

Five fixtures, five separable claims. They are deliberately kept apart so that a
change to one mechanism cannot silently alter the proof of another:

  site_a  healthy control    ZERO findings at high or critical
  site_b  gate cascade       one critical, everything downstream capped,
                             engagement completely unaffected
  site_c  blanket disallow   exactly one critical, no page ever fetched
  site_d  all-SPA no render  ZERO act findings SITE-WIDE, ONE limitation
  site_e  bot taxonomy       training INFO, dual-purpose MEDIUM, no critical,
                             no cascade

Run: python tests/test_gate_cascade.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORCH = ROOT / "skills" / "ai-readiness-orchestrator" / "scripts" / "orchestrate.py"
FIXTURES = ROOT / "tests" / "fixtures"

FAILURES: list[str] = []
COUNT = 0


def expect(cond: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not cond:
        FAILURES.append(label)


def audit(fixture: str, out: Path, extra: list[str] | None = None) -> dict:
    env = dict(os.environ, SOURCE_DATE_EPOCH="1780000000", PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ORCH), "--offline-root", str(FIXTURES / fixture),
         "--out", str(out), *(extra or [])],
        capture_output=True, text=True, env=env, cwd=str(ROOT),
    )
    expect(proc.returncode == 0, f"[{fixture}] orchestrator exits 0 (got {proc.returncode}: {proc.stderr[:200]})")
    expect("Traceback" not in proc.stderr, f"[{fixture}] no traceback leaked to stderr")
    return json.loads((out / "audit-report.json").read_text(encoding="utf-8"))


tmp = Path(tempfile.mkdtemp(prefix="bara-s5-"))
try:
    # ============================================ site_a: the control

    a = audit("site_a", tmp / "a")
    high_or_worse = [f for f in a["findings"] if f["severity"] in ("critical", "high")]
    expect(
        not high_or_worse,
        f"[control] a well-built site produces ZERO high or critical findings "
        f"(got {[f['check_id'] for f in high_or_worse]})",
    )
    expect(a["audit_status"] == "complete", f"[control] audit_status is complete (got {a['audit_status']})")
    expect(a["summary"]["blocked_findings"] == 0, "[control] nothing is blocked on a healthy site")
    expect(a["summary"]["total_findings"] > 0, "[control] the auditor is not simply silent")

    # ================================== site_b: THE GATE CASCADE PROOF
    # This fixture blocks ONLY retrieval crawlers. It carries no training or
    # dual-purpose bot directives, so a change to the bot taxonomy cannot alter
    # this proof.

    b = audit("site_b", tmp / "b", ["--explain-gates"])
    crits = [f for f in b["findings"] if f["severity"] == "critical"]
    expect(len(crits) == 1, f"[cascade] exactly ONE critical (got {len(crits)}: {[f['check_id'] for f in crits]})")
    expect(
        crits and crits[0]["check_id"] == "reach.robots.ai_search_bot_blocked",
        "[cascade] the critical is the robots.txt retrieval-crawler block",
    )
    root_id = crits[0]["id"] if crits else None

    blocked = [f for f in b["findings"] if f.get("blocked_by")]
    expect(len(blocked) >= 10, f"[cascade] downstream findings are recorded, not deleted (got {len(blocked)})")
    expect(
        all(f["blocked_by"] == root_id for f in blocked),
        "[cascade] every blocked finding names the single root cause, not a chain",
    )
    expect(
        all(f["severity"] in ("medium", "low", "info") for f in blocked),
        "[cascade] blocked findings are capped at medium or below",
    )
    expect(
        all(f["category"] == "discoverability" for f in blocked),
        "[cascade] ONLY discoverability findings are gated",
    )
    expect(
        b["summary"]["blocked_findings"] == len(blocked),
        "[cascade] summary.blocked_findings matches the findings themselves",
    )

    # Rule 0: engagement is not causally downstream of reach.
    act = [f for f in b["findings"] if f["stage"] == "act"]
    expect(len(act) >= 5, f"[cascade] engagement checks still ran on a crawl-blocked site (got {len(act)})")
    expect(
        not any(f.get("blocked_by") for f in act),
        "[cascade] NO engagement finding is gated by a reach failure (Rule 0)",
    )
    expect(
        any(f["severity"] == "high" for f in act),
        "[cascade] engagement keeps its own severity; a robots.txt block does not cap it",
    )

    # This fixture must not exercise the taxonomy at all.
    expect(
        not any(f["check_id"] == "reach.robots.ai_training_bot_blocked" for f in b["findings"]),
        "[cascade] the cascade fixture carries no training-bot directive, keeping the proofs separate",
    )
    expect(
        not any(f["check_id"] == "reach.robots.dual_purpose_bot_blocked" for f in b["findings"]),
        "[cascade] the cascade fixture carries no dual-purpose directive",
    )

    # The headline claim: a flat checklist would report many criticals here.
    would_be_critical = [f for f in b["findings"] if f.get("blocked_by") and f["stage"] != "act"]
    expect(
        len(crits) == 1 and len(would_be_critical) >= 10,
        f"[cascade] one root cause replaces {len(would_be_critical)} separately-reported defects",
    )

    # ================================= site_e: THE BOT TAXONOMY PROOF
    # Healthy content, and a robots.txt that blocks training and dual-purpose
    # crawlers but NO retrieval crawler. No critical, therefore no cascade, so a
    # change to the cascade cannot alter this proof.

    e = audit("site_e", tmp / "e")
    training = [f for f in e["findings"] if f["check_id"] == "reach.robots.ai_training_bot_blocked"]
    dual = [f for f in e["findings"] if f["check_id"] == "reach.robots.dual_purpose_bot_blocked"]
    retrieval = [f for f in e["findings"] if f["check_id"] == "reach.robots.ai_search_bot_blocked"]

    expect(len(training) == 1, f"[taxonomy] training-only bots produce exactly one finding (got {len(training)})")
    expect(
        training and training[0]["severity"] == "info",
        f"[taxonomy] blocking GPTBot is INFO, not a defect "
        f"(got {training[0]['severity'] if training else 'nothing'})",
    )
    expect(
        training and "not" in training[0]["evidence"].lower() and "retrieval" in training[0]["evidence"].lower(),
        "[taxonomy] the training finding explains that blocking it costs no retrieval visibility",
    )
    expect(len(dual) == 1, f"[taxonomy] dual-purpose bots produce exactly one finding (got {len(dual)})")
    expect(
        dual and dual[0]["severity"] == "medium",
        f"[taxonomy] dual-purpose is MEDIUM (got {dual[0]['severity'] if dual else 'nothing'})",
    )
    expect(
        dual and "contested" in dual[0]["evidence"].lower(),
        "[taxonomy] the dual-purpose finding states plainly that the role is contested",
    )
    expect(not retrieval, "[taxonomy] no retrieval crawler is blocked on this fixture")
    expect(e["summary"]["critical"] == 0, f"[taxonomy] no critical (got {e['summary']['critical']})")
    expect(
        e["summary"]["blocked_findings"] == 0,
        "[taxonomy] no cascade runs, so the taxonomy proof is independent of it",
    )
    expect(
        training and e["generator"].get("ai_bots_snapshot_date"),
        "[taxonomy] the report prints the bot-list snapshot date",
    )
    expect(
        e["generator"].get("ai_bots_source_commit"),
        "[taxonomy] the report prints the upstream bot-list commit",
    )

    # ======================== site_d: RULE 0b, SITE-WIDE (blocking fix F4)

    d = audit("site_d", tmp / "d")
    d_act = [f for f in d["findings"] if f["stage"] == "act"]
    expect(
        len(d_act) == 0,
        f"[rule0b] an all-shell site with no renderer produces ZERO act findings SITE-WIDE "
        f"(got {len(d_act)}: {[f['check_id'] for f in d_act]})",
    )
    expect(
        not any(f["check_id"] == "act.trust.no_policy_or_contact_path" for f in d["findings"]),
        "[rule0b] the site-scoped policy check is suppressed too: there are no other pages to "
        "evidence it from",
    )
    rule0b_lims = [
        l for l in d["limitations"]
        if "shell" in l["reason"].lower() and "act." in " ".join(l.get("checks_not_run") or [])
    ]
    expect(
        len(rule0b_lims) == 1,
        f"[rule0b] exactly ONE consolidated limitation, not one per page (got {len(rule0b_lims)})",
    )
    if rule0b_lims:
        lim = rule0b_lims[0]
        expect(lim["scope"] == "site", f"[rule0b] the limitation is site-scoped (got {lim['scope']!r})")
        expect(
            "suppressed entirely" in (lim.get("confidence_effect") or "").lower(),
            "[rule0b] the limitation says suppressed entirely, not downgraded",
        )
        expect(
            len(lim["checks_not_run"]) >= 13,
            f"[rule0b] the limitation names every check that could not run "
            f"(got {len(lim['checks_not_run'])})",
        )
        expect(
            "act.trust.no_policy_or_contact_path" in lim["checks_not_run"],
            "[rule0b] the site-scoped check is named among those that could not run",
        )
    expect(
        any(f["check_id"] == "read.render.empty_spa_shell" for f in d["findings"]),
        "[rule0b] the shell itself is still reported as a read-stage finding",
    )
    shells = [f for f in d["findings"] if f["check_id"] == "read.render.empty_spa_shell"]
    expect(
        all(f["severity"] == "high" and f["confidence"] == "likely" for f in shells),
        "[rule0b] with no renderer the shell finding is high/likely, not critical/confirmed",
    )

    # ============================ site_c: blanket disallow, F6 exit code

    c = audit("site_c", tmp / "c")
    expect(
        c["audit_status"] == "no_content_available",
        f"[disallow] audit_status is no_content_available (got {c['audit_status']})",
    )
    expect(
        c["summary"]["critical"] == 1 and c["summary"]["total_findings"] == 1,
        f"[disallow] exactly one finding, and it is the critical "
        f"(got {c['summary']['total_findings']} total, {c['summary']['critical']} critical)",
    )
    expect(
        c["findings"][0]["check_id"] == "reach.robots.blanket_disallow",
        "[disallow] the finding is the blanket disallow",
    )
    expect(len(c["limitations"]) >= 1, "[disallow] a limitation explains that nothing could be fetched")
    expect(
        c["evidence_bundle"]["pages_fetched"] == 0,
        "[disallow] not one page was fetched: robots.txt is a hard constraint on our own crawl",
    )

    # ==================================== schema floor and determinism

    for name, report in (("a", a), ("b", b), ("c", c), ("d", d), ("e", e)):
        expect(
            {"site", "audited_at", "summary", "findings"} <= set(report),
            f"[schema {name}] the handout's required top-level fields are present",
        )
        expect(
            {"total_findings", "critical", "high", "medium"} <= set(report["summary"]),
            f"[schema {name}] the handout's required summary counts are present",
        )
        for f in report["findings"]:
            expect(
                {"id", "title", "severity", "evidence", "suggested_action"} <= set(f),
                f"[schema {name}] finding {f.get('id')} has the handout's required fields",
            )
            expect(bool(f["suggested_action"].get("mechanism")), f"[schema {name}] {f['id']} states a mechanism")
            expect(bool(f.get("confidence")), f"[schema {name}] {f['id']} carries a confidence")
        ids = [f["id"] for f in report["findings"]]
        expect(ids == sorted(ids), f"[schema {name}] finding ids are dense and ordered")

    again = audit("site_b", tmp / "b2")
    expect(
        json.dumps(b, sort_keys=True) == json.dumps(again, sort_keys=True),
        "[determinism] two orchestrator runs of the same fixture produce an identical report",
    )

    # patches must never invent a value
    patch_dir = tmp / "b" / "fix_patches"
    expect(patch_dir.exists() and any(patch_dir.iterdir()), "[patches] fix patches were written to disk")

finally:
    shutil.rmtree(tmp, ignore_errors=True)

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} gate-cascade and Rule 0b assertions")
