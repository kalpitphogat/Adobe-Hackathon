---
name: structured-data-audit
description: >-
  Audit whether a machine can pick out a page's specific facts. Determines each
  page's role first, then asks whether structured data would materially help
  communicate that page's facts, and recommends only the schema.org type that
  matches the role — never Product, Article, FAQPage or LocalBusiness indiscriminately.
  Reports JSON-LD blocks that fail to parse, homepage Organization/WebSite entity
  identity and sameAs, missing or duplicated titles, meta description and Open Graph
  gaps, and pages that state their topic in neither an H1, a title, nor markup.
  Missing JSON-LD is never automatically high severity and "exactly one H1" is not
  treated as a universal requirement. Use in the brand-ai-readiness-audit marketplace
  to explain why an assistant can reach and read a page but still cannot extract the
  exact fact a user asked for.
license: MIT
allowed-tools: [Bash, Read]
---

# Structured Data & Metadata Audit

## When to use
Mechanism 3 of the chain: **can the machine identify the important facts?** The more
explicitly a fact is stated in machine-readable form, the more reliably it is extracted
and attributed.

## The question this skill asks
Never "is best practice X present?" but "are *this page's* important facts expressed in a
form a machine can extract, **given what the page is for**?" A page whose facts are
already plain, readable HTML is not defective for lacking markup.

## Inputs
The shared cache directory. HTML pages only; XML, JSON, images and PDFs are excluded
before any check runs and the exclusion is recorded in `skipped_checks`.

## Procedure
Run `scripts/check_structured_data.py <cache_dir>`.

1. **Unparseable JSON-LD** — the one unambiguous structured-data defect. A block that
   does not parse is discarded by every consumer, so the site believes it has markup
   that in fact delivers nothing. High, regardless of role.
2. **Role-matched schema gap** — runs only for pages whose role was classified with
   confidence **and** for which a genuinely applicable type exists. The full
   recommendation table is in `references/schema-templates.md`; a role absent from it
   gets no recommendation at all, because suggesting Product markup for a documentation
   page is worse than silence. Reported as an improvement.
3. **Homepage entity identity** — missing Organization/WebSite is an improvement, not a
   high-severity defect, and the evidence states that identity inference usually succeeds
   for a well-known brand and is least reliable for colliding names. When entity markup
   *is* present, a missing `sameAs` is reported with evidence that says only what was
   inspected: the homepage markup. No external source is queried and none is claimed.
4. **Titles** — a missing `<title>` on a real HTML content page is a genuine defect.
   Title *length* is a low-priority improvement about display truncation, never a
   significant AI-readiness defect. Duplicate titles are reported only across pages whose
   content actually differs, so `/` and `/index.html` serving one document is left to the
   canonical check instead of being reported twice.
5. **Meta description, Open Graph** — improvements, capped at low. The evidence states
   that engines frequently substitute their own snippet and that this audit did not
   measure whether any assistant uses this site's descriptions as a fact source.
6. **Topical identity** — a missing H1 is a defect only where a substantial page has
   **no** H1, **no** title and **no** schema type, leaving nothing explicit to state the
   subject. A page with an H1 missing but a title present is a low improvement.
7. **Skipped heading levels** — a low improvement about outline reconstruction; the text
   remains fully readable.

## Output
Envelope `{ "skill": "structured-data-audit", "findings": [...], "skipped_checks": [...] }`.

## Guardrails
Read-only, cache-only. Recommends only relevant schema types, and never claims an
external fact it did not fetch.
