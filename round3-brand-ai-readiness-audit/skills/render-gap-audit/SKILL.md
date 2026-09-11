---
name: render-gap-audit
description: Determine whether a page can be read without executing JavaScript, and whether its key facts are locked in non-text. Compares the raw HTML a crawler receives against the rendered DOM a browser builds, detects unhydrated single-page-application shells with no browser required, finds navigation that exists only after hydration, and identifies prices, hours, addresses or specifications that appear only inside an image. Use when a site looks complete to a person but is missing from AI answers, when diagnosing React, Vue, Angular or Next.js sites, or as the read stage of a full AI-readiness audit.
license: MIT
compatibility: Python 3.9+ standard library only for the shell detector and non-text checks. The quantified raw-versus-rendered diff needs a rendered DOM captured by site-evidence-collector via Playwright; without one it reports the gap at reduced severity and confidence rather than pretending to have measured it.
allowed-tools: Bash(python:*) Read
---

# render-gap-audit — stage: read

**One question: can a crawler read this page without executing JavaScript?**

The second of the three steps that must succeed in order. A page that assembles
its content client-side is complete to a person and empty to a machine.

## When to use

As the read stage of an audit, or standalone when a site is built on a
client-side framework and is missing from AI answers despite looking fine.

## Inputs

```bash
python scripts/run.py --bundle ./evidence --profile ./profile.json
```

## Procedure

1. For each rendered page, compare raw main-content wordcount against rendered
   main-content wordcount, and quote sentences that appear only after rendering.
2. For each page with no rendered pair, apply the **static shell signature**.
   All four signals must agree: a framework mount point exists, that mount point
   is **empty**, total body wordcount is under 50, bundle scripts are loaded,
   and the `<noscript>` fallback is thin.
3. Compare raw and rendered internal link counts.
4. For each page, determine which fact its type is expected to state, and check
   whether that fact exists in text or structured data anywhere before blaming
   an image.
5. Classify images as content-bearing or decorative before counting missing alt.

### Why the shell signature keys on the mount point

An earlier version keyed on "main content is short" and fired on a fully
server-rendered page. The discriminating signal is that the framework mount
point is **empty**: a hydrated or server-rendered page puts its content inside
that element, and only an unhydrated shell leaves it bare. This matters more
than usual because a false positive here caps the whole discoverability report
under gate Rule 2 and suppresses 13 engagement checks under Rule 0b.

## Checks

| check_id | detects | default severity |
|---|---|---|
| `read.render.raw_text_gap` | rendered text substantially exceeds raw HTML text | critical |
| `read.render.empty_spa_shell` | served HTML is an empty application mount point | critical, or high without a renderer |
| `read.render.nav_links_js_only` | the internal link graph exists only after hydration | high |
| `read.nontext.key_fact_image_only` | a price, phone or spec exists only inside an image | high |
| `read.nontext.informative_image_no_alt` | content-bearing images carry no alt text | medium |

### SUPPRESS WHEN

- `read.render.raw_text_gap` — no rendered DOM exists for the page, in which
  case it is recorded as *not assessed* rather than passing quietly; or the
  rendered page is under 200 words **and** raw is at least 30% of rendered,
  where the difference is too small to be worth a finding.
- `read.render.empty_spa_shell` — the framework mount point is not empty, no
  bundle scripts are present, or a `<noscript>` block carries the key facts. If
  a rendered DOM was captured for the same page, this defers to
  `read.render.raw_text_gap`, which reports the same defect with a quantified
  gap instead of a signature match.
- `read.render.nav_links_js_only` — no rendered DOM, or raw links are already at
  least 60% of rendered.
- `read.nontext.key_fact_image_only` — the fact appears in page text or in
  structured data anywhere on the page. Whatever the images look like, a fact
  that is machine-readable somewhere is not locked in non-text.
- `read.nontext.informative_image_no_alt` — the image is decorative, is chrome,
  is under 100x100, is an icon, logo or sprite, or the page is below the
  reporting floor. Isolated missing alt text is routine maintenance.

## Output

One JSON object on stdout. Exit 0 ran, 3 precondition unmet, 1 internal error.

## Agent mode

An agent with a fetch tool can run steps 1 and 3 by fetching the page twice, once
plainly and once through a rendering service, and comparing wordcounts. Step 2
needs only the raw HTML. **The quantified diff cannot be reproduced faithfully
by hand**; in agent mode report it at `hypothesis` confidence and say so.

## Guardrails

Read-only, no network. All observations come from the bundle. The renderer, when
used, navigates only: it never clicks, submits, or injects script.
