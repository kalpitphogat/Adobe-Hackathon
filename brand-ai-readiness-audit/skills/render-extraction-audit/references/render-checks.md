# Render & extraction check catalog

Mechanism 2: the machine must be able to **read** the page. A page that looks complete to
a person is not always complete to a program — but establishing that requires measuring
it, not assuming it.

## Three things, kept separate

| | What it is | Measured here? |
|---|---|---|
| **Raw HTML** | what the server sent | yes, on every page |
| **Rendered DOM** | what a browser produces after JavaScript | only when `--render` was used |
| **Crawler behaviour** | which consumers execute JavaScript | **no** — never measured, never asserted |

The third is why a thin raw-HTML shell is **not** proof that a site is invisible to AI.
It is proof that the server response is sparse. The findings say exactly that.

## Checks

| # | Check | How | Trigger | Band |
|---|-------|-----|---------|------|
| 1 | Measured raw-vs-rendered gap | word-set diff of raw text against rendered text | >40% of the rendered vocabulary absent from the server HTML, on a page with >40 rendered words | high (defect, material) |
| 2 | Application shell with no text | extractable text in the server HTML | <300 chars **and** a client-render root element **and** >1.5KB of markup | medium (defect) |
| 3 | Content images without alt | content-area images only | >60% of at least three qualifying images have no `alt` attribute | low (improvement) |
| — | Render comparison unavailable | — | no rendered snapshot in the cache | **not a finding** — recorded in `skipped_checks` |

## Why check 2 is capped at medium

The old version reported this at critical or high, which claimed more than the evidence
supported. Without a rendered comparison the audit knows only that the initial HTML is
sparse; the content may be entirely reachable after JavaScript runs. The finding
therefore carries an explicit `not_verified` line saying so, and pages already covered by
a *measured* gap are not reported a second time.

Check 2 also requires an actual client-render root (`id="root"`, `id="app"`,
`id="__next"`, `id="__nuxt"`, `ng-app`, `data-reactroot`, `id="svelte"`). Without that
requirement a redirect stub, an error page or a genuinely short page was being reported
as a client-rendered site, which was a false-positive source in v1.

## Which images count

Only images that are (a) in the content area, outside `nav`/`header`/`footer`/`aside`,
(b) not marked `role="presentation"` or `role="none"`, and (c) not icon-sized (both
declared dimensions 64px or under). Decorative icons carry no facts and generate no
finding. Even then, the evidence states plainly that whether the remaining images convey
information rather than decoration **was not determined** — position and size were
measured, content was not.

## Rendering

`crawler.py --render` uses Playwright with headless Chromium (auto-discovered under
`PLAYWRIGHT_BROWSERS_PATH`, launched `--no-sandbox`), waits for `networkidle`, and
captures `document.body.innerText`. The browser navigates and reads only; it never
clicks, submits or authenticates. Without Playwright the skill records the limitation and
keeps the capped check 2 — never a false "all clear", and never a false alarm either.

## Fixes

Server-render or static-generate the primary content, or add a prerender layer that
serves fully-rendered HTML. The goal is that the main facts exist in the initial HTML
response — then re-run with `--render` to confirm the gap actually closed.
