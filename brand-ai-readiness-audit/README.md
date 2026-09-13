# Brand AI-Readiness Audit

**Adobe University Hackathon 2026 — Round 3, Build the Agent Skill Marketplace**
Team: Lakshya, Tanmay, Kalpit · MIT

Point this at a website. It tells you why AI assistants do not find, cite or
correctly describe the brand, and why visitors who do arrive leave without
acting — with evidence for every claim, a paste-ready fix, and an order to do
them in. Read-only; it never modifies the site it audits.

```bash
python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://example.com --out ./audit-output
```

Outputs `audit-report.json` (fixed schema) and `report.md`, written for someone
who is not an engineer. Python 3.9+; 63 of 66 checks need nothing but the
standard library.

> **Design rationale, the full check inventory, guardrails and known limitations
> are in [DESIGN.md](DESIGN.md).** This file is the short tour the submission
> asks for: what each skill does, and how the entrypoint composes them.

---

## What each skill does

Nine skills. One entrypoint.

| skill | what it does | stage |
|---|---|---|
| **ai-readiness-orchestrator** | **Entrypoint.** Runs every other skill, applies the gate cascade, dedupes, scores and ranks, and emits the single audit report. | — |
| site-evidence-collector | Fetches and renders the site **exactly once** and writes the shared evidence bundle. The only skill that touches the network. | — |
| site-profile-classifier | Detects the site archetype and per-page type, then selects the thresholds every other skill scores against. | — |
| crawl-access-audit | Can an AI crawler get in? robots.txt against a dated AI-bot snapshot, CDN/WAF reachability, `noindex`, canonicals, redirects, soft 404s, broken links, sitemaps, `llms.txt`. | reach |
| render-gap-audit | Can it read the page without running JavaScript? Raw-vs-rendered diff, unhydrated SPA shells, JSON-island recovery, facts locked in images. | read |
| structured-data-audit | Is the fact machine-typed? JSON-LD, microdata, RDFa and OpenGraph — presence, validity, correct type, required properties, markup-vs-visible contradictions, `hreflang`. | extract |
| answerability-audit | Is the fact quotable? Simulates retrieval over no-JS windows and tests whether each claim survives self-contained: no dangling pronoun, subject named, plus tables, headings and direct-answer blocks. | extract |
| trust-freshness-audit | Would a machine believe it? Date coherence across schema/visible/sitemap/headers, entity identity and NAP consistency, external corroboration, authorship — plus prompt-injection, cloaking and invisible-Unicode integrity checks. | trust |
| engagement-audit | Does the visitor stay and act? First-screen orientation, CTA clarity, form friction, dead ends, interstitials, mobile viewport, page weight, social proof, cost signals. | act |

`site-evidence-collector` and `site-profile-classifier` emit no findings, and
that is deliberate. The **collector** is why six audit skills cannot disagree
about what the site served, and why one crawl fits the time budget. The
**classifier** is where generalisation lives: no check anywhere hardcodes a
threshold, every one asks the profile. Neither performs a check; both are
load-bearing.

---

## How the entrypoint composes them

By **subprocess**, never by import:

```
orchestrate.py  (ai-readiness-orchestrator)
  → collect.py           writes the evidence bundle          (network, once)
  → profile.py           archetype + page types + thresholds
  → 6 × run.py           each reads that bundle, prints one JSON object
  → gate cascade         cap, tag blocked_by, suppress per Rule 0b
  → dedupe, score, rank  severity → ICE → stage → check_id
  → emit                 audit-report.json + report.md + fix_patches/
```

Every audit skill is invoked as
`python <skill>/scripts/run.py --bundle <dir> [--profile <file>]`, returns one
JSON object on stdout, and exits 0 (ran), 3 (precondition unmet) or 1 (error).
The orchestrator holds **no checks of its own** — it is pure composition.

Because nothing imports across skill folders, **any skill folder can be lifted
out of this marketplace and run alone**. Where two skills need the same
predicate it is duplicated on purpose, and a test walks the AST of every script
to fail the build on a cross-skill import, including the `sys.path` dodge.

The ordering is the design. The Round-2 appendix says three things must succeed
**in order** — the crawler is let in, the page can be read, the fact can be
picked out — so when an upstream stage fails, downstream findings are recorded
but **capped and tagged with the id of the finding blocking them**. You get the
root cause first instead of forty equal-looking problems.
See [DESIGN.md](DESIGN.md) for the cascade and Rule 0b in full.

The skill contract is normative and was written before the audit skills:
[`skill-cli-contract.md`](skills/ai-readiness-orchestrator/references/skill-cli-contract.md).

---

## The report

```jsonc
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "summary": { "total_findings": 6, "critical": 1, "high": 2, "medium": 3,
               "by_category": { "discoverability": 5, "engagement": 1 } },
  "findings": [{
    "id": "F-001",
    "title": "...",
    "severity": "critical",
    "evidence": "...",                  // what was observed, with counts and URLs
    "suggested_action": {
      "summary": "...", "priority": "critical",
      "mechanism": "...",               // why the fix works
      "patch": "...",                   // paste-ready
      "ice": 9.3, "effort": "low",
      "verification": "..."             // how to confirm it worked
    },
    "stage": "reach", "confidence": "confirmed", "blocked_by": null
  }],
  "proactive_recommendations": [ /* improvements where no defect was found */ ],
  "limitations": [ /* what could not be assessed, and why */ ]
}
```

Findings are ordered by what to fix first. Anything the audit could not assess
is stated in `limitations` rather than passed silently.

---

## Running it

```bash
# audit a site
python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://example.com --out ./audit-output

# your own site? adds the highest-value check in the marketplace (see DESIGN.md)
python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://your-site.com \
    --out ./audit-output --probe-bot-ua

# no network required
python skills/ai-readiness-orchestrator/scripts/orchestrate.py \
    --offline-root tests/fixtures/site_b --out ./audit-output
```

Playwright is optional and upgrades the render-stage checks; without it the
audit still runs and reports what it could not see. Exit code is 0 whenever a
schema-valid report was written — the outcome lives in `audit_status`, never in
the exit code.

**Tests** — `python tests/validate_marketplace.py` (structure, spec, doc drift),
`python tests/run_offline.py` (6 golden reports byte-for-byte + a determinism
matrix), and `python tests/test_*.py` (10 suites). Details in
[DESIGN.md](DESIGN.md).

---

## Guardrails

- **Recommend-only.** No skill modifies a live site. The HTTP layer validates
  every method against a `{GET, HEAD}` allowlist, so no code path can POST.
- **robots.txt is a hard constraint** on our own crawling, not advice.
- **No authenticated areas, no cookies, no credentials.**
- **Private, loopback and link-local hosts are refused**, on the seed and on
  every redirect hop.
- **Polite:** 5 workers, 0.4s per-host delay, `Retry-After` honoured, backoff on
  429/5xx, crawler-trap guards, 25-page cap.
- **Bounded runtime.** Every stage draws from one shared clock, so the run
  cannot outrun `--time-budget` (default 300s).
- **No hosted API, key or account.** The manifest is self-contained.

Full statements, and the reasoning behind each, in [DESIGN.md](DESIGN.md).

---

*Licence: MIT, declared in every skill's `SKILL.md`, in `marketplace.json`, and
in [`LICENSE`](LICENSE). Third-party sources credited in
[`ATTRIBUTIONS.md`](ATTRIBUTIONS.md).*
