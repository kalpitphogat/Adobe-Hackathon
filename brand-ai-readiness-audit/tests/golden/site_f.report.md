# AI-readiness audit — devtools-forge.test

*Audited 2026-05-28T20:26:40Z · status: **complete***

*Evidence basis: **4 page(s) fetched**, 3 rendered. Every finding below applies only to the URLs it lists. Pages this crawl did not fetch were not assessed — absence of a finding for a page is not a pass for it.*

## What to do first

No actionable defects were found at or above low severity.

## Summary

| Severity | Count |
|---|---|
| critical | 0 |
| high | 0 |
| medium | 0 |
| low | 0 |
| info | 0 |
| **total** | **0** |

Discoverability 0 · engagement 0.

## Worth doing even though nothing is broken

### P-001 · Consider serving a Markdown representation of documentation pages

A request for https://devtools-forge.test/ with Accept: text/markdown returned content-type text/html. Agents that consume documentation handle Markdown with less loss than HTML, because there is no navigation chrome to strip. This is an ergonomics improvement for agent readers, with no evidence of a retrieval or ranking effect, which is why it is a recommendation and not a finding.

### P-002 · Mark up your how-to and reference pages as HowTo or TechArticle

This is a docs site with valid structured data already in place. Typing procedural pages specifically as HowTo or TechArticle, rather than generically, tells a consumer that the page contains ordered steps, which is what a how-do-I question needs.

## What this audit could not assess

- **site** — Edge and CDN reachability for named AI crawlers was not assessed, because --probe-bot-ua was not set. This is the highest-value check in this marketplace: a CDN or WAF rule that returns 403 to OAI-SearchBot, PerplexityBot or Claude-SearchBot removes a brand from those assistants entirely, and leaves no trace in robots.txt or in what a human sees. If you own this site, re-run the orchestrator with the --probe-bot-ua flag:
    orchestrate.py <url> --out ./audit-output --probe-bot-ua
That sends ONE request per crawler, to the homepage only, with an auditor token appended to the user-agent string so it is identifiable in your logs. It is off by default because sending named-crawler user-agents to a site you do not own is not something an audit should do without being asked.
  - Checks not run: reach.edge.bot_ua_blocked, reach.edge.bot_ua_challenged
- **audit environment** — 2 check(s) were not assessed in this run, because an optional capability was unavailable (such as a headless browser or an opt-in probe) or the page carried too little evidence to judge. These are limits on what this run could evaluate, not defects of the site: `reach.edge.bot_ua_blocked`, `reach.edge.bot_ua_challenged`

## Deliberately not reported

Findings other tools would raise that we suppressed, and why:

- `act.blocker.load_time_interstitial` ×1 — suppressed by design
- `act.trust.no_cost_signal` ×1 — suppressed by design
- `extract.ans.no_direct_answer_block` ×1 — suppressed by design
- `extract.ans.no_evidence_markers` ×1 — suppressed by threshold
- `extract.sd.absent_on_eligible_page` ×1 — suppressed by design
- `reach.agent.llms_txt_absent` ×1 — not applicable
- `trust.entity.name_collision` ×1 — suppressed by design
- `trust.entity.no_external_corroboration` ×1 — suppressed by design

---

*brand-ai-readiness-audit 1.0.0 · 0 of 66 checks ran · AI crawler list snapshot 2026-09-09 (commit 0e111dcc24cb) · recommend-only: nothing was written to the audited site.*
