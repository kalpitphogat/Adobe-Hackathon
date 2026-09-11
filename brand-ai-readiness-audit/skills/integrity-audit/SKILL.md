---
name: integrity-audit
description: >-
  Audit a page for content that manipulates the machine reading it rather than
  serving the human — a trust and safety concern for AI discoverability. Detects
  prompt-injection and LLM-directive text such as "ignore previous instructions",
  substantial text hidden from human view that carries no ordinary UI marker, and
  invisible or bidirectional-control Unicode smuggled into page text. The presence of
  display:none is never on its own treated as cloaking: menus, dialogs, tab panels,
  carousels, skip links, consent notices and screen-reader-only text are recognised
  and excluded, and a finding additionally requires the hidden text to be substantial
  relative to what the page actually shows. Use in the brand-ai-readiness-audit
  marketplace to flag pages a consumer may distrust or decline to cite.
license: MIT
allowed-tools: [Bash, Read]
---

# Content Integrity Audit

## When to use
Being found and read is necessary, but a consumer also decides whether to **trust** what
it reads. Pages that address the machine directly, hide text from humans, or smuggle
invisible characters read as manipulation.

## Inputs
The shared cache directory: raw HTML, extracted text, and the crawler's split of hidden
text into UI and non-UI containers.

## Procedure
Run `scripts/check_integrity.py <cache_dir>`.

1. **Text addressed to an AI reader.** A deliberately specific pattern set, so ordinary
   prose that merely mentions AI does not match, searched against the page with `<code>`,
   `<pre>`, `<blockquote>`, `<samp>` and `<kbd>` regions removed. An article that quotes
   an AI-directed note is writing about the technique, not using it, and that outcome is
   recorded in `skipped_checks`. Critical, because after those exclusions it is the one
   signal here that is unambiguous about intent.
2. **Hidden non-UI text.** The parser tracks element nesting and classifies each hidden
   container by its class, id and role. Text inside a menu, drawer, dialog, popover,
   accordion, tab panel, carousel, offcanvas, skip link, consent banner, loading state,
   template or screen-reader helper is counted separately and **never** reported. What
   remains must additionally be substantial relative to the page's visible text before a
   finding is raised. Where every hidden block was legitimate UI, that is recorded in
   `skipped_checks` rather than silently dropped.
3. **Invisible and bidi-control Unicode.** Zero-width and directional-override code
   points in the extracted text. The finding states that these are frequently a
   copy-paste or CMS artefact rather than deliberate.

## Output
Envelope `{ "skill": "integrity-audit", "findings": [...], "skipped_checks": [...] }`.

## Guardrails
Read-only, and descriptive rather than accusatory: the hidden-text finding states that no
CSS or JavaScript was executed, so an element may still become visible through a
stylesheet rule or an interaction, and asks the owner to confirm rather than asserting
cloaking.
