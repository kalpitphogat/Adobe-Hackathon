# Video Part 2: Live trial run (hard cap 2:00 after trimming)

> **What to say** is in [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md) §2, with a drill-down card for each likely
> finding. This run sheet stays the operations manual: setup (§A), what's on screen (§B), and what to
> do if something breaks (§E).

**Rubric (35 points):** *"On an unseen URL, the live agent run surfaces real, evidence-backed
findings — few misses, few false positives."*
**Integrity gate:** one real, continuous run. Trimming idle waits is allowed; splicing is not.
The URL typed on camera, the model and the harness must match `REPLAY_IT_Professionals.txt`.

On-camera URL: **https://docs.pytest.org/**. It has never been audited by our engine; it was
only pre-screened for robots.txt and homepage links with `tools/prescreen.py`.
**Do not run the audit on it before recording.** Every run after the first is a "seen" site.

---

## A. Before recording (off camera, ~10 min)

0. **Run the checker** from the repo root: `.venv\Scripts\python.exe tools\check_replay.py` must print
   `0 problem(s)`. It fails if Claude Code has auto-updated away from the version in the
   REPLAY (it did once already, 2.1.280 → 2.1.281). If it fails on the version, update
   `AGENT_HARNESS` and this run sheet to the installed version and re-run a rehearsal
   (`tools\rehearse.ps1` on a *seen* site), or pin with `claude install <version>`.
1. **Fresh folder, exactly as REPLAY step 1** (Windows PowerShell, at the repo root of any
   machine's clone). Stop before `claude`; that part happens on camera:
   ```powershell
   Remove-Item -Recurse -Force demo-live -ErrorAction SilentlyContinue
   mkdir demo-live; Copy-Item round3-frozen\submission.zip demo-live\; cd demo-live
   ..\.venv\Scripts\Activate.ps1
   python --version            # must print Python 3.11.15
   python -m zipfile -e submission.zip brand-ai-readiness-audit
   cd brand-ai-readiness-audit
   python -c "import shutil; shutil.copytree('skills', '.claude/skills')"
   $env:DISABLE_AUTOUPDATER = "1"   # keep Claude Code on the disclosed version in this terminal
   $env:PYTHONUTF8 = "1"            # UTF-8 for every python the agent runs (no cp1252 crashes)
   ```
   `demo-live/` is new, so there is no leftover `audit-output/`. It's git-ignored.
1b. **Rehearse the prompt once on this machine, on a *seen* site**:
   `powershell -File tools\rehearse.ps1 -Url https://www.docker.com/ -Label docker_confirmed`.
   The two passes were rehearsed 10 times on Linux (`rehearsal/2026-09-25_twopass_*`); the
   2026-09-26 table change (top 5 *confirmed* findings, a verdict on every row) has **not** been
   rehearsed yet. Check that the agent runs pass 1 with `--no-render --out ./audit-precheck`,
   prints the count and picks pass 2 by it; that its table holds only confirmed findings, with the
   likely count underneath; and that it gives every row a verdict. On docker.com the top confirmed
   finding was a `trust.integrity.prompt_injection` false positive (a blog post that says "system
   prompt"), so that row should come back *not supported*.
2. **Integrity:** `python ..\..\tools\verify_engine.py ..\submission.zip .` must end with
   `RESULT : ENGINE UNCHANGED` (155 files, plus the 73-file `.claude/skills` copy). You'll run
   this same command on camera.
3. **Network:** open https://docs.pytest.org/ once in a browser to confirm it's up.
   (A browser visit isn't an audit run.)
4. **Screen:** Windows Terminal maximised, font size 16+, dark theme. Close notifications
   (Focus Assist on). Have VS Code open on `demo-live/` in a second window for step D.
5. **Recorder:** OBS (or Xbox Game Bar, `Win+Alt+R`), full screen, microphone on. **Keep the
   raw, untrimmed file**: it's your proof the run was continuous if anyone asks.
6. **Clipboard:** copy the prompt from `REPLAY_IT_Professionals.txt` step 2, **without the
   final `<URL>`**, i.e. ending in `URL: ` (with the trailing space).
   You'll type the URL by hand on camera.

---

## B. The run (what's on screen, what you say)

Times are **after trimming**. The raw recording will be ~3–5 min; the agent's thinking and the
engine's crawl are the parts you cut.

| time | on screen | you say |
|---|---|---|
| 0:00 | Terminal in `demo-live\brand-ai-readiness-audit`. Run `python ..\..\tools\verify_engine.py ..\submission.zip .` → `ENGINE UNCHANGED`. Then `claude --version` → `2.1.282 (Claude Code)`. | "Part two, live. This folder is our Round 3 zip, unzipped: every file byte-identical to what we submitted. The harness is Claude Code 2.1.282…" |
| 0:08 | Type `claude --model claude-opus-5-5 --allowedTools "Skill" "Bash(python:*)" "PowerShell(python:*)" "Read"`. Once it opens, type `/model` so the model is visible, then Esc. | "…driving Claude Opus 5.5." |
| 0:15 | Paste the prompt, **type** `https://docs.pytest.org/` at the end, press Enter. | "I paste the prompt from our REPLAY file and type a site our audit has never seen." |
| 0:22 | **`Skill(ai-readiness-orchestrator)`** appears, then pass 1: `python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://docs.pytest.org/ --no-render --out ./audit-precheck`. **Hold on each for 2 s.** Approve any permission prompt on camera. | "Wiring: the agent loads our entrypoint skill and runs its orchestrator. No demo code, no hardcoded results." |
| — | *(trim the crawl wait; put a small on-screen caption "⏩ crawl, ~40 s trimmed")* | |
| 0:30 | The agent's count of pages with no same-site links, then pass 2 (`--bundle ./audit-precheck/evidence`, or the browser run if the count is above 0), and its one line saying which and why. **Hold 2 s on that line.** | "First pass without a browser. A browser only helps when a crawler sees an empty page, so the agent checks for that. Here it [did / didn't] find one, so it [renders / re-analyses the same evidence]." Say what's on screen. |
| 0:38 | Agent reads `audit-output/audit-report.json`, prints status + counts. | "Six audit skills over one crawl. The findings come from our engine; the model only runs it and double-checks it." If the status is `partial`: "Partial means the report lists what it didn't measure, here the browser checks." |
| 0:45 | Agent's **priority table**: the top 5 **confirmed** findings in report order, ICE and verdict columns, and the line under it counting the likely ones. | "The fixes in priority order: severity first, then ICE, meaning impact, confidence and ease. These are the ones a deterministic check confirmed; the likely ones are counted right under the table." |
| 1:00 | Agent's **evidence check**: a verdict on **every row**, each from its own fetch. | "Before trusting them, the agent re-fetches every page in the table itself, raw and rendered where it matters, and marks each one supported or not. The report stays exactly as the engine wrote it." |
| 1:15 | Agent's **drill-down** on that finding. Optionally flip to VS Code (section D). | Name the finding; walk evidence, severity, fix and patch (section D wording). |
| 1:50 | — | "Same steps, same URL, in REPLAY_IT_Professionals.txt." |

**Wording rule:** say only what's on screen. If the report says `partial`, say partial. Don't
claim a number of checks or pages the output doesn't show.

---

## C. Which finding gets the drill-down

The prompt makes the agent pick it: **the highest-ranked row of its table that its own evidence
check marked supported**. In rehearsals that was `extract.sd.absent_on_eligible_page` (Django, Sonnet and Opus),
`read.render.nav_links_js_only` where the gap was real (IKEA, verified 112 → 204 same-host links),
and `reach.robots.ai_search_bot_blocked` (Guardian). Follow the agent. Only if it picks one of the
"never" checks below should you talk over a different confirmed finding from its table, in this order:

1. **`extract.sd.absent_on_eligible_page` ("… carry no structured data at all")**, the first
   choice. It was confirmed on 10 of 10 pages checked independently, and comes with a paste-ready JSON-LD patch.
2. **`read.render.raw_text_gap` ("Most of this page's text only exists after JavaScript runs")**
   if it fires. It compares word counts from the raw HTML with the Chromium-rendered page.
3. Any other **`confirmed`** finding whose evidence names a URL and a count you can check.

**Never drill into:**
- `read.render.nav_links_js_only` ("internal link graph only exists after JavaScript runs"),
  **unless** the agent's rendered-page count backs it up (as on IKEA). The engine counts
  off-site links on the rendered side (`NOTES.md` §8), so the gap is often not real.
- `act.orient.no_value_proposition`, `act.cta.absent_for_page_type`: `likely`, and misfire often.
  They are only in the table when fewer than five findings are confirmed.
- `trust.integrity.prompt_injection` on a page that merely discusses AI (the verdict column should
  already say *not supported*).

---

## D. The drill-in (~30 s)

In VS Code (`demo-live/brand-ai-readiness-audit/`), open `audit-output/audit-report.json`, `Ctrl+F` the finding's
`check_id`, and point at four fields in turn:

| field | say |
|---|---|
| `evidence` | "What was observed, with the URLs: these pages carry no JSON-LD, microdata or RDFa." |
| `severity` / `confidence` | "High, because the fact can't be extracted in typed form. Confirmed: a deterministic check saw it." |
| `suggested_action.mechanism` | "Why the fix works: typed data can be extracted without guessing from prose." |
| `suggested_action.patch` and `ice` | "The paste-ready patch. Any value we couldn't read from the site says `__FILL_IN__`, not a guess. ICE is the priority score from the table." |

Then show the proof in 5 s: in the terminal, the agent's evidence-check line for this finding.
If you have time, run the finding's own `verification` command (it's in the JSON). On
Windows use the python form rather than `grep`:
```powershell
python -c "import urllib.request as u;print(u.urlopen('https://docs.pytest.org/en/stable/').read().decode().count('application/ld+json'))"
```
(Use the URL named in the evidence; `0` = the finding holds.)

---

## E. If something goes wrong

| what happens | do this |
|---|---|
| The agent's evidence check says a row is **not supported** (likely for `nav_links_js_only`, or `prompt_injection` on a page that only discusses AI) | **Keep it in.** Say: "The evidence check disagrees here, so we'd verify before acting. The report stays exactly as the engine wrote it." That's an honest, strong moment. Don't drill into that finding. |
| Claude Code asks permission for a command | Approve it on camera ("yes"). It's part of the real run; trim the pause. On Windows the agent sometimes tries the orchestrator first as a chained command (`...; echo $LASTEXITCODE`), which is blocked; it then retries the plain command. Only one crawl runs (checked in `rehearsal/*_skill.md`). |
| Run exits with `no evidence bundle was produced` | You aren't in the marketplace root. Stop, `cd` into `demo-live\brand-ai-readiness-audit`, and **start a new take on the backup URL** (below). |
| Run takes past 5 min / crashes on a crawl delay | New take on the backup URL; REPLAY troubleshooting mentions `--time-budget 600`. |
| The agent chains a command (`...; echo $LASTEXITCODE`) or pipes it | It's blocked, then it retries plain. The prompt now asks for no pipes or chaining; Opus followed it in the final rehearsals. Trim the retry. |
| The agent uses `python3` and gets blocked | Approve it on camera, or restart with `"PowerShell(python3:*)"` added (Sonnet did this once on Linux). |
| Any retake | pytest is now "seen". Use **https://www.sphinx-doc.org/** (pre-screened, never audited), and **change the first `TEST_SITE_URLS` entry, step 2's example and this run sheet to match**, then re-run `tools\check_replay.py`. Never splice two takes. |
| Output is too long for 2:00 | Scroll faster in the edit; trim the agent's thinking. Don't cut the URL entry, the command, the priority table, the evidence check or the drill-down. |

---

## F. After recording

1. Watch the trimmed video once against the REPLAY file: harness `Claude Code v2.1.282`, model
   `Claude Opus 5.5`, URL `https://docs.pytest.org/` (or the backup, if you switched). All three must match.
2. Copy `demo-live/brand-ai-readiness-audit/audit-output/` to `recorded-run/` in this repo and commit it.
3. **Keep the proof the run was real and continuous.** Copy the session transcript Claude Code saved
   (the newest `.jsonl` in the folder under `%USERPROFILE%\.claude\projects\` whose name ends in
   `demo-live-brand-ai-readiness-audit`; `RECORDING_FLOW.md` Stage 4 has the command)
   to `recorded-run/session.jsonl`, and write the raw (untrimmed) video's filename, length and
   `(Get-FileHash <raw-video>).Hash` into `recorded-run/README.md`. The video file itself stays out of git.
   Run `python tools\tool_calls.py recorded-run\session.jsonl` once to confirm it shows the Skill call.
4. Run `tools\check_replay.py` one last time. Then check the total video (Part 1 + Part 2) is ≤ 5:00. Part 1 ≤ 3:00, Part 2 ≤ 2:00, each on its own.
