---
name: structured-data-audit
description: >-
  Audit whether a machine can pick out specific facts from a page. Checks
  schema.org JSON-LD coverage and validity (parse errors), homepage Organization/
  WebSite identity and sameAs entity-disambiguation links, core metadata (unique
  titles, meta descriptions, Open Graph), and heading structure (missing or
  duplicate H1). Use in the brand-ai-readiness-audit marketplace to explain why an
  AI assistant can reach and read a page but still can't extract or attribute the
  exact fact a user asked for.
license: MIT
allowed-tools: [Bash, Read]
---

# Structured Data & Metadata Audit

## When to use
The third discoverability gate (Round-2 appendix A/C): *the crawler has to be able to
pick out the specific fact*. The more explicitly and unambiguously a fact is stated in
machine-readable form, the more reliably it is extracted and quoted.

## Inputs
The shared cache directory (uses cached raw HTML per page).

## Procedure
Run `scripts/check_structured_data.py <cache_dir>`. It reports:
1. **Structured-data coverage** — pages with any valid JSON-LD (high if none).
2. **Invalid JSON-LD** — ld+json blocks that fail to parse (ignored by consumers, so
   the markup is wasted) (high).
3. **Entity identity** — homepage missing Organization/WebSite (high) or missing
   `sameAs` profiles for disambiguation (medium).
4. **Metadata basics** — missing `<title>` (high), no meta descriptions, no Open Graph.
5. **Headings** — pages with no H1 (medium) or multiple H1s (low).

`references/schema-templates.md` provides paste-ready JSON-LD for the common types so
the suggested fixes are concrete.

## Output
Envelope `{ "skill": "structured-data-audit", "findings": [ … ] }` merged by the
orchestrator.

## Guardrails
Read-only; parses only already-cached HTML.
