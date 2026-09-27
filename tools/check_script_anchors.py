"""Check every code anchor in VIDEO_SCRIPT.md against the submitted Round 3 zip.

Part 1 of the video earns credit only for claims traceable to the submitted code, so each
claim has a row in the script's anchor ledger (section 5): an id, a file:line inside the
marketplace, and text that must appear on that exact line. This reads each file straight
out of submission.zip (not an unzipped copy that could have drifted) and fails (exit 1) if
the zip's hash is wrong, a file is missing, or a line no longer says what the script claims.

It also recomputes the numbers the script speaks or captions (29 crawlers and their roles,
155 files, 11 findings blocked by F-001 in the site_b golden, the __FILL_IN__ count) and
counts Part 1's spoken words, failing if the full cut is too long to fit in 3:00 at 150 words
per minute, a normal speaking pace (the timed read in RECORDING_FLOW 0.5 has the last word).

Usage: python tools/check_script_anchors.py [VIDEO_SCRIPT.md] [round3-frozen/submission.zip]
"""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ZIP_SHA256 = "1c872c598dcac741c712cbf9e671f024881a9ba251e2b4da66995f81b6cf8dcf"
ROW = re.compile(r"^\|\s*(A\d+)\s*\|[^|]*\|\s*`([^`]+):(\d+)`\s*\|\s*`(.+)`\s*\|\s*$")

PART1_WPM_FLOOR = 150     # a normal speaking pace
PART1_CAP_SECONDS = 180   # brief: Part 1 hard cap 3:00
PART1_TAB_SECONDS = 8     # title card plus pauses the narration doesn't cover


def part1_spoken_words(script: str, bonus: bool = False) -> int:
    """Words in the '>' lines between the PART 1 heading and the cut ladder.

    Lines starting with **BONUS** are optional extras: counted only when bonus=True, so the
    3:00 check times the main read."""
    start = script.index("PART 1 · Thought process")
    end = script.index("### If the timed run is long")
    words = 0
    for line in script[start:end].splitlines():
        if not line.startswith("> "):
            continue
        text = line[2:]
        if text.startswith("Spoken lines are"):
            continue  # the legend, not narration
        if text.startswith("**BONUS**") != bonus:
            continue
        if bonus:
            text = text[len("**BONUS**"):]
        text = re.sub(r"[*`·]", " ", text)
        words += sum(1 for w in text.split() if re.search(r"\w", w))  # "**price**." is one word
    return words


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    script_path = Path(sys.argv[1] if len(sys.argv) > 1 else "VIDEO_SCRIPT.md")
    zip_path = Path(sys.argv[2] if len(sys.argv) > 2 else "round3-frozen/submission.zip")
    script = script_path.read_text(encoding="utf-8")
    problems: list[str] = []
    ok = 0

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if digest != ZIP_SHA256:
        problems.append(f"{zip_path} sha256 is {digest}, not the submitted {ZIP_SHA256}")
    if not zipfile.is_zipfile(zip_path):
        print(f"[FAIL] {zip_path} is not a zip file\n\n1 problem(s)")
        return 1

    rows = [m.groups() for m in map(ROW.match, script.splitlines()) if m]
    if not rows:
        problems.append(f"no anchor rows found in {script_path}")

    with zipfile.ZipFile(zip_path) as z:
        names = {n for n in z.namelist() if not n.endswith("/")}
        cache: dict[str, list[str]] = {}
        for anchor_id, path, line_no, needle in rows:
            if path not in names:
                problems.append(f"{anchor_id}: {path} is not in the zip")
                continue
            lines = cache.setdefault(path, z.read(path).decode("utf-8").splitlines())
            n = int(line_no)
            if not 1 <= n <= len(lines):
                problems.append(f"{anchor_id}: {path} has {len(lines)} lines, no line {n}")
            elif needle not in lines[n - 1]:
                problems.append(f"{anchor_id}: {path}:{n} reads {lines[n - 1].strip()!r}, "
                                f"expected it to contain {needle!r}")
            else:
                ok += 1

        # numbers the script says out loud or puts in a caption
        bots = json.loads(z.read("skills/crawl-access-audit/references/ai-bots.json"))["bots"]
        roles = {c: sum(1 for b in bots if b["category"] == c)
                 for c in ("retrieval", "training", "dual_purpose")}
        golden = json.loads(z.read("tests/golden/site_b.audit-report.json"))
        blocked = sum(1 for f in golden["findings"] if f.get("blocked_by") == "F-001")
        fill_in = sum(
            1
            for n in names if n.startswith("skills/") and n.endswith(".py")
            for ln in z.read(n).decode("utf-8").splitlines() if "__FILL_IN__" in ln
        )
        facts = {
            "29 crawlers": (len(bots), 29),
            "14 retrieval": (roles["retrieval"], 14),
            "10 training": (roles["training"], 10),
            "5 contested": (roles["dual_purpose"], 5),
            "155 files in the zip": (len(names), 155),
            "11 blocked by F-001 (site_b golden)": (blocked, 11),
            "summary.blocked_findings = 11": (golden["summary"]["blocked_findings"], 11),
            "94 __FILL_IN__ lines in skills/*.py": (fill_in, 94),
            "bonus B5: 1 critical in the site_b golden": (sum(f["severity"] == "critical" for f in golden["findings"]), 1),
            "bonus B5: 8 engagement findings in the site_b golden": (sum(f.get("category") != "discoverability" for f in golden["findings"]), 8),
            "bonus B5: no engagement finding is capped": (sum(1 for f in golden["findings"] if f.get("category") != "discoverability" and f.get("blocked_by")), 0),
        }
        for label, (got, want) in facts.items():
            if got == want:
                ok += 1
            else:
                problems.append(f"{label}: the zip gives {got}")

    words = part1_spoken_words(script)
    seconds = words / PART1_WPM_FLOOR * 60 + PART1_TAB_SECONDS
    verdict = (f"Part 1 full cut: {words} spoken words, about {int(seconds // 60)}:{int(seconds % 60):02d} "
               f"at {PART1_WPM_FLOOR} wpm")
    if seconds > PART1_CAP_SECONDS:
        problems.append(verdict + ", over the 3:00 cap: apply the cut ladder in the script")

    print(f"[ OK ] {ok} anchor(s) and fact(s) match the submitted zip ({len(rows)} ledger rows)")
    print(f"[ -- ] {verdict}; at 155 wpm {words / 155 * 60 + PART1_TAB_SECONDS:.0f} s")
    extra = part1_spoken_words(script, bonus=True)
    total = (words + extra) / PART1_WPM_FLOOR * 60 + PART1_TAB_SECONDS
    print(f"[ -- ] with every BONUS line: +{extra} words, {words + extra} in all, about "
          f"{int(total // 60)}:{int(total % 60):02d} at {PART1_WPM_FLOOR} wpm (optional, not held to the cap)")
    for p in problems:
        print(f"[FAIL] {p}")
    print(f"\n{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
