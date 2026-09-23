"""Check REPLAY_<Team>.txt against Section 5 of the Round 4 brief, and against the run sheet.

Fails (exit 1) on anything that would make judges treat the run as unverified:
wrong file name, a missing or blank field, a URL that is not a full URL, TEST_STEPS
without steps 1-3, or a run sheet that names a different harness, model or URL.

Usage: python tools/check_replay.py [REPLAY_IT_Professionals.txt] [VIDEO_PART2_RUNSHEET.md]
"""
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

FIELDS = ["TEST_SITE_URLS", "LLM_MODEL", "AGENT_HARNESS", "ENV_SETUP", "TEST_STEPS", "EXPECTED_OUTPUT"]


def parse(text: str) -> dict[str, str]:
    """Split the labelled part of the file (before the first comment line) into fields."""
    fields: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("#"):
            break  # everything from the first comment line on is commentary
        m = re.match(r"^([A-Z_]+):\s?(.*)$", line)
        if m and m.group(1) in FIELDS:
            current = m.group(1)
            fields[current] = [m.group(2)]
        elif current:
            fields[current].append(line)
    return {k: "\n".join(v).strip() for k, v in fields.items()}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    replay = Path(sys.argv[1] if len(sys.argv) > 1 else "REPLAY_IT_Professionals.txt")
    runsheet = Path(sys.argv[2] if len(sys.argv) > 2 else "VIDEO_PART2_RUNSHEET.md")
    problems: list[str] = []
    ok: list[str] = []

    if re.fullmatch(r"REPLAY_[A-Za-z0-9_]+\.txt", replay.name):
        ok.append(f"file name {replay.name}")
    else:
        problems.append(f"file name {replay.name!r} is not REPLAY_YourTeamName.txt")

    raw = replay.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        problems.append("not valid UTF-8 plain text")
        text = raw.decode("utf-8", "replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append("starts with a UTF-8 BOM; the first field name would not parse cleanly")

    fields = parse(text)
    for name in FIELDS:
        if not fields.get(name):
            problems.append(f"field {name} missing or blank")
    if all(fields.get(n) for n in FIELDS):
        ok.append("all six mandatory fields present and non-blank")

    urls = [u.strip() for u in fields.get("TEST_SITE_URLS", "").split(",") if u.strip()]
    for u in urls:
        p = urlparse(u)
        if p.scheme not in ("http", "https") or "." not in p.netloc or " " in u:
            problems.append(f"TEST_SITE_URLS entry {u!r} is not an exact full URL")
    if urls and not any("not an exact full URL" in p for p in problems):
        ok.append(f"TEST_SITE_URLS: {len(urls)} full URL(s)")

    steps = fields.get("TEST_STEPS", "")
    for n in (1, 2, 3):
        if not re.search(rf"(?m)^\s*{n}\.\s", steps):
            problems.append(f"TEST_STEPS has no step {n}")
    prompt_lines = [ln.strip() for ln in steps.splitlines() if "SKILL.md" in ln and "URL" in ln]
    if prompt_lines and prompt_lines[-1].endswith("URL: <URL>"):
        ok.append("step-2 prompt ends with 'URL: <URL>' (URL typed last, on camera)")
    else:
        problems.append("step-2 prompt not found, or does not end with 'URL: <URL>'")

    # consistency with the run sheet: harness version, model id, on-camera URL
    if runsheet.exists():
        rs = runsheet.read_text(encoding="utf-8")
        harness_ver = re.search(r"v?(\d+\.\d+\.\d+)", fields.get("AGENT_HARNESS", ""))
        model_id = re.search(r"claude-[a-z0-9-]+", fields.get("LLM_MODEL", ""))
        checks = {
            "harness version": harness_ver.group(1) if harness_ver else None,
            "model id": model_id.group(0) if model_id else None,
            "on-camera URL (first TEST_SITE_URLS entry)": urls[0] if urls else None,
        }
        for label, value in checks.items():
            if value and value in rs:
                ok.append(f"run sheet matches {label}: {value}")
            else:
                problems.append(f"run sheet does not mention {label} {value!r}")
    else:
        problems.append(f"run sheet {runsheet} not found; cannot check consistency with the video")

    for line in ok:
        print(f"[ OK ] {line}")
    for line in problems:
        print(f"[FAIL] {line}")
    print(f"\n{len(ok)} ok, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
