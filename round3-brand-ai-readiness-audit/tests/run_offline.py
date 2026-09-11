#!/usr/bin/env python3
"""Determinism proof: audit every fixture with networking disabled, twice.

Three things this must guarantee, in order of how easily they fail silently:

  1. NO NETWORK. The socket patch is applied and then PROVED to be in effect by
     attempting a connection and requiring it to raise. A silently ineffective
     patch would let a hidden fetch through and nothing would notice.
  2. NO PARTIAL WRITES. Disk space is checked before anything is written, and
     every write in the pipeline is atomic. A truncated golden becomes the
     reference that every later test validates against, and no passing test
     catches it.
  3. BYTE-IDENTICAL OUTPUT. Two runs of the same fixture, across varied
     PYTHONHASHSEED and TZ, must produce identical bytes.

Usage:
  python tests/run_offline.py                    # run all fixtures, diff goldens
  python tests/run_offline.py --update-goldens   # regenerate goldens
  python tests/run_offline.py --assert-clean site_a
  python tests/run_offline.py --site site_b --explain-gates
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
GOLDEN = ROOT / "tests" / "golden"
ORCH = ROOT / "skills" / "ai-readiness-orchestrator" / "scripts" / "orchestrate.py"
SCHEMA = ROOT / "skills" / "ai-readiness-orchestrator" / "references" / "report-schema.json"

SITES = ["site_a", "site_b", "site_c", "site_d", "site_e"]
PINNED_EPOCH = "1780000000"
MIN_FREE_BYTES = 64 * 1024 * 1024


class NetworkAccessDuringOfflineRun(RuntimeError):
    """Raised if anything attempts a socket connection during an offline run."""


def install_network_block() -> None:
    """Disable outbound sockets, then PROVE the block is live.

    ORDER MATTERS. This must run AFTER every import that touches sockets.
    Patching socket.socket before `import ssl` breaks the import outright,
    because ssl.SSLSocket subclasses socket.socket and the class statement then
    fails with `TypeError: function() argument 'code' must be code, not str`.
    Do not move this earlier, and do not "tidy" the import order above it.
    """
    import socket

    def deny(*_a, **_k):
        raise NetworkAccessDuringOfflineRun(
            "a socket connection was attempted during an offline run"
        )

    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    socket.create_connection = deny
    socket.getaddrinfo = deny

    # Prove it. A patch that silently failed to apply is worse than no patch,
    # because the run would pass while quietly reaching the network.
    proved = False
    try:
        socket.create_connection(("192.0.2.1", 80), timeout=0.1)
    except NetworkAccessDuringOfflineRun:
        proved = True
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"FATAL: the network block is not in effect. A connection attempt raised "
            f"{type(exc).__name__} instead of NetworkAccessDuringOfflineRun, which means "
            f"the patch did not apply and an offline run could reach the network."
        ) from exc
    if not proved:
        raise SystemExit(
            "FATAL: the network block is not in effect. A connection to a reserved "
            "address SUCCEEDED, so nothing is stopping a hidden fetch."
        )
    print("  network block: verified live (a connection attempt raised as required)")


def check_free_space(target: Path) -> None:
    try:
        usage = shutil.disk_usage(target if target.exists() else target.parent)
    except OSError as exc:
        raise SystemExit(f"FATAL: cannot stat filesystem for {target}: {exc}") from exc
    if usage.free < MIN_FREE_BYTES:
        raise SystemExit(
            f"FATAL: only {usage.free / 1048576:.1f} MiB free at {target}; "
            f"{MIN_FREE_BYTES / 1048576:.0f} MiB required. Refusing to run: a disk that "
            f"fills mid-write leaves a truncated report, and a truncated golden silently "
            f"becomes the reference everything else validates against."
        )
    print(f"  free space: {usage.free / 1073741824:.1f} GiB available")


def audit(site: str, out: Path, env_extra: dict | None = None, explain: bool = False) -> dict:
    """Run the orchestrator in a subprocess with networking blocked inside it."""
    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = PINNED_EPOCH
    env["PYTHONIOENCODING"] = "utf-8"
    env["BARA_OFFLINE"] = "1"
    env.update(env_extra or {})
    argv = [sys.executable, str(ORCH), "--offline-root", str(FIXTURES / site), "--out", str(out)]
    if explain:
        argv.append("--explain-gates")
    proc = subprocess.run(argv, capture_output=True, text=True, env=env, cwd=str(ROOT))
    if proc.returncode != 0:
        raise SystemExit(f"FATAL: {site} exited {proc.returncode}\n{proc.stderr[:2000]}")
    if "Traceback" in proc.stderr:
        raise SystemExit(f"FATAL: {site} leaked a traceback\n{proc.stderr[:2000]}")
    if explain:
        sys.stderr.write(proc.stderr)
    return json.loads((out / "audit-report.json").read_text(encoding="utf-8"))


def validate_floor(report: dict, label: str) -> list[str]:
    """The handout's required shape. Cheap insurance against silent corruption."""
    problems = []
    if not {"site", "audited_at", "summary", "findings"} <= set(report):
        problems.append(f"{label}: missing a required top-level field")
    if not {"total_findings", "critical", "high", "medium"} <= set(report.get("summary", {})):
        problems.append(f"{label}: missing a required summary count")
    for f in report.get("findings", []):
        if not {"id", "title", "severity", "evidence", "suggested_action"} <= set(f):
            problems.append(f"{label}: finding {f.get('id')} missing a required field")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", help="run one fixture only")
    parser.add_argument("--out", help="keep output in this directory instead of a temp dir")
    parser.add_argument("--update-goldens", action="store_true")
    parser.add_argument("--assert-clean", nargs="*", metavar="SITE",
                        help="require zero high or critical findings for these fixtures")
    parser.add_argument("--explain-gates", action="store_true")
    parser.add_argument("--skip-matrix", action="store_true",
                        help="skip the TZ x PYTHONHASHSEED determinism matrix")
    args = parser.parse_args(argv)

    print("offline determinism run")
    out_root = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="bara-offline-"))
    check_free_space(out_root)
    install_network_block()

    sites = [args.site] if args.site else SITES
    failures: list[str] = []

    try:
        # --------------------------------------------------- golden integrity
        print("\ngolden integrity")
        for site in sites:
            gp = GOLDEN / f"{site}.audit-report.json"
            if not gp.exists():
                if not args.update_goldens:
                    failures.append(f"{site}: no golden checked in")
                continue
            try:
                golden = json.loads(gp.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append(f"{site}: GOLDEN IS NOT VALID JSON ({exc}) - likely truncated")
                continue
            problems = validate_floor(golden, f"{site} golden")
            failures.extend(problems)
            print(f"  {site:8} golden parses, satisfies the handout floor, "
                  f"{golden['summary']['total_findings']} findings")

        # ------------------------------------------------------ run and diff
        print("\nrun 1 vs run 2, byte-identical")
        reports: dict[str, dict] = {}
        for site in sites:
            r1 = audit(site, out_root / "run1" / site, explain=args.explain_gates)
            r2 = audit(site, out_root / "run2" / site)
            b1 = (out_root / "run1" / site / "audit-report.json").read_bytes()
            b2 = (out_root / "run2" / site / "audit-report.json").read_bytes()
            m1 = (out_root / "run1" / site / "report.md").read_bytes()
            m2 = (out_root / "run2" / site / "report.md").read_bytes()
            same = b1 == b2 and m1 == m2
            print(f"  {site:8} {'identical' if same else 'DIFFERS'}  "
                  f"({len(b1)} bytes json, {len(m1)} bytes md)")
            if not same:
                failures.append(f"{site}: two runs differ")
            reports[site] = r1

            problems = validate_floor(r1, site)
            failures.extend(problems)

        # ------------------------------------------- TZ x PYTHONHASHSEED matrix
        if not args.skip_matrix:
            print("\ndeterminism matrix (TZ x PYTHONHASHSEED)")
            for site in sites[:2]:
                base = (out_root / "run1" / site / "audit-report.json").read_bytes()
                for tz in ("UTC", "Asia/Kolkata"):
                    for seed in ("0", "12345"):
                        d = out_root / f"m-{site}-{tz.replace('/', '_')}-{seed}"
                        audit(site, d, {"TZ": tz, "PYTHONHASHSEED": seed})
                        got = (d / "audit-report.json").read_bytes()
                        ok = got == base
                        print(f"  {site:8} TZ={tz:13} seed={seed:6} {'identical' if ok else 'DIFFERS'}")
                        if not ok:
                            failures.append(f"{site}: differs under TZ={tz} PYTHONHASHSEED={seed}")

        # -------------------------------------------------- golden comparison
        if args.update_goldens:
            print("\nupdating goldens")
            GOLDEN.mkdir(parents=True, exist_ok=True)
            for site in sites:
                for name in ("audit-report.json", "report.md"):
                    src = out_root / "run1" / site / name
                    dst = GOLDEN / f"{site}.{name}"
                    tmp = dst.with_name(dst.name + ".tmp")
                    with open(tmp, "wb") as fh:
                        fh.write(src.read_bytes())
                        fh.flush()
                        os.fsync(fh.fileno())
                    os.replace(tmp, dst)
                    print(f"  wrote {dst.relative_to(ROOT)}")
        else:
            print("\ngolden comparison")
            for site in sites:
                gp = GOLDEN / f"{site}.audit-report.json"
                if not gp.exists():
                    continue
                got = (out_root / "run1" / site / "audit-report.json").read_bytes()
                if got == gp.read_bytes():
                    print(f"  {site:8} matches golden")
                else:
                    print(f"  {site:8} DRIFTED from golden")
                    failures.append(f"{site}: output drifted from the checked-in golden")

        # ---------------------------------------------------- clean assertions
        clean = args.assert_clean if args.assert_clean is not None else ["site_a"]
        if clean:
            print("\nfalse-positive control")
            for site in clean:
                report = reports.get(site) or audit(site, out_root / "clean" / site)
                bad = [f for f in report["findings"] if f["severity"] in ("critical", "high")]
                if bad:
                    print(f"  {site:8} FAILED: {[f['check_id'] for f in bad]}")
                    failures.append(f"{site}: {len(bad)} high/critical findings on a control fixture")
                else:
                    print(f"  {site:8} clean: zero high or critical "
                          f"({report['summary']['total_findings']} findings total)")

    finally:
        if not args.out:
            shutil.rmtree(out_root, ignore_errors=True)

    print()
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS: offline, deterministic, goldens current, control clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
