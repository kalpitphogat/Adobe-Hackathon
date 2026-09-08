---
name: integrity-audit
description: >-
  Audit a page for content that manipulates the machine reading it rather than serving
  the human — a trust and safety concern for AI discoverability. Detects prompt-injection
  and hidden LLM-directive text (e.g. "ignore previous instructions", often buried in HTML
  comments or hidden nodes), large amounts of visually-hidden text (display:none /
  off-screen / font-size:0 cloaking), and invisible or zero-width Unicode used to smuggle
  or distort text. Use in the brand-ai-readiness-audit marketplace to flag pages that AI
  assistants may distrust, down-rank, or refuse to cite.
license: MIT
allowed-tools: [Bash, Read]
---

# Content Integrity Audit

## When to use
Getting found and read is necessary, but assistants also decide whether to *trust* what
they read. Pages that hide text from humans, address the AI directly, or smuggle invisible
characters read as manipulation — increasingly detected and penalized. This skill surfaces
those patterns so they can be removed before they cost citations or reputation.

## Inputs
The shared cache directory (uses cached raw HTML + extracted text per page).

## Procedure
Run `scripts/check_integrity.py <cache_dir>`. It reports:
1. **Prompt-injection / hidden LLM instructions** — text phrased as an instruction to an AI
   reader ("ignore previous instructions", "as an AI language model", directives in
   `<!-- ... -->` comments) (critical).
2. **Visually-hidden text (cloaking)** — many elements hidden via CSS
   (`display:none` / `visibility:hidden` / off-screen / `font-size:0`), i.e. content shown
   to machines but not humans (medium).
3. **Invisible / zero-width Unicode** — runs of zero-width or bidi-control code points in
   the text a machine reads (medium).

See `references/integrity-checks.md` for the exact patterns and false-positive guards.

## Output
Envelope `{ "skill": "integrity-audit", "findings": [ … ] }` merged by the orchestrator;
findings are tagged `dimension: discoverability` (a trust signal).

## Guardrails
Read-only; pattern-matches cached content only. Detection is deliberately specific and
conservative (cloaking/zero-width checks require a threshold; injection phrasing is
narrowly scoped) to avoid false positives on ordinary pages that merely discuss AI.
