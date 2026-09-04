---
name: freshness-corroboration-audit
description: >-
  Audit whether a site's facts are current and cross-verifiable, since machines
  trust facts that are fresh and consistently agreed-upon across independent sources.
  Detects stale copyright/last-updated years, article and blog pages with no
  machine-readable publish date, weak entity corroboration (identity that lives only
  on the brand's own site, no sameAs), missing about/identity statements that create
  name-collision risk, and unattributed superlative claims. Use in the
  brand-ai-readiness-audit marketplace to explain why an assistant distrusts, ignores,
  or confuses a brand's facts.
license: MIT
allowed-tools: [Bash, Read]
---

# Freshness & Corroboration Audit

## When to use
Round-2 appendix D: machines treat a fact as more trustworthy when it is current and
when many independent sources agree; a single-source or stale claim is fragile, and
shared names cause mistaken identity.

## Inputs
The shared cache directory (uses cached text + raw HTML).

## Procedure
Run `scripts/check_freshness.py <cache_dir>`. It reports:
1. **Stale copyright / dates** — footer/copyright year more than a year old (medium).
2. **No machine-readable dates** on article/blog pages (no `<time>`, datePublished,
   dateModified) (medium).
3. **Weak entity corroboration** — no `sameAs`/external identity links tying the brand
   to independent sources (medium).
4. **No clear about/identity statement** distinguishing the brand from same-named
   entities (low).
5. **Unattributed superlatives** — strong marketing claims with no third-party backing
   (low).

See `references/corroboration-checks.md` for the reasoning and how off-site agreement
shapes what assistants repeat.

## Output
Envelope `{ "skill": "freshness-corroboration-audit", "findings": [ … ] }` merged by the
orchestrator.

## Guardrails
Read-only; on-page signals only — it does not fetch or probe third-party sites, it
recommends where corroboration should exist.
