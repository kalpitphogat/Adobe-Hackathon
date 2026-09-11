#!/usr/bin/env python3
"""Package the marketplace into ../submission.zip, deterministically.

  python scripts/package.py [-o ../submission.zip]

Excludes build and run artifacts (__pycache__, *.pyc, batch/stress reports, logs,
caches) so the archive contains only source. File order and timestamps are fixed,
so the same tree always produces a byte-identical archive.
"""
import argparse
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXCLUDE_DIRS = {"__pycache__", ".git", ".pytest_cache", ".venv", "venv",
                "batch_reports", "stress_reports"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".zip", ".log")
EXCLUDE_NAMES = {".DS_Store", "report.json", "report.html"}
FIXED_TIME = (2026, 1, 1, 0, 0, 0)   # deterministic archive


def collect():
    files = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs
                         if d not in EXCLUDE_DIRS and not d.startswith("audit_"))
        for n in sorted(names):
            if n in EXCLUDE_NAMES or n.endswith(EXCLUDE_SUFFIX):
                continue
            full = os.path.join(base, n)
            files.append((full, os.path.relpath(full, ROOT).replace(os.sep, "/")))
    return sorted(files, key=lambda t: t[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "..", "submission.zip"))
    args = ap.parse_args()
    out = os.path.abspath(args.out)

    files = collect()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for full, rel in files:
            info = zipfile.ZipInfo(rel, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(full, "rb") as fh:
                z.writestr(info, fh.read())

    size = os.path.getsize(out)
    print(f"wrote {out} - {len(files)} files, {size / 1024:.0f} KB")
    if size > 50 * 1024 * 1024:
        print("WARNING: archive exceeds the 50 MB limit", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
