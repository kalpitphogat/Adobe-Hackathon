# Browser or not: 12 more sites, and the two-pass decision (2026-09-25)

**Question.** Should the live run render every page with Playwright (the path until now), never
render (`--no-render`), or decide per site? And is the worry true that Playwright goes wrong on
very small pages? Engine unchanged; only existing flags (`--no-render`, `--bundle`, and
`--allow-private-hosts` for sites we host ourselves).

**Method.** `tools/site_matrix.py run` audits each site twice from a fresh unzip of
`submission.zip`: `--no-render` and with Playwright 1.56.0 (Chromium 141). `tools/site_matrix.py
eval` re-checks every browser finding (`read.render.nav_links_js_only`, `read.render.raw_text_gap`)
against the engine's **own saved raw and rendered HTML** for that page, counting **same-site links on
both sides**, with the engine's thresholds (rendered ≥ 5 links, raw < 60%; or words ≥ 3× to ≥ 200).
The five test sites come from `tools/test_sites.py` (reproducible; served on 127.0.0.1). Public
sites are the ones this environment's network allowed; www.rust-lang.org redirected to a blocked
host and is left out.

## Results

| site | kind | pages | pages with 0 same-site links (pass 1) | `--no-render`: status, total/high+ | Playwright: status, total/high+ | browser findings true / false |
|---|---|---|---|---|---|---|
| tiny_links (test) | 3 pages < 50 words, 2 internal + 4 social links | 3 | 0 | partial, 11/4 | complete, 14/7 | 0 / **3** |
| tiny_nolinks (test) | 1 page < 50 words, no links | 1 | 1 | partial, 8/3 | complete, 9/3 | 0 / 0 |
| spa (test) | empty `#root`, JavaScript builds everything | 1 | 1 | partial, 7/3 | complete, 13/5 | **2** / 0 |
| normal (test) | 6 server-rendered pages + social footer | 6 | 0 | partial, 9/3 | complete, 9/3 | 0 / 0 |
| partial_js (test) | server text, JavaScript adds the nav | 2 | 0 | partial, 12/4 | complete, 14/6 | **2** / 0 |
| ubuntu.com | large marketing site | 25 | 0 | partial, 77/7 | complete, 77/7 | 0 / 0 |
| www.anthropic.com | marketing site | 21 | 0 | partial, 49/7 | complete, 49/7 | 0 / 0 |
| code.claude.com/docs | docs | 24 | 0 | partial, 9/1 | complete, 9/1 | 0 / 0 |
| jsr.io | registry | 25 | 0 | partial, 29/3 | complete, 29/3 | 0 / 0 |
| nodejs.org/en | Next.js site | 22 | 0 | partial, 32/6 | partial, 32/6 | 0 / 0 |
| pkg.go.dev | server-rendered app | 25 | 0 | partial, 26/5 | complete, 26/5 | 0 / 0 |

(nodejs.org stays `partial` with Playwright because another limitation also applies there.)

## What it shows

1. **Yes, the browser misfires on small pages, and this is why.** On tiny_links the engine reported
   *"the raw HTML contains 2 internal links, the rendered DOM contains 6"*, high and confirmed, on
   all 3 pages. Counting same-site links on both sides gives **2 and 2**: the 6 is the 2 internal
   links plus the 4 social links. The rendered count takes every link on the page
   (`collect.py` line 739) and the raw count only same-site ones (`links.internal`). Any page with
   few internal links and a few off-site ones trips it. Small pages have few internal links, so they
   trip it most; the 23-site study saw the same on large sites (python.org, Mozilla, Django).
2. **On the six public sites the browser changed nothing.** Same findings, same severities; only
   `audit_status` moves from `partial` to `complete`.
3. **The browser is worth it when the crawler sees an empty page.** On the JavaScript-only app,
   rendering found 2 true browser findings and unlocked 3 more engagement findings (gate Rule 0b
   stops suppressing them once the visitor's page is observed).
4. **Pass 1's own evidence tells the two apart.** "A page with status 200 and no same-site links in
   its raw HTML" fired on the JavaScript-only app (render: right) and the empty tiny page (render:
   harmless), and on none of the others, so it avoided all 3 false findings on tiny_links. It
   missed partial_js, where the crawler already sees one link: 2 true findings not measured.

## Decision: two passes in the main path

| strategy (these 11 sites + the 23 in `STRATEGY_COMPARISON.md`) | true browser findings | false |
|---|---|---|
| always Playwright | 24 | 24 |
| never (`--no-render`) | 0 | 0 |
| **two passes** (render only when pass 1 finds a page with 0 same-site links) | **13** | **1** |

The agent runs pass 1 with `--no-render`, counts those pages, and then either renders (count > 0)
or re-analyses pass 1's evidence with `--bundle` (same findings, no second crawl). The REPLAY's step 2
prompt does this, and Fallback E keeps the always-render path for partly-JavaScript sites.

**Rehearsed** with `claude -p` (Claude Code 2.1.282, Linux), 10 runs, `rehearsal/2026-09-25_twopass_*`:
Opus 5.5, Sonnet 5 and Haiku 4.5 all chose the right pass 2 on the JavaScript-only app and on
tiny_links; Opus also on the normal test site and jsr.io. Engine check after every run: unchanged.

## Caveats

- Five of the eleven are sites we built to isolate one behaviour each; they are not a sample of the web.
- One day, one crawl per site and mode; live sites change.
- The pass-1 rule is a heuristic from 34 sites, not a guarantee (see `JS_DETECTION_STUDY.md`).
