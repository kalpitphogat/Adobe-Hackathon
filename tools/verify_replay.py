#!/usr/bin/env python3
"""Be the judge who replays REPLAY_IT_Professionals.txt, before a judge does.

Round 4's unverified floor: a missing or unparseable manifest, or no working
invoke path, and the submission is tagged ran-blocked however good the engine
is. That failure stays silent until someone else runs it, so this script is the
someone else:

  1. parses the manifest's fixed labelled fields and refuses placeholders;
  2. cross-checks the fields against each other (the harness version the
     manifest discloses is the one ENV_SETUP installs; the model it discloses is
     the one TEST_STEPS starts the harness with; the entrypoint it names exists
     in the submitted zip);
  3. unpacks the pinned submission.zip into a fresh folder and runs the exact
     engine command TEST_STEPS documents against every TEST_SITE_URL, then
     checks the report lands at EXPECTED_OUTPUT and meets the Round 3 floor.

    python3 round4/tools/verify_replay.py round4/REPLAY_IT_Professionals.txt
    python3 round4/tools/verify_replay.py round4/REPLAY_IT_Professionals.txt --no-run
    python3 round4/tools/verify_replay.py round4/REPLAY_IT_Professionals.txt --twice

--twice runs each URL twice back to back and compares the findings (the
nondeterminism flag), then re-analyses the saved evidence bundle and checks the
findings are identical to the live run's. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ZIP = REPO / "round3-frozen" / "submission.zip"
PIN_FILE = REPO / "round3-frozen" / "SHA256SUMS"
REQUIRED = ["TEST_SITE_URLS", "LLM_MODEL", "AGENT_HARNESS", "ENV_SETUP", "TEST_STEPS", "EXPECTED_OUTPUT"]
PLACEHOLDER = re.compile(r"<<|>>|\bTODO\b|\bFIXME\b|YourTeamName|\bTBD\b|<FILL", re.I)
# The documented engine command, flags only: "--flag" or "--flag value", nothing
# after the command's last flag (the prompt line continues with prose).
ENGINE_CMD = re.compile(
    r"python3? (skills/ai-readiness-orchestrator/scripts/orchestrate\.py) <URL>"
    r"((?:[ \t]+--[a-z][a-z-]*(?:[ \t]+(?!--)[^\s()]+)?)*)"
)

CHALLENGE = re.compile(r"client challenge|just a moment|attention required|access denied|"
                       r"are you a (human|robot)|verify you are human|request blocked|you have been blocked|"
                       r"pardon our interruption", re.I)

FAILS: list[str] = []
COUNT = 0


def check(ok: bool, label: str, detail: str = "") -> bool:
    global COUNT
    COUNT += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -> ' + detail) if detail else ''}")
    if not ok:
        FAILS.append(label)
    return ok


def parse(path: Path) -> dict[str, str]:
    """Fixed labelled fields. A LABEL: at column 0 starts a field; indented or
    unlabelled lines continue it; lines starting with # are commentary."""
    fields: dict[str, list[str]] = {}
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Z][A-Z0-9_]*):(\s.*|)$", raw)
        if m:
            current = m.group(1)
            fields[current] = [m.group(2).strip()]
        elif current is not None:
            fields[current].append(raw.rstrip())
    return {k: "\n".join(v).strip() for k, v in fields.items()}


def signature(report: dict) -> list[tuple]:
    return sorted(
        (f.get("check_id"), f.get("severity"), f.get("confidence"), tuple(f.get("affected_urls") or []))
        for f in report.get("findings") or []
    )


def floor(report: dict) -> list[str]:
    problems = [f"missing {k}" for k in ("site", "audited_at", "summary", "findings") if k not in report]
    problems += [f"missing summary.{k}" for k in ("total_findings", "critical", "high", "medium", "low")
                 if k not in report.get("summary", {})]
    for f in report.get("findings") or []:
        gap = [k for k in ("id", "title", "severity", "evidence", "suggested_action") if k not in f]
        if gap:
            problems.append(f"{f.get('id', '?')} missing {gap}")
    return problems


def run_engine(engine: Path, argv: list[str], timeout: float) -> tuple[int, str, str]:
    proc = subprocess.run([sys.executable, *argv], cwd=str(engine), capture_output=True, text=True,
                          timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def two_pass(engine: Path, script: str, url: str, flags: list[str],
             timeout: float = 420) -> tuple[int, str, str]:
    """Replay the manifest's two-pass sequence and leave the report in audit-output.

    Pass 1 never renders. Pass 2 opens a browser ONLY when pass 1 found pages the
    crawler received with no internal links at all -- the signal that JavaScript
    builds the page, where a no-JS crawl under-reports. Otherwise pass 2
    re-analyses pass 1's own evidence, which costs no extra fetches and keeps a
    static site free of the render-stage false positives.
    """
    pre = engine / "audit-precheck"
    if pre.exists():
        shutil.rmtree(pre)
    code, _, err = run_engine(engine, [script, url, *flags], timeout)
    if code != 0:
        return code, "pass 1", err

    blank = 0
    pages = pre / "evidence" / "pages.jsonl"
    if pages.is_file():
        for line in pages.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("status") == 200 and not (row.get("links") or {}).get("internal"):
                blank += 1

    if blank:
        code, _, err = run_engine(engine, [script, url, "--out", "./audit-output"], timeout)
        return code, f"pass 2 rendered ({blank} page(s) with no internal links)", err
    code, _, err = run_engine(
        engine, [script, "--bundle", str(pre / "evidence"), "--out", "./audit-output"], timeout)
    return code, "pass 2 re-analysed pass 1's evidence (no blank pages)", err


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--zip", type=Path, default=ZIP)
    ap.add_argument("--no-run", action="store_true", help="parse and cross-check only")
    ap.add_argument("--twice", action="store_true", help="also test run-to-run and bundle determinism")
    ap.add_argument("--evidence", type=int, default=2, help="print evidence for the top N findings")
    ap.add_argument("--skip", action="append", default=[], metavar="URL",
                    help="a TEST_SITE_URL not to audit (repeatable): the video's URL must stay "
                         "unseen until it is recorded")
    args = ap.parse_args(argv)

    print(f"\nmanifest: {args.manifest}")
    if not check(args.manifest.is_file(), "manifest exists"):
        return 1
    name = args.manifest.name
    check(bool(re.fullmatch(r"REPLAY_[A-Za-z0-9_\-]+\.txt", name)) and not PLACEHOLDER.search(name),
          "file is named REPLAY_<TeamName>.txt with the team name filled in", name)
    raw = args.manifest.read_text(encoding="utf-8")
    check(raw.isascii(), "manifest is plain ASCII text (no smart quotes to break a paste)")

    f = parse(args.manifest)
    print("\nfields")
    for key in REQUIRED:
        value = f.get(key, "")
        if check(bool(value), f"{key} present and non-empty"):
            hit = PLACEHOLDER.search(value)
            check(not hit, f"{key} has no placeholder left", hit.group(0) if hit else "")

    urls = [u.strip() for u in f.get("TEST_SITE_URLS", "").split(",") if u.strip()]
    check(bool(urls) and all(re.fullmatch(r"https?://[^\s,]+", u) for u in urls),
          "TEST_SITE_URLS are exact, full URLs", ", ".join(urls))

    model, harness, env, steps = (f.get(k, "") for k in ("LLM_MODEL", "AGENT_HARNESS", "ENV_SETUP", "TEST_STEPS"))
    check(bool(re.search(r"\d", model)), "LLM_MODEL names a version or date", model)
    hv = re.search(r"v?(\d+\.\d+\.\d+)", harness)
    check(bool(hv), "AGENT_HARNESS names a version", harness)

    print("\ncross-checks")
    if hv:
        check(f"@{hv.group(1)}" in env, "ENV_SETUP installs exactly the disclosed harness version",
              f"expects @{hv.group(1)} in ENV_SETUP")
    model_ids = re.findall(r"--model\s+(\S+)", steps)
    check(bool(model_ids) and all(m in model for m in model_ids),
          "TEST_STEPS starts the harness with the disclosed model", ", ".join(model_ids) or "no --model flag")
    check(bool(re.search(r"^\s*1\.", steps, re.M) and re.search(r"^\s*2\.", steps, re.M)
               and re.search(r"^\s*3\.", steps, re.M)), "TEST_STEPS is an ordered 1-2-3 list")
    check("ai-readiness-orchestrator" in steps, "TEST_STEPS names the entrypoint skill")
    cmd = ENGINE_CMD.search(steps)
    check(bool(cmd), "TEST_STEPS documents the exact engine command",
          cmd.group(0) if cmd else "no 'python skills/ai-readiness-orchestrator/scripts/orchestrate.py <URL> ...'")
    expected = f.get("EXPECTED_OUTPUT", "").split()[0] if f.get("EXPECTED_OUTPUT") else ""
    check(expected.endswith("audit-output/audit-report.json"),
          "EXPECTED_OUTPUT names the report file the command writes", expected)

    if not check(args.zip.is_file(), "the Round 3 zip is present", str(args.zip)):
        return report()
    digest = hashlib.sha256(args.zip.read_bytes()).hexdigest()
    pinned = next((l.split()[0] for l in PIN_FILE.read_text(encoding="utf-8").splitlines()
                   if l.strip() and not l.startswith("#")), "")
    check(digest == pinned, "the zip is the pinned Round 3 submission", digest[:16] + "...")
    with zipfile.ZipFile(args.zip) as zf:
        names = set(zf.namelist())
    check("skills/ai-readiness-orchestrator/scripts/orchestrate.py" in names,
          "the entrypoint TEST_STEPS runs exists in the zip")
    # This manifest runs the engine in two passes: pass 1 writes ./audit-precheck,
    # pass 2 writes ./audit-output. EXPECTED_OUTPUT names the pass-2 report, so the
    # path has to appear in TEST_STEPS, not necessarily in the first command.
    check(bool(re.search(r"--out\s+\./audit-output", steps)),
          "TEST_STEPS writes to ./audit-output, matching EXPECTED_OUTPUT")

    if args.no_run or not cmd:
        return report()

    # ---------------------------------------------------------------- replay
    work = Path(tempfile.mkdtemp(prefix="replay-"))
    try:
        # EXPECTED_OUTPUT is written relative to the folder that holds the zip.
        top = work / "judge"
        top.mkdir()
        shutil.copy2(args.zip, top / "submission.zip")
        with zipfile.ZipFile(top / "submission.zip") as zf:
            zf.extractall(top / "brand-ai-readiness-audit")
        engine = top / "brand-ai-readiness-audit"
        flags = shlex.split(cmd.group(2))
        for url in urls:
            if url in args.skip:
                print(f"\nskip {url}  (--skip: not audited, so it stays unseen until the recording)")
                continue
            print(f"\nreplay {url}")
            print(f"  $ python {cmd.group(1)} {url} {' '.join(flags)}")
            out_dir = engine / "audit-output"
            if out_dir.exists():
                shutil.rmtree(out_dir)
            code, which, err = two_pass(engine, cmd.group(1), url, flags)
            if not check(code == 0, f"engine exits 0 on {url}", err.strip()[-200:]):
                continue
            print(f"  -> {which}")
            target = top / expected
            if not check(target.is_file(), f"report written to EXPECTED_OUTPUT for {url}", str(target.relative_to(top))):
                continue
            rep = json.loads(target.read_text(encoding="utf-8"))
            check(not floor(rep), f"report meets the Round 3 schema floor for {url}", "; ".join(floor(rep)[:2]))
            pages_file = out_dir / "evidence" / "pages.jsonl"
            titles = [json.loads(l).get("title") or "" for l in pages_file.read_text(encoding="utf-8").splitlines()
                      if l.strip()] if pages_file.is_file() else []
            bot_checks = [t for t in titles if CHALLENGE.search(t)]
            check(not bot_checks, f"no sampled page was a CDN bot-check page for {url}",
                  f"{len(bot_checks)} page(s) titled {bot_checks[0]!r}: this machine is being challenged; "
                  f"record from another network" if bot_checks else "")
            s = rep["summary"]
            print(f"  -> {rep['site']}: status {rep['audit_status']}, {rep['evidence_bundle'].get('pages_fetched')} pages, "
                  f"{s['total_findings']} findings (C{s['critical']} H{s['high']} M{s['medium']} L{s['low']} "
                  f"I{s.get('info', 0)}), {s.get('blocked_findings', 0)} capped by the cascade")
            for fnd in rep["findings"][: args.evidence]:
                a = fnd.get("suggested_action") or {}
                evidence = re.sub(r"\s+", " ", fnd["evidence"])[:400]
                print(f"     {fnd['id']} {fnd['severity']}/{fnd.get('confidence')} ICE {a.get('ice')} {fnd.get('check_id')}")
                print(f"        {evidence}")

            if args.twice:
                first = signature(rep)
                keep = work / f"first-{abs(hash(url))}"
                shutil.copytree(out_dir, keep)
                shutil.rmtree(out_dir)
                code2, _, err2 = two_pass(engine, cmd.group(1), url, flags)
                if check(code2 == 0, f"second run exits 0 on {url}", err2.strip()[-200:]):
                    second = signature(json.loads(target.read_text(encoding="utf-8")))
                    only_a = sorted(set(first) - set(second))
                    only_b = sorted(set(second) - set(first))
                    same = not only_a and not only_b
                    print(f"  run-to-run: {len(first)} vs {len(second)} findings, "
                          f"{'identical' if same else f'{len(only_a)} only in run 1, {len(only_b)} only in run 2'}")
                    for tag, items in (("run 1 only", only_a), ("run 2 only", only_b)):
                        for item in items[:5]:
                            print(f"     {tag}: {item[0]} {item[1]}/{item[2]} {list(item[3])[:2]}")
                # The engine's own determinism: same evidence in, same findings out.
                # A run that fetched nothing has no bundle to re-analyse, and that is
                # the network's doing, not the manifest's -- a judge behind a proxy
                # that blocks the site would otherwise see this as a manifest defect.
                if rep.get("audit_status") == "no_content_available":
                    print(f"  [ -- ] bundle re-analysis skipped for {url}: the engine fetched 0 pages "
                          f"({rep['audit_status']}), so there is no evidence to re-analyse. "
                          f"This machine could not reach the site.")
                    continue
                bundle_out = work / f"bundle-{abs(hash(url))}"
                code3, _, err3 = run_engine(engine, [cmd.group(1), "--bundle", str(keep / "evidence"),
                                                     "--out", str(bundle_out)], timeout=300)
                if check(code3 == 0, f"re-analysis of the saved evidence bundle exits 0 on {url}", err3[-200:]):
                    a = json.loads((keep / "audit-report.json").read_text(encoding="utf-8"))
                    b = json.loads((bundle_out / "audit-report.json").read_text(encoding="utf-8"))
                    for r in (a, b):
                        r.pop("evidence_bundle", None)
                    check(a == b, f"same evidence gives an identical report for {url} "
                                  "(all fields except evidence_bundle.path)")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return report()


def report() -> int:
    print()
    if FAILS:
        print(f"FAILED {len(FAILS)} of {COUNT} checks:")
        for label in FAILS:
            print(f"  - {label}")
        print("A judge following this manifest could be ran-blocked. Fix these before submitting.")
        return 1
    print(f"OK: all {COUNT} checks passed. A judge following this manifest reaches the same report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
