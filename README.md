# Adobe University Hackathon 2026 — Round 3
## Brand AI-Readiness Audit — an Agent Skill Marketplace

> **One line:** Point this at any website and it tells you *why AI assistants
> (ChatGPT, Claude, Perplexity…) don't find or cite the brand*, and *why visitors
> who do arrive don't stay* — with evidence, severity, and a prioritized fix for
> each problem.

The working project lives in **[`brand-ai-readiness-audit/`](brand-ai-readiness-audit/)**.
This page explains the whole thing from scratch and where we're taking it next.

---

## 1. The problem we're solving

Round 2 asked *why* a brand goes invisible, stale, or ignored inside AI apps.
**Round 3 asks us to encode that reasoning into reusable agent skills** so a general
AI agent, pointed at any site, can audit it automatically.

Two halves of the same problem:

- **AI discoverability** — the brand isn't *found or cited* by AI assistants.
  Answers about it are wrong, generic, or missing entirely.
- **On-site engagement** — the visitors AI *does* send bounce before they engage.

A website can look perfect to a human and still fail both. Our job is to detect the
concrete, repeatable reasons **and** recommend how to fix them — read-only, never
touching the live site.

### Why AI assistants miss a brand (the mental model)

Modern assistants look things up in the moment. For a page to be used as a source,
three things must succeed **in order**:

```
   ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐
   │ 1. GET IN    │ → │ 2. READ IT   │ → │ 3. PICK OUT THE    │
   │ crawler      │   │ content is   │   │ FACT it needs      │
   │ allowed in   │   │ in raw HTML  │   │ stated clearly     │
   └──────────────┘   └──────────────┘   └────────────────────┘
        robots            JS render           structured data
        noindex           images              plain, quotable text
```

If **any** step fails, the page effectively doesn't exist for that assistant — plainly
visible to a person, invisible to the machine. On top of those three gates, assistants
**trust** facts that are *fresh* and *agreed-upon across independent sources*, and they
prefer facts that are *easy to quote*. Our skills map onto exactly these mechanisms.

---

## 2. What we built

An **Agent Skill Marketplace**: a package of focused, independent skills tied together
by a manifest, with **one entrypoint** that runs the audit and emits a single report.
Each skill is authored in the standard [agentskills.io](https://agentskills.io) format
(a `SKILL.md` + optional `scripts/` and `references/`).

We deliberately **split the reasoning into one skill per mechanism** — that's the point
of the marketplace format, and it keeps every concern independently testable.

| Skill | The question it answers | Mechanism |
|-------|-------------------------|-----------|
| **audit-orchestrator** *(entrypoint)* | Crawl once, run the others, compose the one report | — |
| **crawl-access-audit** | Can an (AI) crawler reach & index the site? | Gate 1 — get in |
| **render-extraction-audit** | Are the facts in raw HTML, or only after JavaScript? | Gate 2 — read it |
| **structured-data-audit** | Can a machine extract & attribute the exact fact? | Gate 3 — pick the fact |
| **freshness-corroboration-audit** | Is the fact current & cross-verifiable? | Trust |
| **answerability-audit** | Is the key fact stated as short, quotable text? | Quotability |
| **engagement-audit** | Will an arriving visitor actually stay? | On-site retention |

The first five cover **discoverability**; the last covers **engagement**. Every finding
in the report is tagged with its dimension, so both halves are summarized separately.

### What each skill actually checks (highlights)

- **crawl-access** — robots.txt, whether the major AI bots (GPTBot, ClaudeBot,
  PerplexityBot, Google-Extended…) are blocked, sitemap, `noindex`, HTTP errors, HTTPS,
  broken internal links, mixed content (http resources on https pages), and `llms.txt`.
- **render-extraction** — our highest-signal check: it fetches the **raw HTML** and the
  **JavaScript-rendered** page (headless Chromium) and measures the *gap*. If the price,
  hours, or headline only appears after JS, assistants that read raw HTML miss it.
- **structured-data** — JSON-LD / schema.org coverage and **validity**, Organization
  identity + `sameAs` (so the brand isn't confused with same-named entities), titles,
  meta descriptions, Open Graph, heading structure, duplicate titles/descriptions.
- **freshness-corroboration** — stale copyright/dates, machine-readable publish dates,
  weak external corroboration, unattributed superlative claims.
- **answerability** — FAQ/Q&A markup, thin pages, and whether the homepage plainly says
  *what the brand is and who it's for* (the sentence assistants quote).
- **engagement** — mobile viewport, page weight & latency, clear call-to-action,
  navigation, intrusive pop-ups/autoplay.

---

## 3. How it works (the pipeline)

```
  run_audit.py <site>
        │
        ▼
  ┌─────────────────┐   crawls ONCE, read-only, respects robots.txt
  │  crawler.py     │   → shared cache: raw HTML + text + rendered text per page
  └─────────────────┘
        │  (shared cache)
        ├──────────────┬──────────────┬───────────────┬──────────────┬─────────────┐
        ▼              ▼              ▼               ▼              ▼             ▼
   crawl-access   render-extract  structured-data  freshness    answerability  engagement
        │              │              │               │              │             │
        └──────────────┴──────────────┴───────────────┴──────────────┴─────────────┘
                                     │  each returns { skill, findings[] }
                                     ▼
                          ┌───────────────────────┐
                          │  audit-orchestrator   │  merge → tag dimension →
                          │  composes the report  │  sort by severity → F-001…
                          └───────────────────────┘
                                     │
                                     ▼
                          one structured audit report (JSON)
```

**One crawl feeds every skill** — polite to the target site and fast (well under the
5-minute budget). Severity is **computed from evidence** (a homepage `noindex` is
critical; the same on one deep page is high), not hardcoded — so it generalizes to sites
we've never seen, which is exactly how the round is graded.

---

## 4. Run it

```bash
cd brand-ai-readiness-audit

# audit a site — --render measures the JS fact-gap; --html writes a readable report page
python skills/audit-orchestrator/scripts/run_audit.py https://example.com \
    --render --out report.json --html report.html

# sanity-check the marketplace structure
python scripts/validate.py

# run the full offline test suite (broken + healthy fixture sites)
python tests/run_tests.py
```

**Requirements:** Python 3.8+ (standard library only for crawling/parsing).
`--render` additionally needs `pip install playwright` (Chromium is used headless). The
audit **degrades gracefully** without Playwright — it keeps a thin-HTML heuristic and
notes that the direct render measurement was skipped, never a false "all clear".

### Example output (shape)

```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "scope": { "pages_crawled": 12, "render_used": true, "robots_respected": true },
  "summary": {
    "total_findings": 6, "critical": 1, "high": 2, "medium": 3, "low": 0,
    "by_dimension": { "discoverability": 5, "engagement": 1 }
  },
  "findings": [
    {
      "id": "F-001",
      "title": "Pages are near-empty in raw HTML (client-side rendered)",
      "severity": "critical",
      "dimension": "discoverability",
      "skill": "render-extraction-audit",
      "evidence": "3/12 sampled pages have <300 chars of extractable text in the server HTML despite a full app shell.",
      "suggested_action": {
        "summary": "Server-render or pre-render the primary content so the main facts exist in the initial HTML.",
        "priority": "critical"
      }
    }
  ]
}
```

Every finding carries **machine-derived evidence** (counts, URLs, measured gaps) and a
**specific, mechanism-sound fix** — not "add structured data" but the exact JSON-LD to
paste (see `structured-data-audit/references/schema-templates.md`).

---

## 5. Design decisions that matter

- **Separation of concerns** — the orchestrator holds *no checks of its own*; it only
  composes. Adding a concern = one skill folder + one line in `marketplace.json`.
- **Evidence over opinion** — findings fire only with concrete evidence, and
  "absence" findings require sitewide certainty to avoid false positives.
- **Deterministic & safe** — read-only, GET-only, respects robots.txt, no auth, no
  writes, self-contained (no external service needed to resolve the marketplace).
- **Progressive disclosure** — each `SKILL.md` stays lean; detailed check catalogs and
  fix templates live in each skill's `references/`.

---

## 6. Future plan / roadmap

Where we take this beyond the submission:

### Near-term (polish & coverage)
- [x] **Human-readable report renderer** — `--html` writes a ranked, color-coded,
      theme-aware HTML report on top of the JSON (`render_report.py`).
- [x] **More discoverability checks** — `llms.txt` detection, broken internal links,
      duplicate-title/description detection, and mixed-content warnings shipped.
- [x] **Automated test suite** — `tests/run_tests.py` with broken/healthy fixture sites.
- [ ] **`hreflang`/i18n signals** — detect missing or inconsistent language alternates.
- [ ] **Richer engagement signals** — optional Lighthouse/Core-Web-Vitals pass for real
      LCP/TTFB numbers (today we use fast first-response proxies and say so honestly).
- [ ] **Per-finding confidence score** alongside severity, so borderline heuristics are
      clearly marked.

### Mid-term (depth & trust)
- [ ] **Off-site corroboration, for real** — actually check whether the brand's key facts
      agree across independent sources (Wikidata, LinkedIn, directories), not just whether
      `sameAs` links exist on-site.
- [ ] **Live assistant probing** — ask real assistants a set of brand questions and grade
      whether the brand is surfaced, cited, and described correctly (closing the loop from
      "should be discoverable" to "is discovered").
- [ ] **Competitor benchmarking** — audit a brand against 2–3 competitors and show where
      it's behind on each mechanism.
- [ ] **Historical tracking** — store reports over time to show whether fixes moved the
      needle.

### Long-term (product)
- [ ] **Auto-generated fix PRs** — go from *recommend-only* to optionally opening a pull
      request with the JSON-LD / meta / robots changes (opt-in, still never touching the
      live site directly).
- [ ] **Scheduled monitoring** — re-audit on a cadence and alert when a regression appears
      (a new `noindex`, a schema break, a render regression after a redeploy).
- [ ] **Dashboard** — a shared view of findings, trends, and priorities for a whole team.

---

## 7. Repository layout

```
Adobe-Hackathon/
  README.md                       ← you are here
  brand-ai-readiness-audit/       ← the submission (zip this folder)
    marketplace.json              ← manifest: every skill + the one entrypoint
    README.md                     ← marketplace-level docs
    scripts/validate.py           ← manifest + SKILL.md validator
    skills/
      audit-orchestrator/         ← ENTRYPOINT: crawler.py, run_audit.py, auditlib.py
      crawl-access-audit/
      render-extraction-audit/
      structured-data-audit/
      freshness-corroboration-audit/
      answerability-audit/
      engagement-audit/
```
Each skill folder is an independent, agentskills.io-compliant skill (`SKILL.md` +
`scripts/` + `references/`).

### To package for submission
```bash
cd brand-ai-readiness-audit && zip -r ../submission.zip .   # well under the 50 MB limit
```

---

## 8. Guardrails (per the round rules)

Recommend-only — the marketplace audits and reports; **no skill ever alters a live
site**. No destructive, authenticated, or rate-abusing actions. Respects `robots.txt`.
Runs in under 5 minutes for a typical site. Submission is self-contained.

*License: MIT (declared per-skill in each `SKILL.md`).*
