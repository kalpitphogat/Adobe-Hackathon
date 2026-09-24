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
mismatch. Run it right before recording. Judges pin with `claude install 2.1.281`.

## 10. The findings don't depend on the model; the evidence check does

Same prompt, same site (docs.djangoproject.com), Claude Code 2.1.281: Opus 5.5, Sonnet 5 and
Haiku 4.5 all got the **same 24 findings in the same order** (`tools/diff_reports.py`). Opus and
Sonnet loaded the rendered page and flagged the three `nav_links_js_only` findings as not
supported; Haiku didn't load it, even when the prompt required it, and called them supported.
