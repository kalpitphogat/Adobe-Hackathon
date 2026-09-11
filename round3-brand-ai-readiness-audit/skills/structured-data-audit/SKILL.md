---
name: structured-data-audit
description: Determine whether a page states its facts in a machine-typed form. Extracts JSON-LD, microdata, RDFa and OpenGraph, checks that eligible pages carry structured data at all, that the declared schema.org type matches what the page is about, that JSON-LD parses, that the properties a consumer actually needs are populated, that markup does not contradict the visible page, that the site declares a coherent organisation identity with sameAs links, and that declared hreflang language alternates form a complete, self-consistent cluster. Use when diagnosing why a product, article or business is not represented correctly in AI answers or rich results, or as the extract stage of a full AI-readiness audit.
license: MIT
compatibility: Python 3.9+ standard library only. JSON-LD is parsed exactly; microdata and RDFa are parsed structurally. extruct, when installed, broadens exotic-format coverage but is never required.
allowed-tools: Bash(python:*) Read
---

# structured-data-audit — stage: extract

**One question: is the fact on this page machine-typed?**

Part of the third step. Structured data states a fact in a typed form, so a
consumer can extract it without inferring it from prose it may read differently.

## When to use

As part of the extract stage, or standalone when rich results or AI answers
misrepresent a product, article, or organisation.

## Inputs

```bash
python scripts/run.py --bundle ./evidence --profile ./profile.json
```

## Procedure

1. Flatten every structured-data node on each page from all formats into one
   list of typed nodes with resolvable dotted property paths.
2. Decide **eligibility** before judging absence: utility pages and pages under
   the word floor are not expected to carry markup, and reporting them is the
   most common structured-data false positive.
3. Compare declared types against the expected types for the page type in
   `references/schema-types.json`, accepting documented supertypes.
4. Check required properties on the matching node, honouring the documented
   aliases so a differently-spelled but equivalent property counts as present.
5. Compare schema values against visible page text, normalising currency
   symbols, thousands separators and date formats **before** comparing, so
   formatting differences are never reported as contradictions.
6. Check the homepage identity graph: an Organization, LocalBusiness or Person
   node, its `sameAs` links, and whether any `@id` reference dangles.
7. On pages that **already declare** hreflang alternates, check the cluster is
   internally complete: it names a fallback (an `x-default` or a self-reference)
   and every alternate carries a parseable BCP-47 code. A monolingual page with
   no hreflang is correct and is never reported.

## Checks

| check_id | detects | default severity |
|---|---|---|
| `extract.sd.absent_on_eligible_page` | no structured data of any format on a page that should have it | high |
| `extract.sd.expected_type_missing` | markup present, but not the type the page needs | high |
| `extract.sd.invalid_syntax` | a JSON-LD block does not parse | high |
| `extract.sd.required_props_missing` | a declared type omits the properties that make it useful | medium |
| `extract.sd.contradicts_visible_content` | schema disagrees with the visible page | high |
| `extract.sd.identity_graph_weak` | no organisation identity, no sameAs, or dangling @id references | medium |
| `extract.i18n.hreflang_incomplete` | a declared hreflang cluster lacks a fallback (x-default/self) or names an invalid language code | medium |

Markup that contradicts the page is scored **higher** than markup that is merely
absent, because a consumer that trusts it will state the wrong value. Wrong is
worse than missing.

### SUPPRESS WHEN

- `extract.sd.absent_on_eligible_page` — the page type is login, 404, cart,
  checkout or search-results, **or** main content is under the word floor.
  A thin utility page is not expected to carry markup.
- `extract.sd.expected_type_missing` — the classifier typed the page with
  confidence below 0.6. If we are not sure what kind of page it is, we are not
  sure what type it should declare either. Also suppressed when a documented
  supertype is present.
- `extract.sd.invalid_syntax` — the block parses. Blocks inside `<template>` or
  HTML comments are not evaluated.
- `extract.sd.required_props_missing` — any documented alias supplies the
  property, or the property is supplied through an `@id` that resolves inside
  the page graph.
- `extract.sd.contradicts_visible_content` — the values differ only by
  formatting, or the page shows no comparable value at all, in which case there
  is nothing to disagree with.
- `extract.sd.identity_graph_weak` — an Organization or LocalBusiness node with
  `sameAs` links exists, or a Person node substitutes coherently on a personal
  site.
- `extract.i18n.hreflang_incomplete` — the page declares no hreflang alternates
  at all (a monolingual page is correct, not a defect), or the cluster it does
  declare already carries a fallback and only valid codes.

## Output

One JSON object on stdout, with patches built from values observed on the page.
Where a required value is genuinely absent the patch carries
`__FILL_IN__:<property>` rather than an invented plausible value, because the
absence is usually the defect itself.

Exit 0 ran, 3 precondition unmet, 1 internal error.

## Agent mode

Every step is reproducible by hand: fetch the page, extract
`<script type="application/ld+json">` blocks, parse them, and compare against
`references/schema-types.json` and `references/required-props.md`.

## Guardrails

Read-only, no network. All observations come from the bundle.
