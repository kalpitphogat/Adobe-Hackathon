# Round 4 constraints checklist

Every rule in the Round 4 brief (`adobe.pdf`, "Round 4 — Prototype Showcase (Live Agent Demo)"),
with how we meet it and the evidence. **Re-check this file after every change.** Status:
✅ met and verified · 🎬 met at recording time (checklist in the run sheet) · ⚠️ known risk, mitigated · ⏳ in progress (commit named in the row once done).

## §1–2 What Round 4 is / what we submit

| # | rule (brief wording, shortened) | status | how we meet it · evidence |
|---|---|---|---|
| 1.1 | Show the Round 3 engine works live, and prove it's reproducible | ✅ | Live run in the video + `REPLAY_IT_Professionals.txt`; rehearsed from empty folders (`rehearsal/`) |
| 1.2 | No GUI needed; a CLI session where an agent runs the marketplace is what they want | ✅ | Claude Code in a terminal (`VIDEO_PART2_RUNSHEET.md`) |
| 2.1 | Submit a recorded video, **≤ 5:00 hard cap** | 🎬 | `VIDEO_SCRIPT.md`: Part 1 ≈ 2:49 incl. title card (cut ladder to 2:32), Part 2 ≤ 2:00 after trimming (target 1:55); total ≈ 4:44 |
| 2.2 | Submit a plain-text file named exactly `REPLAY_YourTeamName.txt` | ✅ | `REPLAY_IT_Professionals.txt` (team name IT_Professionals); name checked by `tools/check_replay.py` |
| 2.3 | Don't resubmit Round 3; they reuse that exact package | ✅ | Nothing in this repo changes it; `round3-frozen/submission.zip` + `SHA256SUMS` |
| 2.4 | **Live run must exercise the same submitted marketplace**, or it fails on integrity | ✅ 🎬 | Demo runs from a fresh unzip of the frozen zip; hash `1c872c59…8dcf` printed in REPLAY; `tools/verify_engine.py` proves the unzipped folder is byte-identical, file by file (155/155), and fails on any changed, missing or extra file (tested) |
| 2.5 | Judges replay the demo on their own machine, **including a URL of their choosing** | ✅ ⚠️ | Any-URL instruction in REPLAY step 2; 25-site survey + IKEA head-to-head (`SCOUTING.md`, `COMPARISON_ikea.md`). Risk: engine false positives on some site types, documented in `NOTES.md` |

## §3 The video

| # | rule | status | how we meet it · evidence |
|---|---|---|---|
| 3.1 | Part 1 methodology **≤ 3:00** | ✅ 🎬 | `VIDEO_SCRIPT.md` Part 1: 389 spoken words ≈ 2:49 at 145 wpm incl. title card and pauses; `tools/check_script_anchors.py` fails if the full cut would pass 3:00 even at 140 wpm; a fixed cut ladder (GEO line, golden line, phone/price line) brings it to 349 words ≈ 2:32 |
| 3.2 | Part 2 trial run **≤ 2:00** | 🎬 | Run sheet timeline ends 1:50; agent output cut to top 5 and a stop-at-first-supported evidence check |
| 3.3 | May crop idle waits; **may not splice** a run that didn't happen | 🎬 | One continuous take; raw file kept; "⏩ trimmed" captions; retake = new URL, never a splice |
| 3.4 | Part 1: how we discovered the findings (field research, what separates cited vs ignored sites, distilled into repeatable checks) | ✅ | `VIDEO_SCRIPT.md` cold open + Act I answer "what separates them" directly: the handout's reach/read/quote sentence (`chunking-model.md:40–43`), crawler roles and what blocking each costs (`ai-bots.json:12–14, :71`, `check_robots.py:286/318`), the GEO finding (`geo-methods.md:14–24`); Act IV: the five-site field test (`DESIGN.md:374–379`) and the zero-recall miss (`DESIGN.md:322–335`) |
| 3.5 | Part 1: how we assigned severities | ✅ | `VIDEO_SCRIPT.md` Act II (severity vs confidence, `apply_cascade`, Rule 0, the `site_b` golden), plus the crawler-role severities in Act I |
| 3.6 | Part 1: how we derived suggested actions (mechanism-sound, prioritised) | ✅ | `VIDEO_SCRIPT.md` Act III (`validate_finding`, patches never invented, ICE lookups, total order) |
| 3.7 | **Anchor every claim to code**; untraceable narration earns no credit | ✅ | Every Part 1 line in `VIDEO_SCRIPT.md` has its file on screen and a `file:line` caption; the 57-row anchor ledger (§5) is checked against the zip itself by `tools/check_script_anchors.py`, locally and in CI (`round4.yml`); claims left out on purpose are listed in §6 |
| 3.8 | Part 2 on **a site the audit has never seen** | ✅ 🎬 | https://docs.pytest.org/ has never been audited (only `tools/prescreen.py`, which doesn't run the engine). Retake → https://www.sphinx-doc.org/ |
| 3.9 | **Enter the URL on camera**; real, continuous; interaction, not a pre-rendered report | 🎬 | REPLAY prompt ends in `URL:`; URL typed live |
| 3.10 | Show the agent invoking the **entrypoint skill**, fetching, reasoning, producing findings | ✅ 🎬 | Claude Code loads it with its Skill tool: `Skill(ai-readiness-orchestrator)` is the first tool call in every rehearsal (`rehearsal/*_skill.md`, `*_final.md`), then `orchestrate.py`; run sheet holds on both |
| 3.11 | **Drill into ≥ 1 finding**: real evidence, its severity, the suggested fix | ✅ 🎬 | Prompt step "drill-down"; run sheet section D |
| 3.12 | **Show fixes sorted/prioritised by impact** | ✅ | Prompt asks for the top 10 in report order (severity → ICE) with ICE as a column; rehearsed on IKEA (`rehearsal/2026-09-24_ikea_opus_newprompt.md`): highs first, ICE shown |
| 3.13 | **State harness and model on camera** | 🎬 | `claude --version` + `/model` at 0:00–0:10 |
| 3.14 | **One line on wiring**: it's really the Round 3 entrypoint, not a hardcoded demo | ✅ 🎬 | On camera: `verify_engine.py` → ENGINE UNCHANGED, then the Skill call; the wiring line at 0:22; session transcript kept afterwards (run sheet F) |
| 3.15 | Everything shown comes from the submitted engine, live, so a judge reaches the same substance | ✅ | Prompt: "do not add findings that are not in the report"; the evidence check is labelled commentary. On IKEA it marked the engine's price finding "not supported" without altering the report |

## §4 Harness and model

| # | rule | status | how we meet it · evidence |
|---|---|---|---|
| 4.1 | Disclose LLM **name and version/date** | ✅ | `LLM_MODEL: Claude Opus 5.5 (API model id: claude-opus-5-5), runs of 2026-09` |
| 4.2 | Disclose harness **name and version** | ✅ ⚠️ | `AGENT_HARNESS: Claude Code v2.1.282`, and ENV_SETUP installs exactly that version. Claude Code auto-updated 2.1.280 → 2.1.281 on 2026-09-24 and to 2.1.282 on 2026-09-25; 2.1.283 was published 2026-09-25 18:46 UTC, so a machine left on auto-update no longer matches. `tools/check_replay.py` now fails if the installed version differs from the REPLAY; the recording machine and judges pin with `claude install 2.1.282` |
| 4.3 | **Exact invoke commands**, clean checkout → emitted report | ✅ | TEST_STEPS 1–3; rehearsed verbatim with `claude -p` |
| 4.4 | Closed/paid harness → **document a fallback run path** | ✅ | REPLAY fallbacks: **A** no Playwright (identical to main when pass 1 finds no empty page; Django one-pass 21 vs 24, the 3 extra false); **B** other model or harness (Sonnet 5, Haiku 4.5: same findings; right pass-2 choice 10/10); **C** no agent, plain Python, the two passes by hand; **D** formatted terminal via one downloaded file, `demo_cli.py`, pinned to a commit with its SHA-256, driving the judge's own unzip (`doctor` 155/155 vs their zip). ⚠️ The repo is private: the download only works if it is made public; **E** always render (the previous main path) |
| 4.5 | Judged on substance, not exact strings | ✅ | Deterministic engine; the agent only reads the report back |

## §5 REPLAY file

| # | rule | status | how we meet it · evidence |
|---|---|---|---|
| 5.1 | Fixed labelled fields: `TEST_SITE_URLS`, `LLM_MODEL`, `AGENT_HARNESS`, `ENV_SETUP`, `TEST_STEPS` (1 command, 2 prompt verbatim, 3 where the report goes), `EXPECTED_OUTPUT` | ✅ | `tools/check_replay.py`: all six present and non-blank; steps 1–3 present |
| 5.2 | **Mandatory and parseable**; missing or blank = unverified | ✅ | `tools/check_replay.py` exits 1 on a missing/blank field or BOM (negative-tested with a blanked `AGENT_HARNESS`) |
| 5.3 | Test URLs are **exact full URLs** | ✅ | `tools/check_replay.py` checks scheme + host for every entry |
| 5.4 | Steps **copy-pasteable, in order, from a clean checkout** on the disclosed harness + model | ✅ | Rehearsed from an empty folder (`rehearsal/`); unzip is `python -m zipfile -e`, identical in bash, PowerShell and cmd; CI (`.github/workflows/replay-portability.yml`) runs ENV_SETUP + steps 1 and 3 + fallbacks A and C on Ubuntu and macOS: all passed 2026-09-24 |
| 5.5 | **Consistent with the video**: harness, model, URLs match | ✅ 🎬 | `tools/check_replay.py` checks the run sheet names the same harness version, model id and on-camera URL; section F cross-checks the recorded video |

## §6 Judging gates

| # | gate | status | how we avoid it |
|---|---|---|---|
| 6.1 | **Integrity floor**: fabricated findings, different engine, spliced run, REPLAY contradicting the video | ✅ 🎬 | Frozen zip + hash; the agent may not add findings; one take; section F cross-check |
| 6.2 | **Unverified floor (ran-blocked)**: unparseable REPLAY, no working invoke path, engine won't run | ✅ ⚠️ | Main path rehearsed from empty folders (`rehearsal/`): two-pass version 10× with `claude -p` on Linux, one-pass version on Windows. ⚠️ Rehearse the two-pass prompt once on Windows before recording (run sheet A.1b). `tools/check_replay.py`; fallbacks A–E tested |
| 6.3 | **Nondeterminism flag**: replay gives materially different findings | ✅ ⚠️ | Deterministic engine (`tests/run_offline.py` PASS on 3.11.15); Django gave the same 24 findings on two runs a day apart (`rehearsal/`). Browser vs no browser measured on 34 sites (`SITE_MATRIX.md`, `STRATEGY_COMPARISON.md`); the main path renders only when pass 1 finds an empty page, a deterministic rule on the crawl's own evidence; `--bundle` re-analysis gives identical findings. Second test URL https://www.theguardian.com/ has a stable critical (robots.txt line 102) and a visible cascade (45 of 52 findings `blocked_by: F-001` on 2026-09-24, 38 of 47 in CI on 2026-09-25), with expected substance in the REPLAY |

## §7 Scope and guardrails

| # | rule | status | evidence |
|---|---|---|---|
| 7.1 | Recommend-only; nothing alters a live site; read-only | ✅ | Engine permits only GET/HEAD (`SKILL.md` guardrails); prompt: "Do not create, change or delete any file yourself" (only the engine writes `audit-output/`) |
| 7.2 | **Respect robots.txt** | ✅ | Engine treats robots.txt as a hard rule (and honours Crawl-delay: gnu.org, `NOTES.md` §6) |
| 7.3 | Same engine as Round 3; a demo round, not a rebuild | ✅ | No file under `demo/` is edited; checked before each recording |
| 7.4 | AI assistance allowed | ✅ | |
| 7.5 | No GUI required | ✅ | |
