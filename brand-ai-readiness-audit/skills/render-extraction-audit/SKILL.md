---
name: render-extraction-audit
description: >-
  Audit whether a machine can actually read a page's facts from the server-sent
  HTML, or whether the content only appears after JavaScript runs. Detects
  near-empty client-rendered shells (SPA roots with little raw text), measures the
  static-vs-rendered fact gap by diffing raw HTML text against headless-Chromium
  rendered text, and flags information locked in images without alt text. Use in the
  brand-ai-readiness-audit marketplace to explain why content that is plainly visible
  to a human is invisible to AI assistants and crawlers that read raw HTML.
license: MIT
allowed-tools: [Bash, Read]
---

# Render & Extraction Audit

## When to use
The second discoverability gate (Round-2 appendix C): *the crawler has to be able to
read what's on the page*. Many assistants build answers from raw HTML; a fact injected
only by JavaScript, or trapped in an image, can be missed entirely. This is typically
the highest-signal discoverability defect.

## Inputs
The shared cache directory. For the direct static-vs-rendered comparison, the crawler
must have been run with `--render` (headless Chromium via Playwright); without it, the
skill still applies its thin-HTML heuristics and notes that the direct measurement was
skipped.

## Procedure
Run `scripts/render_diff.py <cache_dir>`. It reports:
1. **Near-empty raw HTML** — pages with an app shell (`#root`/`#app`/`#__next`/Angular/
   React markers) but <300 chars of extractable server text (critical).
2. **Static-vs-rendered fact gap** — share of readable words that exist only after JS
   render, with example JS-only terms (high when large).
3. **Facts locked in non-text** — pages where most images have no alt text (medium).

See `references/render-checks.md` for thresholds and rationale.

## Output
Envelope `{ "skill": "render-extraction-audit", "findings": [ … ] }` merged by the
orchestrator.

## Guardrails
Read-only; rendering navigates the page headlessly (`--no-sandbox`) but performs no
clicks, form submissions, or authenticated actions.
