# Head-to-head: Lakshya's REPLAY vs ours, on https://www.ikea.com/ (2026-09-24)

**Method.** Both `REPLAY_IT_Professionals.txt` files were run **verbatim** (each team's own prompt,
flags and setup), headless with `claude -p`, Claude Code 2.1.280 + Claude Opus 5.5, each from its
own fresh unzip of the same `submission.zip` (sha256 `1c872c59…8dcf`), one after the other.
IKEA was chosen because it's a well-known brand a judge might pick; neither of us had audited it;
`tools/prescreen.py` showed no Crawl-delay, no bot challenge and no AI topic; and e-commerce was the
noisiest category in `SCOUTING.md`, so it's a hard test. (adobe.com was ruled out: it timed out for
a plain scripted request.) Every high finding was then checked independently against the live site.

## Run results

| | Lakshya (`lakshya_round4`) | Ours (`Kalpit_round_4`) |
|---|---|---|
| Engine flags | `--no-render` | default (Playwright + Chromium) |
| Python | 3.11.9 (first on PATH) | 3.11.15 (venv) |
| Exit / report written | 0 / yes | 0 / yes |
| Total time (engine) | 90 s (39.7 s) | 129 s (~63 s) |
| `audit_status` | `partial` (render checks not assessed) | `complete` |
| Checks run | 20 / 66 | 21 / 66 |
| Findings | 52: high 6, medium 45, low 1 | 52: high 7, medium 44, low 1 |

Apart from rendering, the engine output is the same: the same 6 high findings, in the same order,
with the same evidence. Ours has one extra high (below).

## Are the high findings true? (independent check)

| finding | conf. | in | verdict | how checked |
|---|---|---|---|---|
| `extract.ans.fact_coverage_gap` ×3 (/at/en, newsroom, stories) | likely | both | **True as stated, low stakes.** The "claims" are the page's own title/meta-description taglines, which don't appear in the body. | Both agents re-fetched; ours noted the caveat |
| `act.orient.no_value_proposition` (13 of 25 pages) | likely | both | **Doubtful.** Homepage H1 "Welcome to IKEA Global!"; the misfire pattern from `SCOUTING.md` | reading the evidence |
| `extract.sd.absent_on_eligible_page` (/global/en/jobs, /international-sales) | confirmed | both | **True.** 0 JSON-LD, 0 microdata, 0 RDFa on both | `verify_sd.py` |
| `extract.sd.contradicts_visible_content` ("schema 132.00, page shows 10/25/68") | confirmed | both | **False positive.** The rendered page shows `132€ \| Hind 132€` ("Hind" = "Price" in Estonian). The engine's visible-price extraction missed the `132€` format and matched other numbers. | `check_price.py` (raw + Playwright) |
| `read.render.nav_links_js_only` (/ae/ar/: raw 112 → rendered 219) | confirmed | **ours only** | **True, count inflated.** Our independent count: raw 112 → rendered **204** same-host links, a real JS-only gap of 92. The engine's 219 = 204 + 15 off-site (the known `collect.py:739` bug). | `count_links.py` |

**Score on high findings:** both runs share 1 clearly true, 3 true-but-minor, 1 doubtful and
1 false positive. Ours adds 1 more true finding (the JS-only links) that `--no-render` can't see.

## What each agent did with the report

| | Lakshya's prompt | Our prompt |
|---|---|---|
| Priority list | Top 5 **in report order** (severity → ICE): correct "sorted by impact" | Top 10 **sorted by ICE alone**: all tied at 7.7, and mediums rank above three highs. **Weaker.** |
| Drill-down | Top finding: evidence, confidence, mechanism, patch, `blocked_by` count | First three findings: evidence, severity, fix, patch |
| Evidence check | 1 finding, via the report's own verification step: "supports" | 3 findings, independent fetch: all "supports", **plus caveats** (the claims are metadata; the subject name "Hej! Welcome to IKEA Global" is a greeting) |
| Caught the false positive? | No (not in scope of the check) | No (not in the first three) |
| Changed files? | No | No (the harness blocked a script file; the agent used `python -c` instead) |

## Conclusions

1. **Both manifests work end to end** on an unseen, judge-like site. Neither is at risk of being "ran-blocked".
2. **Rendering pays off here:** ours found a real JS-only navigation gap that `--no-render` can't see,
   and reports `complete` instead of `partial`. But it costs a Playwright install for judges, and
   the nav-links count is inflated by the engine bug.
3. **Lakshya's priority list is better.** Report order (severity, then ICE) is the right "sorted by
   impact" view. Sorting by ICE alone lets mediums outrank highs. → **Change our prompt** to list
   the top findings in report order and show ICE as a column.
4. **Our evidence check is more critical** (it flags weak or odd findings), but a 3-finding check
   still missed the price false positive, which sat at position 6.
5. **The same false positive appears in both**, since it's the engine's, so judges replaying either
   manifest on a shop will see it. Worth knowing before a judge picks an e-commerce site.
