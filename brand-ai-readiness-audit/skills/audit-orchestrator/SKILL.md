---
name: audit-orchestrator
description: >-
  Entrypoint skill for the brand-ai-readiness-audit marketplace. Given a website
  URL, it crawls the site once (read-only, robots-respecting), invokes every other
  audit skill against a shared page cache, and composes their findings into a single
  structured audit report — evidence-backed problems with severities plus prioritized,
  actionable fixes — covering both AI discoverability (getting found and cited by AI
  assistants) and on-site engagement (keeping visitors once they arrive). Use this to
  audit any site for why a brand is missing/misrepresented in AI assistants or why
  arriving visitors don't engage.
license: MIT
allowed-tools: [Bash, Read]
---

# Brand AI-Readiness Audit — Orchestrator (entrypoint)

## When to use
Use this when someone wants a website audited for **AI discoverability** (why AI
assistants like ChatGPT/Claude/Perplexity don't find, cite, or correctly describe the
brand) and **on-site engagement** (why visitors who arrive don't stay). This skill is
the marketplace entrypoint: it drives the other skills and emits the one final report.

## Inputs
- A website URL or domain (e.g. `example.com` or `https://example.com`).
- Optional: `--max-pages N` (default 12), `--render` (use headless Chromium to measure
  the static-vs-rendered fact gap; recommended), `--out FILE`.

## Procedure (deterministic)
1. **Crawl once → shared cache.** Run `scripts/crawler.py <site> <cache_dir> [--render]`.
   It reads robots.txt, discovers a sitemap, samples up to N same-host pages (GET only),
   stores raw HTML + extracted text (+ rendered text when `--render`), and writes
   `meta.json`. One crawl feeds every sub-audit — polite and fast.
2. **Fan out sub-audits.** For each non-entrypoint skill in `marketplace.json`, run its
   check script against the cache dir. Each emits an envelope
   `{ "skill": id, "findings": [ … ] }`. See `references/report-format.md`.
3. **Compose.** Merge all findings, tag each with its source skill and dimension
   (discoverability | engagement), sort by severity, assign stable `F-NNN` ids, and
   count by severity. Severity is assigned by each check per `references/severity-rubric.md`.
4. **Emit** the single audit report (schema below) to stdout / `--out`.

The whole flow is one command:
```
python scripts/run_audit.py <site> [--max-pages 12] [--render] [--out report.json] [--html report.html]
```
`--out` writes the JSON report; `--html` additionally renders a readable, severity-ranked
HTML page via `scripts/render_report.py` (also usable standalone). The suite in
`../../tests/run_tests.py` exercises the whole pipeline against local fixture sites.

## Output (fixed schema — floor, not ceiling)
```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "summary": { "total_findings": 6, "critical": 1, "high": 2, "medium": 3, "low": 0 },
  "findings": [
    {
      "id": "F-001",
      "title": "No JSON-LD structured data on product pages",
      "severity": "high",
      "evidence": "Crawled 12 product pages; 0/12 contain schema.org markup.",
      "suggested_action": { "summary": "Add Product/Offer JSON-LD to every product page.", "priority": "high" }
    }
  ]
}
```
This orchestrator also adds `url`, `auditor`, `scope`, `summary.by_dimension`, and per
finding `dimension`, `skill`, and `checked` — all additive to the required floor.

## Composition
The marketplace decomposes the reasoning into one skill per mechanism (crawl access,
JS render/extraction, structured data, freshness/corroboration, answerability,
engagement). This entrypoint owns only orchestration and report assembly — it holds no
checks of its own, so each concern stays independently testable and swappable. See the
root `README.md` for the concern→skill map.

## Guardrails
Read-only. GET requests only; no forms, logins, or state changes. Respects robots.txt
and the per-page directives it reports on. Recommendations only — it never alters the
audited site. Runs offline once the cache exists; no external service resolves the
marketplace.
