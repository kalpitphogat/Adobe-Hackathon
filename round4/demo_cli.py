#!/usr/bin/env python3
"""bairz - a terminal front end for the Round 3 marketplace, built for the demo.

Round 4 wants a CLI session in which an agent runs the marketplace and reports
findings, with one finding drilled into on camera and fixes visibly ordered by
impact. The engine already does all of that; what it does not do is render well
at 720p in a two-minute video. This is that rendering layer, and nothing more.

The one rule it follows, because the integrity gate depends on it:

    THIS FILE CONTAINS NO CHECKS.

Every audit shells out to the submitted entrypoint and reads the report it
writes. Nothing here inspects a website, scores a finding, or decides a
severity. It prints the exact command before running it, so a viewer can see
the engine being driven rather than imitated. If this file disappeared, the
findings would be identical -- they would just be less pleasant to look at.

    python3 round4/demo_cli.py doctor
    python3 round4/demo_cli.py audit https://example.com
    python3 round4/demo_cli.py audit --offline-root tests/fixtures/site_b
    python3 round4/demo_cli.py show ./audit-output
    python3 round4/demo_cli.py show ./audit-output --id F-002
    python3 round4/demo_cli.py prove ./audit-output

Standard library only, so a judge needs nothing installed that the marketplace
does not already need.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / "brand-ai-readiness-audit"
ENTRYPOINT = MARKETPLACE / "skills" / "ai-readiness-orchestrator" / "scripts" / "orchestrate.py"
FREEZE_CHECK = Path(__file__).resolve().parent / "check_engine_frozen.py"


# ───────────────────────────────────────────────────────────── presentation ──

class Ink:
    """ANSI, switched off when nobody can see it."""

    def __init__(self) -> None:
        self.on = (
            sys.stdout.isatty()
            and os.environ.get("NO_COLOR") is None
            and os.environ.get("TERM") != "dumb"
        )

    def _w(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.on else text

    def bold(self, t): return self._w("1", t)
    def dim(self, t): return self._w("2", t)
    def red(self, t): return self._w("1;31", t)
    def amber(self, t): return self._w("1;33", t)
    def blue(self, t): return self._w("1;34", t)
    def green(self, t): return self._w("1;32", t)
    def grey(self, t): return self._w("90", t)
    def invert(self, t): return self._w("7", t)


ink = Ink()

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_INK = {
    "critical": ink.red, "high": ink.amber, "medium": ink.blue,
    "low": ink.grey, "info": ink.grey,
}
STAGE_BLURB = {
    "reach": "can a crawler get in",
    "read": "can it read the page without JavaScript",
    "extract": "can it pick the fact out",
    "trust": "would it believe the fact",
    "act": "does an arriving visitor stay",
}


def width() -> int:
    return min(shutil.get_terminal_size((100, 24)).columns, 100)


def rule(char: str = "─") -> str:
    return ink.grey(char * width())


def heading(text: str) -> None:
    print(f"\n{ink.bold(text)}\n{rule()}")


def wrap(text: str, indent: int = 2, first: str | None = None) -> str:
    """Wrap to the terminal, keeping a hanging indent."""
    import textwrap
    body = textwrap.fill(
        " ".join(str(text).split()),
        width=width() - indent,
        initial_indent=" " * indent if first is None else first,
        subsequent_indent=" " * indent,
    )
    return body


def sev_tag(severity: str) -> str:
    paint = SEVERITY_INK.get(severity, ink.grey)
    return paint(f"{severity.upper():<9}")


# ───────────────────────────────────────────────────────────────── the bits ──

def die(message: str, code: int = 1) -> int:
    print(f"\n{ink.red('error')} {message}\n", file=sys.stderr)
    return code


def load_report(out_dir: Path) -> dict | None:
    path = out_dir / "audit-report.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def engine_fingerprint() -> str:
    """A short, stable id for the engine being driven.

    Hashes the entrypoint scripts and every SKILL.md. Two runs printing the same
    fingerprint drove the same engine, which is the claim the video has to make
    out loud.
    """
    h = hashlib.sha256()
    for path in sorted(MARKETPLACE.glob("skills/*/SKILL.md")) + sorted(
        MARKETPLACE.glob("skills/*/scripts/*.py")
    ):
        h.update(path.relative_to(MARKETPLACE).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


# ──────────────────────────────────────────────────────────────────── doctor ──

def cmd_doctor(args) -> int:
    heading("Preflight")
    ok = True

    def row(good: bool, label: str, detail: str = "") -> None:
        nonlocal ok
        mark = ink.green("  ok  ") if good else ink.red(" FAIL ")
        print(f"{mark} {label:<42} {ink.grey(detail)}")
        ok = ok and good

    v = sys.version_info
    row(v >= (3, 9), "Python >= 3.9", f"{v.major}.{v.minor}.{v.micro}")
    row(ENTRYPOINT.is_file(), "entrypoint present",
        str(ENTRYPOINT.relative_to(ROOT)) if ENTRYPOINT.is_file() else "missing")

    try:
        import playwright  # noqa: F401
        row(True, "Playwright (optional)", "render-stage checks fully enabled")
    except ImportError:
        row(True, "Playwright (optional)",
            "absent - render checks report 'not assessed', audit still runs")

    if FREEZE_CHECK.is_file():
        proc = subprocess.run([sys.executable, str(FREEZE_CHECK)],
                              capture_output=True, text=True, cwd=str(ROOT))
        row(proc.returncode == 0, "engine frozen vs submission.zip",
            "byte-identical" if proc.returncode == 0 else "DRIFTED - see check_engine_frozen.py")

    print(f"\n  engine fingerprint  {ink.bold(engine_fingerprint())}")
    print(wrap(ink.grey("Say this number on camera and print it again after the run; "
                        "identical means the same engine drove both."), indent=2))

    print()
    if not ok:
        print(ink.red("  Not ready to record.\n"))
        return 1
    print(ink.green("  Ready.\n"))
    return 0


# ───────────────────────────────────────────────────────────────────── audit ──

class Progress:
    """Real progress, read off the filesystem the engine is writing to.

    Not a decorative bar: each step flips only when the artifact that proves it
    appears on disk. A step that never lights up genuinely did not happen.
    """

    STEPS = [
        ("evidence/meta.json", "crawled the site", "site-evidence-collector"),
        ("profile.json", "classified the site", "site-profile-classifier"),
        ("audit-report.json", "composed the report", "ai-readiness-orchestrator"),
    ]

    def __init__(self, out: Path) -> None:
        self.out = out
        self.done: set[str] = set()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        started = time.perf_counter()
        while not self._stop.is_set():
            for rel, label, skill in self.STEPS:
                if rel in self.done:
                    continue
                if (self.out / rel).exists():
                    self.done.add(rel)
                    elapsed = time.perf_counter() - started
                    sys.stdout.write("\r\033[K")
                    print(f"  {ink.green('✓')} {label:<26} "
                          f"{ink.grey(skill)} {ink.grey(f'{elapsed:5.1f}s')}")
            if not self._stop.is_set():
                pending = next((s for r, s, _ in self.STEPS if r not in self.done), "")
                sys.stdout.write(
                    f"\r\033[K  {ink.blue(frames[i % len(frames)])} {pending}"
                    f"{ink.grey(f'   {time.perf_counter() - started:5.1f}s')}"
                )
                sys.stdout.flush()
            i += 1
            time.sleep(0.1)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def __enter__(self):
        if sys.stdout.isatty():
            self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1)


def cmd_audit(args) -> int:
    if not args.url and not args.offline_root:
        return die("give a URL, or --offline-root for a shipped fixture")

    out = Path(args.out).resolve()
    target = args.url or f"fixture:{args.offline_root}"

    cmd = [sys.executable, str(ENTRYPOINT)]
    if args.offline_root:
        cmd += ["--offline-root", args.offline_root]
    else:
        cmd.append(args.url)
    cmd += ["--out", str(out)]
    if args.no_render:
        cmd.append("--no-render")
    if args.probe_bot_ua:
        cmd.append("--probe-bot-ua")
    if args.max_pages:
        cmd += ["--max-pages", str(args.max_pages)]
    cmd += ["--time-budget", str(args.time_budget)]

    heading(f"Auditing  {ink.bold(target)}")

    # The shot that proves this is the submitted engine, not a demo harness.
    print(f"\n  {ink.grey('engine')}      {ink.bold(engine_fingerprint())}")
    print(f"  {ink.grey('invoking')}    {ink.dim(str(ENTRYPOINT.relative_to(ROOT)))}")
    shown = " ".join(["python3", str(ENTRYPOINT.relative_to(MARKETPLACE))] + cmd[2:])
    print(f"\n{wrap(ink.dim(shown), indent=2)}\n")

    started = time.perf_counter()
    with Progress(out):
        proc = subprocess.run(cmd, cwd=str(MARKETPLACE), capture_output=True, text=True)
    elapsed = time.perf_counter() - started

    if proc.returncode != 0:
        print(proc.stderr.strip()[:1200])
        return die(f"the engine exited {proc.returncode}")

    report = load_report(out)
    if report is None:
        return die(f"no report at {out / 'audit-report.json'}")

    print(f"  {ink.grey(f'finished in {elapsed:.1f}s')}\n")
    render_summary(report, out)

    if report["findings"]:
        print(wrap(ink.grey(f"Drill in:  python3 round4/demo_cli.py show {args.out}"), indent=2))
    print()
    return 0


def render_summary(report: dict, out: Path) -> None:
    s = report["summary"]
    status = report.get("audit_status", "?")
    bundle = report.get("evidence_bundle", {})

    status_ink = ink.green if status == "complete" else ink.amber
    fetched = bundle.get("pages_fetched", 0)
    rendered = bundle.get("pages_rendered", 0)
    heading(str(report.get("site", "?")))
    scope = ink.grey(f"{fetched} pages fetched, {rendered} rendered")
    print(f"  status {status_ink(status)}   {scope}")

    counts = "   ".join(
        SEVERITY_INK[sev](f"{s.get(sev, 0)} {sev}")
        for sev in SEVERITY_ORDER if s.get(sev, 0)
    ) or ink.green("nothing to report")
    cat = s.get("by_category", {})
    total = s["total_findings"]
    disc = cat.get("discoverability", 0)
    eng = cat.get("engagement", 0)
    print(f"\n  {ink.bold(str(total))} findings    {counts}")
    print(f"  {ink.grey(f'discoverability {disc}  ·  engagement {eng}')}")

    if report["findings"]:
        heading("Fix in this order")
        for i, f in enumerate(report["findings"][:args_top()], 1):
            gate = ""
            if f.get("blocked_by"):
                gate = ink.grey(f"  ← moot until {f['blocked_by']} is fixed")
            ice = f["suggested_action"].get("ice")
            ice_s = ink.grey(f"ICE {ice}") if ice is not None else ""
            print(f"\n  {ink.bold(f['id'])}  {sev_tag(f['severity'])} "
                  f"{ink.grey(f['stage']):<8} {ice_s}{gate}")
            print(wrap(f["title"], indent=8))
            print(wrap(ink.grey('→ ' + f["suggested_action"]["summary"]), indent=8))

        extra = len(report["findings"]) - args_top()
        if extra > 0:
            print(f"\n  {ink.grey(f'... and {extra} more')}")

    blocked = s.get("blocked_findings", 0)
    if blocked:
        print(f"\n  {ink.grey(f'{blocked} downstream findings are capped: they cannot matter')}")
        print(f"  {ink.grey('until the upstream gate above them is cleared.')}")

    suppressed = s.get("suppressed_by_rule") or []
    if suppressed:
        n = sum(x.get("count", 0) for x in suppressed)
        rules = len(suppressed)
        print(f"\n  {ink.grey(f'{n} finding(s) deliberately NOT raised across {rules} documented rules.')}")

    lims = report.get("limitations") or []
    if lims:
        heading("What could not be assessed")
        print(wrap(ink.grey("Not a pass - the audit says so rather than staying quiet."), indent=2))
        for lim in lims[:3]:
            reason = " ".join(str(lim["reason"]).split())
            # Cut at a sentence end rather than mid-word, so a truncated
            # limitation still reads as a statement.
            if len(reason) > 360:
                cut = reason.rfind(". ", 0, 360)
                reason = reason[: cut + 1] if cut > 200 else reason[:360].rsplit(" ", 1)[0] + " ..."
            print()
            print(wrap(reason, indent=4, first="  · "))


_TOP = 5


def args_top() -> int:
    return _TOP


# ────────────────────────────────────────────────────────────────────── show ──

def cmd_show(args) -> int:
    out = Path(args.out).resolve()
    report = load_report(out)
    if report is None:
        return die(f"no report at {out / 'audit-report.json'} - run `audit` first")

    findings = report["findings"]
    if args.id:
        findings = [f for f in findings if f["id"].lower() == args.id.lower()]
        if not findings:
            return die(f"no finding {args.id!r} in this report")
    else:
        findings = findings[: args.top]

    if not findings:
        heading(report.get("site", "?"))
        print(f"\n  {ink.green('No findings.')} "
              f"{ink.grey('Nothing the audit checks is wrong with this site.')}\n")
        return 0

    for f in findings:
        render_finding(f, out)
    print()
    return 0


def render_finding(f: dict, out: Path) -> None:
    a = f["suggested_action"]
    print(f"\n{rule('━')}")
    meta = f"{f['stage']}  ·  {f['category']}  ·  {f['confidence']}"
    print(f"{ink.bold(f['id'])}   {sev_tag(f['severity'])}{ink.grey(meta)}")
    print(wrap(ink.bold(f["title"]), indent=0))
    print(rule())

    if f.get("blocked_by"):
        gate_id = f["blocked_by"]
        print(f"\n  {ink.amber('GATED')} "
              f"{ink.grey(f'by {gate_id} - real, but it changes nothing until that is fixed.')}")

    print(f"\n  {ink.bold('Evidence')}   {ink.grey('what was actually observed')}")
    print(wrap(f["evidence"], indent=4))

    urls = f.get("affected_urls") or []
    if urls:
        count = f.get("affected_url_count", len(urls))
        print(f"\n  {ink.bold('Where')}      {ink.grey(f'{count} page(s)')}")
        for u in urls[:4]:
            print(f"    {ink.grey(u)}")
        if len(urls) > 4:
            print(f"    {ink.grey(f'... and {len(urls) - 4} more')}")

    print(f"\n  {ink.bold('Why it hurts')}")
    print(wrap(a.get("mechanism", "—"), indent=4))

    prio, effort, ice = a.get("priority"), a.get("effort"), a.get("ice")
    print(f"\n  {ink.bold('Fix')}        "
          f"{ink.grey(f'priority {prio}  ·  effort {effort}  ·  ICE {ice}')}")
    print(wrap(a["summary"], indent=4))

    patch = a.get("patch")
    if patch:
        print(f"\n  {ink.bold('Patch')}      {ink.grey('paste-ready')}")
        for line in str(patch).splitlines()[:12]:
            print(f"    {ink.green(line)}")
        if len(str(patch).splitlines()) > 12:
            print(f"    {ink.grey('...')}")
        if a.get("patch_path") and (out / a["patch_path"]).exists():
            rel = a["patch_path"]
            print(f"    {ink.grey(f'full patch: {out.name}/{rel}')}")

    if a.get("verification"):
        print(f"\n  {ink.bold('Verify')}     {ink.grey('confirm the fix landed')}")
        print(wrap(ink.dim(a["verification"]), indent=4))

    if a.get("source"):
        print(f"\n  {ink.grey('source: ' + str(a['source']))}")

    print(f"  {ink.grey('check id: ' + f['check_id'])}")


# ───────────────────────────────────────────────────────────────────── prove ──

def cmd_prove(args) -> int:
    """Determinism and engine identity, the two things a replaying judge tests."""
    heading("Reproducibility")

    print(f"\n  {ink.bold('1.')} Engine identity")
    print(f"     fingerprint {ink.bold(engine_fingerprint())}")
    if FREEZE_CHECK.is_file():
        proc = subprocess.run([sys.executable, str(FREEZE_CHECK)],
                              capture_output=True, text=True, cwd=str(ROOT))
        mark = ink.green("byte-identical to submission.zip") if proc.returncode == 0 \
            else ink.red("DRIFTED from submission.zip")
        print(f"     {mark}")

    print(f"\n  {ink.bold('2.')} Determinism on the shipped fixtures")
    print(f"     {ink.grey('six golden reports, compared byte-for-byte,')}")
    print(f"     {ink.grey('plus a TZ x PYTHONHASHSEED matrix')}")
    proc = subprocess.run([sys.executable, "tests/run_offline.py"],
                          cwd=str(MARKETPLACE), capture_output=True, text=True)
    last = [l for l in proc.stdout.strip().splitlines() if l.strip()][-1:]
    print(f"     {(ink.green if proc.returncode == 0 else ink.red)(last[0] if last else '?')}")

    out = Path(args.out).resolve() if args.out else None
    if out and (out / "audit-report.json").exists():
        print(f"\n  {ink.bold('3.')} Re-running this audit and diffing the report")
        first = load_report(out)
        target = first.get("site")
        print(f"     {ink.grey(f'site: {target}')}")
        print(f"     {ink.grey('re-running against the same target...')}")

        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="prove-"))
        try:
            cmd = [sys.executable, str(ENTRYPOINT)]
            if args.offline_root:
                cmd += ["--offline-root", args.offline_root]
            else:
                cmd.append(f"https://{target}" if not str(target).startswith("http") else target)
            cmd += ["--out", str(tmp), "--time-budget", "300"]
            proc = subprocess.run(cmd, cwd=str(MARKETPLACE), capture_output=True, text=True)
            second = load_report(tmp)
            if proc.returncode != 0 or second is None:
                print(f"     {ink.amber('re-run did not complete; skipping the diff')}")
            else:
                same = compare_reports(first, second)
                if same:
                    print(f"     {ink.green('identical findings, identical order')}")
                else:
                    note = "findings differ - expected on a live site that changed"
                    print(f"     {ink.amber(note)}")
                    for line in same_detail(first, second)[:5]:
                        print(f"       {ink.grey(line)}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print()
    return 0


def _comparable(report: dict) -> list[tuple]:
    """Everything that should be stable between two runs of the same input.

    audited_at always moves and the bundle path is a temp dir, so neither is
    evidence of nondeterminism.
    """
    return [(f["check_id"], f["severity"], f["id"], tuple(sorted(f.get("affected_urls") or [])))
            for f in report["findings"]]


def compare_reports(a: dict, b: dict) -> bool:
    return _comparable(a) == _comparable(b)


def same_detail(a: dict, b: dict) -> list[str]:
    first, second = {x[0] for x in _comparable(a)}, {x[0] for x in _comparable(b)}
    out = [f"only in run 1: {c}" for c in sorted(first - second)]
    out += [f"only in run 2: {c}" for c in sorted(second - first)]
    return out or ["same checks fired; ordering or scope differed"]


# ────────────────────────────────────────────────────────────────────── main ──

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="demo_cli.py",
        description="Terminal front end for the Brand AI-Readiness Audit marketplace. "
                    "Contains no checks: it drives the submitted entrypoint and renders "
                    "what that engine returns.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="preflight before recording")
    d.set_defaults(fn=cmd_doctor)

    a = sub.add_parser("audit", help="run the engine against a URL and summarise")
    a.add_argument("url", nargs="?")
    a.add_argument("--offline-root", help="audit a shipped fixture instead of the network")
    a.add_argument("--out", default="./audit-output")
    a.add_argument("--no-render", action="store_true")
    a.add_argument("--probe-bot-ua", action="store_true",
                   help="probe CDN/WAF reachability - only for a site you own")
    a.add_argument("--max-pages", type=int)
    a.add_argument("--time-budget", type=int, default=300)
    a.set_defaults(fn=cmd_audit)

    s = sub.add_parser("show", help="drill into findings with full evidence")
    s.add_argument("out", nargs="?", default="./audit-output")
    s.add_argument("--id", help="one finding, e.g. F-001")
    s.add_argument("--top", type=int, default=3)
    s.set_defaults(fn=cmd_show)

    p = sub.add_parser("prove", help="engine identity and determinism")
    p.add_argument("out", nargs="?", default=None)
    p.add_argument("--offline-root", help="re-run against this fixture")
    p.set_defaults(fn=cmd_prove)

    args = ap.parse_args(argv)

    if not ENTRYPOINT.is_file():
        return die(f"entrypoint not found at {ENTRYPOINT}\n"
                   f"        run this from the repository root.")
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print(f"\n{ink.grey('interrupted')}\n")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
