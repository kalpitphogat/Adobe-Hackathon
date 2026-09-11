---
name: freshness-corroboration-audit
description: >-
  Audit whether a site's facts are current and whether its entity identity is stated
  in a way external sources can be connected to. Detects copyright years more than a
  year out of date, article pages with no machine-readable publication date, absence
  of sameAs relationships in homepage structured data, and superlative claims with no
  named source. Strictly bounded in what it may claim: it inspects the site's own
  markup and text and queries no external source, so it never concludes that a brand
  lacks external corroboration — only that the homepage does or does not declare any.
  Use in the brand-ai-readiness-audit marketplace to explain why a consumer might
  distrust, mis-date, or confuse a brand's facts.
license: MIT
allowed-tools: [Bash, Read]
---

# Freshness & Corroboration Audit

## When to use
The trust half of mechanism 4: a fact is treated as more reliable when it is current and
when independent sources agree. This skill covers what the **site itself** says about
both.

## The claim boundary
This audit queries **no external source**. Therefore:

- It may say: "No sameAs relationships were detected in the homepage structured data."
- It may **not** say: "No external corroboration exists", or "the brand's identity lives
  only on this site."

Four distinct situations are not interchangeable: (a) no sameAs found, (b) external
sources found, (c) external sources disagree, (d) identity genuinely ambiguous. This
skill can only ever observe (a), and every corroboration finding carries a
`not_verified` line saying that no external source was queried.

## Inputs
The shared cache directory. HTML pages only.

## Procedure
Run `scripts/check_freshness.py <cache_dir>`.

1. **Stale copyright year** — an improvement. The evidence states that a footer year says
   nothing directly about whether the content is current, which was not assessed.
2. **Undated articles** — only for pages confidently classified as articles; a URL
   containing "/blog" is not on its own treated as an article. A real defect, because
   recency is an input when sources make competing claims.
3. **No sameAs on the homepage** — a low improvement, with the claim boundary above
   stated inside the finding.
4. **Unattributed superlatives** — a low improvement at low confidence, with the explicit
   note that whether each claim is attributed in its surrounding context was not
   determined.

## Output
Envelope `{ "skill": "freshness-corroboration-audit", "findings": [...], "skipped_checks": [...] }`.

## Guardrails
Read-only, cache-only, no external lookups. Reports what was inspected, never what it
might have found had it looked further.
