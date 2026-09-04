# Brand AI-Readiness Audit
### Adobe University Hackathon 2026 — Round 3 · Agent Skill Marketplace

Point it at any website; it reports **why AI assistants (ChatGPT, Claude, Perplexity…)
don't find or cite the brand**, and **why visitors who arrive don't stay** — each problem
with evidence, a severity, and a prioritized fix. Read-only. Never touches the live site.

> Submission lives in **[`brand-ai-readiness-audit/`](brand-ai-readiness-audit/)**.

---

## The problem, in one picture

For a page to be usable by an AI assistant, **three gates must pass in order** — then two
trust factors decide whether its facts get repeated:

```
  ┌─ 1. GET IN ──┐   ┌─ 2. READ IT ─┐   ┌─ 3. PICK THE FACT ─┐
  │  crawler      │→ │  content in   │→ │  stated clearly,    │ → trusted if…  FRESH
  │  allowed      │   │  raw HTML     │   │  machine-readable   │               + CORROBORATED
  └───────────────┘   └───────────────┘   └─────────────────────┘               + QUOTABLE
     robots/noindex      JS-render gap        JSON-LD / plain text
```

Fail any gate and the page is invisible to the machine — perfect to a human, absent to the
assistant. A separate axis, **engagement**, decides whether the visitor AI *does* send stays.

---

## Architecture — crawl once, fan out, compose one report

```
  run_audit.py <site>
        │
        ▼
  ┌──────────────┐   read-only · robots-respecting · one polite crawl
  │  crawler.py  │──▶ shared cache:  raw HTML + extracted text + JS-rendered text + meta
  └──────────────┘
        │  (all sub-audits read this cache — never re-fetch)
        ▼
  ┌───────────────┬──────────────────┬─────────────────┬──────────────────────┬────────────────┬──────────────┐
  │ crawl-access  │ render-extraction│ structured-data │ freshness-corrob.    │ answerability  │ engagement   │
  │ gate 1        │ gate 2           │ gate 3          │ trust                │ quotability    │ retention    │
  └───────────────┴──────────────────┴─────────────────┴──────────────────────┴────────────────┴──────────────┘
        │  each returns { skill, findings[] }
        ▼
  ┌────────────────────┐   merge · tag dimension · sort by severity · assign F-001…
  │ audit-orchestrator │──▶ ONE report:  report.json  (+ optional report.html)
  │  (entrypoint)      │
  └────────────────────┘
```

**One crawl feeds every skill** → polite and fast (sub-second to well under the 5-min
budget). The entrypoint holds *no checks itself* — pure composition, so each concern is
independently testable and swappable.

---

## The seven skills (one concern each)

| Skill | Answers | Maps to |
|-------|---------|---------|
| **audit-orchestrator** *(entrypoint)* | Crawl once, run the rest, emit the report | — |
| **crawl-access-audit** | Can an AI crawler reach & index it? robots, AI-bot rules, sitemap, `noindex`, status, HTTPS, broken links, mixed content, `llms.txt` | Gate 1 |
| **render-extraction-audit** | Are facts in raw HTML or only after JS? (raw-vs-rendered gap, thin SPA shells, image-locked facts) | Gate 2 |
| **structured-data-audit** | Can a machine extract & attribute the fact? JSON-LD coverage/validity, Organization + `sameAs`, metadata, headings, duplicates | Gate 3 |
| **freshness-corroboration-audit** | Is it current & cross-verifiable? stale dates, machine-readable dates, `sameAs`, unattributed claims | Trust |
| **answerability-audit** | Is the key fact short, self-contained, quotable? FAQ markup, thin content, clear homepage | Quotability |
| **engagement-audit** | Will an arriving visitor stay? viewport, weight/latency, CTA, nav, interstitials | Retention |

First five → **discoverability**; last → **engagement**. Every finding is tagged with its
dimension; the report summarizes both halves.

---

## The report (fixed schema)

```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "scope": { "pages_crawled": 12, "render_used": true, "robots_respected": true },
  "summary": { "total_findings": 6, "critical": 1, "high": 2, "medium": 3, "low": 0,
               "by_dimension": { "discoverability": 5, "engagement": 1 } },
  "findings": [{
    "id": "F-001",
    "title": "Pages are near-empty in raw HTML (client-side rendered)",
    "severity": "critical", "dimension": "discoverability", "skill": "render-extraction-audit",
    "evidence": "3/12 sampled pages have <300 chars of text in server HTML despite a full app shell.",
    "suggested_action": { "summary": "Server-render or pre-render primary content.", "priority": "critical" }
  }]
}
```
Severity is **computed from evidence** (homepage `noindex` = critical; one deep page =
high), not hardcoded — so it generalizes to unseen sites.

---

## Run & test

```bash
cd brand-ai-readiness-audit

# audit a site — --render adds the JS fact-gap check; --html writes a readable report page
python skills/audit-orchestrator/scripts/run_audit.py https://example.com \
    --render --out report.json --html report.html

python scripts/validate.py     # manifest + SKILL.md compliance
python tests/run_tests.py      # offline suite: broken + healthy fixture sites (8 tests)
```
Python 3.8+, **standard library only** for the audit. `--render` optionally uses
Playwright + Chromium; without it the audit degrades gracefully (thin-HTML heuristic).

---

## Round 3 compliance

| Requirement (from the brief) | ✓ |
|---|---|
| Marketplace + `marketplace.json` with **exactly one** entrypoint | ✅ |
| Every skill folder = valid agentskills.io `SKILL.md` (name/description/license) | ✅ 7/7 |
| Entrypoint composes the rest into **one** report | ✅ |
| Report floor: `site`, `audited_at`, counts-by-severity; per finding `id`, `title`, `severity`, `evidence`, `suggested_action` | ✅ |
| Detects **both** discoverability and engagement | ✅ |
| Recommend-only · read-only · respects `robots.txt` | ✅ |
| Runtime < 5 min · zip ≤ 50 MB · no model weights | ✅ (~65 KB) |
| Root `README.md` describing skills + composition | ✅ |

---

## Repository layout

```
Adobe-Hackathon/
├─ README.md                      ← this file
└─ brand-ai-readiness-audit/      ← the submission (zip this folder)
   ├─ marketplace.json            ← manifest + entrypoint
   ├─ README.md                   ← marketplace-level docs
   ├─ scripts/validate.py         ← manifest/SKILL.md validator
   ├─ tests/                      ← unittest suite + broken/healthy fixtures
   └─ skills/
      ├─ audit-orchestrator/      ← ENTRYPOINT: crawler.py · run_audit.py · render_report.py · auditlib.py
      ├─ crawl-access-audit/
      ├─ render-extraction-audit/
      ├─ structured-data-audit/
      ├─ freshness-corroboration-audit/
      ├─ answerability-audit/
      └─ engagement-audit/
```
Each skill folder is an independent agentskills.io skill: lean `SKILL.md`, executable
`scripts/`, detailed check catalogs and paste-ready fixes in `references/`.

### Package for submission
```bash
cd brand-ai-readiness-audit && zip -r ../submission.zip . -x '*__pycache__*' -x '*.pyc' -x 'tests/*cache*'
```

*License: MIT (declared per-skill).*
