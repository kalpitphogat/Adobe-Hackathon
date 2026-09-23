# Round 4 constraints checklist

Every rule in the Round 4 brief (`adobe.pdf`, "Round 4 — Prototype Showcase (Live Agent Demo)"),
with how we meet it and the evidence. **Re-check this file after every change.** Status:
✅ met and verified · 🎬 met at recording time (checklist in the run sheet) · ⚠️ known risk, mitigated · ⏳ in progress (commit named in the row once done).

## §1–2 What Round 4 is / what we submit

| # | rule (brief wording, shortened) | status | how we meet it · evidence |
|---|---|---|---|
| 1.1 | Show the Round 3 engine works live, and prove it's reproducible | ✅ | Live run in the video + `REPLAY_IT_Professionals.txt`; rehearsed from empty folders (`rehearsal/`) |
| 1.2 | No GUI needed; a CLI session where an agent runs the marketplace is what they want | ✅ | Claude Code in a terminal (`VIDEO_PART2_RUNSHEET.md`) |
| 2.1 | Submit a recorded video, **≤ 5:00 hard cap** | 🎬 | Part 1 script ~2:40, Part 2 ≤ 2:00 after trimming |
| 2.2 | Submit a plain-text file named exactly `REPLAY_YourTeamName.txt` | ✅ | `REPLAY_IT_Professionals.txt` (team name IT_Professionals); name checked by `tools/check_replay.py` |
| 2.3 | Don't resubmit Round 3; they reuse that exact package | ✅ | Nothing in this repo changes it; `round3-frozen/submission.zip` + `SHA256SUMS` |
| 2.4 | **Live run must exercise the same submitted marketplace**, or it fails on integrity | ✅ 🎬 | Demo runs from a fresh unzip of the frozen zip; hash `1c872c59…8dcf` printed in REPLAY; checked before recording |
| 2.5 | Judges replay the demo on their own machine, **including a URL of their choosing** | ✅ ⚠️ | Any-URL instruction in REPLAY step 2; 25-site survey + IKEA head-to-head (`SCOUTING.md`, `COMPARISON_ikea.md`). Risk: engine false positives on some site types, documented in `NOTES.md` |

## §3 The video

| # | rule | status | how we meet it · evidence |
|---|---|---|---|
| 3.1 | Part 1 methodology **≤ 3:00** | ✅ 🎬 | `VIDEO_PART1_SCRIPT.md`, word count checked (≤ 2:50 target) |
| 3.2 | Part 2 trial run **≤ 2:00** | 🎬 | Run sheet timeline ends 1:55 |
| 3.3 | May crop idle waits; **may not splice** a run that didn't happen | 🎬 | One continuous take; raw file kept; "⏩ trimmed" captions; retake = new URL, never a splice |
| 3.4 | Part 1: how we discovered the findings (field research, what separates cited vs ignored sites, distilled into repeatable checks) | ✅ | Beat 1 of the Part 1 script |
| 3.5 | Part 1: how we assigned severities | ✅ | Beat 2 |
| 3.6 | Part 1: how we derived suggested actions (mechanism-sound, prioritised) | ✅ | Beat 3 |
| 3.7 | **Anchor every claim to code**; untraceable narration earns no credit | ✅ | Every line of the Part 1 script names a file + line in the unzipped submission; checked 2026-09-23; unanchored claims listed as excluded |
| 3.8 | Part 2 on **a site the audit has never seen** | ✅ 🎬 | https://docs.pytest.org/ has never been audited (only `tools/prescreen.py`, which doesn't run the engine). Retake → https://www.sphinx-doc.org/ |
| 3.9 | **Enter the URL on camera**; real, continuous; interaction, not a pre-rendered report | 🎬 | REPLAY prompt ends in `URL:`; URL typed live |
| 3.10 | Show the agent invoking the **entrypoint skill**, fetching, reasoning, producing findings | ✅ 🎬 | Prompt makes the agent read `skills/ai-readiness-orchestrator/SKILL.md` and run `orchestrate.py`; run sheet holds on that command |
| 3.11 | **Drill into ≥ 1 finding**: real evidence, its severity, the suggested fix | ✅ 🎬 | Prompt step "drill-down"; run sheet section D |
| 3.12 | **Show fixes sorted/prioritised by impact** | ⏳ | Current prompt sorts by ICE alone, which let mediums outrank highs on IKEA (`COMPARISON_ikea.md`). Fix ⏳: report order (severity → ICE) with ICE shown |
| 3.13 | **State harness and model on camera** | 🎬 | `claude --version` + `/model` at 0:00–0:10 |
| 3.14 | **One line on wiring**: it's really the Round 3 entrypoint, not a hardcoded demo | 🎬 | Run sheet line at 0:25 |
| 3.15 | Everything shown comes from the submitted engine, live, so a judge reaches the same substance | ✅ | Prompt forbids adding findings; the agent's evidence check is labelled commentary |

## §4 Harness and model

| # | rule | status | how we meet it · evidence |
|---|---|---|---|
| 4.1 | Disclose LLM **name and version/date** | ✅ ⏳ | `LLM_MODEL: Claude Opus 5.5 (API model id: claude-opus-5-5)`; run date to add ⏳ |
| 4.2 | Disclose harness **name and version** | ✅ | `AGENT_HARNESS: Claude Code v2.1.280` (`claude --version`) |
| 4.3 | **Exact invoke commands**, clean checkout → emitted report | ✅ | TEST_STEPS 1–3; rehearsed verbatim with `claude -p` |
| 4.4 | Closed/paid harness → **document a fallback run path** | ⏳ | No-agent path documented but untested; other-model and no-Playwright paths ⏳ |
| 4.5 | Judged on substance, not exact strings | ✅ | Deterministic engine; the agent only reads the report back |

## §5 REPLAY file

| # | rule | status | how we meet it · evidence |
|---|---|---|---|
| 5.1 | Fixed labelled fields: `TEST_SITE_URLS`, `LLM_MODEL`, `AGENT_HARNESS`, `ENV_SETUP`, `TEST_STEPS` (1 command, 2 prompt verbatim, 3 where the report goes), `EXPECTED_OUTPUT` | ✅ | `tools/check_replay.py`: all six present and non-blank; steps 1–3 present |
| 5.2 | **Mandatory and parseable**; missing or blank = unverified | ✅ | `tools/check_replay.py` exits 1 on a missing/blank field or BOM (negative-tested with a blanked `AGENT_HARNESS`) |
| 5.3 | Test URLs are **exact full URLs** | ✅ | `tools/check_replay.py` checks scheme + host for every entry |
| 5.4 | Steps **copy-pasteable, in order, from a clean checkout** on the disclosed harness + model | ✅ | Rehearsed from an empty folder (`rehearsal/`) |
| 5.5 | **Consistent with the video**: harness, model, URLs match | ✅ 🎬 | `tools/check_replay.py` checks the run sheet names the same harness version, model id and on-camera URL; section F cross-checks the recorded video |

## §6 Judging gates

| # | gate | status | how we avoid it |
|---|---|---|---|
| 6.1 | **Integrity floor**: fabricated findings, different engine, spliced run, REPLAY contradicting the video | ✅ 🎬 | Frozen zip + hash; the agent may not add findings; one take; section F cross-check |
| 6.2 | **Unverified floor (ran-blocked)**: unparseable REPLAY, no working invoke path, engine won't run | ✅ ⏳ | Main path rehearsed 3× from empty folders; checker + three tested fallbacks ⏳ |
| 6.3 | **Nondeterminism flag**: replay gives materially different findings | ✅ ⚠️ ⏳ | Deterministic engine (`tests/run_offline.py` PASS on 3.11.15); Django gave the same 24 findings on two runs a day apart (`rehearsal/`). ⏳ a stable second URL (Guardian robots.txt) and documenting how a Playwright run and a `--no-render` run differ |

## §7 Scope and guardrails

| # | rule | status | evidence |
|---|---|---|---|
| 7.1 | Recommend-only; nothing alters a live site; read-only | ✅ | Engine permits only GET/HEAD (`SKILL.md` guardrails); prompt forbids modifying `skills/` (stricter "no file changes" wording ⏳) |
| 7.2 | **Respect robots.txt** | ✅ | Engine treats robots.txt as a hard rule (and honours Crawl-delay: gnu.org, `NOTES.md` §6) |
| 7.3 | Same engine as Round 3; a demo round, not a rebuild | ✅ | No file under `demo/` is edited; checked before each recording |
| 7.4 | AI assistance allowed | ✅ | |
| 7.5 | No GUI required | ✅ | |
