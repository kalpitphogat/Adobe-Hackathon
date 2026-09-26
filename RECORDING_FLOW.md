# Recording flow: what to run, what to say

One page for the person recording, in order: every command or click, and the exact line to say
with it. The spoken lines are copied word for word from [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md)
(branch `final-3`). If the two ever differ, `VIDEO_SCRIPT.md` wins for what you say and
[`VIDEO_PART2_RUNSHEET.md`](VIDEO_PART2_RUNSHEET.md) wins for what you type.

Machine: **Tanmay's Windows PC**, PowerShell, repo clone at `C:\verify-final3`.

How to read this file:
- **RUN** is typed in PowerShell.
- **DO** is a click or key in VS Code or the terminal.
- **SAY** is spoken. **Bold** words get stress, `·` is a half-beat pause.
- In Part 2, a `[bracket]` means you read the value off the screen. Never say a number the
  terminal isn't showing.

---

## Stage 0 · One-time setup, off camera (~20 min)

### 0.1 Update the clone
```powershell
cd C:\verify-final3
git pull
git log -1 --oneline
```

### 0.2 The disclosed environment
This is REPLAY ENV_SETUP, Windows block. Skip any line that is already done.
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
winget install --id astral-sh.uv -e
uv python install 3.11.15
uv venv --python 3.11.15 .venv-rec
.venv-rec\Scripts\Activate.ps1
uv pip install playwright==1.63.0
python -m playwright install chromium
npm install -g @anthropic-ai/claude-code@2.1.282
[Environment]::SetEnvironmentVariable("DISABLE_AUTOUPDATER", "1", "User")
```
- If `winget install` installs uv, open a new PowerShell window, `cd C:\verify-final3`, and carry on from `uv python install`.
- `.venv-rec` is the recording venv: Python 3.11.15 with Playwright. It is separate from the test venvs.

### 0.3 Pre-flight checks (both must print `0 problem(s)`)
```powershell
cd C:\verify-final3
.venv-rec\Scripts\Activate.ps1
python --version                     # Python 3.11.15
claude --version                     # 2.1.282 (Claude Code)
python tools\check_script_anchors.py
python tools\check_replay.py
```

### 0.4 Rehearse the new prompt once, on a site that has already been audited
```powershell
powershell -ExecutionPolicy Bypass -File tools\rehearse.ps1 -Url https://www.docker.com/ -Label docker_confirmed -Venv .venv-rec
```
Paste the transcript to Claude for checking. The table should hold only confirmed findings,
with a verdict on every row, and the `prompt_injection` row should be marked **not supported**.

### 0.5 Time Part 1
Read Part 1 (Stage 2 below) aloud once with a stopwatch, tab switches included.
**Over 2:50** → apply the cut ladder (end of Stage 2), in order.

> **Do not** open or audit `https://docs.pytest.org/` with the engine at any point before the take.
> A browser visit is fine; a run of the audit is not.

---

## Stage 1 · Recording day setup (off camera, ~10 min)

### 1.1 VS Code for Part 1
Open the **unzipped submission** with the 12 tabs in script order, each at its first line:
```powershell
cd C:\verify-final3
Remove-Item -Recurse -Force demo -ErrorAction SilentlyContinue
python -m zipfile -e round3-frozen\submission.zip demo
code demo
code -g demo\skills\answerability-audit\references\chunking-model.md:40
code -g demo\skills\ai-readiness-orchestrator\references\gate-rules.md:10
code -g demo\skills\crawl-access-audit\references\ai-bots.json:12
code -g demo\skills\crawl-access-audit\scripts\check_robots.py:286
code -g demo\skills\answerability-audit\references\geo-methods.md:14
code -g demo\skills\ai-readiness-orchestrator\references\severity-model.md:43
code -g demo\skills\ai-readiness-orchestrator\scripts\gate_model.py:117
code -g demo\tests\golden\site_b.report.md:58
code -g demo\skills\ai-readiness-orchestrator\scripts\orchestrate.py:242
code -g demo\skills\structured-data-audit\scripts\extract_markup.py:203
code -g demo\skills\ai-readiness-orchestrator\scripts\severity.py:26
code -g demo\DESIGN.md:369
```
- In VS Code, turn on Zen mode (`Ctrl+K Z`), set the font to 20, turn the minimap off and use a high-contrast theme.
- Click tab 1. `Ctrl+PgDn` then walks the tabs in script order.

### 1.2 Terminal for Part 2
This is a fresh folder, exactly as in REPLAY step 1:
```powershell
cd C:\verify-final3
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Remove-Item -Recurse -Force demo-live -ErrorAction SilentlyContinue
mkdir demo-live
Copy-Item round3-frozen\submission.zip demo-live\
cd demo-live
..\.venv-rec\Scripts\Activate.ps1
python --version
python -m zipfile -e submission.zip brand-ai-readiness-audit
cd brand-ai-readiness-audit
python -c "import shutil; shutil.copytree('skills', '.claude/skills')"
$env:DISABLE_AUTOUPDATER = "1"
$env:PYTHONUTF8 = "1"
python ..\..\tools\verify_engine.py ..\submission.zip .
Clear-Host
```
- `python --version` must print Python 3.11.15.
- The `verify_engine.py` run is a dry run of the on-camera command and must end with `RESULT : ENGINE UNCHANGED`.

### 1.3 Clipboard, screen and recorder
- **Clipboard:** copy the REPLAY step-2 prompt, from `Use the ai-readiness-orchestrator skill` to `URL: `.
  Include the trailing space and leave out `<URL>`: you type the URL by hand on camera.
- **Browser:** open https://docs.pytest.org/ once to confirm it's up. A visit is not an audit.
- **Screen:**
  - Windows Terminal maximised, font 16+, dark theme.
  - Focus Assist on, so no notifications.
  - VS Code open on `demo-live\brand-ai-readiness-audit` in a second window, for the optional JSON flip.
- **Recorder:** OBS, full screen, mic on. Record 5 s of silence first, for noise reduction.
  **Keep the raw file.**

---

## Stage 2 · PART 1 · Thought process (cap 3:00, target 2:50)

Part 1 may be recorded in several takes.
- Every shot needs its file on screen, the line highlighted (click its line number), and a
  lower-third caption.
- Captions are added in the editor.

### 0:00–0:02 · Title card
| | |
|---|---|
| DO | Black card, 2 s: **INVISIBLE TO THE MACHINE** · *Brand AI-Readiness Audit* · IT_Professionals · Round 4 |
| SAY | *(silent)* |

### 0:02–0:21 · Cold open
| | |
|---|---|
| DO | Tab 1 `chunking-model.md`, highlight lines **40–43** |
| CAPTION | `chunking-model.md:40–43 · the handout, quoted in our code` |
| SAY | "Ask an AI assistant about a brand: it either **quotes** the site · or acts like it **doesn't exist**. The handout says why: if nothing is easy to **reach, read, and quote**, it won't make the answer. We're IT_Professionals, and our agent finds **which step fails**." |

*Slow down on "doesn't exist", and smile on the last line.*

### 0:21–0:58 · Act I · What separates the cited from the ignored
| DO | CAPTION | SAY |
|---|---|---|
| `Ctrl+PgDn` → Tab 2 `gate-rules.md`, lines **10–14** | `gate-rules.md:10 · 66 checks: DESIGN.md:108 (count generated from the code)` | "And the steps come **in order**, so each of our 66 checks has a stage: reach, read, extract, trust · and act, for visitors." |
| `Ctrl+PgDn` → Tab 3 `ai-bots.json`, lines **12–14** | `ai-bots.json:12–14 · 29 crawlers: 14 retrieval, 10 training, 5 contested` | "Reach taught us rule one: lists say which AI bots to **block**; we asked what blocking each **costs**, and sorted 29 by role." |
| `Ctrl+G 71` (GPTBot, `"category": "training"`) | *(same)* | "Block GPTBot: you've opted out of **training**. Block a retrieval bot: you **vanish from its answers**." |
| `Ctrl+PgDn` → Tab 4 `check_robots.py` line **286**, then `Ctrl+G 318` | `check_robots.py:286 critical · :318 info` | "Same rule · **critical** for one, line 286 · **info** for the other, line 318." |
| `Ctrl+PgDn` → Tab 5 `geo-methods.md` lines **14–19**, then `Ctrl+G 24` | `geo-methods.md:14–24 · GEO (KDD 2024): a benchmark gain, not a defect` | "Quote: GEO research says statistics help · **in a benchmark** · so their absence scores **low**." *(cut-ladder step 1)* |

### 0:58–1:35 · Act II · How bad, how sure
| DO | CAPTION | SAY |
|---|---|---|
| `Ctrl+PgDn` → Tab 6 `severity-model.md` line **43**, then `Ctrl+G 56` | `severity-model.md:43 · :56` | "Severity asks: **how bad, if true?** Confidence is a separate field: **how sure?** A check that couldn't run says so: a clean report and one that couldn't look are **different things**." |
| `Ctrl+PgDn` → Tab 7 `gate_model.py` line **117** | `gate_model.py:117 apply_cascade · :42 ceiling "medium" · :129 Rule 0` | "A flat checklist gives a site blocking AI crawlers **fifteen criticals**, fourteen of them moot. `apply_cascade` caps those at medium and tags the **one** blocker. **Capped · never deleted.**" |
| `Ctrl+G 128`, highlight **128–129** | *(same)* | "Line 128: engagement is **never** gated. A visitor from an ad doesn't care if a crawler got in." |
| `Ctrl+PgDn` → Tab 8 `site_b.report.md` lines **58–60** | `tests/golden/site_b.report.md:60 · same in site_b.audit-report.json:109 ("blocked_by": "F-001")` | "Our golden: **one** critical, **eleven** findings waiting on F-001, engagement untouched." *(cut-ladder step 2)* |

### 1:35–2:01 · Act III · Every fix earns its place
| DO | CAPTION | SAY |
|---|---|---|
| `Ctrl+PgDn` → Tab 9 `orchestrate.py` lines **242–253** | `orchestrate.py:242 validate_finding · rejection logged at :695` | "Every fix must say **why** it works: `validate_finding` rejects any finding without a mechanism, and logs it." |
| `Ctrl+PgDn` → Tab 10 `extract_markup.py` lines **203–210** | `extract_markup.py:204 · "__FILL_IN__" when a value is absent (94 places in the engine)` | "Patches reuse values seen on the page · **never invented**. Anything missing stays **FILL_IN**." |
| `Ctrl+PgDn` → Tab 11 `severity.py` lines **26–29**, `Ctrl+G 13`, then `Ctrl+G 68` | `severity.py:27–29 lookups · :13 impact from post-gate severity · :68 total order` | "Priority is **ICE**: impact, confidence, ease, from fixed lookups. Impact uses the **capped** severity, so a moot defect can't outrank its blocker. A total sort order: **same evidence, same ranking.**" |

### 2:01–2:47 · Act IV · The day the real web proved us wrong
| DO | CAPTION | SAY |
|---|---|---|
| `Ctrl+PgDn` → Tab 12 `DESIGN.md` lines **369–380** | `DESIGN.md:374–379 · field test on five live sites` | "Then the real web **humbled** us. Five live sites · **365 findings** · which was itself the finding. File sizes read as **phone numbers**. A free download page told to show a **price**. We named twelve false positives before touching a threshold, and got to **205**." *(the phone/price sentence is cut-ladder step 3; otherwise give it a beat, it's the laugh)* |
| `Ctrl+G 320`, highlight **320–335** | `DESIGN.md:324, :334 · rewritten: dom.py:56 NOSCRIPT_JS_NOTICE · pinned: tests/test_regressions.py R1–R12` | "Worse: our empty-page detector fired **zero times** · even on a docs site with **sixteen words**. It was tuned to our own fixture. A fixture proves a check does what you wrote · **not that you wrote the right thing.**" |
| `Ctrl+P` → type `geo-methods.md:56` → `Enter` | `geo-methods.md:56` | "Our own code puts it best: a citation you can't check is worse than none · **because it looks like evidence.** So don't trust us. · **Watch.**" |

*Hard cut to Part 2 on "Watch."*

### Cut ladder: only if the timed read is over 2:50, and only in this order
1. Cut the GEO line and tab 5's first shot (−14 words → about 2:43).
2. Cut "Our golden: one critical…" and tab 8 (−11 words → about 2:39).
3. Cut "File sizes read as phone numbers… show a price." (−15 words → about 2:32).

**Never cut:**
- the cold open
- the crawler-roles lines
- `apply_cascade`
- "never gated"
- `validate_finding`
- ICE
- the zero-recall story
- the closing quote

### Bonus lines: only if the read is under 2:35
1. After "…got in.": `Ctrl+PgUp` back to Tab 2 `gate-rules.md`, `Ctrl+G 54`. Caption `gate-rules.md:54–57 · Rule 0b`.
   SAY: "And if we never saw the page a visitor sees, those findings aren't softened, they're **suppressed**. Capping asserts a weaker claim. Suppression asserts **none**."
2. After "…the right thing.": open `tests\test_regressions.py` at line 2 and scroll the `# R1.` … `# R12.` headers.
   SAY: "Tests R1 to R12 keep fixed bugs fixed."

---

## Stage 3 · PART 2 · Live trial run (cap 2:00 after trimming, target 1:55)

**This is one continuous take.** You may trim idle waits, but you never splice two takes.
- Talk live, and stay silent while the agent is only waiting, so a trim never cuts a word.
- On-camera URL: `https://docs.pytest.org/`.
- Harness: Claude Code 2.1.282. Model: Claude Opus 5.5.

Start in the terminal from Stage 1.2: folder `C:\verify-final3\demo-live\brand-ai-readiness-audit`,
venv active, and the screen cleared.

### 0:00–0:02 · Title strip
| | |
|---|---|
| DO | Overlay (added in the edit): **PART 2 · LIVE · one continuous take · idle waits trimmed** |
| SAY | *(silent)* |

### 0:02–0:12 · The engine is the one we submitted
| | |
|---|---|
| RUN | `python ..\..\tools\verify_engine.py ..\submission.zip .` → wait for `byte-identical : 155` … `RESULT : ENGINE UNCHANGED` |
| RUN | `claude --version` → `2.1.282 (Claude Code)` |
| SAY | "Part two: **live, one take.** This is our Round 3 zip, unzipped: **155 files, byte-identical** to what we submitted. The harness is **Claude Code 2.1.282**…" |

### 0:12–0:18 · The model
| | |
|---|---|
| RUN | `claude --model claude-opus-5-5 --allowedTools "Skill" "Bash(python:*)" "PowerShell(python:*)" "Read"` |
| DO | When it opens, type `/model` so **Opus 5.5** shows, then `Esc` |
| SAY | "…running **Claude Opus 5.5.**" |

### 0:18–0:28 · The URL, typed live
| | |
|---|---|
| DO | `Ctrl+V` the prompt (it ends in `URL: `), **type** `https://docs.pytest.org/` by hand, `Enter` |
| SAY | "I paste our REPLAY prompt, word for word · and type a site our engine has **never seen**." |

### 0:28–0:38 · The wiring
| | |
|---|---|
| DO | `Skill(ai-readiness-orchestrator)` appears: **hold 2 s**. Then pass 1 `python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://docs.pytest.org/ --no-render --out ./audit-precheck`: **hold 2 s**. Approve any permission prompt on camera ("Yes"). |
| SAY | "That's the **wiring**: the agent loads our entrypoint skill, *ai-readiness-orchestrator*, and runs its `orchestrate.py`. **No demo script, no canned results.**" |

*Trim the crawl. Badge: **⏩ crawl · ~40 s trimmed***

### 0:38–0:50 · Pass 2, chosen from pass 1's own evidence
| | |
|---|---|
| DO | Show the agent's `python -c` count on `pages.jsonl`, its one line naming pass 2 and why (**hold 2 s**), and the pass-2 command. |
| SAY, if the count is **0** | "Pass one: no browser. The agent checks that crawl for any page only JavaScript could build. **None** · so pass two re-reads the **same evidence**, no second crawl." |
| SAY, if the count is **above 0** | "Pass one: no browser. The agent checks that crawl for pages only JavaScript could build. It found **[N]** · so pass two **renders** the site in Chromium." |

*Trim pass 2 and the agent's reading. Badge: **⏩ ~Ns trimmed***

### 0:50–1:00 · Section (1): status and counts
| | |
|---|---|
| DO | Show the agent's `audit_status`, the counts by severity and "not assessed" |
| SAY, if **partial** | "**[N] findings** from six audit skills. Status **partial**, and it says why: **[the browser checks weren't run]**, so they're listed as **not assessed.**" |
| SAY, if **complete** | "**[N] findings** from six audit skills. Status **complete**. The one blind spot it names is the edge probe, which stays off unless you own the site." |

### 1:00–1:10 · Section (2): the table
| | |
|---|---|
| DO | Scroll slowly over the table of the **top 5 confirmed** findings (ICE column), and the line under it with the likely count |
| SAY | "Here are the fixes, **sorted by impact**: severity first, then ICE. These are the ones a deterministic check **confirmed**; the **[N] likely** ones are counted right under the table, not hidden." *(optional, drop first if long:)* "That's the **engine's** order, not the model's." |

### 1:10–1:22 · Section (3): the verdict column
| | |
|---|---|
| DO | Hold on a row whose verdict is *supported*, with its numbers |
| SAY | "Now the agent **audits the auditor.** It re-fetches **every row** itself: **[what it counted, e.g. "zero JSON-LD blocks"]**. **Supported.** That's commentary; the report stays exactly as the engine wrote it." |
| SAY, **first**, if any row says **not supported** (Card F) | "Look, the agent says **this one doesn't hold** on the live page. So we'd verify before acting, and the report stays exactly as the engine wrote it. The drill-down is on **[F-00x]**, which **does.**" |

*Card F is a strength, not a stumble: don't trim it out.*

### 1:22–1:48 · Section (4): the drill-down
**DO:** scroll the agent's drill-down top to bottom: evidence, severity and confidence, mechanism,
patch, ICE, the `blocked_by` count, then verification.
- The agent picks the finding itself: the highest-ranked row its evidence check supported.
- Optional: flip to VS Code, open `audit-output\audit-report.json`, and `Ctrl+F` the `check_id`.

**SAY:** the card below whose `check_id` matches the finding on screen. Swap in the numbers from the screen.

| if the drill-down is… | SAY |
|---|---|
| **A** · `extract.sd.absent_on_eligible_page` (most likely on a docs site) | "Drill-down: **[16 of 16]** eligible pages carry no structured data. **High**: nothing is machine-typed. **Confirmed**: a deterministic check saw it. The mechanism: typed facts are read **without guessing from prose.** The patch is JSON-LD built from the page's own title, and whatever it couldn't see says **FILL_IN**. ICE **7.3**." |
| **B** · `reach.robots.ai_search_bot_blocked` | "Drill-down on **F-001**: robots.txt blocks **[N] retrieval crawlers**, quoting the exact rule and line. **Critical, confirmed**: these bots fetch pages at answer time, so the brand can't be cited. The patch: one Allow block per bot, training policy untouched. ICE **9.3**. And **[N] findings** point at it with `blocked_by`: **the cascade from Part 1, live.**" |
| **C** · `reach.index.noindex_on_content` | "Drill-down: **[N]** content pages tell crawlers **not to index them**, through **[the X-Robots-Tag header / a meta robots tag]**. A noindexed page is read, then **discarded**, so it can never be cited: critical, confirmed. The fix: drop the directive. ICE **9.3**." Only if the agent says it may be deliberate, add: "And the agent flags it may be **on purpose**. That's the owner's call; the report says exactly what it saw." |
| **D** · `read.render.raw_text_gap` (only if pass 2 rendered) | "Drill-down: the raw HTML has **[X] words**; after JavaScript runs, **[Y]**. A crawler that doesn't run JavaScript **never sees** that text: high, confirmed. And the agent **re-counted both sides in Playwright** itself. The fix is server-side or pre-rendering; the verify command counts the words again." |
| **E** · `trust.date.absent_on_dated_content`, or any other confirmed medium | "Drill-down: **[N]** pages of dated content carry **no date at all.** Freshness is weighed when sources disagree, and an undated page **can't compete** on it. Medium, confirmed. The patch adds datePublished and dateModified as **FILL_IN**, because we will **not invent a date.** ICE **7.7**." |

**Never drill into:**
- `trust.integrity.prompt_injection` on a page that only discusses AI;
- `read.render.nav_links_js_only`, unless the agent's same-host counts back it up;
- `act.orient.no_value_proposition` or `act.cta.absent_for_page_type` (likely, and they misfire).

If the agent picks one of these, talk over the next confirmed row it supported, and use that row's card.

### 1:48–1:55 · Close
| | |
|---|---|
| DO | Stay on the verification command, or on the `fix_patches\` folder in VS Code |
| SAY | "Evidence, severity, mechanism, patch, and a **command to verify it**, on every finding. It's all in **REPLAY_IT_Professionals.txt.** Pick your own URL · and **check us.**" |

Type `/exit` in Claude Code and stop recording.

### If it goes sideways during the take
| what happens | do |
|---|---|
| Permission prompt | Approve it on camera and trim the pause. It is part of the real run. |
| The agent chains a command (`...; echo $LASTEXITCODE`), or tries `python3`, and gets blocked | It retries the plain command. Approve if asked, and trim the retry. |
| `no evidence bundle was produced`, a crash, or more than 5 min | Stop. Start a **new take on `https://www.sphinx-doc.org/`**, after changing the first `TEST_SITE_URLS` entry, the step-2 example and the run sheet to match, and re-running `python tools\check_replay.py`. **Never splice.** |
| Too long for 2:00 | Trim waits and the agent's thinking harder, then drop the *(optional)* sentence. Never cut: the typed URL, the `Skill(...)` call, the pass-2 line, the table, the verdicts, or the drill-down. |

---

## Stage 4 · After recording

Run these from `C:\verify-final3`:
```powershell
cd C:\verify-final3
Remove-Item -Recurse -Force recorded-run -ErrorAction SilentlyContinue
Copy-Item -Recurse demo-live\brand-ai-readiness-audit\audit-output recorded-run
Get-ChildItem $env:USERPROFILE\.claude\projects\*demo-live-brand-ai-readiness-audit* | Get-ChildItem -Filter *.jsonl | Sort-Object LastWriteTime | Select-Object -Last 1 | Copy-Item -Destination recorded-run\session.jsonl
python tools\tool_calls.py recorded-run\session.jsonl
(Get-FileHash "<path to the raw video>").Hash
python tools\check_replay.py
```
- `tools\tool_calls.py` must show the `Skill` call.
- Write the raw video's file name, length and hash into `recorded-run\README.md`. The video itself stays out of git.

Final checks:
- Part 1 is 3:00 or less, Part 2 is 2:00 or less, and the total is 5:00 or less.
- Watch the export once with the REPLAY open. The harness (2.1.282), the model (Claude Opus 5.5)
  and the URL (`https://docs.pytest.org/`, or the backup) must match what the video shows.
