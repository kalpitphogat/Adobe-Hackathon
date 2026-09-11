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
  ┌──────────────┬─────────────────┬───────────────┬────────────────────┬──────────────┬────────────┬────────────┐
  │ crawl-access │ render-extract. │ structured-data│ freshness-corrob.  │ answerability│ integrity  │ engagement │
  │ gate 1       │ gate 2          │ gate 3        │ trust              │ quotability  │ trust/safety│ retention │
  └──────────────┴─────────────────┴───────────────┴────────────────────┴──────────────┴────────────┴────────────┘
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

## The eight skills (one concern each)

| Skill | Answers | Mechanism |
|-------|---------|-----------|
| **audit-orchestrator** *(entrypoint)* | Classify resources and roles, compose, validate evidence, deduplicate, gate severity, emit the one report | — |
| **crawl-access-audit** | Can a crawler reach and index it? robots.txt and per-AI-bot rules, **edge/CDN bot blocks**, sitemap, `noindex` on HTML pages only, status, HTTPS, broken links, insecure sub-resources, `llms.txt` | reach |
| **render-extraction-audit** | Are the facts in the server HTML, or only after JS? A **measured** raw-vs-rendered diff; sparse HTML is reported as sparse HTML, not as AI invisibility | read |
| **structured-data-audit** | Can a machine extract and attribute the fact, **given what this page is for**? Role-matched schema only, entity identity, titles, topical identity | identify facts |
| **freshness-corroboration-audit** | Is it current, and is identity stated so external sources can be connected? Dates, `sameAs` — with an explicit no-external-lookup claim boundary | fresh & corroborated |
| **answerability-audit** | Are the important facts hard to locate? Existing Q&A markup, thin information pages, homepage self-description, contact routes | clarity of facts |
| **integrity-audit** | Does the page manipulate the machine reading it? Prompt injection, hidden **non-UI** text, invisible Unicode | trust |
| **engagement-audit** | Can an arriving visitor do what they came for? Role-relevant next step, orientation, viewport, latency, real interstitials | visitor task |

First seven map to **discoverability** (integrity is a trust signal on that side); the
last to **engagement**. Every finding is tagged with its dimension and with
`finding_type` (defect or improvement), and the report summarizes both splits.

### What makes this version different

Three shared mechanisms in `auditlib.py`, used by every skill, decide whether a check
runs at all and how loudly it may speak:

1. **Resource classification.** Content-Type, then a body sniff, then a URL extension, in
   that order, with no single signal deciding alone. HTML-only checks never touch an XML
   sitemap, a JSON endpoint, an image or a PDF.
2. **Page-role classification** with a confidence level, from converging evidence.
   `unknown` is a valid answer that makes role-specific checks stand down rather than guess.
3. **Evidence discipline and severity gates.** Each finding separates what was *measured*
   from what it may *imply*, and names what was *not verified*. An improvement can never
   exceed `low`; confidence caps severity; and `critical`/`high` require materiality to
   have been established. Every cap is recorded on the finding itself.

Deliberately **not** findings: no CTA where the role does not imply one; no footer; a low
link count; no FAQ; missing JSON-LD as high severity; no `sameAs` as proof of anything
external; no H1 where the title already states the topic; sparse raw HTML as proof of AI
invisibility; a cookie banner as an interstitial; muted autoplay; `noindex` on a sitemap;
a render comparison that could not be run.

---

## The report (fixed schema)

```json
{
  "site": "example.com",
  "audited_at": "2026-09-12T14:32:00Z",
  "status": "ok",
  "scope": { "pages_crawled": 12, "html_pages_analyzed": 9, "non_html_resources": 3,
             "resource_kinds": { "html": 9, "xml": 2, "json": 1 },
             "page_roles": { "homepage": 1, "article": 4, "documentation": 3, "unknown": 1 },
             "sample_based": true, "render_used": true, "robots_respected": true,
             "checks_skipped": [ { "check": "...", "reason": "..." } ] },
  "summary": { "total_findings": 6, "critical": 1, "high": 2, "medium": 3, "low": 0,
               "by_dimension": { "discoverability": 5, "engagement": 1 },
               "by_type": { "defects": 4, "improvements": 2 } },
  "findings": [{
    "id": "F-001",
    "title": "HTML pages carry a noindex directive",
    "severity": "critical", "dimension": "discoverability", "finding_type": "defect",
    "confidence": "high", "skill": "crawl-access-audit", "mechanism": "reach",
    "evidence": "1/9 sampled HTML pages set noindex: https://example.com/ [meta robots, role=homepage]. noindex instructs search engines and assistant crawlers to exclude the page entirely - and this includes the homepage.",
    "evidence_detail": { "observation": "1/9 sampled HTML pages set noindex ...",
                         "interpretation": "noindex instructs ...", "not_verified": "" },
    "suggested_action": { "summary": "Remove noindex from the public pages listed above.", "priority": "critical" }
  }]
}
```
Severity is computed from evidence and then **gated**: no check can emit `critical` or
`high` without having established materiality, and no improvement can exceed `low`. No
score is reported, because no scoring formula is implemented.

---

## Run & test

```bash
cd brand-ai-readiness-audit

# audit a site — --render adds the JS fact-gap check; --html writes a readable report page
python skills/audit-orchestrator/scripts/run_audit.py https://example.com \
    --render --out report.json --html report.html

python scripts/validate.py     # manifest + SKILL.md compliance
python tests/run_tests.py      # 70 offline tests across five fixture sites
python batch_audit.py --all    # live: 10-site benchmark + 9-site generalisation set
```
Python 3.8+, **standard library only** for the audit. `--render` optionally uses
Playwright + Chromium; without it the audit records the missing measurement as a scope
limitation rather than guessing.

---

## Round 3 compliance

| Requirement (from the brief) | ✓ |
|---|---|
| Marketplace + `marketplace.json` with **exactly one** entrypoint | ✅ |
| Every skill folder = valid agentskills.io `SKILL.md` (name/description/license) | ✅ 8/8 |
| Findings separate defect from improvement, and state their scope | ✅ |
| Audit limitations reported as scope, never as website defects | ✅ |
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
      ├─ integrity-audit/
      └─ engagement-audit/
```
Each skill folder is an independent agentskills.io skill: lean `SKILL.md`, executable
`scripts/`, detailed check catalogs and paste-ready fixes in `references/`.

### Package for submission
```bash
cd brand-ai-readiness-audit && zip -r ../submission.zip . -x '*__pycache__*' -x '*.pyc' -x 'tests/*cache*'
```

## Related work
The check design was informed by open-source AEO/GEO auditors — notably
[geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) and
[ai-seo-auditor](https://github.com/ngstcf/ai-seo-auditor). Ideas adopted here include the
**edge/CDN AI-bot reachability** probe (a WAF can block GPTBot even when robots.txt allows
it) and **answer-formatting / chunkability** checks (lists, tables, question-style
headings). Our take stays decomposed into concern-scoped skills, computes severity from
evidence, covers the engagement half explicitly, and enforces read-only + robots.txt as a
hard guardrail.

*License: MIT (declared per-skill).*
