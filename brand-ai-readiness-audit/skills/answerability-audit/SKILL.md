---
name: answerability-audit
description: >-
  Audit whether a page's important facts are stated clearly enough to be identified,
  extracted and quoted. Tests whether important facts are hard to locate, not whether
  a page contains a particular density of lists, tables or FAQ markup — legal pages,
  essays, documentation and editorial prose are legitimately paragraph-heavy and are
  never penalised for that. Checks that an existing question-and-answer block is
  marked up, that information-bearing pages carry extractable text, that the homepage
  states in the server HTML what the site is, that reference-style pages break their
  look-up facts out of continuous prose, and that a contact page publishes a contact
  route as real text. Use in the brand-ai-readiness-audit marketplace to explain why a
  reachable, readable page still yields no clear answer.
license: MIT
allowed-tools: [Bash, Read]
---

# Answerability Audit

## When to use
Mechanism 4 of the chain: **are the facts sufficiently clear?** A consumer builds an
answer from the page it can most easily quote a clear fact from. Content that is present
but vague, buried, or implied rather than stated is less usable.

## What this skill refuses to do
It does not equate good content with lists and tables. Absence of structure is not a
defect. The structure check runs **only** for product and documentation pages, whose
purpose implies discrete look-up facts. Articles, legal text, generic content and
unclassified pages are excluded by name, and the exclusion is recorded in
`skipped_checks` so a reader can see it was a decision rather than an oversight.

## Inputs
The shared cache directory. HTML pages only.

## Procedure
Run `scripts/check_answerability.py <cache_dir>`.

1. **Unmarked question-and-answer content** — never a defect. Raised only when a page
   carries at least three question-style headings or four full question sentences, and no
   page in the sample declares FAQ structured data. The action says to mark up the
   questions that already exist, explicitly not to invent new ones.
2. **Thin information pages** — only for roles whose purpose is to convey information, so
   a login screen, a tool or a listing is not penalised for being short on prose.
3. **Homepage self-description** — fires when the opening of the homepage's server HTML
   contains no descriptive phrasing and almost no sentence structure. Capped at medium,
   and where the page looks client-rendered the finding states that what a visitor
   actually sees was not assessed.
4. **Reference pages as unbroken prose** — product and documentation roles only, 1200+
   characters, no list, no table, at most one heading. A low improvement.
5. **Contact route as text** — runs only where a contact page exists, so a personal blog
   or a documentation site is never told to publish a phone number.

## Output
Envelope `{ "skill": "answerability-audit", "findings": [...], "skipped_checks": [...] }`.

## Guardrails
Read-only. Measures the server HTML, and says so wherever text added by JavaScript would
change the answer.
