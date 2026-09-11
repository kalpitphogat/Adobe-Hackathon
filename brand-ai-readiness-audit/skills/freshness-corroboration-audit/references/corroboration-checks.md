# Freshness & corroboration check catalog

Mechanism 4's trust half: a fact is treated as more reliable when it is **current** and
when **independent sources agree**. This skill audits what the site itself says about
both, and nothing else.

## The claim boundary — read this first

This audit queries **no external source**. There is no search, no Wikidata lookup, no
social-platform check. Therefore only one of the following four situations is observable
here, and the other three must never be asserted:

| Situation | Can this skill observe it? |
|-----------|---------------------------|
| (a) no `sameAs` found in the homepage markup | **yes** |
| (b) external sources describing the brand exist | no |
| (c) external sources disagree with the site | no |
| (d) the brand's identity is genuinely ambiguous | no |

So the evidence reads:

> "The homepage's server HTML was searched for a sameAs property in its structured data,
> and none was found."

and explicitly **not**:

> ~~"No external corroboration exists."~~
> ~~"The brand's identity lives only on this site."~~

Every corroboration finding carries a `not_verified` line stating that no external source
was queried. If a future version does query external sources, it must report which
sources were checked and whether they agreed — and only then may it speak to (b), (c) or
(d).

## Checks

| # | Check | Trigger | Band |
|---|-------|---------|------|
| 1 | Stale copyright year | most recent `© YYYY` in page text is more than one year old | low (improvement) |
| 2 | Undated articles | pages **confidently classified as articles** with no `<time>`, `datePublished`, `dateModified` or `article:published_time` | medium (defect, material) |
| 3 | No sameAs declared | homepage structured data contains no `sameAs` | low (improvement) |
| 4 | Unattributed superlatives | ≥3 matched superlative phrases across the sampled pages | low (improvement, confidence low) |

## Why check 2 is the only defect here

Recency is a genuine input when sources make competing claims, and a page with no
declared date cannot be placed on a timeline except by guessing from its text. That is a
measurable, material gap. It runs only for pages confidently classified as articles — a
URL containing "/blog" is not, on its own, treated as an article, which was a v1
false-positive source.

## What the freshness check does not claim

A stale footer year says nothing directly about whether the page's **content** is out of
date, which this audit does not assess. The finding says so. The fix recommended is to
render the year from the current date and to surface a real last-reviewed date where
facts change — not to pretend the content is fresh by updating a number.

## False-positive guards

- The copyright check takes the **most recent** year found on a page, ignores years in the
  future and pre-2001 noise, so a cited historical date cannot make a maintained page look
  abandoned.
- The superlative check matches phrases only, and states in its own evidence that whether
  each claim is attributed in its surrounding context was **not** determined. It is
  low-confidence, which caps it at low severity.
- The v1 "no about statement" check was removed. It searched the raw HTML for the string
  "about", which every navigation bar contains, so it was a dead check that could only
  ever mislead.
