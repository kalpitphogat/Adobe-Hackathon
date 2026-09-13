# AI-readiness audit — members-only.test

*Audited 2026-05-28T20:26:40Z · status: **no_content_available***

> **No page content could be assessed.** See Limitations below for why. 
> The findings that follow are limited to what could be observed without page content.

## What to do first

**F-001 · CRITICAL** — robots.txt forbids every crawler from the entire site

- **Do:** Replace the site-wide Disallow with rules that exclude only genuinely private paths.
- **Why it works:** A crawler that is refused at robots.txt never requests the page, so no amount of on-page quality can compensate; this is the first of the three steps that must succeed in order.
- **Effort:** low · **ICE:** 9.3
- **Verify:** `curl -s https://members-only.test/robots.txt | grep -A5 'User-agent: \*'`


## Summary

| Severity | Count |
|---|---|
| critical | 1 |
| high | 0 |
| medium | 0 |
| low | 0 |
| info | 0 |
| **total** | **1** |

Discoverability 1 · engagement 0.

## Reach — can a crawler get in?

### F-001 · CRITICAL · robots.txt forbids every crawler from the entire site

*confidence: confirmed · check: `reach.robots.blanket_disallow`*

**Evidence.** robots.txt at https://members-only.test/robots.txt contains a wildcard group with "Disallow: /" on line 2 and no narrower Allow rule that re-admits content. Every crawler, including every AI retrieval bot, is excluded from all 1 discovered paths. This auditor honoured it and fetched no page content.

**Fix.** Replace the site-wide Disallow with rules that exclude only genuinely private paths.

**Why this works.** A crawler that is refused at robots.txt never requests the page, so no amount of on-page quality can compensate; this is the first of the three steps that must succeed in order.

**Patch**

```
User-agent: *
Disallow: /admin/
Disallow: /cart/
Disallow: /checkout/
Allow: /

Sitemap: https://members-only.test/sitemap.xml

```

**Verify**

```
curl -s https://members-only.test/robots.txt | grep -A5 'User-agent: \*'
```

*Source: RFC 9309 section 2.2.2*

## What this audit could not assess

- **site** — Edge and CDN reachability for named AI crawlers was not assessed, because --probe-bot-ua was not set. This is the highest-value check in this marketplace: a CDN or WAF rule that returns 403 to OAI-SearchBot, PerplexityBot or Claude-SearchBot removes a brand from those assistants entirely, and leaves no trace in robots.txt or in what a human sees. If you own this site, re-run the orchestrator with the --probe-bot-ua flag:
    orchestrate.py <url> --out ./audit-output --probe-bot-ua
That sends ONE request per crawler, to the homepage only, with an auditor token appended to the user-agent string so it is identifiable in your logs. It is off by default because sending named-crawler user-agents to a site you do not own is not something an audit should do without being asked.
  - Checks not run: reach.edge.bot_ua_blocked, reach.edge.bot_ua_challenged
- **site** — No page content was collected, so only origin-level policy could be assessed. robots.txt disallows this auditor from fetching the seed URL. robots.txt is a hard constraint on our own crawling, so no page content was fetched. The robots policy itself is still reported.
  - Checks not run: reach.agent.llms_txt_absent, reach.edge.bot_ua_blocked, reach.edge.bot_ua_challenged, reach.http.broken_internal_links, reach.http.insecure_or_mixed_scheme, reach.http.soft_404, reach.index.canonical_conflict, reach.index.noindex_on_content …
- **audit environment** — 11 check(s) were not assessed in this run, because an optional capability was unavailable (such as a headless browser or an opt-in probe) or the page carried too little evidence to judge. These are limits on what this run could evaluate, not defects of the site: `act.perf.above_fold_weight`, `extract.sd.identity_graph_weak`, `reach.edge.bot_ua_blocked`, `reach.edge.bot_ua_challenged`, `reach.perf.slow_median_ttfb`, `read.render.nav_links_js_only`, `read.render.raw_text_gap`, `trust.entity.no_external_corroboration`, `trust.integrity.cloaked_text`, `trust.integrity.invisible_unicode`, `trust.integrity.prompt_injection`

## Deliberately not reported

Findings other tools would raise that we suppressed, and why:

- `act.trust.no_policy_or_contact_path` ×1 — suppressed entirely
- `reach.agent.llms_txt_absent` ×1 — suppressed by design
- `reach.sitemap.absent_or_invalid` ×1 — suppressed by threshold

---

*brand-ai-readiness-audit 1.0.0 · 1 of 65 checks ran · AI crawler list snapshot 2026-09-09 (commit 0e111dcc24cb) · recommend-only: nothing was written to the audited site.*
