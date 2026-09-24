# Skill CLI contract

**This document is normative and was written before the six audit skills.**
Every audit skill script is built against it. The orchestrator composes skills by
running them as subprocesses under this contract; nothing in this marketplace
composes by importing another skill's code.

## Why a subprocess contract and not imports

The handout requires every skill folder to independently satisfy the
agentskills.io spec. A folder that cannot be lifted out of this marketplace and
run on its own does not satisfy that. So:

* No script in `skills/<a>/scripts/` may import from `skills/<b>/scripts/`.
* There is no `shared/` package. A shared library at the marketplace root would
  be a tenth top-level component, would break the lift-out property, and would
  invite the "padding" reading the rubric warns about.
* Where two skills genuinely need the same predicate, the predicate is
  **duplicated**, and the duplication is documented in both SKILL.md files as a
  portability decision. This is deliberate: a small amount of duplicated logic is
  cheaper than a dependency that makes every folder non-portable.

`tests/validate_marketplace.py` enforces this as `portability.no_cross_skill_imports`.
It walks the AST of every `skills/*/scripts/*.py`, fails on any `import` or
`from ... import` naming a sibling skill, and also fails on a string constant
containing a sibling skill directory used as a path (the `sys.path` dodge).

## Invocation

```
python skills/<skill>/scripts/<entry>.py --bundle <evidence_dir> [--profile <profile.json>] [options]
```

* `--bundle` is **required** and is a directory written by
  `site-evidence-collector`. The script reads it and performs **no network I/O
  of any kind**.
* `--profile` is optional and points at the JSON emitted by
  `site-profile-classifier`. Without it, a script falls back to its built-in
  default thresholds and lowers its confidence accordingly.
* `--help` must work and must document every flag.
* Scripts must be non-interactive. They never prompt, never read stdin.

## Output

**stdout carries exactly one JSON object and nothing else.** Diagnostics,
warnings and progress go to stderr. A script that prints anything else to stdout
breaks the orchestrator.

```json
{
  "skill": "crawl-access-audit",
  "stage": "reach",
  "schema_version": "1.0",
  "checks_run": ["reach.robots.blanket_disallow", "..."],
  "checks_skipped": [
    { "check_id": "reach.edge.bot_ua_blocked",
      "reason": "--probe-bot-ua was not set during collection",
      "confidence_effect": "not assessed" }
  ],
  "findings": [
    {
      "check_id": "reach.robots.ai_search_bot_blocked",
      "title": "...",
      "severity": "critical",
      "confidence": "confirmed",
      "category": "discoverability",
      "stage": "reach",
      "scope": "site",
      "evidence": "quantified, quoted, with counts and URLs",
      "affected_urls": ["..."],
      "suggested_action": {
        "summary": "...", "effort": "low",
        "mechanism": "one sentence on why the fix works",
        "source": "citation",
        "patch": "paste-ready, values from the bundle only",
        "verification": "the exact command that confirms the fix landed"
      }
    }
  ],
  "proactive_recommendations": [],
  "limitations": []
}
```

Notes on the shape:

* Audit skills emit `check_id`, **not** `id`. Report-level `F-001` ids are
  assigned by the orchestrator after dedupe and gating, so that ids are stable
  and dense in the final report.
* Audit skills emit `severity` and `confidence` as their own honest assessment.
  The orchestrator may **lower** severity under the gate cascade and may lower
  confidence under a degraded capability. It never raises either.
* `scope` is `site` or `url`. It decides how gate Rule 2 applies.
* Every finding must carry evidence, confidence, mechanism and a patch. A
  finding missing any of these is rejected by the orchestrator as malformed and
  reported as an internal error, not silently dropped.
* All arrays are sorted before printing: `findings` by `check_id` then by first
  affected URL, `affected_urls` lexicographically. Determinism starts here, not
  in the orchestrator.

## Exit codes

| code | meaning | orchestrator behaviour |
|------|---------|------------------------|
| `0` | ran to completion; `findings` may be empty | merge the findings |
| `3` | precondition unmet (no bundle, unreadable bundle, required evidence absent) | record a `limitations[]` entry naming the skill and reason; continue |
| `1` | internal error | record a `limitations[]` entry; continue; surface in the report |
| `2` | output path unusable | fail the run |

**Exit code never encodes what was found.** A skill that finds fifteen criticals
exits 0. A skill that finds nothing exits 0. This mirrors the rule at the
orchestrator level: `audit_status` lives in the report, not in the exit code,
because a grading harness may read any non-zero exit as a crash.

## Agent mode

The same procedure must be executable by an agent that has only a generic fetch
tool and no ability to run Python. Therefore every audit skill's `SKILL.md`
Procedure section is written as numbered, deterministic steps against the
**evidence bundle**, with `scripts/` described as accelerators rather than
requirements. An agent reads the bundle files directly and applies the same
rules, then assembles the same JSON by hand.

Two checks cannot be reproduced faithfully by hand and say so in their SKILL.md:
`extract.ans.fact_coverage_gap` (chunking and self-containment) and
`read.render.raw_text_gap` (quantified diff). In agent mode both drop to
`hypothesis` confidence and the SKILL.md gives a reduced heuristic.
