---
name: engagement-audit
description: >-
  Audit the on-site engagement half of the problem: once a visitor arrives, will they
  stay? Checks for a mobile viewport meta tag, oversized HTML documents and slow server
  responses (proxies for load time and bounce), a clear call-to-action / next step on
  key pages, sufficient internal navigation for orientation, and intrusive
  interstitials or autoplay media. Use in the brand-ai-readiness-audit marketplace to
  explain why visitors who do reach the site leave without engaging.
license: MIT
allowed-tools: [Bash, Read]
---

# On-Site Engagement Audit

## When to use
The engagement half of the Round-2 problem: getting cited brings visitors, but poor
orientation, slow/heavy pages, no clear next step, or intrusive pop-ups make them
bounce before they engage.

## Inputs
The shared cache directory (uses `meta.json` metrics + cached raw HTML).

## Procedure
Run `scripts/check_engagement.py <cache_dir>`. It reports:
1. **Missing mobile viewport** meta tag (high if sitewide).
2. **Heavy documents / slow responses** — >2MB HTML or >3s fetch (medium).
3. **No clear call-to-action** on the majority of pages (medium).
4. **Sparse internal navigation** — very few links to explore (low).
5. **Intrusive interstitials / autoplay** signals (low).

See `references/engagement-checks.md` for thresholds and the engagement rationale.

## Output
Envelope `{ "skill": "engagement-audit", "findings": [ … ] }` merged by the
orchestrator. These findings are tagged `dimension: engagement` in the final report.

## Guardrails
Read-only; measures cached responses only. Page-weight/latency are first-response
proxies for real-user metrics (LCP/TTFB), not a substitute for field data.
