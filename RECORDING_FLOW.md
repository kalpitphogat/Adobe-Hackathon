# Recording flow: what to run, what to say

One page for the person recording, in order: every command or click, and the exact line to say
with it. The spoken lines are copied word for word from [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md)
(branch `final-3`). If the two ever differ, `VIDEO_SCRIPT.md` wins for what you say and
[`VIDEO_PART2_RUNSHEET.md`](VIDEO_PART2_RUNSHEET.md) wins for what you type.

This file works unchanged on **any Windows PC** with PowerShell, whoever's machine records.
Nothing below names a user, a drive or a folder outside this repo:
- **Every command runs at the repo root:** the folder of your clone that holds `REPLAY_IT_Professionals.txt`.
  To open PowerShell there, open that folder in File Explorer, click the address bar, type `powershell`, and press Enter.
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
```
The first line stops Claude Code from updating itself, in every new window from now on. That
matters: 2.1.283 came out on 2026-09-25, and the REPLAY says 2.1.282. When the video is done,
`[Environment]::SetEnvironmentVariable("DISABLE_AUTOUPDATER", $null, "User")` turns updates back on.

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

**Building `.venv`.** These are the REPLAY's own Windows lines. An existing wrong `.venv` is
renamed, not deleted; `.venv-*` folders are git-ignored. If `uv --version` isn't recognised, run
`winget install --id astral-sh.uv -e` (or `pip install uv`) first, then open a new PowerShell at
the repo root.
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
if (Test-Path .venv) { Rename-Item .venv (".venv-old-" + (Get-Date -Format "yyyyMMdd-HHmmss")) }
uvx --from "uv>=0.11" uv python install 3.11.15
uv venv --python 3.11.15 .venv
.venv\Scripts\Activate.ps1
uv pip install playwright==1.63.0
python -m playwright install chromium
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
- **Over 2:50** → apply the cut ladder (end of Stage 2), in order.
- **Under 2:45** → you have room for a restore line (end of Stage 2). Only 13 words fit under the
  3:00 cap without also taking a cut-ladder step, so read that table's arithmetic before adding one.
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
```
- `verify_engine.py` must end with `RESULT : ENGINE UNCHANGED`.
- You should see 10 tabs. If `code` isn't recognised, open the `demo` folder in VS Code by hand
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
```
- `python --version` must print Python 3.11.15.
- The `verify_engine.py` run is a dry run of the on-camera command and must end with `RESULT : ENGINE UNCHANGED`.
- The last line starts Claude Code once, **off camera**, so its first-run questions don't land in the take.
  - If it asks whether you trust the files in this folder, answer **Yes**.
  - Don't send it a prompt: type `/exit`, then `Clear-Host`.
- Leave this window open: Part 2 starts here, and the venv and both `$env:` settings belong to this window.
  If you close it, run this whole block again.

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

## Stage 2 · PART 1 · Thought process (cap 3:00, target 2:50)

Part 1 may be recorded in several takes.
- Every shot needs its file on screen, its lines highlighted, and a lower-third caption.
- Captions are added in the editor. Each tab's caption is written above its table.
- **Ten tabs, fourteen spoken beats.** Every SAY line is a complete sentence, so if you fluff one you
  restart that sentence, not the paragraph.

**Moving around in VS Code.** Each row below is one screen: do the DO, then say the SAY.
- `Ctrl+PgDn`: the next tab. Each tab opens on the first line it needs.
- `Ctrl+G`, type the line number, `Enter`: go to another line in the same file. VS Code puts that line mid-screen.
- `Ctrl+P`, type `file:line`, `Enter`: jump straight to a line in any file, open or not. Steps 6d,
  7 and 11 use it, and so do the restore lines.
- **Highlight:** click the line number in the left margin. For several lines, click the first number, then **Shift+click** the last.
  - A row that says only "click" needs no jump: that line is already on screen, a few lines away.
  - If a line you need is ever off screen, scroll to it.
- **When a sentence carries on in the next row:** say the row's words, stop, press the keys, then carry on.
  Every split falls on a `·` pause or between two sentences, so you never talk while you type.
  The silent key presses can be trimmed in the edit.
- **Retake:**
  1. In the Stage 1.1 window, run the 10 `code -g` lines again, so every tab is back on its first line.
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
| 1 | Tab 1 is on screen, on line 40. Click **40**, Shift+click **43**. | "Ask an AI assistant about a brand, and it either **quotes** the site or acts as if it **doesn't exist**. The handout explains why: unless a page is easy to **reach, read and quote**, it never reaches the answer. Our agent finds **which step fails**." |

*Slow down on "doesn't exist", and smile on the last sentence.*

### 0:21–0:56 · Act I · What separates the cited from the ignored
**Tab 2 `gate-rules.md`** · CAPTION `gate-rules.md:10 · 66 checks: DESIGN.md:108 (count generated from the code)`

| step | DO | SAY |
|---|---|---|
| 2 | `Ctrl+PgDn` → tab 2, on line 10. Click **10**, Shift+click **14**. | "Those steps happen **in order**, so each of our 66 checks belongs to a stage: reach, read, extract, trust · and act, the visitor who arrives." |

**Tab 3 `ai-bots.json`** · CAPTION `ai-bots.json:12–14 · 29 crawlers: 14 retrieval, 10 training, 5 contested`

| step | DO | SAY |
|---|---|---|
| 3a | `Ctrl+PgDn` → tab 3, on line 12. Click **12**, Shift+click **14**. | "Lists tell you which AI crawlers to **block**; we asked what blocking each one **costs**, and sorted 29 by role." |
| 3b | `Ctrl+G` → type `71` → `Enter`. Click **71**: `"GPTBot"` … `"category": "training"`. | "Block GPTBot and you have opted out of **training**." |
| 3c | `Ctrl+G` → type `26` → `Enter`. Click **26**: "Blocking one of these removes the brand from that assistant's answers." | "Block a retrieval crawler and you **vanish from that assistant's answers**." |

**Tab 4 `check_robots.py`** · CAPTION `check_robots.py:286 critical · :318 info` · *cut-ladder step 1 skips 4a–4b*

| step | DO | SAY |
|---|---|---|
| 4a | `Ctrl+PgDn` → tab 4, on line 286. Click **286**: `severity="critical"`. | "So one robots.txt rule is **critical** against a retrieval crawler," |
| 4b | `Ctrl+G` → type `318` → `Enter`. Click **318**: `severity="info"`. | "and merely **informational** against a training one." |

### 0:56–1:33 · Act II · How bad, how sure
**Tab 5 `severity-model.md`** · CAPTION `severity-model.md:43`

| step | DO | SAY |
|---|---|---|
| 5 | `Ctrl+PgDn` → tab 5, on line 43. Click **43**. | "Severity asks **how bad this is if true**; confidence asks **how sure we are**." |

**Tab 6 `gate_model.py`** · CAPTION `gate_model.py:117 apply_cascade · :42 ceiling "medium" · :120 cap, never delete · :129 Rule 0`

| step | DO | SAY |
|---|---|---|
| 6a | `Ctrl+PgDn` → tab 6, on line 117. Click **117**, Shift+click **118**. | "A flat checklist hands a site that blocks AI crawlers **fifteen criticals**, and fourteen are moot." |
| 6b | Click **120**, two lines down: `Rule 3: cap, never delete.` | "`apply_cascade` caps those at medium and tags the **one** blocker that matters: **capped, never deleted**." |
| 6c | `Ctrl+G` → type `128` → `Enter`. Click **128**, Shift+click **129**. | "Engagement is never gated: a visitor from an ad doesn't care whether a crawler got in." |

**Rule 0b, back in `gate-rules.md` (tab 2)** · CAPTION `gate-rules.md:54–57 · Rule 0b`

| step | DO | SAY |
|---|---|---|
| 6d | `Ctrl+P` → type `gate-rules.md:54` → `Enter`. This is tab 2 again, no new tab. Click **54**, Shift+click **55**. | "And when we never even saw the page a visitor sees, those findings aren't capped, they're **suppressed**." |
| 6e | Click **56**, Shift+click **57**: "Capping asserts a weaker claim. Suppression asserts none." | "A cap still claims something · suppression claims **nothing**." *(cut-ladder step 3 drops this row)* |

*Capping says "real, but moot"; suppression says "we never looked". You are now on tab 2, so step 7
uses `Ctrl+P`, not `Ctrl+PgDn`.*

### 1:33–1:59 · Act III · Every fix earns its place
**Tab 7 `orchestrate.py`** · CAPTION `orchestrate.py:242 validate_finding · rejection logged at :695`

| step | DO | SAY |
|---|---|---|
| 7 | `Ctrl+P` → type `orchestrate.py:242` → `Enter` (**not** `Ctrl+PgDn`: 6d left you on tab 2). Click **242**, Shift+click **253**. | "Every fix must say **why** it works, so `validate_finding` rejects any finding without a mechanism." |

**Tab 8 `extract_markup.py`** · CAPTION `extract_markup.py:204 · "__FILL_IN__" when a value is absent (94 places in the engine)`

| step | DO | SAY |
|---|---|---|
| 8a | `Ctrl+PgDn` → tab 8, on line 203. Click **203**, Shift+click **204**: `Never invented.` | "Our patches reuse values from the page and **never invent one**;" |
| 8b | Click **209**, Shift+click **210**, five lines down: `__FILL_IN__`. | "whatever we couldn't find stays **FILL_IN**." |

**Tab 9 `severity.py`** · CAPTION `severity.py:27–29 lookups · :13 impact from post-gate severity · :68 total order`

| step | DO | SAY |
|---|---|---|
| 9a | `Ctrl+PgDn` → tab 9, on line 26. Click **26**, Shift+click **29**. | "Priority is **ICE**: impact, confidence, ease." |
| 9b | `Ctrl+G` → type `13` → `Enter`. Click **13**, Shift+click **15**. | "Impact uses the **capped** severity, so a moot defect cannot outrank its blocker," |
| 9c | `Ctrl+G` → type `68` → `Enter`. Click **68**, Shift+click **71**. | "and **the same evidence always ranks the same way**." *(cut-ladder step 2 drops this row; end 9b on "blocker.")* |

### 1:59–2:39 · Act IV · The day the real web proved us wrong
**Tab 10 `DESIGN.md`, the field test** · CAPTION `DESIGN.md:374–379 · field test on five live sites`, then `DESIGN.md:377–378`

| step | DO | SAY |
|---|---|---|
| 10a | `Ctrl+PgDn` → tab 10, on line 369. Click **369**, Shift+click **374**. | "Then the real web **humbled** us. Five live sites produced **365 findings**, and that number was itself the finding." |
| 10b | Click **374**, Shift+click **379**: twelve false positives … **205**. | "We named twelve false positives before touching a threshold, and came down to **205**." |
| 10c | Click **377**, Shift+click **378**, already on screen: file sizes as phone numbers, a free download page asked for a price. | "Two of them: we were reading file sizes as **phone numbers**, and telling a free download page to publish a **price**." *(cut-ladder step 4 drops this row)* |

*Let 10c breathe. It is the one laugh in Part 1, and it turns "twelve false positives" into something
a judge can picture.*

**Tab 10 `DESIGN.md`, the zero-recall story** · CAPTION `DESIGN.md:324, :334 · rewritten: dom.py:56 NOSCRIPT_JS_NOTICE · pinned: tests/test_regressions.py R1–R12`

| step | DO | SAY |
|---|---|---|
| 10d | `Ctrl+G` → type `322` → `Enter`. Click **322**, Shift+click **325**: "fired **zero times** … **16 words**". | "Worse, our empty-page detector fired **zero times**, even on a docs site of **sixteen words**, because we'd tuned it to our own fixture." |
| 10e | `Ctrl+G` → type `332` → `Enter`. Click **332**, Shift+click **335**: "A fixture proves a check does what you wrote". | "A fixture proves a check does what you wrote · **not that you wrote the right thing**." |

*Don't rush 10d–10e. The admission is what earns the closing line.*

### 2:39–2:50 · Close
**`geo-methods.md`, opened fresh** · CAPTION `geo-methods.md:56`

| step | DO | SAY |
|---|---|---|
| 11 | `Ctrl+P` → type `geo-methods.md:56` → `Enter`. Click **56**, Shift+click **57**. | "Our own code puts it best: a citation you can't check is worse than none, **because it looks like evidence**. So don't trust us. · **Watch.**" |

*Hard cut to Part 2 on "Watch."*

### Cut ladder: only if your timed read is over 2:50, and only in this order
The full cut is 391 words: **2:55** at the cautious 140 words a minute the checker uses, 2:50 at 145.
Each step drops a whole sentence.

1. Skip steps 4a–4b, the `check_robots.py` beat (−17 words → about 2:48). From tab 3, press
   `Ctrl+PgDn` **twice** to reach tab 5.
2. Skip step 9c, "and the same evidence always ranks the same way" (−9 words → about 2:44). End 9b on "blocker."
3. Skip step 6e, "A cap still claims something…" (−8 words → about 2:41). Keep 6d: Rule 0b still
   lands on **suppressed**.
4. Skip step 10c, the phone-numbers line (−21 words → about 2:32). It is the one laugh in Part 1, so
   it goes last, not first.

**Never cut:**
- the cold open
- the crawler-roles beat (steps 3a–3c)
- `apply_cascade` and "engagement is never gated"
- step 6d, Rule 0b's first sentence
- `validate_finding`
- "never invent one" and FILL_IN
- steps 9a–9b (ICE)
- the 365 → 205 field test
- the zero-recall story (10d–10e)
- the closing quote

### Restore lines: only if your timed read is under 2:45
The phone-numbers laugh (10c) and Rule 0b (6d–6e) are **already in the main read**. These four are
the lines that did not fit. Each is still in the anchor ledger, so it is safe to put back.

**Mind the cap.** 391 words is 2:55 at 140 words a minute, so only **13 more words** fit under 3:00.
R1 and R5 fit together (+10 words). R2, R3 or R4 needs a cut-ladder step to pay for it. Re-run
`python tools\check_script_anchors.py` after any restore: it must still print `0 problem(s)`.

| step | DO | SAY |
|---|---|---|
| R1, before 3a (+6 words) | No new shot: tab 3, lines **12–14**, as in 3a. | "Reach taught us our first rule." |
| R5, at the end of 7 (+4 words) | No new shot: the caption already cites `:695`. | "…and logs the rejection." |
| R2, after 5 (+19 words) | In tab 5, `Ctrl+G` → type `56` → `Enter`. Click **56**, Shift+click **57**. CAPTION `severity-model.md:56` | "A check that cannot run says so, because a clean report and one that **couldn't look** are different things." |
| R3, after 4b (+24 words) | `Ctrl+P` → type `geo-methods.md:14` → `Enter`. Click **14**, Shift+click **19**, then `Ctrl+G 24`, click **24**. CAPTION `geo-methods.md:14–24 · GEO (KDD 2024): a benchmark gain, not a defect` | "We calibrate against research, not instinct: the GEO paper shows that adding statistics helps **in a benchmark**, so a page without them scores **low**." |
| R4, after 6e (+19 words) | `Ctrl+P` → type `site_b.report.md:58` → `Enter`. Click **58**, Shift+click **60**. CAPTION `tests/golden/site_b.report.md:60 · same in site_b.audit-report.json:109 ("blocked_by": "F-001")` | "You can see the cascade in our golden report: **one** critical, **eleven** findings waiting on it, and engagement untouched." |

- **R2 says in plain words what 6d–6e now says precisely.** Restore it only if Rule 0b landed badly.
- **R4 is last:** Part 2's Card B already shows the same cascade on a live site.
- R3 and R4 open a file that is **not** one of the ten tabs, so afterwards come back with `Ctrl+P` and
  the `file:line` of the step you were on, not `Ctrl+PgDn`.

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
