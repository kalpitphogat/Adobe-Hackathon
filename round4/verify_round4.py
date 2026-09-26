#!/usr/bin/env python3
"""Round 4 verifier: the demo runs the unchanged Round 3 engine, and the
reproduction manifest is well formed.

Read-only, standard library only, never touches the network.

  python round4/verify_round4.py                  freeze + manifest checks (seconds)
  python round4/verify_round4.py --goldens        also re-run the six Round 3 fixture
                                                  audits offline and compare them to
                                                  the checked-in goldens
  python round4/verify_round4.py --compare A B    substance diff between two
                                                  audit-report.json files, e.g. a
                                                  judge's replay against our run
  python round4/verify_round4.py --make-freeze    regenerate ENGINE_FREEZE.json from
                                                  the Round 3 commit in git

This script is harness tooling that sits beside the marketplace. It contains
no audit checks, imports nothing from the marketplace, and writes nothing
inside it: the golden re-run writes to a temporary directory and disables
bytecode caching so not even __pycache__ appears in the engine folder.

Exit 0 when every check passes (warnings allowed), 1 when any check fails.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ENGINE_DIR = REPO / "brand-ai-readiness-audit"
ZIP_PATH = REPO / "submission.zip"
FREEZE_PATH = HERE / "ENGINE_FREEZE.json"
PROMPT_PATH = HERE / "PROMPT.txt"

# The last commit that touched the engine folder or submission.zip on the
# Round 3 submission branch (final-submission).
ROUND3_COMMIT = "ede3a6b"

# Present in the folder but deliberately not packaged: git configuration.
FOLDER_ONLY_FILES = {".gitattributes"}
# Created by running the engine or its tests. Never part of the engine.
RUNTIME_DIRS = {"__pycache__", "audit-output", "evidence", ".pytest_cache"}

REPLAY_FIELDS = [
    "TEST_SITE_URLS", "LLM_MODEL", "AGENT_HARNESS", "ENV_SETUP", "TEST_STEPS", "EXPECTED_OUTPUT",
]

# Golden re-run: the same pinned clock the Round 3 suite uses (tests/run_offline.py).
PINNED_EPOCH = "1780000000"
FIXTURES = ["site_a", "site_b", "site_c", "site_d", "site_e", "site_f"]
# Metadata that records the interpreter the goldens were generated on. It is
# not a finding, so it is excluded from the substance comparison.
VOLATILE_METADATA = ("generator", "tool_versions")

results: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str) -> None:
    results.append((status, name, detail))
    print(f"[{status}] {name:<34} {detail}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str | None:
    try:
        proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace").strip()


def git_bytes(*args: str) -> bytes | None:
    try:
        proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def zip_members(data: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {i.filename: sha256(z.read(i)) for i in z.infolist() if not i.is_dir()}


# ---------------------------------------------------------------- freeze

def make_freeze() -> int:
    commit = git("rev-parse", ROUND3_COMMIT)
    if not commit:
        print(f"error: cannot resolve Round 3 commit {ROUND3_COMMIT} in git", file=sys.stderr)
        return 1
    data = git_bytes("show", f"{commit}:submission.zip")
    if data is None:
        print("error: submission.zip is not present at the Round 3 commit", file=sys.stderr)
        return 1
    freeze = {
        "_comment": [
            "Fingerprint of the Round 3 submission, generated from git by",
            "`python round4/verify_round4.py --make-freeze`. The Round 4 demo must run",
            "exactly these bytes. Regenerating it from the same commit reproduces this",
            "file exactly, so it cannot be quietly edited to match a changed engine.",
        ],
        "round3_branch": "final-submission",
        "round3_commit": commit,
        "round3_commit_date": git("show", "-s", "--format=%cI", commit),
        "engine_dir": ENGINE_DIR.name,
        "engine_git_tree": git("rev-parse", f"{commit}:{ENGINE_DIR.name}"),
        "submission_zip": {
            "path": ZIP_PATH.name,
            "sha256": sha256(data),
            "bytes": len(data),
            "git_blob": git("rev-parse", f"{commit}:submission.zip"),
        },
        "folder_only_files": sorted(FOLDER_ONLY_FILES),
        "files": dict(sorted(zip_members(data).items())),
    }
    with open(FREEZE_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(freeze, indent=2) + "\n")
    print(f"wrote {FREEZE_PATH.relative_to(REPO)}: {len(freeze['files'])} files, "
          f"zip sha256 {freeze['submission_zip']['sha256']}")
    return 0


def check_freeze() -> dict | None:
    if not FREEZE_PATH.exists():
        record("FAIL", "freeze.present", f"{FREEZE_PATH.name} is missing")
        return None
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    frozen = freeze["files"]

    # 1. The package the judges already hold.
    if not ZIP_PATH.exists():
        record("FAIL", "freeze.zip_sha256", "submission.zip is missing")
    else:
        data = ZIP_PATH.read_bytes()
        digest = sha256(data)
        want = freeze["submission_zip"]["sha256"]
        record("PASS" if digest == want else "FAIL", "freeze.zip_sha256",
               f"{digest}" + ("" if digest == want else f" != Round 3 {want}"))
        members = zip_members(data)
        bad = sorted(k for k in set(members) | set(frozen) if members.get(k) != frozen.get(k))
        record("PASS" if not bad else "FAIL", "freeze.zip_members",
               f"{len(members)} files byte-identical to Round 3" if not bad
               else f"{len(bad)} differ, e.g. {bad[:3]}")
        if digest != want and not bad:
            # Same files, different container: the zip was rebuilt. Python's
            # zipfile stamps each header with the host OS (create_system 0 on
            # Windows, 3 on Linux/macOS), so a rebuild on Windows can never match
            # the Linux-built Round 3 artifact even from identical sources.
            record("FAIL", "freeze.zip_rebuilt",
                   "contents match Round 3 but the container was rebuilt (package_submission.py "
                   "without --check?). Restore the submitted artifact: git checkout -- submission.zip")

    # 2. The folder the video and the repo-checkout replay load.
    seen: dict[str, str] = {}
    for path in sorted(ENGINE_DIR.rglob("*")):
        rel_parts = path.relative_to(ENGINE_DIR).parts
        if any(part in RUNTIME_DIRS for part in rel_parts) or not path.is_file():
            continue
        seen["/".join(rel_parts)] = sha256(path.read_bytes())
    changed = sorted(k for k in frozen if seen.get(k) != frozen[k])
    extra = sorted(k for k in seen if k not in frozen and k not in FOLDER_ONLY_FILES)
    ok = not changed and not extra
    detail = (f"{len(frozen)} engine files identical to submission.zip, no additions"
              if ok else f"changed {changed[:3]} added {extra[:3]}")
    record("PASS" if ok else "FAIL", "freeze.folder_matches_zip", detail)

    # 3. Git's own record, when a checkout is available.
    tree = git("rev-parse", f"HEAD:{ENGINE_DIR.name}")
    if tree is None:
        record("SKIP", "freeze.git_tree", "not a git checkout; the byte checks above still hold")
    else:
        want_tree = freeze["engine_git_tree"]
        record("PASS" if tree == want_tree else "FAIL", "freeze.git_tree",
               f"HEAD:{ENGINE_DIR.name} = {tree[:12]} (Round 3 {freeze['round3_commit'][:7]})"
               if tree == want_tree else f"{tree[:12]} != Round 3 {want_tree[:12]}")
        dirty = git("status", "--porcelain", "--", ENGINE_DIR.name, ZIP_PATH.name)
        record("PASS" if not dirty else "FAIL", "freeze.no_uncommitted_edits",
               "working tree matches the commit" if not dirty else dirty.splitlines()[0])
    return freeze


# ---------------------------------------------------------------- manifest

def parse_replay(text: str) -> dict[str, str]:
    """Labelled fields. A field runs until the next label; '#' starts a comment."""
    label = re.compile(r"^(" + "|".join(REPLAY_FIELDS) + r"):\s*(.*)$")
    fields: dict[str, list[str]] = {}
    current = None
    for raw in text.splitlines():
        m = label.match(raw)
        if m:
            current = m.group(1)
            fields[current] = [m.group(2)]
        elif current and not raw.startswith("#"):
            fields[current].append(raw)
    return {k: "\n".join(v).strip() for k, v in fields.items()}


def strip_comment(value: str) -> str:
    return re.sub(r"\s+#.*$", "", value.splitlines()[0]).strip()


def check_replay(freeze: dict | None) -> None:
    candidates = sorted(REPO.glob("REPLAY_*.txt"))
    if len(candidates) != 1:
        record("FAIL", "replay.present", f"expected exactly one REPLAY_*.txt at repo root, found "
                                         f"{[c.name for c in candidates]}")
        return
    path = candidates[0]
    raw = path.read_bytes()
    try:
        text = raw.decode("ascii")
        record("PASS", "replay.plain_ascii", f"{path.name}, {len(raw)} bytes")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", "replace")
        record("FAIL", "replay.plain_ascii", "non-ASCII bytes; keep the manifest plain text")

    fields = parse_replay(text)
    missing = [f for f in REPLAY_FIELDS if not fields.get(f)]
    record("PASS" if not missing else "FAIL", "replay.fields",
           "all 6 labelled fields present and non-blank" if not missing else f"missing/blank {missing}")
    if missing:
        return

    urls = [u.strip() for u in strip_comment(fields["TEST_SITE_URLS"]).split(",") if u.strip()]
    bad = [u for u in urls if urllib.parse.urlsplit(u).scheme not in ("http", "https")
           or not urllib.parse.urlsplit(u).netloc]
    record("PASS" if urls and not bad else "FAIL", "replay.urls",
           ", ".join(urls) if not bad else f"not full URLs: {bad}")

    steps = re.findall(r"^\s*(\d+)\.\s+(.*)$", fields["TEST_STEPS"], re.M)
    numbers = [int(n) for n, _ in steps]
    ordered = numbers == list(range(1, len(numbers) + 1)) and len(numbers) >= 3
    record("PASS" if ordered else "FAIL", "replay.steps_numbered",
           f"{len(numbers)} steps, numbered 1..{len(numbers)}" if ordered else f"got {numbers}")

    # The prompt judges paste must be the one this repo ships, verbatim.
    prompt = PROMPT_PATH.read_text(encoding="utf-8").strip() if PROMPT_PATH.exists() else ""
    in_steps = bool(prompt) and prompt in " ".join(fields["TEST_STEPS"].split())
    record("PASS" if in_steps else "FAIL", "replay.prompt_verbatim",
           "TEST_STEPS carries round4/PROMPT.txt verbatim" if in_steps
           else "the prompt in TEST_STEPS differs from round4/PROMPT.txt")
    missing_urls = [u for u in urls if u not in prompt]
    record("PASS" if not missing_urls else "FAIL", "replay.urls_in_prompt",
           "every TEST_SITE_URL is the URL the prompt audits" if not missing_urls
           else f"not in prompt: {missing_urls}")

    expected = strip_comment(fields["EXPECTED_OUTPUT"])
    hosts = {urllib.parse.urlsplit(u).hostname for u in urls}
    record("PASS" if any(h and h in expected for h in hosts) and expected.endswith("audit-report.json")
           else "FAIL", "replay.expected_output", expected)

    if freeze:
        want = freeze["submission_zip"]["sha256"]
        record("PASS" if want in text else "FAIL", "replay.cites_zip_sha256",
               "manifest pins the Round 3 package by SHA-256" if want in text
               else "manifest does not state the submission.zip SHA-256")

    model = strip_comment(fields["LLM_MODEL"])
    harness = strip_comment(fields["AGENT_HARNESS"])
    model_id = re.search(r"claude-[a-z0-9-]+", fields["LLM_MODEL"] + " " + fields["TEST_STEPS"])
    record("PASS" if model_id and model_id.group(0) in fields["TEST_STEPS"] else "FAIL",
           "replay.model_pinned_in_command",
           f"{model}; launch command passes --model {model_id.group(0)}" if model_id
           else "the launch command does not pin the model")

    version = re.search(r"v?(\d+\.\d+\.\d+)", harness)
    exe = shutil.which("claude")
    if not exe:
        record("SKIP", "replay.harness_on_this_machine", "claude not on PATH; nothing to compare")
    else:
        try:
            out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60).stdout
        except (OSError, subprocess.TimeoutExpired):
            out = ""
        local = re.search(r"(\d+\.\d+\.\d+)", out or "")
        if version and local and version.group(1) == local.group(1):
            record("PASS", "replay.harness_on_this_machine", f"claude --version = {local.group(1)}, as disclosed")
        else:
            record("WARN", "replay.harness_on_this_machine",
                   f"this machine has {local.group(1) if local else 'unknown'}, manifest says "
                   f"{version.group(1) if version else '?'}. Record with the disclosed version, "
                   f"or update AGENT_HARNESS to match the recording.")


# ---------------------------------------------------------------- narration anchors

SCRIPT_PATH = HERE / "VIDEO_SCRIPT.md"
ANCHOR = re.compile(r"`([\w./-]+\.(?:py|md|json))?:(\d+)(?:-(\d+))?`")

# The claims Part 1 makes, and the code each must land on. If the engine or the
# script drifted apart, a claim would point at the wrong code; this catches it.
KEY_ANCHORS = [
    # (file, exact line, text that line must contain)
    ("marketplace.json", 10, '"entrypoint": true'),
    ("skills/ai-readiness-orchestrator/scripts/orchestrate.py", 51, "AUDIT_SKILLS = ["),
    ("skills/ai-readiness-orchestrator/scripts/orchestrate.py", 242, "def validate_finding"),
    ("skills/crawl-access-audit/scripts/check_robots.py", 263, 'by_category[bot["category"]]'),
    ("skills/crawl-access-audit/scripts/check_robots.py", 286, 'severity="critical"'),
    ("skills/crawl-access-audit/scripts/check_robots.py", 318, 'severity="info"'),
    ("skills/crawl-access-audit/scripts/check_robots.py", 351, 'severity="medium"'),
    ("skills/crawl-access-audit/scripts/check_robots.py", 305, "patch="),
    ("skills/crawl-access-audit/references/ai-bots.json", 16, '"snapshot_date"'),
    ("skills/site-evidence-collector/scripts/politeness.py", 4, "urllib.robotparser"),
    ("skills/render-gap-audit/scripts/diff_raw_rendered.py", 233, "empty_spa_shell"),
    ("skills/render-gap-audit/scripts/diff_raw_rendered.py", 261, '"high", "likely"'),
    ("skills/answerability-audit/scripts/citability.py", 83, 'severity="low"'),
    ("skills/answerability-audit/scripts/retrievability_sim.py", 112, "def self_contained"),
    ("skills/ai-readiness-orchestrator/scripts/gate_model.py", 81, "def build_gate_state"),
    ("skills/ai-readiness-orchestrator/scripts/gate_model.py", 129, "Rule 0"),
    ("skills/ai-readiness-orchestrator/scripts/gate_model.py", 137, "cap_severity"),
    ("skills/engagement-audit/scripts/gating.py", 51, "RULE_0B_EXEMPT"),
    ("skills/trust-freshness-audit/scripts/corroboration.py", 101, '"likely"'),
    ("skills/trust-freshness-audit/scripts/corroboration.py", 133, "__FILL_IN__"),
    ("skills/site-profile-classifier/scripts/profile.py", 266, "necessary"),
    ("skills/ai-readiness-orchestrator/scripts/severity.py", 27, "CONFIDENCE_TO_ICE"),
    ("skills/ai-readiness-orchestrator/scripts/severity.py", 48, "def ice"),
    ("skills/ai-readiness-orchestrator/scripts/severity.py", 68, "def sort_key"),
    ("tests/expected_inventory.json", 612, "h1_cta_mismatch"),
    ("DESIGN.md", 320, "zero recall"),
    ("DESIGN.md", 374, "365 findings"),
]


def resolve(name: str) -> Path | None:
    direct = ENGINE_DIR / name
    if direct.is_file():
        return direct
    matches = [p for p in ENGINE_DIR.rglob(Path(name).name) if p.is_file()
               and "__pycache__" not in p.parts and str(p.as_posix()).endswith(name)]
    return matches[0] if len(matches) == 1 else None


def check_anchors() -> None:
    if not SCRIPT_PATH.exists():
        record("FAIL", "script.anchors_resolve", "round4/VIDEO_SCRIPT.md is missing")
        return
    part1 = SCRIPT_PATH.read_text(encoding="utf-8").split("## Part 1")[1].split("## Part 2")[0]
    last: Path | None = None
    total, broken = 0, []
    for name, start, end in ANCHOR.findall(part1):
        path = resolve(name) if name else last
        if name and path:
            last = path
        total += 1
        lo, hi = int(start), int(end or start)
        if path is None:
            broken.append(f"{name or '?'}:{start}")
            continue
        n_lines = len(path.read_text(encoding="utf-8").splitlines())
        if not (1 <= lo <= hi <= n_lines):
            broken.append(f"{path.name}:{lo}-{hi} (file has {n_lines} lines)")
    record("PASS" if total and not broken else "FAIL", "script.anchors_resolve",
           f"{total} path:line anchors in Part 1 resolve inside the frozen engine" if not broken
           else f"unresolved: {broken[:4]}")

    wrong = []
    for rel, line, needle in KEY_ANCHORS:
        path = ENGINE_DIR / rel
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        if len(lines) < line or needle not in lines[line - 1]:
            wrong.append(f"{Path(rel).name}:{line} lacks {needle!r}")
    record("PASS" if not wrong else "FAIL", "script.claims_land_on_code",
           f"{len(KEY_ANCHORS)} narrated claims land on the code they describe" if not wrong
           else "; ".join(wrong[:3]))


# ---------------------------------------------------------------- goldens

def substance(report: dict) -> dict:
    clean = json.loads(json.dumps(report))
    node = clean
    for key in VOLATILE_METADATA[:-1]:
        node = node.get(key, {})
    node.pop(VOLATILE_METADATA[-1], None)
    return clean


def check_goldens() -> None:
    entry = ENGINE_DIR / "skills" / "ai-readiness-orchestrator" / "scripts" / "orchestrate.py"
    env = dict(os.environ, SOURCE_DATE_EPOCH=PINNED_EPOCH, PYTHONIOENCODING="utf-8",
               PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryDirectory(prefix="round4-goldens-") as tmp:
        for site in FIXTURES:
            out = Path(tmp) / site
            proc = subprocess.run(
                [sys.executable, str(entry), "--offline-root", str(ENGINE_DIR / "tests" / "fixtures" / site),
                 "--out", str(out)],
                capture_output=True, text=True, env=env, timeout=300,
            )
            if proc.returncode != 0:
                record("FAIL", f"goldens.{site}", f"exit {proc.returncode}: {proc.stderr.strip()[:160]}")
                continue
            got = json.loads((out / "audit-report.json").read_text(encoding="utf-8"))
            golden_json = ENGINE_DIR / "tests" / "golden" / f"{site}.audit-report.json"
            want = json.loads(golden_json.read_text(encoding="utf-8"))
            md_same = (out / "report.md").read_bytes() == (
                ENGINE_DIR / "tests" / "golden" / f"{site}.report.md").read_bytes()
            same = substance(got) == substance(want)
            record("PASS" if same and md_same else "FAIL", f"goldens.{site}",
                   f"{len(got['findings'])} findings identical to golden; report.md byte-identical"
                   if same and md_same else "differs from the checked-in golden")


# ---------------------------------------------------------------- compare

def compare(path_a: str, path_b: str) -> int:
    a = json.loads(Path(path_a).read_text(encoding="utf-8"))
    b = json.loads(Path(path_b).read_text(encoding="utf-8"))

    def by_check(report: dict) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for f in report["findings"]:
            out.setdefault(f["check_id"], []).append(f)
        return out

    ca, cb = by_check(a), by_check(b)
    print(f"A: {path_a}\n   {a['site']} audited {a['audited_at']}")
    print(f"B: {path_b}\n   {b['site']} audited {b['audited_at']}\n")
    print(f"{'':24}{'A':>6}{'B':>6}")
    for key in ("total_findings", "critical", "high", "medium", "low", "info", "blocked_findings"):
        print(f"{key:<24}{a['summary'].get(key, 0):>6}{b['summary'].get(key, 0):>6}")

    def worst(fs: list[dict]) -> str:
        order = ["info", "low", "medium", "high", "critical"]
        return max((f["severity"] for f in fs), key=order.index)

    print(f"\n{'check_id':<44}{'A (worst, count)':>18}{'B (worst, count)':>18}")
    for check in sorted(set(ca) | set(cb)):
        sa = f"{worst(ca[check])} x{len(ca[check])}" if check in ca else "-"
        sb = f"{worst(cb[check])} x{len(cb[check])}" if check in cb else "-"
        same = (check in ca) == (check in cb) and (check not in ca or worst(ca[check]) == worst(cb[check]))
        print(f"{check:<44}{sa:>18}{sb:>18}{'' if same else '   <'}")

    head_a = (a["findings"][0]["check_id"], a["findings"][0]["severity"]) if a["findings"] else None
    head_b = (b["findings"][0]["check_id"], b["findings"][0]["severity"]) if b["findings"] else None
    serious = lambda c: {k for k, fs in c.items() if worst(fs) in ("critical", "high")}
    same_head = head_a == head_b
    same_serious = serious(ca) == serious(cb)
    print(f"\nF-001 (top priority): A={head_a} B={head_b} -> {'same' if same_head else 'DIFFERENT'}")
    print(f"critical/high checks: {'same set' if same_serious else 'DIFFERENT'}: "
          f"A={sorted(serious(ca))} B={sorted(serious(cb))}")
    verdict = same_head and same_serious
    print("\nverdict:", "SAME SUBSTANCE (top finding and every critical/high check agree)" if verdict
          else "MATERIAL DIFFERENCE (see rows marked <)")
    print("Lower-severity rows can legitimately differ between runs of a live site whose pages change "
          "(a news homepage samples different articles each day); the engine itself is deterministic "
          "for a fixed evidence bundle.")
    return 0 if verdict else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--goldens", action="store_true", help="also re-run the six fixture audits offline")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"), help="substance diff of two reports")
    parser.add_argument("--make-freeze", action="store_true", help="regenerate ENGINE_FREEZE.json from git")
    args = parser.parse_args(argv)

    if args.make_freeze:
        return make_freeze()
    if args.compare:
        return compare(*args.compare)

    print("Round 4 verification: the demo runs the unchanged Round 3 engine\n")
    freeze = check_freeze()
    print()
    check_replay(freeze)
    print()
    check_anchors()
    if args.goldens:
        print()
        check_goldens()

    failed = [name for status, name, _ in results if status == "FAIL"]
    warned = [name for status, name, _ in results if status == "WARN"]
    passed = sum(1 for status, _, _ in results if status == "PASS")
    print(f"\n{passed} passed, {len(warned)} warning(s), {len(failed)} failed")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("OK: engine is byte-identical to the Round 3 submission and the manifest is well formed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
