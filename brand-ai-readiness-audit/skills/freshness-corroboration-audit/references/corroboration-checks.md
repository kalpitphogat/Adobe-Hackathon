# Freshness & corroboration check catalog

Round-2 appendix D: machines trust facts that are **current** and **agreed-upon across
independent sources**, and get confused by **shared names** (mistaken identity).

## Checks
| # | Check | Signal | Severity |
|---|-------|--------|----------|
| 1 | Stale copyright/date | visible `© YYYY` older than last year | medium |
| 2 | No machine-readable dates | article/blog pages with no `<time>`/datePublished/dateModified | medium |
| 3 | Weak corroboration | homepage has no `sameAs`/external identity links | medium |
| 4 | No identity statement | no about/who-we-are text on homepage | low |
| 5 | Unattributed superlatives | >=3 "best/#1/world-leading" claims with no cited source | low |

## Why off-site agreement matters
A claim that lives in only one place (the brand's own site) is fragile; the same claim
repeated consistently across unrelated, independent sources is far more likely to be
believed and repeated back by an assistant. This skill can only see the brand's own
pages, so it audits the **on-site hooks** for corroboration — chiefly `sameAs` links to
authoritative external profiles (Wikidata, LinkedIn, Crunchbase, industry directories,
press) — and recommends establishing consistent, agreeing descriptions off-site.

## Mistaken identity
When several entities share a name, a system mixes them up unless something clearly
distinguishes one. Fixes: an explicit identity statement, Organization JSON-LD with
`sameAs`, and consistent naming/description everywhere the brand appears.

## Freshness
Stale copyright years and undated articles signal abandonment and prevent recency
ranking. Surface a visible "last updated" date and machine-readable `dateModified` on
anything time-sensitive.

## False-positive guards
- Copyright check ignores years in the future and pre-2001 noise, and takes the first
  match per page.
- Superlative check stays `low` — it flags a pattern to review, not a certain defect.
