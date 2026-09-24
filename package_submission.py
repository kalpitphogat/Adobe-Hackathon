#!/usr/bin/env python3
"""Build submission.zip from the marketplace, and refuse to if it is not valid.

The handout's packaging rules are short enough to check mechanically, so they
are checked here rather than trusted to a `zip -r` in a README that nobody
re-reads:

  * the zip's root holds marketplace.json, README.md and skills/ -- "a zip of
    the marketplace root directory (containing marketplace.json and every skill
    folder)". Flat, so a grader who unzips and runs the entrypoint finds the
    manifest where the handout says it is, with no folder to descend into first.
  * exactly one skill is marked entrypoint
  * every skill in the manifest exists on disk with a SKILL.md carrying YAML
    frontmatter with name, description and license
  * <= 50 MB, and no pre-trained model weights

The build is deterministic: entries are sorted and every timestamp is fixed, so
rebuilding from unchanged sources produces a byte-identical zip. Without that,
the committed artifact churns on every run and its diff stops meaning anything.

Run:  python package_submission.py            # build and verify
      python package_submission.py --check    # verify the existing zip only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKETPLACE = ROOT / "brand-ai-readiness-audit"
ZIP_PATH = ROOT / "submission.zip"

MAX_ZIP_BYTES = 50 * 1024 * 1024

# Everything in the marketplace ships except build noise and git plumbing,
# which mean nothing inside a zip.
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git", ".idea", ".vscode",
                "audit-output", "evidence", ".venv", "venv"}
EXCLUDE_NAMES = {".DS_Store", ".gitattributes", ".gitignore"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".zip"}

# Weight formats, so "no pre-trained model weights" is enforced and not merely
# asserted in a README.
WEIGHT_SUFFIXES = {".bin", ".ckpt", ".gguf", ".h5", ".joblib", ".msgpack",
                   ".npy", ".npz", ".onnx", ".pb", ".pkl", ".pickle", ".pt",
                   ".pth", ".safetensors", ".tflite", ".weights"}

# A fixed DOS timestamp (1980-01-01) keeps rebuilds byte-identical.
FIXED_DATE = (1980, 1, 1, 0, 0, 0)

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class Failed(Exception):
    pass


def say(ok: bool, label: str, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {label:<44} {detail}")
    if not ok:
        raise Failed(label)


# ------------------------------------------------------------------ manifest

def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm: dict = {}
    for line in text[4:end].splitlines():
        if line and not line[0].isspace() and ":" in line:
            key, value = line.split(":", 1)
            fm[key.strip()] = value.strip()
    return fm


def validate_source() -> list[dict]:
    manifest_path = MARKETPLACE / "marketplace.json"
    say(manifest_path.is_file(), "manifest.present", str(manifest_path.relative_to(ROOT)))

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        say(False, "manifest.parses", str(exc))
        raise

    skills = manifest.get("skills") or []
    say(bool(skills), "manifest.lists_skills", f"{len(skills)} skills")

    entrypoints = [s["id"] for s in skills if s.get("entrypoint") is True]
    say(len(entrypoints) == 1, "manifest.exactly_one_entrypoint",
        entrypoints[0] if len(entrypoints) == 1 else f"found {len(entrypoints)}: {entrypoints}")

    # "the marketplace manifest should be self-contained -- no external service
    # needed to resolve it."
    blob = manifest_path.read_text(encoding="utf-8")
    say("http://" not in blob and "https://" not in blob,
        "manifest.self_contained", "no external URLs to resolve")

    on_disk = sorted(p.name for p in (MARKETPLACE / "skills").iterdir() if p.is_dir())
    say(sorted(s["id"] for s in skills) == on_disk,
        "manifest.matches_disk", f"{len(on_disk)} folders")

    for skill in skills:
        folder = MARKETPLACE / skill["path"]
        label = skill["id"]
        say(folder.is_dir(), f"skill.{label}.folder", skill["path"])

        md = folder / "SKILL.md"
        say(md.is_file(), f"skill.{label}.SKILL_md", "present")

        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        say(bool(fm), f"skill.{label}.frontmatter", "YAML frontmatter parsed")

        name = fm.get("name", "")
        say(name == folder.name and NAME_RE.match(name) is not None and len(name) <= 64,
            f"skill.{label}.name", name)
        desc = fm.get("description", "")
        say(bool(desc) and len(desc) <= 1024, f"skill.{label}.description", f"{len(desc)} chars")
        say(bool(fm.get("license")), f"skill.{label}.license", fm.get("license", ""))

    say((MARKETPLACE / "README.md").is_file(), "marketplace.README", "present at marketplace root")
    return skills


# ------------------------------------------------------------------- packing

def files_to_pack() -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for path in MARKETPLACE.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(MARKETPLACE)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDE_NAMES or path.suffix.lower() in EXCLUDE_SUFFIXES:
            continue
        out.append((path, rel.as_posix()))
    out.sort(key=lambda item: item[1])
    return out


def build() -> None:
    entries = files_to_pack()
    say(bool(entries), "pack.has_files", f"{len(entries)} files")

    weights = [arc for _, arc in entries if Path(arc).suffix.lower() in WEIGHT_SUFFIXES]
    say(not weights, "pack.no_model_weights", "none" if not weights else str(weights[:3]))

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path, arc in entries:
            info = zipfile.ZipInfo(arc, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())

    size = ZIP_PATH.stat().st_size
    say(size <= MAX_ZIP_BYTES, "pack.size_limit",
        f"{size / 1024:.0f} KB of {MAX_ZIP_BYTES // (1024 * 1024)} MB")


# -------------------------------------------------------------- verification

def verify() -> None:
    """Check the artifact itself, not the tree it was built from."""
    say(ZIP_PATH.is_file(), "zip.present", ZIP_PATH.name)

    with zipfile.ZipFile(ZIP_PATH) as zf:
        broken = zf.testzip()
        say(broken is None, "zip.not_corrupt", broken or "CRCs verify")
        names = zf.namelist()

        say("marketplace.json" in names, "zip.manifest_at_root",
            "marketplace.json is at the zip root, not nested in a folder")
        say("README.md" in names, "zip.readme_at_root", "README.md is at the zip root")
        say(any(n.startswith("skills/") for n in names), "zip.skills_at_root", "skills/ is at the zip root")

        manifest = json.loads(zf.read("marketplace.json"))
        skills = manifest["skills"]
        entrypoints = [s["id"] for s in skills if s.get("entrypoint") is True]
        say(len(entrypoints) == 1, "zip.exactly_one_entrypoint", entrypoints[0])

        for skill in skills:
            arc = f"{skill['path']}/SKILL.md"
            say(arc in names, f"zip.{skill['id']}.SKILL_md", arc)

        # The entrypoint has to actually be in the zip, or the grader has a
        # manifest pointing at nothing.
        ep = next(s for s in skills if s.get("entrypoint"))
        scripts = [n for n in names if n.startswith(f"{ep['path']}/scripts/") and n.endswith(".py")]
        say(bool(scripts), f"zip.{ep['id']}.scripts", f"{len(scripts)} executable scripts")

        junk = [n for n in names
                if "__pycache__" in n or n.endswith(".pyc") or n.startswith("/") or ".." in n]
        say(not junk, "zip.no_junk_or_traversal", "none" if not junk else str(junk[:3]))

        weights = [n for n in names if Path(n).suffix.lower() in WEIGHT_SUFFIXES]
        say(not weights, "zip.no_model_weights", "none" if not weights else str(weights[:3]))

    size = ZIP_PATH.stat().st_size
    say(size <= MAX_ZIP_BYTES, "zip.size_limit", f"{size / 1024:.0f} KB")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="verify the existing submission.zip without rebuilding it")
    args = ap.parse_args(argv)

    try:
        if args.check:
            verify()
        else:
            validate_source()
            build()
            verify()
    except Failed as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        return 1

    print(f"\nOK: {ZIP_PATH.name} is valid and ready to submit "
          f"({ZIP_PATH.stat().st_size / 1024:.0f} KB).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
