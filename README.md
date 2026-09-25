# Brand AI-Readiness Audit: Round 4 live agent demo

**Team IT_Professionals:** Lakshya, Tanmay, Kalpit · Adobe University Hackathon 2026, Round 4

Round 4 is a demonstration and reproducibility round, not a rebuild. We submit a video (≤ 5:00)
and `REPLAY_IT_Professionals.txt`. The engine in the video is our Round 3 Agent Skill
Marketplace, **unchanged**: `round3-frozen/submission.zip`, sha256
`1c872c598dcac741c712cbf9e671f024881a9ba251e2b4da66995f81b6cf8dcf`. An AI agent runs it live from
the command line against a site the audit has never seen.

## The run at a glance

| | |
|---|---|
| Engine | Round 3 `submission.zip`, unchanged (hash above) |
| Entrypoint skill | `skills/ai-readiness-orchestrator` (`SKILL.md` → `scripts/orchestrate.py`) |
| Agent harness | Claude Code v2.1.282, loading the entrypoint with its Skill tool |
| LLM | Claude Opus 5.5 (`claude-opus-5-5`) |
| Live-run URL | https://docs.pytest.org/ (never audited before the recording) |
| Second test URL | https://www.theguardian.com/ (stable: robots.txt critical + gate cascade) |
| Setup | Python 3.11.15 + Playwright 1.63.0 (Chromium); fallbacks need neither |
| How it runs | Two passes: without a browser first; the agent renders only if a page came back with no same-site links (`SITE_MATRIX.md`) |
| Report | `audit-output/audit-report.json`, plus `report.md` and `fix_patches/` |

## Replaying it

The exact commands and the verbatim prompt are in **`REPLAY_IT_Professionals.txt`**. Every path
below was actually run: on our Windows machine (`rehearsal/` has the transcripts) or in CI (Linux/macOS row):

| path | who it's for | tested |
|---|---|---|
| **Main**: Claude Code + Opus 5.5 + Playwright, REPLAY steps 1–3 (two passes) | reproduces the video | 10 `claude -p` rehearsals on Linux (`rehearsal/2026-09-25_twopass_*`); the one-pass version on Windows: Django, IKEA, Guardian |
| **A**: no Playwright | no browser install | identical to the main path when pass 1 finds no empty page; Django one-pass: 21 vs 24 findings, the 3 extra all false `nav_links_js_only` |
| **B**: another model or agent harness, same prompt | no Opus, or no Claude Code | Sonnet 5 and Haiku 4.5: same 24 findings as Opus (one-pass); right pass-2 choice 10/10 (two-pass) |
| **C**: no agent at all, any Python 3.9+ | no model, no special setup | the same two passes by hand; Python 3.13 (Windows), 3.12 (Ubuntu), 3.14 (macOS), no venv: exit 0 |
| **D**: formatted terminal (`demo_cli.py`, one pinned file) | a readable view without an agent | drives the judge's own unzip; `doctor` checks it 155/155 against their zip |
| **E**: always render | partly-JavaScript sites | the previous main path; all browser checks measured, with the false positives in `SITE_MATRIX.md` |
| **Linux / macOS** | judges not on Windows | CI runs ENV_SETUP as written + steps 1 and 3 + A and C on Ubuntu and macOS: all pass |

`tools/check_replay.py` checks the REPLAY file (fields, URLs, steps) and that it matches the run
sheet and the installed harness version. It must print `0 problem(s)` before recording.

## Where the reasoning lives in code

All paths are inside the unzipped submission; line numbers were checked against it.

| idea | implemented in |
|---|---|
| reach → read → extract → trust ordering and the gate cascade | `skills/ai-readiness-orchestrator/scripts/gate_model.py:117` (`apply_cascade`), `references/gate-rules.md` |
| engagement is never capped by crawler access (Rule 0) | `gate_model.py:128`; Rule 0b in `skills/engagement-audit/scripts/gating.py:32` |
| retrieval vs training crawlers | `skills/crawl-access-audit/references/ai-bots.json` (29 bots); `scripts/check_robots.py:286` critical, `:318` info |
| what each severity means; confidence kept separate | `skills/ai-readiness-orchestrator/references/severity-model.md` |
| every fix carries a mechanism, or the finding is rejected | `orchestrate.py:242` (`validate_finding`) |
| missing values say `__FILL_IN__`, never a guess | e.g. `skills/structured-data-audit/scripts/check_hierarchy.py:211` |
| ICE score and total ranking order | `skills/ai-readiness-orchestrator/scripts/severity.py:26–29`, `:68` |
| fixed false positives can't come back | `tests/test_regressions.py` R1–R12 |

The Part 1 narration with the same anchors is `VIDEO_PART1_SCRIPT.md`.

**When to use the browser** is decided by the agent, not the engine, from pass 1's own evidence:
`SITE_MATRIX.md` (11 sites, including 5 test sites that isolate each case), `STRATEGY_COMPARISON.md`
(23 sites) and `JS_DETECTION_STUDY.md` (18 sites). Always rendering gave 24 true and 24 false browser
findings across them; two passes gave 13 true and 1 false.

## What we verified, including where the engine is wrong

We didn't take the engine's word for it. `SCOUTING.md` covers 25 live sites; `NOTES.md` has 10
verified behaviours (with the fix for each in how we set up and run it); `COMPARISON_ikea.md`
compares our REPLAY and Lakshya's on an unseen site. Known engine false positives (the engine
stays frozen) include `read.render.nav_links_js_only` on pages with many off-site links, and a
structured-data price mismatch on IKEA. The agent's evidence check caught both in rehearsals
(`rehearsal/2026-09-24_django_*.md`, `rehearsal/2026-09-24_ikea_opus_newprompt.md`).

## Repo layout

| path | what |
|---|---|
| `REPLAY_IT_Professionals.txt` | the reproduction manifest (submitted with the video) |
| `VIDEO_PART1_SCRIPT.md`, `VIDEO_PART2_RUNSHEET.md` | narration and live-run sheet |
| `CONSTRAINTS.md` | every rule in the Round 4 brief, with status and evidence |
| `round3-frozen/` | the Round 3 upload and its hash; never edited |
| `rehearsal/` | agent transcripts from every rehearsal, dated |
| `tools/` | `check_replay.py`, `verify_engine.py`, `rehearse.ps1`, `tool_calls.py`, `prescreen.py`, `scout.py`, `summarize.py`, `diff_reports.py`, `count_links.py`, `check_price.py` |
| `.github/workflows/` | `replay-portability.yml`: the REPLAY on Ubuntu and macOS |
| `NOTES.md`, `SCOUTING.md`, `COMPARISON_ikea.md` | findings about the engine |

## Local setup (Windows, PowerShell)

```powershell
uv python install 3.11.15
uv venv --python 3.11.15 .venv
uv pip install --python .venv\Scripts\python.exe playwright==1.63.0
.venv\Scripts\python.exe -m playwright install chromium
Expand-Archive round3-frozen\submission.zip demo -Force
cd demo; ..\.venv\Scripts\python.exe tests\run_offline.py   # PASS on 3.11.15
```

## Deliverables

- [x] `REPLAY_IT_Professionals.txt`, rehearsed from clean unzips, with three tested fallbacks
- [x] `VIDEO_PART1_SCRIPT.md`: 380 words (~2:43), every claim tied to a file and line
- [x] `VIDEO_PART2_RUNSHEET.md`: live run on https://docs.pytest.org/
- [ ] The video: Part 1 ≤ 3:00, Part 2 ≤ 2:00, total ≤ 5:00

## How this was built

One change per commit, pushed as it happened: `git log --oneline` reads as the build history.
