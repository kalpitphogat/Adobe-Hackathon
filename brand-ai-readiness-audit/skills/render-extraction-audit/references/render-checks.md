# Render & extraction check catalog

Gate 2 (Round-2 appendix C): the machine must be able to **read** the page. A page that
looks complete to a person is not always complete to a program.

## Checks & thresholds
| # | Check | How | Threshold | Severity |
|---|-------|-----|-----------|----------|
| 1 | Near-empty raw HTML | extractable text length in server HTML | <300 chars **and** an app-shell marker present (or >1.5KB markup) | critical |
| 2 | Static-vs-rendered gap | diff word-sets of raw text vs headless-rendered text | >40% of readable words are render-only (and rendered has >40 words) | high |
| 3 | Facts in images | fraction of `<img>` without `alt` on image-heavy pages (>=3 imgs) | >60% missing alt | medium |

App-shell markers: `id="root"`, `id="app"`, `id="__next"`, `ng-app`, `data-reactroot`.

## Why the static/rendered diff is the key check
Many AI assistants and crawlers fetch and parse **raw HTML** and do not execute
JavaScript (or do so inconsistently). If the price, hours, description, or headline is
injected by client-side JS, it can be present for a human and absent for the machine —
the page is cited without its facts, or not at all. Measuring the gap directly (raw vs
rendered) turns a vague "SPA is bad for SEO" into evidence: *"63% of readable words on
/pricing appear only after JS; e.g. 'annual', 'enterprise', '$49'."*

## Rendering
`crawler.py --render` uses Playwright + headless Chromium (auto-discovered under
`PLAYWRIGHT_BROWSERS_PATH`, launched `--no-sandbox`), waits for `networkidle`, and
captures `document.body.innerText`. If Playwright is unavailable the skill degrades to
the thin-HTML heuristic (check 1) and emits a low-severity note that the direct
measurement was skipped — never a false "all clear".

## Fixes
Server-side render (SSR) or static-generate (SSG) the primary content, or add a
prerender layer that serves fully-rendered HTML to bots. The goal: the main facts exist
in the initial HTML response.
