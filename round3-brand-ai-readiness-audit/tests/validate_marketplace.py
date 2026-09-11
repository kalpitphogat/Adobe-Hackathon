#!/usr/bin/env python3
"""Structural validator for the brand-ai-readiness-audit marketplace.

Enforces, with no third-party dependencies:

  * marketplace.json is well formed, every listed path exists, exactly one
    skill is the entrypoint, and every skill id equals its folder basename.
  * every SKILL.md satisfies the agentskills.io spec: name matches the parent
    directory, name/description/compatibility length and character rules, and
    the body stays under the recommended 500 lines.
  * the live check registry, parsed statically out of each skill's own
    scripts, equals tests/expected_inventory.json exactly - ids, stages,
    categories, tiers and default severities.
  * every count that appears in prose (README.md) is regenerated from that
    registry rather than hand maintained.
  * no script imports from a sibling skill directory, so every skill folder
    can be lifted out and run alone.

Statuses: PASS, SKIP (artifact scheduled for a later build step), FAIL.
Exit code is 0 unless something FAILs. --strict turns every SKIP into a FAIL
and is what the final packaging step runs.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
INVENTORY = ROOT / "tests" / "expected_inventory.json"
README = ROOT / "README.md"

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CHECK_ID_RE = re.compile(r"^(reach|read|extract|trust|act)[.][a-z0-9_]+[.][a-z0-9_]+$")
AUTO_BLOCK_RE = re.compile(
    r"<!-- INVENTORY:AUTO -->\n(.*?)\n<!-- /INVENTORY:AUTO -->", re.DOTALL
)

SEVERITIES = {"critical", "high", "medium", "low", "info"}
TIERS = {"core", "enrichment"}
STAGES = {"reach", "read", "extract", "trust", "act"}
CATEGORIES = {"discoverability", "engagement"}


class Results:
    def __init__(self, strict: bool) -> None:
        self.strict = strict
        self.rows: list[tuple[str, str, str]] = []

    def add(self, status: str, name: str, detail: str = "") -> None:
        if status == "SKIP" and self.strict:
            status = "FAIL"
        self.rows.append((status, name, detail))

    def ok(self, name, detail=""):
        self.add("PASS", name, detail)

    def skip(self, name, detail=""):
        self.add("SKIP", name, detail)

    def fail(self, name, detail=""):
        self.add("FAIL", name, detail)

    @property
    def failed(self) -> bool:
        return any(r[0] == "FAIL" for r in self.rows)

    def report(self) -> None:
        width = max((len(r[1]) for r in self.rows), default=0)
        for status, name, detail in self.rows:
            line = f"[{status:4}] {name.ljust(width)}"
            if detail:
                line += f"  {detail}"
            print(line)
        counts = {s: sum(1 for r in self.rows if r[0] == s) for s in ("PASS", "SKIP", "FAIL")}
        print(
            f"\n{counts['PASS']} passed, {counts['SKIP']} skipped, {counts['FAIL']} failed"
        )


# ---------------------------------------------------------------- frontmatter


def parse_frontmatter(text: str) -> tuple[dict, int]:
    """Minimal YAML-subset frontmatter parser.

    Handles `key: value`, folded multi-line values (continuation lines indented
    deeper than the key), and quoted scalars. Deliberately not a full YAML
    implementation: SKILL.md frontmatter is a flat string map by spec, and
    depending on PyYAML would break the stdlib-only guarantee.

    Returns (mapping, body_line_count).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, len(lines)
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, len(lines)

    data: dict[str, str] = {}
    key = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", raw)
        if m and not raw.startswith((" ", "\t")):
            key = m.group(1)
            data[key] = m.group(2).strip()
        elif key is not None and raw.startswith((" ", "\t")):
            data[key] = (data[key] + " " + raw.strip()).strip()
    for k, v in list(data.items()):
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            data[k] = v[1:-1]
    return data, len(lines) - (end + 1)


# ------------------------------------------------------------------- registry


def extract_checks_from_source(path: Path) -> list[dict]:
    """Statically read a module-level CHECKS list literal.

    Parsed with ast rather than imported: importing would execute skill code
    and could pull in optional dependencies, which would make the validator
    itself depend on the enrichment tier it is supposed to be measuring.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "CHECKS":
                try:
                    value = ast.literal_eval(node.value)
                except ValueError as exc:
                    raise ValueError(f"{path}: CHECKS is not a literal ({exc})") from exc
                if not isinstance(value, list):
                    raise ValueError(f"{path}: CHECKS must be a list")
                return value
    return []


def collect_live_registry() -> tuple[list[dict], list[str]]:
    checks: list[dict] = []
    errors: list[str] = []
    for script in sorted(SKILLS_DIR.glob("*/scripts/*.py")):
        skill = script.parent.parent.name
        try:
            found = extract_checks_from_source(script)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        for entry in found:
            entry = dict(entry)
            entry.setdefault("skill", skill)
            entry["_source"] = str(script.relative_to(ROOT))
            checks.append(entry)
    return checks, errors


def derive_totals(checks: list[dict]) -> dict:
    by_stage: dict[str, int] = {}
    by_skill: dict[str, int] = {}
    for c in checks:
        by_stage[c["stage"]] = by_stage.get(c["stage"], 0) + 1
        by_skill[c["skill"]] = by_skill.get(c["skill"], 0) + 1
    return {
        "checks": len(checks),
        "core": sum(1 for c in checks if c["tier"] == "core"),
        "enrichment": sum(1 for c in checks if c["tier"] == "enrichment"),
        "discoverability": sum(1 for c in checks if c["category"] == "discoverability"),
        "engagement": sum(1 for c in checks if c["category"] == "engagement"),
        "by_stage": dict(sorted(by_stage.items())),
        "by_skill": dict(sorted(by_skill.items())),
        "rule_0b_suppressible": sum(
            1 for c in checks if c.get("rule_0b_suppressible") is True
        ),
    }


def render_inventory_block(totals: dict) -> str:
    """The exact prose block README.md must contain, generated from the registry."""
    stage = totals["by_stage"]
    skill = totals["by_skill"]
    lines = [
        f"**{totals['checks']} checks** across six audit skills "
        f"({totals['discoverability']} discoverability, {totals['engagement']} engagement).",
        "",
        f"- Dependency tier: **{totals['core']} CORE** (Python standard library only), "
        f"**{totals['enrichment']} ENRICHMENT** (cannot fire without an optional dependency).",
        "- By stage: "
        + ", ".join(f"{k} {stage[k]}" for k in ("reach", "read", "extract", "trust", "act") if k in stage)
        + ".",
        "- By skill: " + ", ".join(f"{k} {skill[k]}" for k in sorted(skill)) + ".",
        f"- Engagement checks suppressed entirely under gate Rule 0b when a page has no "
        f"observed rendered content: **{totals['rule_0b_suppressible']}** of {stage.get('act', 0)}.",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------- validators


def check_manifest(res: Results) -> list[dict]:
    path = ROOT / "marketplace.json"
    if not path.exists():
        res.fail("manifest.exists", "marketplace.json missing")
        return []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        res.fail("manifest.parses", str(exc))
        return []
    res.ok("manifest.parses")

    for field in ("name", "version", "skills"):
        if field not in manifest:
            res.fail("manifest.required_fields", f"missing {field}")
            return []
    res.ok("manifest.required_fields", "name, version, skills")

    skills = manifest["skills"]
    entrypoints = [s for s in skills if s.get("entrypoint") is True]
    if len(entrypoints) == 1:
        res.ok("manifest.exactly_one_entrypoint", entrypoints[0]["id"])
    else:
        res.fail(
            "manifest.exactly_one_entrypoint",
            f"found {len(entrypoints)}: {[s.get('id') for s in entrypoints]}",
        )

    ids = [s["id"] for s in skills]
    if len(set(ids)) == len(ids):
        res.ok("manifest.unique_ids", f"{len(ids)} skills")
    else:
        res.fail("manifest.unique_ids", "duplicate skill ids")

    missing = [s["path"] for s in skills if not (ROOT / s["path"]).is_dir()]
    if missing:
        res.fail("manifest.paths_exist", f"missing dirs: {missing}")
    else:
        res.ok("manifest.paths_exist", f"{len(skills)} directories")

    mismatched = [s["id"] for s in skills if Path(s["path"]).name != s["id"]]
    if mismatched:
        res.fail("manifest.id_equals_basename", str(mismatched))
    else:
        res.ok("manifest.id_equals_basename")

    on_disk = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()} if SKILLS_DIR.is_dir() else set()
    unlisted = on_disk - set(ids)
    if unlisted:
        res.fail("manifest.no_unlisted_skills", f"on disk but not in manifest: {sorted(unlisted)}")
    else:
        res.ok("manifest.no_unlisted_skills")

    return skills


def check_skill_md(res: Results, skills: list[dict]) -> None:
    present = 0
    for skill in skills:
        folder = ROOT / skill["path"]
        md = folder / "SKILL.md"
        label = skill["id"]
        if not md.exists():
            res.skip(f"skill.{label}.SKILL_md", "not written yet (build step S8)")
            continue
        present += 1
        text = md.read_text(encoding="utf-8")
        fm, body_lines = parse_frontmatter(text)

        if not fm:
            res.fail(f"skill.{label}.frontmatter", "no YAML frontmatter found")
            continue

        name = fm.get("name", "")
        if name != folder.name:
            res.fail(f"skill.{label}.name_matches_dir", f"name={name!r} dir={folder.name!r}")
        elif not NAME_RE.match(name):
            res.fail(f"skill.{label}.name_charset", f"{name!r} violates naming rules")
        elif len(name) > 64:
            res.fail(f"skill.{label}.name_length", f"{len(name)} > 64")
        else:
            res.ok(f"skill.{label}.name", name)

        desc = fm.get("description", "")
        if not desc:
            res.fail(f"skill.{label}.description", "missing or empty")
        elif len(desc) > 1024:
            res.fail(f"skill.{label}.description_length", f"{len(desc)} > 1024")
        else:
            res.ok(f"skill.{label}.description", f"{len(desc)} chars")

        compat = fm.get("compatibility")
        if compat is not None:
            if len(compat) > 500:
                res.fail(f"skill.{label}.compatibility_length", f"{len(compat)} > 500")
            else:
                res.ok(f"skill.{label}.compatibility", f"{len(compat)} chars")

        if body_lines >= 500:
            res.fail(f"skill.{label}.body_length", f"{body_lines} lines >= 500")
        else:
            res.ok(f"skill.{label}.body_length", f"{body_lines} lines")

    if present == 0:
        res.skip("skill.all.SKILL_md", "no SKILL.md written yet (build step S8)")


def check_no_cross_skill_imports(res: Results) -> None:
    """F2: a skill folder that cannot be lifted out and run alone is not portable."""
    if not SKILLS_DIR.is_dir():
        res.fail("portability.no_cross_skill_imports", "skills/ missing")
        return
    skill_names = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    module_names = {n.replace("-", "_") for n in skill_names}
    offenders: list[str] = []
    scripts = sorted(SKILLS_DIR.glob("*/scripts/*.py"))
    for script in scripts:
        own = script.parent.parent.name
        others = (skill_names | module_names) - {own, own.replace("-", "_")}
        try:
            tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        except SyntaxError as exc:
            offenders.append(f"{script.relative_to(ROOT)}: unparseable ({exc})")
            continue
        # Docstrings legitimately name sibling skills - they cite the CLI
        # contract and explain why code is duplicated. Excluding them keeps this
        # check on its actual target: a string used to REACH a sibling folder.
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc is not None:
                    docstrings.add(doc)

        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                head = n.split(".")[0]
                if head in others:
                    offenders.append(f"{script.relative_to(ROOT)} imports {n}")
            # A string used to reach into a sibling skill's code, which is the
            # sys.path dodge around the import rule. Only a path that actually
            # points at a sibling's scripts/ counts; prose that merely mentions
            # a sibling by name does not.
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in docstrings:
                    continue
                normalised = node.value.replace("\\", "/")
                for other in others:
                    if f"{other}/scripts" in normalised:
                        offenders.append(
                            f"{script.relative_to(ROOT)} builds a path into sibling skill "
                            f"{other!r}: {node.value!r}"
                        )
    if offenders:
        res.fail("portability.no_cross_skill_imports", "; ".join(sorted(set(offenders))))
    elif not scripts:
        res.skip("portability.no_cross_skill_imports", "no scripts written yet")
    else:
        res.ok("portability.no_cross_skill_imports", f"{len(scripts)} scripts clean")


def check_registry(res: Results) -> dict | None:
    if not INVENTORY.exists():
        res.fail("inventory.exists", "tests/expected_inventory.json missing")
        return None
    spec = json.loads(INVENTORY.read_text(encoding="utf-8"))
    spec_checks = spec["checks"]
    declared = spec["totals"]

    # (a) the spec file must be internally consistent
    self_derived = derive_totals(spec_checks)
    diffs = [k for k in declared if declared[k] != self_derived.get(k)]
    if diffs:
        res.fail(
            "inventory.self_consistent",
            "; ".join(f"{k}: declared={declared[k]} derived={self_derived.get(k)}" for k in diffs),
        )
    else:
        res.ok("inventory.self_consistent", f"{self_derived['checks']} checks")

    ids = [c["id"] for c in spec_checks]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        res.fail("inventory.unique_ids", str(dupes))
    else:
        res.ok("inventory.unique_ids")

    bad_shape = []
    for c in spec_checks:
        if not CHECK_ID_RE.match(c["id"]):
            bad_shape.append(f"{c['id']}: id pattern")
        if not c["id"].startswith(c["stage"] + "."):
            bad_shape.append(f"{c['id']}: stage prefix != {c['stage']}")
        if c["stage"] not in STAGES:
            bad_shape.append(f"{c['id']}: stage")
        if c["category"] not in CATEGORIES:
            bad_shape.append(f"{c['id']}: category")
        if c["tier"] not in TIERS:
            bad_shape.append(f"{c['id']}: tier")
        if c["default_severity"] not in SEVERITIES:
            bad_shape.append(f"{c['id']}: severity")
        if c["stage"] == "act" and c["category"] != "engagement":
            bad_shape.append(f"{c['id']}: act stage must be engagement category")
        if c["stage"] != "act" and c["category"] != "discoverability":
            bad_shape.append(f"{c['id']}: non-act stage must be discoverability category")
    if bad_shape:
        res.fail("inventory.well_formed", "; ".join(bad_shape))
    else:
        res.ok("inventory.well_formed")

    # (b) Rule 0b only applies to act.*
    stray = [c["id"] for c in spec_checks if c.get("rule_0b_suppressible") and c["stage"] != "act"]
    if stray:
        res.fail("inventory.rule_0b_scope", f"non-act checks marked suppressible: {stray}")
    else:
        res.ok("inventory.rule_0b_scope", "act stage only")

    # (c) every act.* check must state its Rule 0b disposition explicitly
    unset = [c["id"] for c in spec_checks if c["stage"] == "act" and "rule_0b_suppressible" not in c]
    if unset:
        res.fail("inventory.rule_0b_explicit", f"act checks with no disposition: {unset}")
    else:
        res.ok("inventory.rule_0b_explicit")

    # (d) the live registry parsed out of skill scripts must equal the spec
    live, errors = collect_live_registry()
    for err in errors:
        res.fail("registry.parse", err)
    if not live:
        res.skip("registry.matches_inventory", "no CHECKS registries written yet (build step S4)")
        return self_derived

    live_ids = sorted(c["id"] for c in live)
    spec_ids = sorted(ids)
    missing = sorted(set(spec_ids) - set(live_ids))
    extra = sorted(set(live_ids) - set(spec_ids))
    if missing or extra:
        detail = []
        if missing:
            detail.append(f"declared but not implemented: {missing}")
        if extra:
            detail.append(f"implemented but not declared: {extra}")
        res.fail("registry.matches_inventory", "; ".join(detail))
    else:
        res.ok("registry.matches_inventory", f"{len(live_ids)} checks")

    spec_by_id = {c["id"]: c for c in spec_checks}
    field_diffs = []
    for c in live:
        ref = spec_by_id.get(c["id"])
        if not ref:
            continue
        for field in ("stage", "category", "tier", "default_severity", "skill"):
            if c.get(field) != ref.get(field):
                field_diffs.append(
                    f"{c['id']}.{field}: code={c.get(field)!r} inventory={ref.get(field)!r}"
                )
    if field_diffs:
        res.fail("registry.fields_match", "; ".join(field_diffs))
    elif live:
        res.ok("registry.fields_match")

    live_totals = derive_totals(live)
    tot_diffs = [k for k in declared if declared[k] != live_totals.get(k)]
    if tot_diffs:
        res.fail(
            "registry.totals_match",
            "; ".join(f"{k}: code={live_totals.get(k)} inventory={declared[k]}" for k in tot_diffs),
        )
    else:
        res.ok("registry.totals_match", f"{live_totals['core']} core / {live_totals['enrichment']} enrichment")

    return live_totals


def check_readme_counts(res: Results, totals: dict | None) -> None:
    """F1: no count in prose that is not derived from the registry."""
    if totals is None:
        res.skip("readme.inventory_block", "no totals available")
        return
    if not README.exists():
        res.skip("readme.inventory_block", "README.md not written yet (build step S10)")
        return
    text = README.read_text(encoding="utf-8")
    m = AUTO_BLOCK_RE.search(text)
    if not m:
        res.fail(
            "readme.inventory_block",
            "README.md must contain an <!-- INVENTORY:AUTO --> block",
        )
        return
    expected = render_inventory_block(totals)
    if m.group(1).strip() != expected.strip():
        res.fail("readme.inventory_block", "block is stale; regenerate with --write-readme-block")
    else:
        res.ok("readme.inventory_block", "counts match the live registry")


CHECK_ID_IN_PROSE = re.compile(r"\b((?:reach|read|extract|trust|act)\.[a-z0-9_]+\.[a-z0-9_]+)\b")
SUPPRESS_CLAUSE = re.compile(r"SUPPRESS\s+WHEN", re.IGNORECASE)


def check_doc_drift(res: Results) -> None:
    """S8 is where a SKILL.md can quietly describe behaviour the code lacks.

    Two directions of drift, both fatal to the engineering-hygiene criterion:

      1. A SKILL.md names a check_id that does not exist. The document promises
         a check nothing implements.
      2. A SKILL.md documents a SUPPRESS WHEN clause for a check that has no
         entry in tests/test_suppression.py :: SUPPRESSION_CASES. The document
         promises a suppression nothing proves.
    """
    if not INVENTORY.exists():
        res.fail("docs.check_ids_exist", "inventory missing")
        return
    known = {c["id"] for c in json.loads(INVENTORY.read_text(encoding="utf-8"))["checks"]}

    skill_mds = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    if not skill_mds:
        res.skip("docs.check_ids_exist", "no SKILL.md written yet (build step S8)")
        res.skip("docs.suppress_clauses_tested", "no SKILL.md written yet (build step S8)")
        return

    unknown: list[str] = []
    documented: set[str] = set()
    for md in skill_mds:
        text = md.read_text(encoding="utf-8")
        for check_id in CHECK_ID_IN_PROSE.findall(text):
            documented.add(check_id)
            if check_id not in known:
                unknown.append(f"{md.parent.name}/SKILL.md names {check_id}, which does not exist")
    if unknown:
        res.fail("docs.check_ids_exist", "; ".join(sorted(set(unknown))))
    else:
        res.ok("docs.check_ids_exist", f"{len(documented)} check_ids referenced, all real")

    # Every check whose SKILL.md section carries a SUPPRESS WHEN clause must
    # have a suppression case registered.
    suppression_path = ROOT / "tests" / "test_suppression.py"
    if not suppression_path.exists():
        res.fail("docs.suppress_clauses_tested", "tests/test_suppression.py is missing")
        return
    try:
        tree = ast.parse(suppression_path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        res.fail("docs.suppress_clauses_tested", f"test_suppression.py does not parse: {exc}")
        return
    registered: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and node.targets and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
        else:
            continue
        if name == "SUPPRESSION_CASES" and value is not None:
            try:
                registered = set(ast.literal_eval(value))
            except ValueError:
                res.fail("docs.suppress_clauses_tested", "SUPPRESSION_CASES is not a literal")
                return

    missing: list[str] = []
    for md in skill_mds:
        text = md.read_text(encoding="utf-8")
        # Split on headings so a clause is attributed to the check it sits under.
        blocks = re.split(r"\n(?=#{2,4}\s)", text)
        for block in blocks:
            if not SUPPRESS_CLAUSE.search(block):
                continue
            for check_id in set(CHECK_ID_IN_PROSE.findall(block)):
                if check_id in known and check_id not in registered:
                    missing.append(
                        f"{md.parent.name}/SKILL.md documents a SUPPRESS WHEN for {check_id} "
                        f"with no case in SUPPRESSION_CASES"
                    )
    if missing:
        res.fail("docs.suppress_clauses_tested", "; ".join(sorted(set(missing))))
    else:
        res.ok(
            "docs.suppress_clauses_tested",
            f"{len(registered)} suppression rules registered and tested",
        )


def check_report_schema(res: Results) -> None:
    path = SKILLS_DIR / "ai-readiness-orchestrator" / "references" / "report-schema.json"
    if not path.exists():
        res.fail("schema.exists", "report-schema.json missing")
        return
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        res.fail("schema.parses", str(exc))
        return
    res.ok("schema.parses")

    floor_top = {"site", "audited_at", "summary", "findings"}
    if floor_top.issubset(set(schema.get("required", []))):
        res.ok("schema.handout_floor_top", "site, audited_at, summary, findings")
    else:
        res.fail("schema.handout_floor_top", f"required={schema.get('required')}")

    summary_req = set(
        schema["properties"]["summary"].get("required", [])
    )
    if {"total_findings", "critical", "high", "medium"}.issubset(summary_req):
        res.ok("schema.handout_floor_summary")
    else:
        res.fail("schema.handout_floor_summary", str(sorted(summary_req)))

    finding_req = set(
        schema["properties"]["findings"]["items"].get("required", [])
    )
    if {"id", "title", "severity", "evidence", "suggested_action"}.issubset(finding_req):
        res.ok("schema.handout_floor_finding")
    else:
        res.fail("schema.handout_floor_finding", str(sorted(finding_req)))


# ----------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true", help="treat SKIP as FAIL (used at packaging time)")
    parser.add_argument("--json", action="store_true", help="emit results as JSON on stdout")
    parser.add_argument(
        "--print-readme-block",
        action="store_true",
        help="print the generated INVENTORY:AUTO block and exit",
    )
    args = parser.parse_args(argv)

    if args.print_readme_block:
        spec = json.loads(INVENTORY.read_text(encoding="utf-8"))
        live, _ = collect_live_registry()
        totals = derive_totals(live) if live else derive_totals(spec["checks"])
        print(render_inventory_block(totals))
        return 0

    res = Results(strict=args.strict)
    skills = check_manifest(res)
    check_report_schema(res)
    totals = check_registry(res)
    check_skill_md(res, skills)
    check_no_cross_skill_imports(res)
    check_doc_drift(res)
    check_readme_counts(res, totals)

    if args.json:
        print(json.dumps([{"status": s, "check": n, "detail": d} for s, n, d in res.rows], indent=2))
    else:
        res.report()
    return 1 if res.failed else 0


if __name__ == "__main__":
    sys.exit(main())
