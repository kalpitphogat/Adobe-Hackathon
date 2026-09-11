---
name: trust-freshness-audit
description: Determine whether a machine would believe what a page says. Checks that dated content carries a date, that schema dates, visible dates, sitemap lastmod and the Last-Modified header agree, and that pages asserting time-sensitive facts such as prices or opening hours have been updated within a sensible window. Also checks entity identity: whether a brand name collides with common words without a disambiguating descriptor, whether name, address and phone are consistent across the site, whether anything links the site to an independent record of the same entity, and whether articles are attributed. Use when AI assistants confuse a brand with something else, repeat stale facts about it, or decline to cite it despite good content, or as the trust stage of a full AI-readiness audit.
license: MIT
compatibility: Python 3.9+ standard library only. htmldate improves visible-date extraction and an optional Wikidata lookup can corroborate identity; both are off or absent by default, and the run never depends on either.
allowed-tools: Bash(python:*) Read
---

# trust-freshness-audit — stage: trust

**One question: would a machine believe this?**

Reaching, reading and extracting a fact is not enough. The handout appendix puts
it plainly: a claim that lives in only one spot is fragile, and when several
things share a name a system can mix them up unless something distinguishes one
from the others.

## When to use

When a brand is confused with something else, when assistants repeat outdated
facts, or as the trust stage of a full audit.

## Inputs

```bash
python scripts/run.py --bundle ./evidence --profile ./profile.json
```

## Procedure

1. For each page, gather every date signal: schema `datePublished` and
   `dateModified`, a visible date in the first 600 characters, the sitemap
   `lastmod`, and the `Last-Modified` header. Parse ISO, long-form and HTTP
   date formats.
2. Compare the signals. A spread beyond a small tolerance means the page states
   several different dates, and a reader has no basis to choose between them.
3. Where a page contains time-sensitive language, compare its newest date signal
   against the archetype staleness window.
4. Derive the brand name from schema, then title. Check it against a list of
   terms that collide with many unrelated entities, and look for a
   disambiguating descriptor within ten words of the name.
5. Collect every address and phone number across the site, normalised, and
   report genuine variants.
6. Read the homepage `sameAs` links and count how many point at an independent
   identity source.

## Checks

| check_id | detects | default severity |
|---|---|---|
| `trust.date.absent_on_dated_content` | an article or docs page with no date anywhere | medium |
| `trust.date.signals_disagree` | date signals conflict beyond tolerance | medium |
| `trust.date.stale_volatile_facts` | time-sensitive claims on a long-unmodified page | medium |
| `trust.entity.name_collision` | an ambiguous brand name with no descriptor near it | medium |
| `trust.entity.nap_inconsistent` | the site states more than one address or phone for itself | medium |
| `trust.entity.no_external_corroboration` | nothing links the site to an independent record | medium |
| `trust.authorship.unattributed` | articles naming no author | low |
| `trust.integrity.prompt_injection` | text phrased as an instruction to an AI reader (often in HTML comments or hidden nodes) | critical |
| `trust.integrity.cloaked_text` | many elements hidden from view via CSS while remaining in the served HTML (cloaking) | medium |
| `trust.integrity.invisible_unicode` | runs of zero-width or bidi-control code points in the extracted text | medium |

### A confidence ceiling that matters

`trust.entity.no_external_corroboration` can **never** reach `confirmed`.
Absence of corroboration cannot be proven from one site: we can observe that a
site declares no sameAs links and cites no external sources, but we cannot
observe that nobody else mentions it. The finding says what we saw, not what
exists, and its confidence is capped at `likely`, dropping to `hypothesis` when
the optional Wikidata cross-check is unavailable.

### SUPPRESS WHEN

- `trust.date.absent_on_dated_content` — the page type is not article or docs.
  A homepage, product or contact page is not expected to carry a date.
- `trust.date.signals_disagree` — the spread is two days or less, which is
  publishing lag rather than disagreement; or only one signal exists, in which
  case there is nothing to disagree with.
- `trust.date.stale_volatile_facts` — no date signal exists at all, in which
  case `trust.date.absent_on_dated_content` applies instead; or the page is
  within the archetype staleness window.
- `trust.entity.name_collision` — a descriptor appears within ten words of the
  name, or a schema `description` supplies one; or the name is several tokens
  long and distinctive.
- `trust.entity.nap_inconsistent` — variants differ only by formatting. Phone
  numbers are compared on digits alone and addresses on collapsed whitespace, so
  punctuation and abbreviation differences never count as inconsistency. Also
  suppressed when too few pages were crawled to judge and the archetype does not
  require NAP consistency.
- `trust.entity.no_external_corroboration` — at least two `sameAs` links point
  at independent identity sources such as Wikipedia, Wikidata, Companies House,
  LinkedIn or GitHub.
- `trust.authorship.unattributed` — the archetype is e-commerce or SaaS
  marketing, where corporate rather than personal authorship is idiomatic and an
  unattributed page is not a defect.

## Output

One JSON object on stdout. Exit 0 ran, 3 precondition unmet, 1 internal error.

## Agent mode

Every step is reproducible by hand from the bundle. The optional Wikidata
lookup is the only networked element and is off by default; without it, report
corroboration findings at `hypothesis` confidence.

## Reference material

`references/corroboration-model.md` — why cross-source agreement matters, and
precisely what can and cannot be established from a single site.

## Guardrails

Read-only. No network by default. The optional Wikidata lookup, when explicitly
enabled, is a single read-only query and never blocks the run: on any failure
the check degrades to `hypothesis` and the audit continues.
