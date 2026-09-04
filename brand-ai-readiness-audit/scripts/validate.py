#!/usr/bin/env python3
"""
Convenience validator for the marketplace: checks the manifest is well-formed with
exactly one entrypoint, that every listed skill folder exists with a SKILL.md, and that
each SKILL.md has the required agentskills.io frontmatter keys (name, description).

  python scripts/validate.py

Exit code 0 = OK, 1 = problems (printed). This is a sanity check, not a substitute for
`skills-ref validate` if you have it.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_frontmatter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None
    keys = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z0-9_-]+)\s*:", line)
        if km:
            keys[km.group(1)] = True
    return keys


def main():
    errors, warnings = [], []
    mpath = os.path.join(ROOT, "marketplace.json")
    if not os.path.exists(mpath):
        print("FAIL: marketplace.json not found")
        return 1
    try:
        manifest = json.load(open(mpath, encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: marketplace.json invalid JSON: {e}")
        return 1

    for key in ("name", "version", "skills"):
        if key not in manifest:
            errors.append(f"marketplace.json missing top-level '{key}'")

    skills = manifest.get("skills", [])
    entrypoints = [s for s in skills if s.get("entrypoint")]
    if len(entrypoints) != 1:
        errors.append(f"expected exactly 1 entrypoint, found {len(entrypoints)}")

    seen_ids = set()
    for s in skills:
        sid, path = s.get("id"), s.get("path")
        if not sid or not path:
            errors.append(f"skill entry missing id/path: {s}")
            continue
        if sid in seen_ids:
            errors.append(f"duplicate skill id: {sid}")
        seen_ids.add(sid)
        folder = os.path.join(ROOT, path)
        skill_md = os.path.join(folder, "SKILL.md")
        if not os.path.isdir(folder):
            errors.append(f"[{sid}] folder not found: {path}")
            continue
        if not os.path.exists(skill_md):
            errors.append(f"[{sid}] SKILL.md not found in {path}")
            continue
        fm = parse_frontmatter(skill_md)
        if fm is None:
            errors.append(f"[{sid}] SKILL.md has no YAML frontmatter")
            continue
        for req in ("name", "description"):
            if req not in fm:
                errors.append(f"[{sid}] SKILL.md frontmatter missing '{req}'")
        # entrypoint id must be resolvable
        if s.get("entrypoint") and manifest.get("entrypoint") not in (None, sid):
            warnings.append(f"manifest.entrypoint='{manifest.get('entrypoint')}' but "
                            f"entrypoint skill id='{sid}'")

    # top-level entrypoint pointer (if present) resolves to a skill
    ep = manifest.get("entrypoint")
    if ep and ep not in seen_ids:
        errors.append(f"manifest.entrypoint '{ep}' is not a listed skill id")

    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        print(f"\n{len(errors)} problem(s).")
        return 1
    print(f"OK: {len(skills)} skills, 1 entrypoint ({ep or entrypoints[0]['id']}), "
          f"all SKILL.md present and valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
