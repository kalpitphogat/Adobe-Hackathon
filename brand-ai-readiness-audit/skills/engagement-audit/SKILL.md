---
name: engagement-audit
description: >-
  Audit why a visitor who arrives on a page might fail to understand it, accomplish
  the task they came for, or continue deeper. Starts from what the page is FOR (its
  classified role) and asks whether the likely primary task is understandable and
  whether a task-relevant next step is discoverable, using technical signals —
  mobile viewport, crawler-observed response latency, unusually large HTML
  documents, blocking entry overlays, unmuted autoplay, and genuine navigational
  dead ends — as contextual supporting evidence rather than as universal
  requirements. Deliberately does NOT treat a missing call-to-action, a missing
  footer, or a low link count as defects. Use in the brand-ai-readiness-audit
  marketplace to explain why visitors who reach the site leave without engaging.
license: MIT
allowed-tools: [Bash, Read]
---

# On-Site Engagement Audit

## When to use
The engagement half of the problem: citation brings a visitor to the door, and what
happens next decides whether the visit was worth anything. Use this to explain why
arriving visitors do not get what they came for.

## The question this skill asks
Not "does this page have a CTA?" but:

> Given what this page appears to be FOR, can a visitor tell what it is, do the thing
> it exists to let them do, and find the next relevant step?

Engagement is **not** equated with having a call-to-action, five links, a footer, a
particular header structure, a heading count, or any other HTML pattern. Those are
supporting signals at most. A documentation page, a browser tool, an essay, a legal
notice and a login screen are all perfectly good without marketing copy, and this skill
will not say otherwise.

## Inputs
The shared cache directory. Uses `meta.json` per-page metadata (role, role confidence,
viewport, internal/external link split, landmarks, parsed media elements, response
timing and size) plus the cached raw HTML for overlay markup.

## Procedure
Run `scripts/check_engagement.py <cache_dir>`. Non-HTML resources are excluded from
every check before anything else happens.

1. **Mobile viewport.** The one genuine universal here: without the meta tag a mobile
   browser renders a desktop layout at desktop width, whatever the page is for.
2. **Task-relevant next step.** Runs only for roles whose purpose implies an action
   (homepage, product, contact) and only when the role was classified with confidence.
   Looks for wording relevant to *that role's* task, never for generic words such as
   "contact" or "learn more" appearing anywhere on the page. Reported as an improvement.
3. **Route onward.** Not a link-count rule. Flags only a genuine dead end: zero same-host
   links, no nav/header/footer landmark, and no form.
4. **Crawler-observed latency.** Explicitly labelled as this auditor's own single-sample
   request time from one network location. It is not Largest Contentful Paint and not
   field data, and the finding says so and recommends measuring properly first.
5. **Unusually large HTML.** Measures the HTML document only, excluding every
   sub-resource. Stated as such, and reported as an improvement.
6. **Unmuted autoplay and entry overlays.** Read from parsed media attributes, so the
   common `muted autoplay` ordering is not misread. Overlay detection requires markup
   naming a newsletter, email-capture, paywall, exit-intent or welcome-mat element, and
   explicitly excludes cookie-consent, privacy and age-gate elements. Because the audit
   does not execute JavaScript, an overlay is reported at low confidence as something to
   verify, never as a confirmed barrier.

Checks that do not apply are recorded in `skipped_checks` with a reason, not omitted
silently. See `references/engagement-checks.md`.

## Output
Envelope `{ "skill": "engagement-audit", "findings": [...], "skipped_checks": [...] }`.
These findings are tagged `dimension: engagement` in the final report.

## Guardrails
Read-only; reasons over cached responses only. Never claims causality it did not
measure: it reports that a page "lacks an observable task-relevant next step under this
audit's criteria", not that the page "causes visitors to bounce".
