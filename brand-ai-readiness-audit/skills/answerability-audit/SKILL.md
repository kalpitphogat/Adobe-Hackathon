---
name: answerability-audit
description: >-
  Audit whether a site states its key facts as short, self-contained, quotable text —
  the form AI assistants prefer when choosing what to cite. Checks for FAQ/Q&A content
  marked up with FAQPage/Question schema, thin pages with little quotable body text, a
  homepage that plainly states what the brand is and who it serves, and contact facts
  (email/phone) available as real text rather than only in images or widgets. Use in
  the brand-ai-readiness-audit marketplace to explain why a reachable, readable page
  still isn't easy to quote a clear answer from.
license: MIT
allowed-tools: [Bash, Read]
---

# Answerability Audit

## When to use
Round-2 appendix B/C: assistants build answers from the pages they can most easily
*quote a clear fact from*. Content that is present but buried, vague, or implied rather
than stated plainly is less likely to be cited.

## Inputs
The shared cache directory (uses cached text + raw HTML).

## Procedure
Run `scripts/check_answerability.py <cache_dir>`. It reports:
1. **No FAQ/Q&A markup** — no FAQPage/Question structured data (the most directly
   quotable format) (medium).
2. **Thin pages** — little quotable body text (<500 chars) (medium/low by prevalence).
3. **Unclear homepage** — the first screen doesn't plainly say what the brand is / who
   it's for (high) — this is the sentence assistants quote to describe the brand.
4. **Unstructured content** — substantial pages that are walls of text with no lists,
   tables, or question-style headings, so there's nothing discrete to quote (medium).
5. **Missing contact facts** — no email/phone as extractable text (low).

See `references/answerability-checks.md` for how to write self-contained, extractable
claims.

## Output
Envelope `{ "skill": "answerability-audit", "findings": [ … ] }` merged by the
orchestrator.

## Guardrails
Read-only; analyzes only cached content.
