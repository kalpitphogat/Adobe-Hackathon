# Verified facts about the frozen engine

Each item below was reproduced on 2026-09-23 on Windows 11 with Python 3.11.15 and Playwright 1.63.0,
against `round3-frozen/submission.zip` unzipped into `demo/`. None of it can be fixed in
code (the engine is frozen); every item is handled by how we set up, invoke and demo it.

## 1. Python version decides whether the goldens match

`tests/run_offline.py` compares against goldens built with **Python 3.11.15**. The only
field that moves between versions is `generator.tool_versions.python`, but that is enough to
fail the byte-for-byte check. On 3.11.15 it prints
`PASS: offline, deterministic, goldens current, control clean.` On 3.13 all six sites drift.
→ Setup pins 3.11.15 via `uv` (python.org stops shipping Windows installers after 3.11.9).

## 2. Relative `--out` only works from the marketplace root

`orchestrate.py` runs the collector with `cwd=<marketplace root>`, but checks for the bundle
relative to the caller's cwd. Run from anywhere else with a relative `--out` and it exits 1:
`error: no evidence bundle was produced; cannot write a report` (the bundle lands under
`demo/<out>/evidence/` instead).
→ Always `cd` into the marketplace root and use `--out ./audit-output` (the documented form),
or pass an absolute `--out`.

## 3. `tests/test_ssrf.py` S1 fails on Windows

`http://127.1/` (short-form loopback) is not refused on Windows; the other 29 assertions pass,
and the result is the same on 3.11.15 and 3.13. Do not show this suite on camera.

## 4. Playwright changes the findings

stripe.com, same day:

| | renderer | checks run | findings | high |
|---|---|---|---|---|
| no Playwright | none | 24/66 | 69 | 10 |
| Playwright | playwright | 25/66 | 71 | 10 |

With Playwright the engine adds `read.render.raw_text_gap` (confirmed): the raw-HTML-vs-rendered-DOM
evidence the brief names first. Without it that check is "not assessed".
→ REPLAY `ENV_SETUP` installs Playwright + Chromium, so judges get the same checks we show.

## 5. Engagement checks can misfire on some sites

On stripe.com, `act.orient.no_value_proposition` fires on a homepage whose H1 plainly states
the offer, and `act.cta.absent_for_page_type` fires on `marketplace.stripe.com` with "0 links".
Both are `likely`, not `confirmed`. The rubric penalises false positives in the live run.
→ Choose the demo URL deliberately; in the walkthrough, drill into a `confirmed` finding.
The 25-site survey in `SCOUTING.md` shows this pattern across site types.

## 6. A large `Crawl-delay` can crash a default run

https://www.gnu.org/ sets `Crawl-delay: 4`. The collector honours it (correct), but 25 pages
at 4 s each pushes it to ~292 s against its 180 s share of the budget. At 300 s the orchestrator
kills it, no bundle exists, and the run exits 1 with `no evidence bundle was produced`.
Reproduced twice. `--no-render` finished in 293 s with exit 0, so this is timing, not rendering.
→ REPLAY troubleshooting: add `--time-budget 600` (an existing engine flag) for sites with a
large Crawl-delay. That raises the collector's share to 360 s and the overall ceiling to 600 s.

## 7. Talking about prompt injection is flagged as prompt injection

`trust.integrity.prompt_injection` fires at **critical/confirmed** on pages whose text merely
discusses the topic (linear.app/legal/aup, pydantic.dev/docs/ai). Avoid AI-topic sites for the
demo; if a judge's site trips it, the evidence string shows the quoted phrase, which is easy to
check by hand.

## 8. `read.render.nav_links_js_only` counts off-site links on the rendered side

`collect.py:739` counts every rendered href; `collect.py:632` counts only internal raw hrefs.
Independent Playwright counts show identical same-host link sets raw vs rendered on Django docs,
mozilla.org and htmx.org, where the engine reported gaps of 38, 51 and 42. The finding is
high/confirmed and false. Found by the REPLAY prompt's evidence check on 2026-09-23. Details in
`SCOUTING.md`.

## 9. Claude Code updates itself

Between 2026-09-23 and 2026-09-24 the harness went from 2.1.280 to 2.1.281 on its own. A REPLAY
that names one version while the video shows another is an integrity failure (brief §5).
→ `tools/check_replay.py` compares `claude --version` with `AGENT_HARNESS` and fails on a
mismatch. Run it right before recording. It kept moving: 2.1.282 on 2026-09-25, and 2.1.283 was
published later that day (18:46 UTC). The recording machine and judges pin with
`claude install 2.1.282`, the version in the REPLAY.

## 10. The findings don't depend on the model; the evidence check does

Same prompt, same site (docs.djangoproject.com), Claude Code 2.1.281: Opus 5.5, Sonnet 5 and
Haiku 4.5 all got the **same 24 findings in the same order** (`tools/diff_reports.py`). Opus and
Sonnet loaded the rendered page and flagged the three `nav_links_js_only` findings as not
supported; Haiku didn't load it, even when the prompt required it, and called them supported.

## 11. Brotli responses are read as garbage

https://www.berkshirehathaway.com/ answers with `content-encoding: br` even though the engine asks
for `Accept-Encoding: gzip, deflate` (`fetch.py:260`). `_decompress` (`fetch.py:197–207`) handles
only gzip and deflate, so the saved "HTML" is compressed bytes: the page reads as 0 links and 0 words
and the audit sees nothing. A browser decodes it fine. Found by `JS_DETECTION_STUDY.md` on
2026-09-25. Frozen engine: recorded, not fixed.

## 12. The browser pass is chosen per site (two passes)

§8's off-site counting hits hardest on small pages: a test page with 2 internal and 4 social links
got three high, confirmed `nav_links_js_only` findings (`raw 2, rendered 6`; same-site 2 and 2).
On six public sites the browser changed no finding at all. So the agent now runs pass 1 with
`--no-render`, and renders only if a page came back with status 200 and no same-site links;
otherwise it re-analyses pass 1's evidence with `--bundle`. Across 34 sites: always rendering gave
24 true and 24 false browser findings, two passes 13 true and 1 false (`SITE_MATRIX.md`).
Rehearsed 10× with `claude -p` (`rehearsal/2026-09-25_twopass_*`).

## 13. The agent's table shows confirmed findings, and it re-checks every row

The engine ranks by severity, then ICE, and several high-severity "likely" heuristics
(`extract.ans.fact_coverage_gap`, `act.orient.no_value_proposition`,
`read.nontext.key_fact_image_only`, `act.cta.absent_for_page_type`) crowd the top of the report.
On 2026-09-26 both passes were run on 20 public sites (the ones a restricted network allowed), and
each row of two candidate tables was graded by hand from its evidence, every disputed row
against the live page (curl): T true, S true but rated too severe, W weak (a count or claim a reader cannot check, or a borderline threshold),
F false.

| table | T | S | W | F |
|---|---|---|---|---|
| first 5 findings in report order (the old prompt) | 28 | 7 | 31 | 34 |
| first 5 **confirmed** findings (the new prompt) | 75 | 7 | 7 | 11 |

Confirmed-table rows, in order (F and S noted):

| site | rows | notes |
|---|---|---|
| jsr.io | S T T W W | S: noindex critical on package-version pages |
| rubygems.org | T W T T T | W: `/sign_out` 404 counted as a broken link |
| pkg.go.dev | T T T W W | |
| hub.docker.com | T T T T T | |
| bitbucket.org | S T F T T | S: http link to the status page rated high; F: its 403 counted as broken |
| nodejs.org/en | T T T T T | |
| www.nuget.org | T T T F T | F: `/packages` (a listing) treated as dated content |
| pub.dev | S F T F T | F: viewport on `feed.atom`; F: plain-text sitemaps called "not a sitemap" |
| hex.pm | T T T T T | |
| metacpan.org | T T F W F | F: soft-404 and thin content produced by a bot-protection page |
| packagist.org | S T T T W | S: noindex critical on `/statistics` |
| pypi.org | T T T T T | |
| www.docker.com | F T T T T | F: prompt injection = a blog post saying "system prompt" |
| www.anaconda.com | F T T T T | F: prompt injection = product pages saying "prompt injection" |
| ubuntu.com | S F S T T | F: AI group disallows only noise paths, called a block; S: noindex, cross-host canonical |
| cloud.google.com | F T T T T | F: prompt injection; T: robots.txt and sitemap.xml return HTML (checked with curl) |
| www.apache.org | T T T T T | |
| kotlinlang.org | T T T T T | |
| gradle.org | S F T T T | F: viewport on a 162-byte redirect stub |
| yarnpkg.com | T T T T T | |

Six of the 11 F rows are the three cases prompt part 3 now names (topic text read as an
instruction, a feed or stub read as a page, a partial robots.txt group read as a block). The
prompt keeps the report untouched: the table is chosen by the engine's own `confidence` field, and
the line under it gives the likely count and the highest likely finding.

Also run that day: 12 small test sites built for the purpose (a clean control plus one planted
defect each). The engine missed old content (newest date 2018, prices "last reviewed January
2018") and a schema `foundingDate` that contradicts the page (both now in the REPLAY's KNOWN
LIMITS). It also never reports a missing meta description (the collector reads it, but no check
fires on its absence), and it reported a site with no structured data at all only as a medium
identity finding.

Not yet rehearsed with an agent: the table selection above was replayed on the saved reports. Run
sheet §A 1b rehearses it once with `claude -p` before recording.
