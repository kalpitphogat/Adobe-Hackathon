---
name: crawl-access-audit
description: >-
  Audit whether an automated crawler — especially the AI-assistant fetchers
  (GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended) — is even
  allowed to reach and index a site. Checks robots.txt presence and AI-bot
  allow/deny rules, XML sitemap discovery, per-page HTTP status, meta-robots and
  X-Robots-Tag noindex, robots Disallow coverage, canonical hygiene, and HTTPS.
  Use as part of the brand-ai-readiness-audit marketplace to explain why a brand is
  never crawled or indexed in the first place.
license: MIT
allowed-tools: [Bash, Read]
---

# Crawl & Access Audit

## When to use
The first of the three discoverability gates (Round-2 appendix A): *the crawler has to
be let in*. If access fails, the page effectively does not exist for that system, no
matter how good the content is.

## Inputs
A shared cache directory produced by the orchestrator's `crawler.py`.

## Procedure
Run `scripts/check_access.py <cache_dir>`. It inspects `meta.json` + cached raw HTML and
reports findings for:
1. Missing robots.txt.
2. AI-assistant crawlers explicitly blocked in robots.txt (critical for the major
   fetchers; high for others).
3. No discoverable XML sitemap.
4. `noindex` via meta-robots or `X-Robots-Tag` (critical on the homepage).
5. Public pages Disallow'd in robots.txt.
6. 4xx/5xx error pages.
7. No `rel=canonical` anywhere.
8. Site served over HTTP.

See `references/crawl-checks.md` for the full check catalog and severity logic.

## Output
An envelope `{ "skill": "crawl-access-audit", "findings": [ … ] }` where each finding has
`title, severity, category, evidence, suggested_action{summary,priority}` (and `checked`).
The orchestrator merges these into the final report.

## Guardrails
Read-only; operates entirely on the pre-fetched cache. Never fetches authenticated or
disallowed URLs; simply reports on them.
