# Recording flow: what to run, what to say

One page for the person recording, in order: every command or click, and the exact line to say
with it. The spoken lines are copied word for word from [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md)
(branch `final-3`). If the two ever differ, `VIDEO_SCRIPT.md` wins for what you say and
[`VIDEO_PART2_RUNSHEET.md`](VIDEO_PART2_RUNSHEET.md) wins for what you type.

This file works unchanged on **any Windows PC** with PowerShell, whoever's machine records.
Nothing below names a user, a drive or a folder outside this repo:
- **Every command runs at the repo root:** the folder of your clone that holds `REPLAY_IT_Professionals.txt`.
  To open PowerShell there, open that folder in File Explorer, click the address bar, type `powershell`, and press Enter.
  A VS Code terminal opens in your home folder unless VS Code has the repo folder open, so check that
  the prompt ends in `Adobe-Hackathon>` before you paste.
- **Blocks that must not run anywhere else are wrapped** in `if (Test-Path REPLAY_IT_Professionals.txt) { … }`.
  Paste the whole block, and press `Enter` once more if nothing happens. Outside the repo root it prints one
  red `Wrong folder` line and runs nothing, instead of creating or deleting folders in the wrong place.
- **The venv is `.venv` in the repo root,** the name the REPLAY uses. Stage 0.2 checks it, and
  builds it only if it's missing or wrong.
- `python tools\check_replay.py` fails if a machine-specific path ever gets into this file, the
  run sheet or the REPLAY.

How to read this file:
- **RUN** is typed in PowerShell.
- **DO** is a click or key in VS Code or the terminal.
- **SAY** is spoken. **Bold** words get stress, `·` is a half-beat pause.
- In Part 2, a `[bracket]` means you read the value off the screen. Never say a number the
  terminal isn't showing.

---

## Stage 0 · One-time setup, off camera (~15 min)

### 0.1 Put the clone on `final-3`
No clone yet? Run `git clone --branch final-3 https://github.com/kalpitphogat/Adobe-Hackathon`, then
open PowerShell in the new folder and skip to 0.2. Otherwise, at the repo root:
```powershell
git status --short
git fetch origin
git checkout final-3
git pull origin final-3
git log -1 --oneline
```
- Check `git status --short` before switching branches:
  - Lines starting with `??` are untracked files, which are fine.
  - Any other line is a local change to a tracked file. **Stop and paste it to Claude.**
- If `git checkout` refuses because untracked files "would be overwritten", paste that message to Claude too.
- `git log` must show the newest `final-3` commit.

### 0.2 Check what's installed; install only what's missing
Run this at the repo root. On a machine that is already set up, every line prints what's expected
and nothing needs installing.
```powershell
if (Test-Path REPLAY_IT_Professionals.txt) {
  [Environment]::SetEnvironmentVariable("DISABLE_AUTOUPDATER", "1", "User")
  $env:DISABLE_AUTOUPDATER = "1"
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  Test-Path .venv\Scripts\python.exe
  .venv\Scripts\Activate.ps1
  python --version
  python -c "from importlib.metadata import version; print('playwright', version('playwright'))"
  python -c "from playwright.sync_api import sync_playwright as s; p = s().start(); b = p.chromium.launch(); print('chromium', b.version); b.close(); p.stop()"
  claude --version
  (Get-Command claude).Source
} else { Write-Host "Wrong folder: cd into your Adobe-Hackathon clone (the folder with REPLAY_IT_Professionals.txt), then paste this block again." -ForegroundColor Red }
```
The first line stops Claude Code from updating itself, in every new window from now on. That
matters: 2.1.283 came out on 2026-09-25, and the REPLAY says 2.1.282. When the video is done,
`[Environment]::SetEnvironmentVariable("DISABLE_AUTOUPDATER", $null, "User")` turns updates back on.
Leave Claude Code's `effortLevel` setting at `"medium"` until the video is done: the REPLAY discloses
that value (section REASONING EFFORT).

Expected output:
```
True
Python 3.11.15
playwright 1.63.0
chromium <any version number>
2.1.282 (Claude Code)
<the path claude runs from>
```

Fix only the lines that differ, then run the block again:

| line differs | fix |
|---|---|
| `False`, or Python isn't 3.11.15 | Build `.venv` the REPLAY's way (next block). |
| `playwright` is missing or isn't 1.63.0 | `uv pip install playwright==1.63.0` |
| The chromium line prints an error | `python -m playwright install chromium` |
| `claude` isn't recognised | 1. `node --version` must print v18 or newer. If it doesn't, run `winget install OpenJS.NodeJS.LTS` and open a new PowerShell at the repo root.<br>2. Run `npm install -g @anthropic-ai/claude-code@2.1.282`.<br>3. Open a new PowerShell at the repo root, run `claude` once to sign in, then type `/exit`. |
| claude isn't **2.1.282**. An install that updated itself after 2026-09-25 shows 2.1.283. | If the path on the last line contains `npm`, run `npm install -g @anthropic-ai/claude-code@2.1.282`. Otherwise run `claude install 2.1.282`. Then open a new PowerShell at the repo root and check again. |

**Building `.venv`.** These are the REPLAY's own Windows lines, wrapped so they run only at the repo root. An existing wrong `.venv` is
renamed, not deleted; `.venv-*` folders are git-ignored. If `uv --version` isn't recognised, run
`winget install --id astral-sh.uv -e` (or `pip install uv`) first, then open a new PowerShell at
the repo root.
```powershell
if (Test-Path REPLAY_IT_Professionals.txt) {
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  if (Test-Path .venv) { Rename-Item .venv (".venv-old-" + (Get-Date -Format "yyyyMMdd-HHmmss")) }
  uvx --from "uv>=0.11" uv python install 3.11.15
  uv venv --python 3.11.15 .venv
  .venv\Scripts\Activate.ps1
  uv pip install playwright==1.63.0
  python -m playwright install chromium
} else { Write-Host "Wrong folder: cd into your Adobe-Hackathon clone (the folder with REPLAY_IT_Professionals.txt), then paste this block again." -ForegroundColor Red }
```

### 0.3 Pre-flight checks (both must print `0 problem(s)`)
At the repo root:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
python tools\check_script_anchors.py
python tools\check_replay.py
```
`check_replay.py` also compares the installed Claude Code with the REPLAY, so a harness that has
auto-updated fails here, before it can reach the video. It also fails if this file, the run sheet
or the REPLAY names a machine-specific path.

### 0.4 Rehearse the new prompt once, on a site that has already been audited
This uses Claude usage from the signed-in account and takes about 3 minutes. Run it at the repo root.
```powershell
powershell -ExecutionPolicy Bypass -File tools\rehearse.ps1 -Url https://www.docker.com/ -Label docker_confirmed
Get-ChildItem rehearsal\*_docker_confirmed.md | Get-Content -Encoding UTF8
```
Paste the output to Claude for checking. What it should show:
- The header shows `harness: 2.1.282` and `playwright: yes`.
- The table holds only confirmed findings, with a verdict on every row.
- The `prompt_injection` row is marked **not supported**.
- The file ends with the finding check that Stage 4 runs after the take. It must end with `0 problem(s)`.

### 0.5 Time Part 1
Set up VS Code as in Stage 1.1 first. Then do Stage 2 once with a stopwatch, reading aloud and
pressing every key in it: tab switches, `Ctrl+G` jumps and highlights.
- **Over 2:55** → apply the cut ladder (end of Stage 2), in order. The full read is 2:59 at 150 words
  a minute, so a careful reader will need step 1.
- **Under 2:45** → you read faster than that, so there is room for a restore line (end of Stage 2).
  Add one at a time and time it again.
- Every highlight must fit on screen, and every highlighted line must be readable to its end.
  If one doesn't, set the font to 18 and check again.

> **Do not** open or audit `https://docs.pytest.org/` with the engine at any point before the take.
> A browser visit is fine; a run of the audit is not.

---

## Stage 1 · Recording day setup (off camera, ~10 min)

### 1.1 VS Code for Part 1
Open a **fresh unzip of the submission**, proven byte-identical, with the 10 tabs in script order,
each at its first line.
- An older `demo` folder is renamed, not deleted, so nothing kept in it is lost.
  `demo-*` folders are git-ignored.
- Any older `demo-old-*` folders from earlier recording days are safe to delete once you've checked them.

At the repo root:
```powershell
if (Test-Path REPLAY_IT_Professionals.txt) {
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .venv\Scripts\Activate.ps1
  if (Test-Path demo) { Rename-Item demo ("demo-old-" + (Get-Date -Format "yyyyMMdd-HHmmss")) }
  python -m zipfile -e round3-frozen\submission.zip demo
  python tools\verify_engine.py round3-frozen\submission.zip demo
  code demo
  code -g demo\skills\answerability-audit\references\chunking-model.md:40
  code -g demo\skills\ai-readiness-orchestrator\references\gate-rules.md:10
  code -g demo\skills\crawl-access-audit\references\ai-bots.json:12
  code -g demo\skills\crawl-access-audit\scripts\check_robots.py:286
  code -g demo\skills\ai-readiness-orchestrator\references\severity-model.md:43
  code -g demo\skills\ai-readiness-orchestrator\scripts\gate_model.py:117
  code -g demo\skills\ai-readiness-orchestrator\scripts\orchestrate.py:242
  code -g demo\skills\structured-data-audit\scripts\extract_markup.py:203
  code -g demo\skills\ai-readiness-orchestrator\scripts\severity.py:26
  code -g demo\DESIGN.md:369
} else { Write-Host "Wrong folder: cd into your Adobe-Hackathon clone (the folder with REPLAY_IT_Professionals.txt), then paste this block again." -ForegroundColor Red }
```
- `verify_engine.py` must end with `RESULT : ENGINE UNCHANGED`.
- You should see 10 tabs. More than 10 means VS Code reopened tabs from an earlier session: press
  `Ctrl+K Ctrl+W` in VS Code to close them all, then run the 10 `code -g` lines again.
- If `code` isn't recognised, open the `demo` folder in VS Code by hand
  and open each file with `Ctrl+P`, typing its name then `:line` (for example `chunking-model.md:40`).
- VS Code settings: press `Ctrl+,`, keep the **User** tab selected so nothing is written into `demo`,
  then search each setting by name and set it:
  - `editor.fontSize`: 20.
  - `editor.minimap.enabled`: off.
  - `editor.wordWrap`: on, so long lines such as `ai-bots.json:26` can be read to the end.
  - `zenMode.hideLineNumbers`: off. Zen mode hides line numbers unless you turn this off, and
    Part 1 needs them: the viewer hears "line 286", and you click the numbers to highlight.
- Theme: `Ctrl+K Ctrl+T` → a High Contrast theme.
- Click tab 1, then turn on Zen mode (`Ctrl+K Z`). Check the line numbers still show.
  `Ctrl+PgDn` then walks the tabs in script order.

### 1.2 Terminal for Part 2
This is a fresh folder, exactly as in REPLAY step 1 and run sheet §A.1.
- `demo-live` holds the last take or rehearsal. If a take in it isn't saved yet (Stage 4), save it first.

At the repo root:
```powershell
if (Test-Path REPLAY_IT_Professionals.txt) {
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  Remove-Item -Recurse -Force demo-live -ErrorAction SilentlyContinue
  mkdir demo-live
  Copy-Item round3-frozen\submission.zip demo-live\
  cd demo-live
  ..\.venv\Scripts\Activate.ps1
  python --version
  python -m zipfile -e submission.zip brand-ai-readiness-audit
  cd brand-ai-readiness-audit
  python -c "import shutil; shutil.copytree('skills', '.claude/skills')"
  $env:DISABLE_AUTOUPDATER = "1"
  $env:PYTHONUTF8 = "1"
  python ..\..\tools\verify_engine.py ..\submission.zip .
  claude
} else { Write-Host "Wrong folder: cd into your Adobe-Hackathon clone (the folder with REPLAY_IT_Professionals.txt), then paste this block again." -ForegroundColor Red }
```
- `python --version` must print Python 3.11.15.
- The `verify_engine.py` run is a dry run of the on-camera command and must end with `RESULT : ENGINE UNCHANGED`.
- The last line starts Claude Code once, **off camera**, so its first-run questions don't land in the take.
  - If it asks whether you trust the files in this folder, answer **Yes**.
  - Don't send it a prompt: type `/exit`, then `Clear-Host`.
- Leave this window open: Part 2 starts here, and the venv and both `$env:` settings belong to this window.
  If you close it, open a new PowerShell at the repo root and run this whole block again.

### 1.3 Clipboard, screen and recorder
Do this last, just before recording, in the Stage 1.1 PowerShell window (at the repo root). Keep
the Stage 1.2 window clean: it's the one on camera.

**Clipboard: the step-2 prompt without its `<URL>`.** On camera you paste the prompt and type the
URL by hand, because the brief wants the URL entered on camera and the prompt pasted word for word
from the REPLAY. The prompt is one line of about 3,100 characters, so let PowerShell copy it rather than
selecting it by hand. It uses the same match as `tools\rehearse.ps1`:
```powershell
$prompt = (Get-Content REPLAY_IT_Professionals.txt -Encoding UTF8 | Where-Object { $_ -match "SKILL\.md" -and $_.TrimEnd().EndsWith("URL: <URL>") } | Select-Object -First 1).Trim()
Set-Clipboard -Value $prompt.Substring(0, $prompt.Length - 5)
(Get-Clipboard -Raw).EndsWith("URL: ")
```
- The last line must print `True`: the clipboard ends in `URL: ` with the space, and without `<URL>`.
- Copy nothing else before the take, or you'll overwrite it. If you do, run the three lines again.
- Claude Code may show a long paste as a short `[Pasted text #1]` label. That's normal: the whole
  prompt is still sent, and the saved transcript has it. Type the URL straight after the label.

**Browser: check the site is up.** Open https://docs.pytest.org/ once in Chrome or Edge.
- If it doesn't load, don't start the take. Use the backup URL (see "If it goes sideways").
- The rule is that **our engine** has never run on the site. Looking at it in a browser is fine;
  running `orchestrate.py` or `rehearse.ps1` on it is not.

**Screen: what the camera sees.**
- **Windows Terminal (the Stage 1.2 window):**
  - Maximised (`Win+Up`).
  - Font size 16 or more, so judges can read it at 1080p: `Ctrl+,` → Profiles → Defaults →
    Appearance → Font size.
  - A dark colour scheme. The default, Campbell, is dark.
- **No pop-ups:** these could interrupt the take or show private messages.
  - Windows 11: Settings → System → Notifications → **Do not disturb**, on.
  - Windows 10: Action Center → **Focus assist** → Alarms only.
  - Close chat apps and email.
- **Optional, for the drill-down's JSON flip:** a second VS Code window on the **parent** folder `demo-live`:
  ```powershell
  code -n demo-live
  ```
  - At 1:22, open `brand-ai-readiness-audit\audit-output\audit-report.json` and `Ctrl+F` the finding's `check_id`.
  - Open `demo-live`, never `demo-live\brand-ai-readiness-audit`. A settings change or an extension
    can create a `.vscode` folder in the folder VS Code has open. Inside the engine folder, that
    makes the on-camera engine check print `ENGINE DIFFERS FROM THE SUBMISSION`.

**Recorder: OBS Studio (free, obsproject.com).**
- **Setup:**
  - Settings → Video: 1920×1080, 30 fps.
  - Source: **Display Capture** of the whole screen, so switching from Terminal to VS Code is captured.
  - Audio: your mic on. Its meter should move in the green and yellow when you talk, not the red.
- **Test first:** record 10 seconds, play it back, and check the text is readable and the voice is clear.
- **For the take:**
  - Start recording, then **stay silent for 5 seconds**. The editor uses that silence to learn the
    room's background noise and remove it.
  - Record Part 2 in **one continuous take**.
- **Keep the raw, untrimmed file.** Edit a copy. The raw file proves the run was continuous if
  anyone asks; Stage 4 records its hash, and video files are git-ignored.

---

## Stage 2 · PART 1 · Thought process (cap 3:00; the full read is 2:59 at 150 words a minute)

Part 1 may be recorded in several takes.
- Every shot needs its file on screen, its lines highlighted, and a lower-third caption.
- Captions are added in the editor. Each tab's caption is written above its table.
- **Ten tabs, plus two files opened with `Ctrl+P`:** `suppression-rules.md` (step 4c) and `geo-methods.md` (step 11).
- **Every SAY is one or more complete sentences, and the lines you highlight show what it claims.**
  If you fluff one, restart that sentence, not the paragraph.

**Moving around in VS Code.** Each row below is one screen: do the DO, then say the SAY.
- `Ctrl+PgDn`: the next tab. Each tab opens on the first line it needs.
- `Ctrl+G`, type the line number, `Enter`: go to another line in the same file. VS Code puts that line mid-screen.
- `Ctrl+P`, type `file:line`, `Enter`: jump straight to a line in any file, open or not. Steps 4c,
  6c, 7 and 11 use it, and so do the restore lines.
- **Highlight:** click the line number in the left margin. For several lines, click the first number, then **Shift+click** the last.
  - A row that says only "click" needs no jump: that line is already on screen, a few lines away.
  - If a line you need is ever off screen, scroll to it.
- **Press keys only between rows.** Every row ends on a full stop, so you never talk while you type.
  The silent key presses can be trimmed in the edit.
- **Retake:**
  1. In VS Code press `Ctrl+K Ctrl+W` to close every tab, then run the 10 `code -g` lines again in the
     Stage 1.1 window. The tabs are back in script order, each on its first line, and no file the last
     take opened with `Ctrl+P` is left sitting between two of them for `Ctrl+PgDn` to land on.
  2. `Ctrl+P` → `chunking-model.md:40` → `Enter` to start at tab 1, or use the `file:line` of the row you restart from.

### 0:00–0:02 · Title card
| | |
|---|---|
| DO | Black card, 2 s: **INVISIBLE TO THE MACHINE** · *Brand AI-Readiness Audit* · IT_Professionals · Round 4 |
| SAY | *(silent)* |

### 0:02–0:21 · Cold open
**Tab 1 `chunking-model.md`** · CAPTION `chunking-model.md:40–43 · the handout, quoted in our code`

| step | DO | SAY |
|---|---|---|
| 1 | Tab 1 is on screen, on line 40. Click **40**, Shift+click **43**. | "Ask an AI assistant about a brand, and it either **quotes** the site or acts as if it **doesn't exist**. The handout says why: a page that isn't easy to **reach, read and quote** never makes it into the answer. Our agent finds **which step fails**." |

*Slow down on "doesn't exist", and smile on the last sentence.*

### 0:21–1:17 · Act I · What separates the cited from the ignored
**Tab 2 `gate-rules.md`** · CAPTION `gate-rules.md:10–19 · 66 checks by stage: DESIGN.md:108–111 (reach 18, read 5, extract 16, trust 10, act 17)`

| step | DO | SAY |
|---|---|---|
| 2a | `Ctrl+PgDn` → tab 2, on line 10. Click **10**, Shift+click **14**: "three things have to succeed in order". | "Those steps have to succeed **in order**, so we group our **66 checks** into stages in the same order." |
| 2b | Click **16**, Shift+click **19**, a few lines down: "fifteen criticals … Fourteen of them are real defects that currently change nothing." | "A flat checklist ignores that order: a site blocking AI crawlers gets **fifteen critical** findings, and **fourteen** don't matter yet." |

**Tab 3 `ai-bots.json`** · CAPTION `ai-bots.json:12–14 · 29 crawlers: 14 retrieval, 10 training, 5 contested`

| step | DO | SAY |
|---|---|---|
| B1 | `Ctrl+PgDn` → tab 3, on line 12. Click **12**, Shift+click **14**. | **BONUS** "Reach is the first stage, and it taught us our first rule." |
| 3a | Same screen as B1. If you skipped B1: `Ctrl+PgDn` → tab 3, on line 12. Click **12**, Shift+click **14**. | "Most lists tell you which AI crawlers to **block**. We asked what blocking each one **costs**, and sorted 29 by role." |
| 3b | `Ctrl+G` → type `71` → `Enter`. Click **71**, Shift+click **72**: `"GPTBot"` … `"category": "training"`, then "Blocking it does not remove a site from ChatGPT search results". | "Block GPTBot, and you have only opted out of **training**." |
| 3c | `Ctrl+G` → type `26` → `Enter`. Click **26**: "Blocking one of these removes the brand from that assistant's answers." | "Block a **retrieval** crawler, and you **vanish from that assistant's answers**." |

**Tab 4 `check_robots.py`** · CAPTION `check_robots.py:285–286 critical · :317–318 info` · *cut-ladder step 1 skips 4a–4b*

| step | DO | SAY |
|---|---|---|
| 4a | `Ctrl+PgDn` → tab 4, on line 286. Click **285**, Shift+click **286**: "AI retrieval crawler(s) that cite sources at answer time", `severity="critical"`. | "So one robots.txt rule is **critical** against a retrieval crawler." |
| 4b | `Ctrl+G` → type `317` → `Enter`. Click **317**, Shift+click **318**: "recorded as an observation, not a defect", `severity="info"`. | "Against a training crawler, the same rule is only **info**." |

**`suppression-rules.md`, opened with `Ctrl+P`** · CAPTION `suppression-rules.md:22–27 · enforced: check_agent_files.py:24 docs sites only, :62 severity="low" · tests/test_suppression.py`

| step | DO | SAY |
|---|---|---|
| 4c | `Ctrl+P` → type `suppression-rules.md:22` → `Enter`. Click **22**, Shift+click **27**. It opens as a new tab just right of tab 4, so the next `Ctrl+PgDn` still reaches tab 5. | "Hype doesn't set our severity. Google says llms.txt neither helps nor harms visibility, and a study of nearly **300,000 domains** found no link to AI citations. Most tools rate a missing llms.txt **high**; we rate it **low**." |

**BONUS: `geo-methods.md`, opened with `Ctrl+P`** · CAPTION `geo-methods.md:5–7 GEO, KDD 2024 · :14–16 the three rewrites · :23–27 fires at low: a benchmark gain, not a defect`

| step | DO | SAY |
|---|---|---|
| B2a | `Ctrl+P` → type `geo-methods.md:14` → `Enter`. Click **14**, Shift+click **16** (the paper's name and KDD 2024 are on lines 5–7, just above). It opens next to the llms.txt tab, so the next `Ctrl+PgDn` still reaches tab 5. | **BONUS** "We calibrate against research, not instinct. The GEO paper, from KDD 2024, found that citing sources, adding statistics and adding quotations made a page more prominent in AI answers." |
| B2b | `Ctrl+G` → type `23` → `Enter`. Click **23**, Shift+click **27**: "fires at **low** severity" … "in a benchmark". | **BONUS** "That gain was measured in a benchmark, not on any real brand, so a page with none of the three gets only a **low** finding." |

### 1:17–1:47 · Act II · How bad, how sure
**Tab 5 `severity-model.md`** · CAPTION `severity-model.md:43`

| step | DO | SAY |
|---|---|---|
| 5 | `Ctrl+PgDn` → tab 5, on line 43. Click **43**. | "Each finding has two ratings: **severity**, how bad if true, and **confidence**, how sure we are." |
| B3 | `Ctrl+G` → type `56` → `Enter`. Click **56**, Shift+click **57**: "A clean report and a report that could not look are different things". | **BONUS** "A check that cannot run says so, because a clean report and a report that **couldn't look** are different things." |

**Tab 6 `gate_model.py`** · CAPTION `gate_model.py:117–122 apply_cascade · :42 ceiling "medium" · :120 cap, never delete · :129 Rule 0, why: gate-rules.md:31–32`

| step | DO | SAY |
|---|---|---|
| 6a | `Ctrl+PgDn` → tab 6, on line 117. Click **117**, Shift+click **122**: `apply_cascade` … `Rule 3: cap, never delete.` … "The finding stays in the report". | "Our `apply_cascade` function fixes the flat checklist: it caps findings behind the **one** blocker at **medium**, and never deletes them." |
| 6b | `Ctrl+G` → type `128` → `Enter`. Click **128**, Shift+click **129**: `# Rule 0: gates never touch engagement`. | "Engagement is **never** capped: a visitor from an ad doesn't care whether a crawler got in." |

**Rule 0b, back in `gate-rules.md` (tab 2)** · CAPTION `gate-rules.md:54–57 · Rule 0b`

| step | DO | SAY |
|---|---|---|
| 6c | `Ctrl+P` → type `gate-rules.md:54` → `Enter`. This is tab 2 again, no new tab. Click **54**, Shift+click **57**: "`read` failures suppress engagement findings because the evidence is absent." | "But if we never saw the page a visitor sees, we **suppress** its engagement findings, because we have no evidence." |
| B4 | No key press: lines **56–57** are already highlighted: "Capping asserts a weaker claim. Suppression asserts none." | **BONUS** "A cap still makes a weaker claim; a suppression makes **no claim** at all." |

**BONUS: `site_b.report.md`, opened with `Ctrl+P`** · CAPTION `tests/golden/site_b.report.md:58–60 · site_b.audit-report.json: 1 critical, 11 blocked_by F-001, 8 engagement findings, none capped`

| step | DO | SAY |
|---|---|---|
| B5 | `Ctrl+P` → type `site_b.report.md:58` → `Enter`. Click **58**, Shift+click **60**: "11 finding(s) are recorded but capped at medium because F-001". | **BONUS** "Our golden test report shows the cascade: **one** critical blocker, **eleven** findings capped behind it, and all **eight** engagement findings left untouched." |

*Capping says "real, but moot"; suppression says "we never looked". You are now on tab 2 (or on
`site_b.report.md` after B5), so step 7 uses `Ctrl+P`, not `Ctrl+PgDn`.*

### 1:47–2:10 · Act III · Every fix earns its place
**Tab 7 `orchestrate.py`** · CAPTION `orchestrate.py:242 validate_finding · rejection logged at :695`

| step | DO | SAY |
|---|---|---|
| 7 | `Ctrl+P` → type `orchestrate.py:242` → `Enter` (**not** `Ctrl+PgDn`: 6c left you on tab 2). Click **242**, Shift+click **253**. | "Every fix must say **why** it works, so `validate_finding` rejects any finding without a mechanism." |
| B6 | No key press: the caption already cites `orchestrate.py:695`, where the rejection is logged. | **BONUS** "It also logs every rejection, so no finding is dropped silently." |

**Tab 8 `extract_markup.py`** · CAPTION `extract_markup.py:204 · "__FILL_IN__" when a value is absent (94 places in the engine)`

| step | DO | SAY |
|---|---|---|
| 8a | `Ctrl+PgDn` → tab 8, on line 203. Click **203**, Shift+click **204**: `Never invented.` | "Our patches reuse values from the page; we **never invent** one." |
| 8b | Click **209**, Shift+click **210**, five lines down: `__FILL_IN__`. | "Whatever we couldn't find is left as **FILL_IN**." |

**Tab 9 `severity.py`** · CAPTION `severity.py:27–29 lookups · :13 impact from post-gate severity · :68 total order`

| step | DO | SAY |
|---|---|---|
| 9a | `Ctrl+PgDn` → tab 9, on line 26. Click **26**, Shift+click **29**. | "We rank fixes by **ICE**: impact, confidence and ease." |
| 9b | `Ctrl+G` → type `13` → `Enter`. Click **13**, Shift+click **15**. | "Impact uses the **capped** severity, so a blocked finding never outranks its blocker." |
| B7 | `Ctrl+G` → type `68` → `Enter`. Click **68**, Shift+click **71**: `def sort_key` … "the ordering is total and therefore deterministic". | **BONUS** "The order is total, so the same evidence always ranks the **same way**." |

### 2:10–2:48 · Act IV · The day the real web proved us wrong
**Tab 10 `DESIGN.md`, the field test** · CAPTION `DESIGN.md:374–379 · field test on five live sites`, then `DESIGN.md:377–378`

| step | DO | SAY |
|---|---|---|
| 10a | `Ctrl+PgDn` → tab 10, on line 369. Click **369**, Shift+click **374**. | "Then the real web **humbled** us. Five live sites produced **365 findings**, and that number was itself the finding." |
| 10b | Click **374**, Shift+click **379**: twelve false positives … **205**. | "We named **twelve false positives** before touching any threshold, and fixing them cut the count to **205**." |
| 10c | Click **377**, Shift+click **378**, already on screen: file sizes as phone numbers, a free download page asked for a price. | "Two were embarrassing: we read file sizes as **phone numbers**, and asked a free download page for a **price**." *(cut-ladder step 2 drops this row)* |

*Let 10c breathe. It is the one laugh in Part 1, and it turns "twelve false positives" into something
a judge can picture.*

**Tab 10 `DESIGN.md`, the zero-recall story** · CAPTION `DESIGN.md:324, :332–334 · rewritten: dom.py:56 NOSCRIPT_JS_NOTICE · pinned: tests/test_regressions.py R1–R12`

| step | DO | SAY |
|---|---|---|
| 10d | `Ctrl+G` → type `322` → `Enter`. Click **322**, Shift+click **325**: "fired **zero times** … **16 words**". | "Worse, our empty-page detector fired **zero times**, even on a **sixteen-word** docs site." |
| 10e | `Ctrl+G` → type `332` → `Enter`. Click **332**, Shift+click **335**: "tuned to a synthetic Next.js fixture" … "A fixture proves a check does what you wrote". | "We'd tuned it to our own fixture, and a fixture proves a check does what you wrote · **not that you wrote the right thing**." |

*Don't rush 10d–10e. The admission is what earns the closing line.*

### 2:48–3:00 · Close
**`geo-methods.md`, opened fresh** · CAPTION `geo-methods.md:56`

| step | DO | SAY |
|---|---|---|
| 11 | `Ctrl+P` → type `geo-methods.md:56` → `Enter`. Click **56**, Shift+click **57**. | "Our own code puts it best: a citation you can't check is worse than none, **because it looks like evidence**. So don't trust us. · **Watch.**" |

*Hard cut to Part 2 on "Watch."*

### Cut ladder: only if your timed read is over 2:55, and only in this order
The full read is 429 words: **2:59** at 150 words a minute, the pace the checker uses, and 2:54 at 155.
Each step drops whole sentences.

1. Skip steps 4a–4b, the `check_robots.py` beat (−20 words → about 2:51). From tab 3, do 4c,
   then press `Ctrl+PgDn` **twice** to reach tab 5.
2. Skip step 10c, the phone-numbers line (−19 words → about 2:44). It is the one laugh in Part 1, so
   it goes last, not first.

**Never cut:**
- the cold open
- the order and the flat checklist (steps 2a–2b)
- the crawler-roles beat (steps 3a–3c)
- the llms.txt beat (step 4c)
- `apply_cascade` and "engagement is never capped" (steps 6a–6b)
- Rule 0b (step 6c)
- `validate_finding`
- "never invent one" and FILL_IN
- steps 9a–9b (ICE)
- the 365 → 205 field test
- the zero-recall story (10d–10e)
- the closing quote

### BONUS rows
The rows whose SAY starts with **BONUS** (B1–B7) are optional: the arguments that did not fit under
3:00, written in place as complete sentences. Say them for a longer cut or a practice read; skip them
for the 3:00 take. To skip one, skip its keys too. Skipping B2 or B5 skips their `Ctrl+P`, and the
next row's keys still work; skipping B1 means doing its keys in 3a, as 3a says.
`python tools\check_script_anchors.py` times the main read without them and prints the total with them.

## Stage 3 · PART 2 · Live trial run (cap 2:00 after trimming, target 1:55)

**This is one continuous take.** You may trim idle waits, but you never splice two takes.
- Talk live, and stay silent while the agent is only waiting, so a trim never cuts a word.
- On-camera URL: `https://docs.pytest.org/`.
- Harness: Claude Code 2.1.282. Model: Claude Opus 5.5.

Start in the terminal window from Stage 1.2:
- folder `demo-live\brand-ai-readiness-audit` inside the repo;
- venv active, and the screen cleared.

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
- Optional: flip to the VS Code window from Stage 1.3, open `brand-ai-readiness-audit\audit-output\audit-report.json`, and `Ctrl+F` the `check_id`.

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
| Permission prompt, or the folder-trust question | Approve it on camera and trim the pause. It is part of the real run. |
| The agent chains a command (`...; echo $LASTEXITCODE`), or tries `python3`, and gets blocked | It retries the plain command. Approve if asked, and trim the retry. |
| The agent's first `orchestrate.py` command starts `python .claude/skills/...` and fails with `no evidence bundle was produced` | Keep going. It ran the copy made for the Skill tool, and it reruns `skills/...` by itself (judge-mode run, 2026-09-27). Approve anything it asks, keep the detour in, and trim only the waiting. It is still one real run. |
| `no evidence bundle was produced` from `python skills/...`, a crash, or more than 5 min | Stop. Start a **new take on `https://www.sphinx-doc.org/`**, after changing the first `TEST_SITE_URLS` entry, the step-2 example and the run sheet to match, and re-running `python tools\check_replay.py`. **Never splice.** |
| Too long for 2:00 | Trim waits and the agent's thinking harder, then drop the *(optional)* sentence. Never cut: the typed URL, the `Skill(...)` call, the pass-2 line, the table, the verdicts, or the drill-down. |

---

## Stage 4 · After recording

Right after the take, before any other Claude Code session, go back from the recording window to
the repo root and check that nothing is saved yet:
```powershell
cd ..\..
Test-Path REPLAY_IT_Professionals.txt
Test-Path recorded-run
```
The first line must print `True` (you're at the repo root) and the second `False`. If it prints `True`, an earlier run is saved there: stop and ask before
overwriting it. Then save the run, its session transcript and the video's hash:
```powershell
Copy-Item -Recurse demo-live\brand-ai-readiness-audit\audit-output recorded-run
Get-ChildItem $env:USERPROFILE\.claude\projects\*demo-live-brand-ai-readiness-audit* | Get-ChildItem -Filter *.jsonl | Sort-Object LastWriteTime | Select-Object -Last 1 | Copy-Item -Destination recorded-run\session.jsonl
python tools\tool_calls.py recorded-run\session.jsonl
(Get-FileHash "<path to the raw video>").Hash
python tools\check_replay.py
```
- `tools\tool_calls.py` must show the `Skill` call.
- Write the raw video's file name, length and hash into `recorded-run\README.md`. The video itself stays out of git.

**Prove every finding on screen is real.** The rules fail a video that shows fabricated
findings, and the drill-down must show real evidence. Run this straight away, while the site is
still as it was during the take:
```powershell
python tools\check_findings.py recorded-run
```
It must end with `0 problem(s)`. It checks two things, and saves both in `recorded-run\finding-check.md`:
1. **Nothing was invented.** Every row, ID, severity, ICE, title and count the agent showed is
   the engine's own, from `audit-report.json`. This includes the drill-down's `blocked_by` count.
2. **What was shown is true on the live site.** It fetches each table row's pages again and
   counts for itself, without using the engine's code or the agent's.

Reading the result:
- `[HAND]`: a check it can't do automatically. Open the URL it gives, confirm the claim by eye,
  and write what you saw in `recorded-run\README.md`.
- `[WARN]`: read it; it doesn't mean a retake. Example: a row that holds only in part.
- `[FAIL]`: **don't submit this take.** Paste the output to Claude. A new take uses the backup
  URL (see "If it goes sideways"), never a splice.
- The table shows confirmed findings only, so a "likely" critical or high finding is counted under
  it, not re-checked. Add `--severe` to re-check those too, in a part 3:
  `python tools\check_findings.py recorded-run --severe`. To list every finding, highest first:
  `python tools\summarize.py recorded-run\audit-report.json --top 15`.

Then commit the run, as run sheet §F says:
`git add recorded-run`, then `git commit -m "Recorded run: docs.pytest.org"`, then `git push origin final-3`.

Final checks:
- Part 1 is 3:00 or less, Part 2 is 2:00 or less, and the total is 5:00 or less.
- Watch the export once with the REPLAY open. The harness (2.1.282), the model (Claude Opus 5.5)
  and the URL (`https://docs.pytest.org/`, or the backup) must match what the video shows.
