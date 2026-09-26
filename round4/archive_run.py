#!/usr/bin/env python3
"""Archive one audit run into round4/ and prove its findings came from the
frozen Round 3 engine.

Run this once, right after recording the Round 4 video, on the output folder
the on-camera session wrote:

  python round4/archive_run.py audit-output/www.npr.org
  python round4/archive_run.py audit-output/www.npr.org --label recorded-run \
      --note "Round 4 video take, Claude Code 2.1.283, claude-opus-5-5"

It writes round4/<label>/<host>/ containing:

  audit-report.json, report.md, profile.json, fix_patches/   the engine's output, verbatim
  evidence-excerpt/robots.txt, meta.json                     the evidence behind F-001 and the
                                                             run's timestamp and tool versions
  EVIDENCE_SHA256SUMS                                        a hash of every file in the full
                                                             evidence bundle
  REDERIVATION.txt                                           the frozen engine re-run on that
                                                             bundle with --bundle (no network):
                                                             it must reproduce the report exactly
  RUN_INFO.json                                              hashes, engine fingerprint, note

The full evidence bundle holds the crawled pages' text, which is the audited
site's content, so it is hashed here but not copied into the repository.

Read-only towards the marketplace: nothing is written inside
brand-ai-readiness-audit/, and bytecode caching is disabled for the re-run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ENGINE = REPO / "brand-ai-readiness-audit" / "skills" / "ai-readiness-orchestrator" / "scripts" / "orchestrate.py"
FREEZE = HERE / "ENGINE_FREEZE.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rederive(evidence: Path, archived_report: Path) -> tuple[bool, str]:
    """Re-run the frozen engine on the captured bundle and compare."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryDirectory(prefix="round4-rederive-") as tmp:
        out = Path(tmp) / "out"
        proc = subprocess.run(
            [sys.executable, str(ENGINE), "--bundle", str(evidence.resolve()), "--out", str(out)],
            capture_output=True, text=True, env=env, timeout=600,
        )
        if proc.returncode != 0:
            return False, f"engine exited {proc.returncode}: {proc.stderr.strip()[:300]}"
        got = json.loads((out / "audit-report.json").read_text(encoding="utf-8"))
        want = json.loads(archived_report.read_text(encoding="utf-8"))
        # Under --bundle the engine labels the bundle path "external" instead of
        # the relative path it wrote during collection. That label is the only
        # field allowed to differ.
        got["evidence_bundle"].pop("path", None)
        want["evidence_bundle"].pop("path", None)
        if got != want:
            diff = [f["id"] for f, g in zip(want["findings"], got["findings"]) if f != g]
            return False, (f"re-derived report differs: {len(want['findings'])} vs "
                           f"{len(got['findings'])} findings; first differing ids {diff[:5]}")
        md_same = (out / "report.md").read_bytes() == (archived_report.parent / "report.md").read_bytes()
        if not md_same:
            return False, "audit-report.json matches but report.md differs"
        return True, (f"identical: {len(got['findings'])} findings, same order, ids, severities, evidence "
                      f"and patches; report.md byte-identical")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", help="the --out folder of the run, e.g. audit-output/www.npr.org")
    parser.add_argument("--label", default="recorded-run", help="subfolder of round4/ (default recorded-run)")
    parser.add_argument("--note", default="", help="free text stored in RUN_INFO.json")
    args = parser.parse_args(argv)

    run = Path(args.run_dir)
    report = run / "audit-report.json"
    evidence = run / "evidence"
    if not report.exists() or not (evidence / "meta.json").exists():
        print(f"error: {run} does not contain audit-report.json and evidence/meta.json", file=sys.stderr)
        return 2

    data = json.loads(report.read_text(encoding="utf-8"))
    host = data["site"]
    dest = HERE / args.label / host
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "evidence-excerpt").mkdir(parents=True)

    for name in ("audit-report.json", "report.md", "profile.json"):
        if (run / name).exists():
            shutil.copy2(run / name, dest / name)
    if (run / "fix_patches").is_dir():
        shutil.copytree(run / "fix_patches", dest / "fix_patches")
    for name in ("robots.txt", "meta.json"):
        if (evidence / name).exists():
            shutil.copy2(evidence / name, dest / "evidence-excerpt" / name)

    sums = []
    for path in sorted(p for p in evidence.rglob("*") if p.is_file()):
        sums.append(f"{sha256_file(path)}  {path.relative_to(evidence).as_posix()}")
    with open(dest / "EVIDENCE_SHA256SUMS", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(sums) + "\n")

    ok, detail = rederive(evidence, report)
    with open(dest / "REDERIVATION.txt", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "Re-derivation of this run's findings from its captured evidence bundle\n"
            "======================================================================\n\n"
            f"command : python brand-ai-readiness-audit/skills/ai-readiness-orchestrator/scripts/"
            f"orchestrate.py --bundle <evidence> --out <tmp>\n"
            f"network : none (--bundle re-analyses the captured bundle; nothing is fetched)\n"
            f"result  : {'PASS' if ok else 'FAIL'}: {detail}\n\n"
            "The engine is deterministic for a fixed evidence bundle, so every finding in\n"
            "audit-report.json follows mechanically from the captured evidence. A live\n"
            "replay can still differ below the top finding when the site's own pages change\n"
            "between runs; the bundle hashes in EVIDENCE_SHA256SUMS pin what this run saw.\n"
        )

    freeze = json.loads(FREEZE.read_text(encoding="utf-8")) if FREEZE.exists() else {}
    s = data["summary"]
    info = {
        "site": host,
        "audited_at": data["audited_at"],
        "archived_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": args.note,
        "summary": {k: s[k] for k in ("total_findings", "critical", "high", "medium", "low", "info",
                                      "blocked_findings")},
        "top_finding": ({"id": data["findings"][0]["id"], "check_id": data["findings"][0]["check_id"],
                         "severity": data["findings"][0]["severity"]} if data["findings"] else None),
        "audit_report_sha256": sha256_file(report),
        "evidence_bundle_files": len(sums),
        "rederivation": "PASS" if ok else "FAIL",
        "engine": {
            "round3_commit": freeze.get("round3_commit"),
            "submission_zip_sha256": (freeze.get("submission_zip") or {}).get("sha256"),
        },
    }
    with open(dest / "RUN_INFO.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(info, indent=2) + "\n")

    print(f"archived {run} -> {dest.relative_to(REPO)}")
    print(f"  {s['total_findings']} findings (critical {s['critical']}, high {s['high']}), "
          f"{s['blocked_findings']} capped by the gate cascade")
    print(f"  evidence bundle: {len(sums)} files hashed (not copied)")
    print(f"  re-derivation from the bundle: {'PASS' if ok else 'FAIL'}: {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
