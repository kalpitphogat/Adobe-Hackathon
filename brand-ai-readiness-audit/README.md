# brand-ai-readiness-audit

An **Agent Skill Marketplace** that audits any website for the two problems from
Round 2 — poor **AI discoverability** (the brand isn't found or cited by AI assistants)
and poor **on-site engagement** (visitors who arrive don't stay) — and emits one
structured report of evidence-backed findings plus prioritized, actionable fixes.

**Recommend-only.** Every skill runs read-only in a sandbox, respects `robots.txt`, and
never modifies, authenticates to, or rate-abuses the audited site. Suggested actions are
recommendations, not changes applied to the site.

## Quick start
```bash
# audit a site (add --render to measure the JS fact gap with headless Chromium)
python skills/audit-orchestrator/scripts/run_audit.py https://example.com --render \
    --out report.json --html report.html
```
The entrypoint crawls the site once, runs every other skill against a shared page cache,
and prints the final JSON report. `--out` writes the JSON, `--html` additionally writes a
readable, severity-ranked HTML report a non-expert can act on. Runs in well under 5
minutes for a typical site.

## Why these skills (concern → skill map)
The report's reasoning is decomposed into one focused skill per **mechanism** behind AI
visibility (drawn from the Round-2 appendix), so each concern is independently testable
and the entrypoint just composes them:

| Skill | Round-2 mechanism | The question it answers |
|-------|-------------------|-------------------------|
| **audit-orchestrator** *(entrypoint)* | — | Crawl once, run the others, compose the one report |
| **crawl-access-audit** | A — *let the crawler in* | Can an (AI) crawler reach & index the site? (robots, AI-bot rules, sitemap, noindex, status, HTTPS) |
| **render-extraction-audit** | C — *read the page* | Are the facts in raw HTML, or only after JS? (static-vs-rendered gap, thin shells, image-locked facts) |
| **structured-data-audit** | A/C — *pick out the fact* | Can a machine extract & attribute the fact? (JSON-LD coverage/validity, entity identity, metadata, headings) |
| **freshness-corroboration-audit** | D — *agreement across the web* | Is the fact current & cross-verifiable? (stale dates, sameAs, identity collision, unattributed claims) |
| **answerability-audit** | B — *easy to quote* | Is the key fact stated as short, self-contained, quotable text? (FAQ markup, thin content, clear homepage, chunkable structure) |
| **integrity-audit** | trust / safety | Does the page manipulate the machine? (prompt-injection, hidden/cloaked text, invisible Unicode) |
| **engagement-audit** | on-site retention | Will an arriving visitor stay? (viewport, weight/latency, CTA, navigation, interstitials) |

Discoverability is covered by the first six (integrity is a trust signal on that side);
engagement by the last. The report tags
every finding with its `dimension` and summarizes both halves separately.

## How the entrypoint composes the others
`audit-orchestrator` holds **no checks of its own**. It:
1. Runs `crawler.py` once → a shared cache (`meta.json` + raw/extracted/rendered text per
   page). One polite crawl feeds all sub-audits.
2. Invokes each sub-audit script on that cache; each returns an envelope
   `{ skill, findings[] }` (contract in
   `skills/audit-orchestrator/references/report-format.md`).
3. Merges, tags dimension, sorts by severity, assigns stable `F-NNN` ids, counts by
   severity → emits the fixed-schema report.

Adding or swapping a concern = add a skill folder + one line in `marketplace.json`; the
orchestrator needs no change beyond its sub-audit list.

## Output schema
Meets the required floor (`site`, `audited_at`, `summary` counts, and per finding `id`,
`title`, `severity`, `evidence`, `suggested_action`) and adds `url`, `auditor`, `scope`,
`summary.by_dimension`, and per-finding `dimension` / `skill` / `checked`. Severity is
computed from evidence per `skills/audit-orchestrator/references/severity-rubric.md`, not
hardcoded, so it generalizes to unseen sites.

## Layout
```
brand-ai-readiness-audit/
  marketplace.json            # manifest: every skill + the one entrypoint
  README.md
  scripts/validate.py         # convenience: sanity-check manifest + all SKILL.md files
  skills/
    audit-orchestrator/       # ENTRYPOINT — crawler.py, run_audit.py, auditlib.py, refs
    crawl-access-audit/
    render-extraction-audit/
    structured-data-audit/
    freshness-corroboration-audit/
    answerability-audit/
    integrity-audit/
    engagement-audit/
```
Each skill folder is an independent, agentskills.io-compliant skill (SKILL.md with YAML
frontmatter + `scripts/` + `references/`). Detailed check catalogs and paste-ready fixes
live in each skill's `references/` (progressive disclosure).

## Requirements
- Python 3.8+ (standard library only for crawling/parsing/checks).
- Optional: `playwright` + Chromium for `--render` (the static-vs-rendered fact gap). The
  audit degrades gracefully without it, keeping the thin-HTML heuristic.

## Validate & test
```bash
python scripts/validate.py          # manifest well-formedness + one entrypoint + each SKILL.md
python tests/run_tests.py           # full offline test suite (add --render for the browser path)
# or, if available:  skills-ref validate ./skills/<folder>
```
`tests/` ships two local fixture sites — a deliberately-broken one (`badsite`) and a
healthy one (`goodsite`). The suite boots each, runs the real end-to-end audit, and
asserts that the expected problems are detected on the broken site and *not* falsely
raised on the healthy one — plus schema-floor conformance, severity sorting, and the HTML
renderer. Standard-library `unittest`; no network required.

## Scope & guardrails
Read-only; GET only; no destructive, authenticated, or rate-abusing actions; respects
`robots.txt`. Submission is self-contained — no external service resolves the
marketplace. Suggested actions may go beyond detected defects (proactive improvements
like adding `llms.txt`, FAQ schema, or `sameAs` identity links) but never modify the site.

## License
MIT (per-skill in each SKILL.md).
