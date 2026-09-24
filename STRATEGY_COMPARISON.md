# Python-only vs always-Playwright vs two-step: a real run (2026-09-25)

**What was run.** `tools/strategy_compare.py run` on 23 sites, each for real: the frozen engine
with `--no-render` (Python-only); the engine with Playwright; and **two-step**, meaning the
Python-only run first, then a second, Playwright run **only if** any crawled page had 0 same-site
links in the crawler's raw HTML (otherwise the Python-only report is the result). Only existing
engine flags were used. The engine is unchanged.

**How findings were judged.** `tools/strategy_compare.py eval` checks every browser-dependent
finding (`read.render.nav_links_js_only`, `read.render.raw_text_gap`) against the live page:
same-site links / visible words in **the raw HTML the engine's crawler saved** vs **the page a
human sees in Chromium**, with the engine's own thresholds applied to a fair count.

Sites: the 17 from `JS_DETECTION_STUDY.md` plus 6 whose behaviour we knew (Django, Mozilla, htmx:
past false positives; Khan Academy, cal.com, IKEA: real JavaScript). pytest and sphinx-doc were
not used, so they stay unseen.

## Results

| site | trigger fired? | Python-only (total/high+) | always Playwright (total/high+, browser findings true/false) | two-step (total/high+, true/false) |
|---|---|---|---|---|
| excalidraw.com | yes | 6/1 | 9/2, 0/0 | 9/2, 0/0 |
| open.spotify.com | no | 25/7 | 36/15, **6/3** | 25/7, 0/0 |
| twitch.tv | yes | 5/2 | 7/4, 2/0 | 17/4, 2/0 |
| app.diagrams.net | yes | 8/2 | 8/2, 0/0 | 8/2, 0/0 |
| figma.com | yes | 38/4 | 38/4, 0/0 | 38/4, 0/0 |
| vercel.com | no | 33/7 | 46/8, 0/0 | 33/7, 0/0 |
| airbnb.com | yes | 5/2 | 5/2, 0/0 | 5/2, 0/0 |
| notion.com | yes | 61/2 | 60/2, 0/0 | 60/2, 0/0 |
| example.com | yes | 6/0 | 7/0, 0/0 | 7/0, 0/0 |
| info.cern.ch | no | 9/3 | 9/3, 0/0 | 9/3, 0/0 |
| neverssl.com | no | 0/0 | 0/0 | 0/0 |
| berkshirehathaway.com | yes | 36/4 | 32/5, 1/0 | 32/5, 1/0 |
| python.org | no | 43/3 | 58/14, **0/5** | 43/3, 0/0 |
| gov.uk | no | 37/4 | 51/10, 0/0 | 37/4, 0/0 |
| w3.org | no | 39/4 | 40/5, **0/1** | 39/4, 0/0 |
| craigslist.org/about | no | 24/1 | 24/1, 0/0 | 24/1, 0/0 |
| rust-lang.org | yes | 51/8 | 60/13, 4/1 | 60/13, 4/1 |
| docs.djangoproject.com | no | 21/1 | 24/4, **0/3** | 21/1, 0/0 |
| mozilla.org | no | 40/5 | 54/15, 1/**5** | 40/5, 0/0 |
| htmx.org | no | 63/13 | 55/10, 1/**3** | 63/13, 0/0 |
| khanacademy.org | yes | 10/1 | 21/4, 2/0 | 21/4, 2/0 |
| cal.com | yes | 67/10 | 60/12, 2/0 | 60/12, 2/0 |
| ikea.com | no | 61/16 | 65/17, 1/0 | 61/16, 0/0 |

### Totals over 23 sites

| strategy | findings | high + critical | browser findings: true | false | share true |
|---|---|---|---|---|---|
| always Python-only | 688 | 100 | none | **none** | – |
| always Playwright | 769 | 152 | 20 | **21** | 49% |
| **two-step** | 712 | 114 | 11 | **1** | **92%** |

The trigger fired on 11 of 23 sites.

### What two-step missed (true browser findings only always-Playwright had)

| site | findings | why missed |
|---|---|---|
| open.spotify.com | 6 × nav_links | Spotify sends crawlers pre-rendered HTML with links, so no page has 0 links; humans see ~3× more links |
| ikea.com | 1 × nav_links (`/ae/ar/`) | raw HTML already has links; JavaScript adds more |
| mozilla.org, four.htmx.org | 1 × nav_links each | the crawler received a **smaller page than a browser** (Mozilla: 31 vs 106 same-site links). True for crawlers, but **not caused by JavaScript**; yesterday, with a browser User-Agent, raw and rendered were equal |

## What it shows

1. **Always-Playwright is a coin flip on browser findings:** 20 true, 21 false. The false ones
   are the nav_links counting bug on ordinary sites (python.org, Django, Mozilla, htmx, w3.org).
2. **Two-step keeps most of the real ones and drops almost all the false ones:** 11 true, 1 false.
   It never rendered python.org, Django, Mozilla, htmx or w3.org, where the false positives were.
3. **What two-step gives up** is the partly-JavaScript sites (Spotify, IKEA), where crawlers
   already see most of the page, plus two pages whose difference isn't JavaScript at all.
4. **On JavaScript sites two-step also unlocks the engagement checks.** On Twitch, Khan Academy and
   cal.com, the Playwright run observes the page a visitor sees, so gate Rule 0b stops suppressing
   the engagement checks (e.g. Twitch 5 → 17 findings).
5. **Counts of "high" findings are not a clean score.** Crawl sampling differs between runs, and
   the engine sometimes groups one issue as a site-wide finding in one run and splits it per page
   in another (python.org: 1 site-wide "claims can't be quoted" vs 7 per-page). The verified browser
   findings are the fair comparison.

## Caveats

- 23 sites, one day. Live sites change and crawl samples differ between runs.
- "True" means our fair re-count agrees a crawler gets fewer links/words than a human. For
  Mozilla and four.htmx the cause is a different page served to the crawler, not JavaScript.
- `act.perf.above_fold_weight` never fired, so it is not assessed here.
