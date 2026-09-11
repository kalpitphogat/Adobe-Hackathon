---
name: audit-orchestrator
description: >-
  Entrypoint skill for the brand-ai-readiness-audit marketplace. Given a website URL,
  it crawls the site once (read-only, robots-respecting), classifies every fetched
  resource and every HTML page's role, invokes each specialised audit skill against a
  shared cache, then normalises, deduplicates, evidence-validates and severity-gates
  their findings into one structured report — evidence-backed problems separated from
  optional improvements, each with its scope and a prioritised, mechanism-specific
  fix — covering both AI discoverability (getting found and cited by AI assistants)
  and on-site engagement (visitors who arrive not staying). Use this to audit any site
  for why a brand is missing or misrepresented in AI assistants, or why arriving
  visitors do not engage.
license: MIT
allowed-tools: [Bash, Read]
---

# Brand AI-Readiness Audit — Orchestrator (entrypoint)

## When to use
When someone wants a website audited for **AI discoverability** (why assistants do not
find, cite, or correctly describe a brand) and **on-site engagement** (why visitors who
arrive do not stay). This is the marketplace entrypoint: it drives the other skills and
emits the one final report.

## Inputs
- A website URL or domain (`example.com` or `https://example.com`).
- Optional: `--max-pages N` (default 12, hard-bounded at 100), `--render` (headless
  Chromium, to measure the raw-versus-rendered gap directly), `--cache DIR`,
  `--out FILE`, `--html FILE`.

## Procedure (deterministic)
One command runs the whole flow:

```
python scripts/run_audit.py <site> [--max-pages 12] [--render] [--out report.json] [--html report.html]
```

1. **Understand the site — one polite crawl.** `crawler.py` reads robots.txt, honours
   any `Crawl-delay` above a 0.25s politeness floor, records per-AI-user-agent
   allow/deny, probes edge reachability twice, discovers sitemaps (following an index one
   level), then samples same-host URLs. Every response is **classified** by Content-Type,
   then a body sniff, then a URL extension — so an XML sitemap mislabelled `text/html`
   is still an XML resource, and an HTML page at a URL containing the word "sitemap" is
   still a page. Each HTML page then gets a **role** and a role confidence from converging
   evidence (URL, title, headings, structured-data type, forms, link density, dates,
   code blocks). `unknown` is a valid answer and suppresses role-specific checks.
2. **Fan out.** Each sub-audit runs against the shared cache and returns
   `{ skill, findings[], skipped_checks[] }`. A sub-audit that crashes, times out or
   emits a malformed envelope is recorded and skipped; it never corrupts the report.
3. **Compose.** In order: normalise, annotate shared root causes, **validate evidence**
   (a finding with no observation, zero scope, or no action is dropped and listed),
   **deduplicate** by key and by known same-root-cause group, **calibrate severity**
   through the gates, then prioritise defects before improvements and assign stable
   `F-NNN` ids.
4. **Emit** the report to stdout, `--out`, and optionally a readable HTML page.

The entrypoint holds **no checks of its own**, invents no facts, evidence or counts, and
emits **no score** — no scoring formula is implemented, so none is reported.

## Output (required floor, plus additive fields)
```json
{
  "site": "example.com",
  "audited_at": "2026-09-12T14:32:00Z",
  "summary": { "total_findings": 6, "critical": 1, "high": 2, "medium": 3, "low": 0 },
  "findings": [
    {
      "id": "F-001",
      "title": "HTML pages carry a noindex directive",
      "severity": "critical",
      "evidence": "1/10 sampled HTML pages set noindex: https://example.com/ [meta robots, role=homepage]. noindex instructs search engines and assistant crawlers to exclude the page entirely...",
      "suggested_action": { "summary": "Remove noindex from the public pages listed above.", "priority": "critical" }
    }
  ]
}
```
Additive: `url`, `auditor`, `status`, `scope`, `summary.by_dimension`,
`summary.by_type`, and per finding `dimension`, `category`, `skill`, `finding_type`,
`confidence`, `evidence_detail`, `mechanism`, `page_role`, `checked`, and
`severity_capped_from` / `severity_cap_reason` where a gate applied. Full contract in
`references/report-format.md`; the gates in `references/severity-rubric.md`.

`scope` states what was actually inspected: resources crawled, HTML pages analysed,
non-HTML resources by kind, the page-role histogram, whether the sample hit its cap, and
every check that did not run **with its reason**.

## Failure is explicit
A crawl that reaches nothing emits `status: "failed"` with a machine-readable `failure`
object and a non-zero exit code — never a hollow report that could be mistaken for a
clean site.

## Composition
One skill per mechanism: reach (crawl-access), read (render-extraction), identify facts
(structured-data), freshness and corroboration, clarity of facts (answerability), trust
(integrity), and visitor task and usability (engagement). This entrypoint owns only
orchestration and report assembly, so each concern stays independently testable and
swappable. See the root `README.md` for the concern-to-skill map.

## Guardrails
Read-only. GET/HEAD only; no forms, logins or state changes. Respects robots.txt and
never requests a disallowed URL. Bounded page count, response size and timeouts.
Recommendations only — it never alters the audited site.
