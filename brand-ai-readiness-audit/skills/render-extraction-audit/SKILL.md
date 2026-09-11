---
name: render-extraction-audit
description: >-
  Audit whether a machine can read a page's facts from the server-sent HTML, or
  whether they only appear after JavaScript runs. Distinguishes raw HTML from the
  rendered DOM from crawler behaviour, and treats a thin raw-HTML shell as evidence
  that the server response is sparse rather than as proof the site is invisible to
  AI. Measures the raw-versus-rendered vocabulary gap directly when a headless
  browser is available, and when it is not, records that as an audit limitation in
  skipped_checks rather than as a website defect. Also flags content-area images that
  carry no alt text, excluding icons and decorative elements. Use in the
  brand-ai-readiness-audit marketplace to explain why content a human plainly sees is
  absent from what a raw-HTML reader receives.
license: MIT
allowed-tools: [Bash, Read]
---

# Render & Extraction Audit

## When to use
Mechanism 2 of the chain: **can the machine read the content?** A fact injected only by
JavaScript, or trapped in an image, can be missed by a consumer that reads the server
response.

## The three things this skill keeps separate
- **Raw HTML** — what the server sent. Directly measured on every page.
- **Rendered DOM** — what a browser produces after executing JavaScript. Measured only
  when `--render` was used.
- **Crawler behaviour** — which consumers actually execute JavaScript. **Not measured at
  all**, and never asserted.

A sparse raw HTML document is evidence about the first, and by itself says nothing about
the third. The findings say so explicitly.

## Inputs
The shared cache directory: raw HTML, extracted text, and rendered text when available.

## Procedure
Run `scripts/render_diff.py <cache_dir>`.

1. **Measured raw-versus-rendered gap.** Only when rendered snapshots exist. Compares the
   vocabulary of the two texts word by word and reports the percentage of the rendered
   vocabulary absent from the server HTML. This is the only finding here that reaches
   `high`, because it is the only one with a measured gap behind it.
2. **Application shell with almost no text.** Requires an actual client-render root
   element, so a redirect stub, an error page or a genuinely short page is not misread as
   a client-rendered site. Capped at medium, with evidence stating that whether the
   content is reachable after rendering was not measured. Pages already covered by a
   confirmed gap are not reported twice.
3. **Render comparison unavailable is NOT a finding.** It is an audit limitation, recorded
   in `skipped_checks` with instructions to re-run with `--render`.
4. **Content images without alt text.** Counts only images in the content area, outside
   nav/header/footer/aside, not icon-sized, and not `role="presentation"`. A low
   improvement, with the explicit note that whether those images carry information rather
   than decoration was not determined.

## Output
Envelope `{ "skill": "render-extraction-audit", "findings": [...], "skipped_checks": [...] }`.

## Guardrails
Rendering uses headless Chromium via Playwright when present and degrades to a documented
limitation when it is not. Read-only: the browser navigates and reads; it never clicks,
submits or authenticates.
