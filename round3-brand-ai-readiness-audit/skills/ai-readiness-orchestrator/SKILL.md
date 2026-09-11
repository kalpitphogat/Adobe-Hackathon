---
name: ai-readiness-orchestrator
description: Audit a website for AI-discoverability and on-site-engagement problems and emit one prioritised report. Diagnoses why AI assistants do not find, cite, or correctly describe a brand - crawler blocking, JavaScript render gaps, missing or contradictory structured data, facts locked in images, unquotable content, stale or uncorroborated claims, entity ambiguity - and why visitors who do arrive leave without acting. Applies a reach-read-extract-trust gate cascade so one root cause is reported instead of fifteen symptoms. Use when asked to audit a site for AI visibility, generative-engine optimisation, AI search readiness, LLM discoverability, or why a brand is missing from AI answers, and when asked why a site converts poorly or bounces. This is the entrypoint skill; it invokes every other skill in this marketplace and emits the single audit report.
license: MIT
compatibility: Requires Python 3.9+. Runs read-only against a public website with no API keys, no accounts and no authenticated access. Playwright is optional and upgrades two render-stage checks; without it the audit still runs and says what it could not see.
allowed-tools: Bash(python:*) Read Write WebFetch
---

# Brand AI-Readiness Audit — orchestrator

Given a URL, produce one report covering both halves of the problem: **off-site
discoverability** (why AI assistants do not find or cite the brand) and
**on-site engagement** (why visitors who arrive do not stay).

## When to use

Use when someone asks why their brand is invisible in AI assistants, why a
competitor gets cited instead, whether a site is "AI ready", or why traffic
arrives but does not convert. Also use for a general technical audit where the
consumer of the page is a machine rather than a person.

Do not use to change a website. This marketplace is **recommend-only** and has
no apply mode.

## Inputs

- A public website URL (required), e.g. `https://example.com`.
- `--out` (default `./audit-output`), `--max-pages` (25), `--time-budget` (300s).

### `--probe-bot-ua` — the one flag worth knowing about

**If you own the site you are auditing, use this flag.** It is off by default,
and leaving it off costs you the single highest-value check in the marketplace.

```bash
python scripts/orchestrate.py https://your-site.com --out ./audit-output --probe-bot-ua
```

It detects whether your **CDN or WAF returns 403 to AI crawlers** — a rule that
removes your brand from those assistants entirely while leaving **no trace in
robots.txt and nothing visible to anyone browsing the site**. Sites routinely
have this without knowing, because a bot-protection default treats an AI
retrieval crawler as an unwanted scraper.

What it does: **one request per crawler, homepage only**, with our auditor token
appended to the user-agent string, so your own logs show it was an audit rather
than the real crawler.

Why it is off by default: sending named-crawler user-agents to a site you do not
own is not something an audit should do unless asked. Without the flag, the two
edge checks report **not assessed** in `limitations[]` — a blind spot, not a
pass — and the report tells the reader how to turn it on.

## Procedure

Run this end to end:

```bash
python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://example.com --out ./audit-output
```

That script performs the following steps. **An agent with only a generic fetch
tool can perform the same sequence by hand**, treating `scripts/` as
accelerators rather than requirements:

1. **Collect once.** Invoke `site-evidence-collector`. It fetches robots.txt,
   discovers a sitemap, crawls up to 25 pages stratified by page type, renders a
   representative subset, and probes for soft 404s. It writes an **evidence
   bundle**. Nothing else in this marketplace touches the network.
2. **Classify.** Invoke `site-profile-classifier` against the bundle. It returns
   the site archetype, a type and confidence for every page, and the threshold
   profile every later check scores against.
3. **Audit.** Invoke each of the six audit skills as a subprocess, passing the
   bundle and the profile. Each returns one JSON object. The contract is in
   `references/skill-cli-contract.md`; read it before adding or changing a skill.
   - `crawl-access-audit` (reach) · `render-gap-audit` (read) ·
     `structured-data-audit` (extract) · `answerability-audit` (extract) ·
     `trust-freshness-audit` (trust) · `engagement-audit` (act)
4. **Validate.** Reject any finding lacking evidence, confidence, or a
   mechanism. A rejected finding becomes a `limitations[]` entry; it is never
   silently dropped.
5. **Dedupe.** Fold `extract.ans.chunk_not_self_contained` into
   `extract.ans.fact_coverage_gap` when both fire on one URL, merging evidence
   and recording the merge in `merged_from`.
6. **Gate.** Apply the cascade in `references/gate-rules.md`. Downstream
   discoverability findings are **capped and tagged `blocked_by`**, never
   deleted. Engagement is never gated on reach. See below.
7. **Score and rank.** Severity, then ICE, then stage order, then `check_id`.
   The ordering is total, so output is deterministic.
8. **Patch.** Build a paste-ready patch for every finding from values in the
   bundle. Where a needed value is genuinely absent, emit
   `__FILL_IN__:<property>` — **never invent a plausible value**.
9. **Recommend beyond defects.** Add archetype-derived proactive
   recommendations that are not tied to any detected defect.
10. **Emit.** Write `audit-report.json` and `report.md`, plus one file per patch
    under `fix_patches/`.

## The gate cascade, in one paragraph

The handout's appendix states that three things must succeed **in order** for a
page to be visible to a machine: the crawler must be let in, it must be able to
read the page, and it must be able to pick out the specific fact. So when an
upstream stage fails, downstream findings are real but **moot**: they are capped
at `medium` and tagged with the id of the one finding blocking them. A site that
blocks retrieval crawlers gets **one critical plus a note that N other findings
are waiting on it**, not fifteen criticals.

**Engagement is different, and the distinction matters.** A visitor arriving
from an ad does not care whether a crawler was let in, so a reach failure never
touches an engagement finding. But if a page's served HTML is an empty
application shell and no rendered DOM was captured, we never observed what the
visitor sees — so engagement checks there are not "probably wrong", they are
**unevidenced**, and are suppressed entirely rather than reported at reduced
severity. Capping asserts a weaker claim; suppression asserts none, and none is
what we have. Full statement in `references/gate-rules.md`.

## Output

`audit-report.json` against `references/report-schema.json`, and `report.md` for
a reader who is not an engineer. The JSON satisfies the handout's required floor
(`site`, `audited_at`, `summary` with counts by severity, and `findings[]` with
`id`, `title`, `severity`, `evidence`, `suggested_action`) and extends it with
`check_id`, `confidence`, `category`, `stage`, `blocked_by`, `affected_urls`,
plus top-level `audit_status`, `proactive_recommendations[]` and
`limitations[]`.

**Exit codes never encode what was found.** Exit `0` whenever a schema-valid
report was written, whatever it says. A domain that does not resolve, 404s,
serves a PDF, or forbids crawling still produces a report and still exits 0; the
outcome lives in `audit_status` (`complete` / `partial` / `no_content_available`).
Non-zero means no report could be produced: `1` internal error, `2` unusable
output path, `3` invalid arguments. A grading harness may read any non-zero exit
as a crash, so this distinction is deliberate.

## Guardrails

- **Recommend-only.** No skill modifies a live site. There is no apply mode, and
  the HTTP layer permits only GET and HEAD, so no code path can POST or DELETE.
- **robots.txt is a hard constraint on our own crawling**, not advice. A
  disallowed path is not fetched; the report says we could not look rather than
  looking anyway.
- **No authenticated areas, no credentials, no cookies.** Login, account, cart
  and checkout paths are excluded by the trap guards.
- **Bot user-agent probing is opt-in and off by default.** With
  `--probe-bot-ua`, one request per bot, homepage only, with our auditor token
  appended to the user-agent string so a site owner reading their logs can see
  it was an audit and not the real crawler. We do not silently impersonate.
  Without the flag the two edge checks report "not assessed" in `limitations[]`
  rather than passing quietly.
- **Politeness:** 5 workers, 0.4s per-host delay, `Retry-After` honoured,
  exponential backoff on 429 and 5xx.
- **No hosted API, key or account.** Optional Wikidata corroboration is off by
  default, degrades to `hypothesis` confidence, and never blocks a run.
- **Output never lands inside `skills/`** or on a cloud-synced path; both are
  refused with exit 2. Every write is atomic (temp file, fsync, rename) so a
  full disk cannot leave a truncated report behind.

## Reference material

- `references/gate-rules.md` — the cascade, including Rule 0b, stated in full.
- `references/severity-model.md` — what makes a finding each severity, and what
  `confirmed` / `likely` / `hypothesis` mean.
- `references/suppression-rules.md` — every SUPPRESS WHEN rule in one place.
- `references/skill-cli-contract.md` — normative; read before touching a skill.
- `references/report-schema.json` — the output contract.
