---
name: crawl-access-audit
description: Determine whether an AI crawler can reach a site at all. Checks robots.txt against a dated snapshot of AI crawler user agents, classifying each blocked bot as retrieval, training-only, or dual-purpose so that a deliberate content-licensing choice is not reported as a defect. Also checks CDN and WAF reachability for named AI crawlers, noindex directives, canonical conflicts, redirect chains, soft 404s, broken internal links, transport security, response latency, sitemap validity, and agent-facing files such as llms.txt. Use when diagnosing why a site is absent from AI assistants or search results, when robots.txt or crawler access is in question, or as the reach stage of a full AI-readiness audit.
license: MIT
compatibility: Python 3.9+ standard library only. Reads an evidence bundle; performs no network I/O of its own. Optional Protego cross-checks the bundled RFC 9309 matcher but is never required.
allowed-tools: Bash(python:*) Read
---

# crawl-access-audit — stage: reach

**One question: can an AI crawler get in at all?**

This is the first of the three steps that must succeed in order. If a crawler is
refused here, nothing downstream matters: no amount of structured data or
content quality reaches a system that never received the page.

## When to use

As the reach stage of an audit, or standalone when robots.txt, CDN rules, or
indexability are in question.

## Inputs

- `--bundle <dir>` (required) — an evidence bundle from `site-evidence-collector`.
- `--profile <file>` (optional) — the profile from `site-profile-classifier`.
  Without it, default thresholds apply.

```bash
python scripts/run.py --bundle ./evidence --profile ./profile.json
```

## Procedure

An agent without Python can perform every step by reading the bundle directly.

1. Read `robots.txt` from the bundle verbatim. Parse it into groups per RFC 9309
   §2.2.1: consecutive `User-agent` lines accumulate into one group, and the
   first rule line closes the agent list.
2. For each bot in `references/ai-bots.json`, find its matching group (longest
   matching product token wins; the wildcard group is the fallback and is never
   merged with a specific group). Evaluate `/` and each crawled path with
   longest-pattern-wins matching, `*` and trailing `$`, Allow winning ties.
3. **Classify every blocked bot by category, not by name.** This is the step
   that separates this skill from a flat checklist. A blocked retrieval crawler
   is a critical defect. A blocked training crawler is a licensing decision.
4. Read `probes.json` for `bot_reach`, `llms_txt`, `soft_404` and
   `ttfb_samples_ms`. If `bot_reach.enabled` is false, record both edge checks
   as *not assessed* — this is a real blind spot, not a clean result.
5. Read `pages.jsonl` for `meta_robots`, `x_robots_tag`, `canonical`,
   `redirect_chain`, `status` and `links.internal`, and `sitemap.json` for
   coverage.
6. Emit one JSON object per `ai-readiness-orchestrator/references/skill-cli-contract.md`.

## Checks

Bot classification comes from `references/ai-bots.json`, which carries a
`snapshot_date` and the upstream commit; both are printed in every report,
because bot names churn and a dated list is more honest than a confident one.

| check_id | detects | default severity |
|---|---|---|
| `reach.robots.ai_search_bot_blocked` | robots.txt disallows a retrieval crawler that cites sources at answer time | critical |
| `reach.robots.blanket_disallow` | wildcard `Disallow: /` with no narrower re-allow | critical |
| `reach.robots.ai_training_bot_blocked` | training-only crawlers blocked | **info** |
| `reach.robots.dual_purpose_bot_blocked` | a contested crawler blocked, e.g. Google-Extended | medium |
| `reach.robots.unparseable` | non-200, HTML body, or unparseable directives | medium |
| `reach.robots.crawl_delay_excessive` | a Crawl-delay that starves crawlers of a site this size | medium |
| `reach.edge.bot_ua_blocked` | CDN or WAF refuses a named AI crawler that a browser is served | critical |
| `reach.edge.bot_ua_challenged` | bot receives 200 with a challenge interstitial instead of content | high |
| `reach.sitemap.absent_or_invalid` | no valid XML sitemap | medium |
| `reach.sitemap.coverage_gap` | sitemap omits much of the site, or lastmod carries no information | low |
| `reach.index.noindex_on_content` | noindex on a content page, via meta or header | critical |
| `reach.index.canonical_conflict` | canonical points off-domain, at a 4xx, or reciprocally | high |
| `reach.index.redirect_chain_or_loop` | more than two hops, or a cycle | medium |
| `reach.http.soft_404` | HTTP 200 for URLs that cannot exist | medium |
| `reach.http.broken_internal_links` | internal links into 4xx or 5xx | medium |
| `reach.http.insecure_or_mixed_scheme` | invalid TLS, or content served over plain http | high |
| `reach.perf.slow_median_ttfb` | median time to first byte above the profile threshold | low |
| `reach.agent.llms_txt_absent` | no llms.txt on an agent-facing site | **low** |

### SUPPRESS WHEN

- `reach.robots.ai_search_bot_blocked` — no retrieval-classified bot is
  disallowed, or the bot sits in an Allow-dominant group under longest-match.
- `reach.robots.blanket_disallow` — a narrower Allow re-admits content, or
  robots.txt is non-200 (then `unparseable` applies instead).
- `reach.robots.ai_training_bot_blocked` — **capped at info and never
  escalated.** Blocking GPTBot or CCBot does not reduce whether a brand is found
  or cited: training-corpus collection and answer-time retrieval are separate
  pipelines with separate user-agent tokens. Reported so the choice is visible,
  not because it is wrong. Omitted entirely when no retrieval bot is also blocked.
- `reach.robots.dual_purpose_bot_blocked` — reported as a contested trade-off,
  never as an error, with the contestedness stated in the finding text.
- `reach.robots.unparseable` — a 404 robots.txt is permissive and correct.
- `reach.robots.crawl_delay_excessive` — the directive reaches only agents we do
  not classify as retrieval-relevant. Crawl-delay is not in RFC 9309: Bing and
  Yandex honour it, Google ignores it, so setting it for Bingbot is a supported
  choice and not a mistake.
- `reach.edge.bot_ua_blocked` / `reach.edge.bot_ua_challenged` — `--probe-bot-ua`
  was not set (recorded as *not assessed*), or the browser baseline is refused
  too, meaning the site refuses everyone rather than targeting bots.
- `reach.sitemap.absent_or_invalid` — fewer than 15 pages discovered.
- `reach.sitemap.coverage_gap` — no sitemap at all, or omissions are all utility
  or paginated URLs.
- `reach.index.noindex_on_content` — the page type is utility, checkout, cart,
  login, search-results or thank-you, where noindex is correct.
- `reach.index.canonical_conflict` — the canonical is self-referential.
- `reach.index.redirect_chain_or_loop` — exactly one hop, or scheme and www
  normalisation.
- `reach.http.soft_404` — probes return 404 or 410. If the probe body is
  identical to the real 404 body, only the status code is wrong, so it is
  downgraded to low rather than overstated.
- `reach.http.broken_internal_links` — below both the rate floor and the count
  floor. A handful of stale links is maintenance, not a discoverability defect.
- `reach.perf.slow_median_ttfb` — **fewer than three samples.** This check never
  fires on a single measurement and always reports the median, never the maximum.
- `reach.agent.llms_txt_absent` — the archetype is not docs or
  developer-platform, in which case it is **not surfaced at all**. Where it does
  fire it is LOW, and the finding carries the reasoning: Google Search Central
  states plainly that machine-readable AI text files are not used by Google
  Search and neither help nor harm visibility, no major assistant provider has
  publicly committed to consuming llms.txt at answer time, and SE Ranking's
  analysis of nearly 300,000 domains measured 10.13% adoption with no
  correlation to AI citations. Most audit tools score this as high severity; we
  say why we do not.

## Output

One JSON object on stdout. Exit 0 ran, 3 precondition unmet, 1 internal error.

## Guardrails

Read-only. Performs no network I/O — every observation comes from the bundle.
The bot list is a bundled dated snapshot and is never fetched at runtime, so the
marketplace resolves with no external service.
