# brand-ai-readiness-audit

An **Agent Skill Marketplace** that audits any website for poor **AI discoverability**
(the brand isn't found or cited by AI assistants) and poor **on-site engagement**
(visitors who arrive don't get what they came for), and emits one structured report of
evidence-backed findings plus prioritized, actionable fixes.

**Recommend-only.** Every skill runs read-only, respects `robots.txt`, and never modifies,
authenticates to, or rate-abuses the audited site.

## Quick start
```bash
# audit a site (add --render to measure the JS fact gap with headless Chromium)
python skills/audit-orchestrator/scripts/run_audit.py https://example.com --render \
    --out report.json --html report.html
```
The entrypoint crawls once, runs every other skill against a shared cache, and prints the
final JSON report. `--html` additionally writes a readable, severity-ranked page.

## The design principle

Most site auditors answer "which conventions are missing?" This one answers a different
question, because the first one produces confident findings about things that are not
problems:

> **Is a check even relevant to this resource and this page — and does the evidence
> actually support reporting it?**

Three mechanisms enforce that, and they are the substance of the marketplace.

### 1. Resource classification — an XML sitemap is not a page
Every fetched response is classified by **Content-Type**, then a **body sniff**, then a
URL extension, in that order. No single signal decides alone. A sitemap mislabelled
`text/html` is still XML; an HTML page at a URL containing the word "sitemap" is still a
page. HTML-only checks — title, H1, viewport, CTA, navigation, structured data — never
run against XML, JSON, images or PDFs, and the exclusions appear in the report's scope.

### 2. Page-role classification — a tool is not a landing page
Each HTML page gets a role and a **confidence** from converging evidence: URL, title,
headings, structured-data `@type`, form and password fields, link density, `<time>`
elements, code blocks. A URL keyword alone is never enough for high confidence.
`unknown` is a valid, preferred answer, and it makes role-specific checks stand down
rather than guess.

Roles: homepage · article · product · documentation · utility · contact · legal ·
directory · authentication · resource · generic · **unknown**

### 3. Evidence discipline — observation, interpretation, conclusion
Every finding separates what was **measured** from what it may **imply**, and names what
was **not verified**. Severity is then capped by `auditlib.calibrate()`, which no check
can bypass: an improvement can never exceed `low`; confidence caps severity; and
`critical`/`high` additionally require `material: true`, set only after establishing that
the resource is relevant, the problem is real, the impact is material, the evidence
supports the conclusion, and the condition is not simply intentional design. Every cap is
recorded on the finding as `severity_capped_from` and `severity_cap_reason`.

| Instead of | The report says |
|---|---|
| "No external corroboration exists." | "No sameAs relationships were detected in the homepage structured data. … No external source was queried by this audit." |
| "The site is invisible to AI." | "N/M sampled pages return a client-side application root with under 300 characters of extractable text in the server response. … Whether they are reachable after rendering was not measured in this run." |
| "The page causes users to bounce." | "N/M pages with a confidently-classified product role contain no text matching an action relevant to that role." |
| "Render comparison unavailable" *(as a finding)* | a `skipped_checks` entry — an audit limitation is not a website defect |

### What is deliberately NOT a finding
No CTA on a page whose role doesn't imply one · no footer · a low link count · no FAQ ·
no JSON-LD as a high-severity defect · no `sameAs` as proof of anything external · no H1
where the title already states the topic · sparse raw HTML as proof of AI invisibility ·
a cookie banner as an intrusive interstitial · muted autoplay · `noindex` on a sitemap ·
a render comparison that could not be run.

## Concern → skill map
Each skill owns one mechanism from the chain, so each is independently testable:

| Skill | Mechanism | The question it answers |
|-------|-----------|-------------------------|
| **audit-orchestrator** *(entrypoint)* | — | Classify, compose, validate, deduplicate, gate severity, emit the one report |
| **crawl-access-audit** | reach | Can a crawler reach and index the content? |
| **render-extraction-audit** | read | Are the facts in the server HTML, or only after JS? (measured, not assumed) |
| **structured-data-audit** | identify facts | Can a machine extract and attribute the fact, given what this page is for? |
| **freshness-corroboration-audit** | fresh & corroborated | Is the fact current, and is identity stated so external sources can be connected? |
| **answerability-audit** | clarity of facts | Are the important facts hard to locate? |
| **integrity-audit** | trust | Does the page manipulate the machine reading it? |
| **engagement-audit** | visitor task | Can an arriving visitor do what they came for? |

Adding a concern = a skill folder plus one line in `marketplace.json`.

## How the entrypoint composes the others
1. **Crawl once → shared cache.** robots.txt, `Crawl-delay`, per-AI-bot rules, a
   two-user-agent edge probe, sitemap discovery, then a bounded same-host sample. Every
   resource is classified and every HTML page is given a role.
2. **Fan out.** Each sub-audit returns `{ skill, findings[], skipped_checks[] }`. A
   sub-audit that crashes, times out or returns a malformed envelope is recorded and
   skipped; it never corrupts the report.
3. **Compose.** Normalise → annotate shared root causes → **validate evidence** (a
   finding with no observation, zero scope or no action is dropped and listed) →
   **deduplicate** → **calibrate severity** → prioritise defects before improvements →
   assign stable `F-NNN` ids.

The orchestrator holds no checks, invents no facts, and reports **no score** — no scoring
formula is implemented, so none is emitted.

## Output schema
Meets the required floor (`site`, `audited_at`, `summary` counts, and per finding `id`,
`title`, `severity`, `evidence`, `suggested_action`). Adds `url`, `auditor`, `status`,
`scope`, `summary.by_dimension`, `summary.by_type`, and per finding `dimension`,
`category`, `skill`, `finding_type`, `confidence`, `evidence_detail`, `mechanism`,
`page_role`, `checked`, and `severity_capped_from`/`severity_cap_reason` where a gate
applied. Contract: `skills/audit-orchestrator/references/report-format.md`; gates:
`…/severity-rubric.md`.

`scope` states exactly what was inspected — resources crawled, HTML pages analysed,
non-HTML resources by kind, the page-role histogram, whether the sample hit its cap, and
**every check that did not run, with its reason**.

A crawl that reaches nothing emits `status: "failed"` with a machine-readable `failure`
object and a non-zero exit code, never a hollow report that reads like a clean site.

## Layout
```
brand-ai-readiness-audit/
  marketplace.json            # manifest: every skill + the one entrypoint
  scripts/validate.py         # manifest + SKILL.md sanity check
  scripts/package.py          # deterministic submission.zip builder
  batch_audit.py              # live benchmark + generalisation runner
  skills/
    audit-orchestrator/       # ENTRYPOINT - auditlib.py, crawler.py, run_audit.py, render_report.py
    crawl-access-audit/  render-extraction-audit/  structured-data-audit/
    freshness-corroboration-audit/  answerability-audit/  integrity-audit/  engagement-audit/
  tests/                      # 61 tests, offline
```
`auditlib.py` owns the three shared mechanisms above, so every skill classifies and gates
identically. Each skill folder is an independent agentskills.io-compliant skill.

## Requirements
- Python 3.8+ (standard library only for crawling, parsing and every check).
- Optional: `playwright` + Chromium for `--render`. Without it the audit degrades to a
  documented limitation rather than a guess.

## Validate & test
```bash
python scripts/validate.py     # manifest well-formedness + one entrypoint + each SKILL.md
python tests/run_tests.py      # 61 offline tests (add --render for the browser path)
python batch_audit.py --all    # live: 10-site benchmark + 9-site generalisation set
python scripts/package.py      # build ../submission.zip (deterministic, source only)
```
Five fixture sites run offline. `badsite` must trip the severe checks; `goodsite` must
not; `integritysite` covers injection, cloaking and invisible Unicode; `robotssite`
proves a disallowed URL is never fetched; and **`varietysite`** is the false-positive
suite — a documentation/tool site with no CTA, no footer, no FAQ, a cookie banner, muted
autoplay, an XML sitemap and a `noindex` sitemap response, every one of which must stay
out of the report.

## Scope & guardrails
Read-only; GET/HEAD only; no destructive, authenticated or rate-abusing actions; a
politeness floor plus any declared `Crawl-delay`; bounded page count, response size and
timeouts; respects `robots.txt` and never requests a disallowed URL. Self-contained: no
external service resolves the marketplace.

## License
MIT (per-skill in each SKILL.md).
