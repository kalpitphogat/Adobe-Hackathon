#!/usr/bin/env python3
"""Write audit-report.json, report.md and output/fix_patches/.

Durability: every write is atomic. A truncated report that later becomes a
checked-in golden is a silent poison - no test catches it, because the corrupt
file IS the reference. Write to a temporary file in the same directory, flush,
fsync, then os.replace, so a full disk or a crash leaves either the old file or
the new one and never a half-written one.

The atomic_write helper is DELIBERATELY DUPLICATED from
site-evidence-collector/scripts/collect.py. No script may import from a sibling
skill folder; see references/skill-cli-contract.md.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from severity import SEVERITY_ORDER, sort_key

MIN_FREE_BYTES = 64 * 1024 * 1024
SCHEMA_VERSION = "1.0"


def check_free_space(target: Path, minimum: int = MIN_FREE_BYTES) -> str | None:
    try:
        usage = shutil.disk_usage(target if target.exists() else target.parent)
    except OSError as exc:
        return f"cannot stat filesystem for {target}: {exc}"
    if usage.free < minimum:
        return (
            f"only {usage.free / 1048576:.1f} MiB free at {target}; "
            f"{minimum / 1048576:.0f} MiB required. Refusing to write a report that could be "
            f"truncated."
        )
    return None


def atomic_write(path: Path, data: str | bytes) -> None:
    payload = data.encode("utf-8") if isinstance(data, str) else data
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def guard_output_path(out: Path) -> str | None:
    resolved = str(out.resolve()).lower()
    if "onedrive" in resolved:
        return (
            f"refusing to write audit output to a cloud-synced path: {out.resolve()}. A sync "
            f"client rewriting files mid-run corrupts the report and breaks determinism."
        )
    if f"{os.sep}skills{os.sep}" in str(out.resolve()) or str(out.resolve()).endswith(f"{os.sep}skills"):
        return (
            f"refusing to write audit output inside the marketplace skills/ tree: {out.resolve()}. "
            f"Skill folders must stay clean so each can be lifted out and shipped alone."
        )
    return None


def build_report(
    site: str,
    audited_at: str,
    findings: list[dict],
    proactive: list[dict],
    limitations: list[dict],
    suppressed: list[dict],
    generator: dict,
    evidence_summary: dict,
    audit_status: str,
    blocked_count: int,
) -> dict:
    ordered = sorted(findings, key=sort_key)
    for index, finding in enumerate(ordered, start=1):
        finding["id"] = f"F-{index:03d}"

    counts = {s: sum(1 for f in ordered if f["severity"] == s) for s in SEVERITY_ORDER}
    by_category = {
        "discoverability": sum(1 for f in ordered if f.get("category") == "discoverability"),
        "engagement": sum(1 for f in ordered if f.get("category") == "engagement"),
    }
    by_stage: dict[str, int] = {}
    for f in ordered:
        stage = f.get("stage")
        if stage:
            by_stage[stage] = by_stage.get(stage, 0) + 1

    for index, rec in enumerate(sorted(proactive, key=lambda r: r.get("title", "")), start=1):
        rec["id"] = f"P-{index:03d}"

    report = {
        "schema_version": SCHEMA_VERSION,
        "site": site,
        "audited_at": audited_at,
        "audit_status": audit_status,
        "generator": generator,
        "summary": {
            "total_findings": len(ordered),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
            "info": counts["info"],
            "blocked_findings": blocked_count,
            "suppressed_by_rule": suppressed,
            "by_category": by_category,
            "by_stage": dict(sorted(by_stage.items())),
        },
        "findings": ordered,
        "proactive_recommendations": sorted(proactive, key=lambda r: r["id"]),
        "limitations": sorted(limitations, key=lambda l: (l.get("scope", ""), l.get("reason", ""))),
        "evidence_bundle": evidence_summary,
    }
    return report


SEVERITY_LABEL = {
    "critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM", "low": "LOW", "info": "INFO",
}


def render_markdown(report: dict, gate_notes: list[str]) -> str:
    s = report["summary"]
    lines: list[str] = []
    add = lines.append

    add(f"# AI-readiness audit — {report['site']}")
    add("")
    add(f"*Audited {report['audited_at']} · status: **{report['audit_status']}***")
    add("")

    if report["audit_status"] == "no_content_available":
        add("> **No page content could be assessed.** See Limitations below for why. ")
        add("> The findings that follow are limited to what could be observed without page content.")
        add("")

    add("## What to do first")
    add("")
    actionable = [f for f in report["findings"] if not f.get("blocked_by") and f["severity"] != "info"]
    if not actionable:
        add("No actionable defects were found at or above low severity.")
    else:
        for f in actionable[:5]:
            act = f["suggested_action"]
            add(f"{len(lines) and ''}**{f['id']} · {SEVERITY_LABEL[f['severity']]}** — {f['title']}")
            add("")
            add(f"- **Do:** {act['summary']}")
            add(f"- **Why it works:** {act.get('mechanism', '')}")
            add(f"- **Effort:** {act.get('effort', 'unknown')} · **ICE:** {act.get('ice', '—')}")
            if act.get("verification"):
                add(f"- **Verify:** `{act['verification'].splitlines()[0]}`")
            add("")
    add("")

    add("## Summary")
    add("")
    add("| Severity | Count |")
    add("|---|---|")
    for sev in ("critical", "high", "medium", "low", "info"):
        add(f"| {sev} | {s[sev]} |")
    add(f"| **total** | **{s['total_findings']}** |")
    add("")
    add(
        f"Discoverability {s['by_category']['discoverability']} · "
        f"engagement {s['by_category']['engagement']}."
    )
    add("")

    if gate_notes:
        add("## Fix these first — everything else is waiting on them")
        add("")
        for note in gate_notes:
            add(f"- {note}")
        add("")

    stage_titles = {
        "reach": "Reach — can a crawler get in?",
        "read": "Read — can it read the page without running JavaScript?",
        "extract": "Extract — can it lift out the specific fact?",
        "trust": "Trust — would it believe the page?",
        "act": "Act — does a visitor who arrives stay and act?",
    }
    for stage in ("reach", "read", "extract", "trust", "act"):
        group = [f for f in report["findings"] if f.get("stage") == stage and not f.get("blocked_by")]
        if not group:
            continue
        add(f"## {stage_titles[stage]}")
        add("")
        for f in group:
            act = f["suggested_action"]
            add(f"### {f['id']} · {SEVERITY_LABEL[f['severity']]} · {f['title']}")
            add("")
            add(f"*confidence: {f.get('confidence', 'unknown')} · check: `{f.get('check_id', '')}`*")
            add("")
            add(f"**Evidence.** {f['evidence']}")
            add("")
            add(f"**Fix.** {act['summary']}")
            add("")
            if act.get("mechanism"):
                add(f"**Why this works.** {act['mechanism']}")
                add("")
            if act.get("patch"):
                add("**Patch**")
                add("")
                add("```")
                add(act["patch"])
                add("```")
                add("")
            if act.get("verification"):
                add("**Verify**")
                add("")
                add("```")
                add(act["verification"])
                add("```")
                add("")
            if act.get("source"):
                add(f"*Source: {act['source']}*")
                add("")

    blocked = [f for f in report["findings"] if f.get("blocked_by")]
    if blocked:
        add("<details>")
        add(f"<summary>{len(blocked)} finding(s) are moot until the blockers above are fixed</summary>")
        add("")
        for f in blocked:
            add(
                f"- **{f['id']}** · {f['severity']} · {f['title']} "
                f"— blocked by {f['blocked_by']} (`{f.get('check_id', '')}`)"
            )
        add("")
        add("</details>")
        add("")

    if report["proactive_recommendations"]:
        add("## Worth doing even though nothing is broken")
        add("")
        for rec in report["proactive_recommendations"]:
            add(f"### {rec['id']} · {rec['title']}")
            add("")
            add(rec["rationale"])
            add("")

    add("## What this audit could not assess")
    add("")
    if not report["limitations"]:
        add("Nothing material. Every check ran against collected evidence.")
    else:
        for lim in report["limitations"]:
            add(f"- **{lim['scope']}** — {lim['reason']}")
            if lim.get("checks_not_run"):
                add(f"  - Checks not run: {', '.join(lim['checks_not_run'][:8])}"
                    + (" …" if len(lim["checks_not_run"]) > 8 else ""))
    add("")

    if s["suppressed_by_rule"]:
        add("## Deliberately not reported")
        add("")
        add("Findings other tools would raise that we suppressed, and why:")
        add("")
        for item in s["suppressed_by_rule"][:20]:
            add(f"- `{item['check_id']}` ×{item['count']} — {item.get('reason', '')}")
        add("")

    gen = report["generator"]
    add("---")
    add("")
    add(
        f"*{gen['name']} {gen['version']} · {gen.get('checks_run', 0)} of "
        f"{gen.get('checks_available', 0)} checks ran · AI crawler list snapshot "
        f"{gen.get('ai_bots_snapshot_date', 'unknown')} "
        f"(commit {str(gen.get('ai_bots_source_commit', ''))[:12]}) · "
        f"recommend-only: nothing was written to the audited site.*"
    )
    return "\n".join(lines) + "\n"


def write_all(out: Path, report: dict, gate_notes: list[str]) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    patches_dir = out / "fix_patches"
    patches_dir.mkdir(exist_ok=True)

    atomic_write(out / "audit-report.json", json.dumps(report, indent=2, sort_keys=True))
    atomic_write(out / "report.md", render_markdown(report, gate_notes))

    written = []
    for finding in report["findings"]:
        patch = (finding.get("suggested_action") or {}).get("patch")
        if not patch:
            continue
        name = f"{finding['id']}.{finding.get('check_id', 'unknown')}.txt"
        atomic_write(patches_dir / name, patch + "\n")
        finding["suggested_action"]["patch_path"] = f"fix_patches/{name}"
        written.append(name)

    # rewrite the JSON now that patch_path fields exist
    atomic_write(out / "audit-report.json", json.dumps(report, indent=2, sort_keys=True))
    return {"patches": sorted(written)}
