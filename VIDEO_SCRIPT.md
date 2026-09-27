# 🎬 Invisible to the Machine: the Round 4 video script

**Team IT_Professionals** (Lakshya, Tanmay, Kalpit) · Adobe University Hackathon 2026, Round 4

This is the whole video, word for word and shot by shot: Part 1 (≤ 3:00) and Part 2 (≤ 2:00).
It **replaces the narration** in `VIDEO_PART1_SCRIPT.md` and the "you say" column in
`VIDEO_PART2_RUNSHEET.md`. The run sheet is still the **operations manual** for the live run
(fresh folder, recorder, what to do if something breaks). Where the two differ, this file wins
for *what you say*; the run sheet wins for *what you type*.
[`RECORDING_FLOW.md`](RECORDING_FLOW.md) puts the two side by side, step by step: each command or
click next to the line you say with it.

| | hard cap | target | spoken words | at 145 wpm |
|---|---|---|---|---|
| **Part 1**: thought process | 3:00 | **2:49** | 389 (cut ladder → 349) | 2:49 incl. title card and pauses (→ 2:32) |
| **Part 2**: live trial run | 2:00 | **1:55** after trimming idle waits | ~230, incl. one drill-down card | ~1:35 of talk, over the screen action |
| **Total** | 5:00 | **4:44** | | 16 s of headroom |

`python tools/check_script_anchors.py` re-checks every file:line in this script against
`round3-frozen/submission.zip` and re-counts the Part 1 words. **It must print `0 problem(s)`
before you record.**

---

## The story in one breath

A brand is either quoted by AI assistants or treated as if it doesn't exist. **Act I** shows
where our signals came from: the handout's *reach, read, quote* and the non-obvious lesson that
AI crawlers are not all equal. **Act II** shows how bad each problem is and why the *order* of
failures matters more than the count. **Act III** shows how every fix earns its place.
**Act IV** is the twist: the real web proved our own tool wrong, and we show how we fixed it.
The last line of Part 1 is a quote from our own code, *"a citation that can't be checked is worse
than none"*, and it hands straight to **Part 2**, where you don't have to take our word for anything.
The agent runs the engine live on a site it has never seen, then **checks the engine's own
evidence** before it drills in.

**The through-line:** *evidence you can check.* Every claim in Part 1 is shown in the code while
you say it. Every finding in Part 2 comes with a URL, a count and a command to verify it.

---

## Three rules for whoever holds the mic

1. **Every Part 1 sentence has its file on screen while you say it.** The brief: *"Narration that
   cannot be traced to the submitted code earns no credit."* If you cut a sentence, cut its shot.
2. **In Part 2, `[brackets]` mean read the number off the screen.** Never say a number or finding
   the terminal isn't showing. The example values below come from rehearsals; the live run decides.
3. **Part 1 can be edited freely; Part 2 cannot.** Record Part 1 in as many takes as you like.
   Part 2 is one continuous take: trim waits, never splice.

---

## 0 · Before you hit record

**Checks, from the repo root** (same venv as the run sheet):

```
python tools/check_script_anchors.py   # every anchor below still matches the zip → 0 problem(s)
python tools/check_replay.py           # REPLAY fields + harness version → 0 problem(s)
```

Then do **run sheet §A** (fresh `demo-live/`, clipboard prompt without the URL, recorder on).
**Do not open or audit https://docs.pytest.org/ with the engine before the take.** It has to be unseen.

**The step-2 prompt changed on 2026-09-26:** the table now shows the top 5 *confirmed* findings and
the agent re-checks **every** row. Rehearse it once before the take (run sheet §A, step 1b) on a
*seen* site. `https://www.docker.com/` is the useful one: its top confirmed finding is a
`trust.integrity.prompt_injection` false positive, which the verdict column should mark *not supported*.

**VS Code for Part 1:** open the **unzipped submission** (`demo/`, never another copy). Zen mode
(`Ctrl+K Z`) **with line numbers on** (`zenMode.hideLineNumbers` off; Zen hides them by default),
font 20, minimap off, word wrap on, high-contrast theme. Pre-open these tabs **in this order**
so `Ctrl+PgDn` walks the script. Each is already scrolled to its first line; "then" is each
`Ctrl+G` jump. [`RECORDING_FLOW.md`](RECORDING_FLOW.md) Stage 2 splits every line at its jump,
key by key:

| tab | file (relative to the marketplace root) | first line | then |
|---|---|---|---|
| 1 | `skills/answerability-audit/references/chunking-model.md` | 40 | |
| 2 | `skills/ai-readiness-orchestrator/references/gate-rules.md` | 10 | |
| 3 | `skills/crawl-access-audit/references/ai-bots.json` | 12 | → 71 → 26 |
| 4 | `skills/crawl-access-audit/scripts/check_robots.py` | 286 | → 318 |
| 5 | `skills/answerability-audit/references/geo-methods.md` | 14 | → 24 |
| 6 | `skills/ai-readiness-orchestrator/references/severity-model.md` | 43 | → 56 |
| 7 | `skills/ai-readiness-orchestrator/scripts/gate_model.py` | 117 | → 128 |
| 8 | `tests/golden/site_b.report.md` | 58 | |
| 9 | `skills/ai-readiness-orchestrator/scripts/orchestrate.py` | 242 | |
| 10 | `skills/structured-data-audit/scripts/extract_markup.py` | 203 | |
| 11 | `skills/ai-readiness-orchestrator/scripts/severity.py` | 26 | → 13 → 68 |
| 12 | `DESIGN.md` | 369 | → 322 → 332 |
| — | the closing shot: `Ctrl+P`, type `geo-methods.md:56`, `Enter` (jumps tab 5 straight to line 56) | | |

**Highlight the line you're talking about** (click its line number) so the viewer's eye lands
on it. Every shot also gets a **lower-third caption** with `file:line` (see §3). That caption is
how a judge traces the claim, even if the code is small on their screen.

---

## 1 · PART 1 · Thought process (hard cap 3:00, target 2:50)

*Spoken lines are the `>` blockquotes. **Bold** = lean on the word. `·` = a half-beat pause.
Everything else is direction, not speech.*

### Title card (0:00–0:02)

**SCREEN:** black card, white text, 2 seconds, no voice:
**INVISIBLE TO THE MACHINE** · *Brand AI-Readiness Audit* · IT_Professionals · Round 4

### Beat 0 · Cold open (0:02–0:21)

**SCREEN:** Tab 1 `chunking-model.md`, lines **40–43** highlighted (the handout's own sentence).
**CAPTION:** `chunking-model.md:40–43 · the handout, quoted in our code`

> Ask an AI assistant about a brand: it either **quotes** the site · or acts like it **doesn't exist**.
> The handout says why: if nothing is easy to **reach, read, and quote**, it won't make the answer.
> We're IT_Professionals, and our agent finds **which step fails**.

*Deliver it like a question you're dying to answer: slower on "doesn't exist", a smile on the last line.*

### Act I · What separates the cited from the ignored (0:21–0:58)

**SCREEN:** Tab 2 `gate-rules.md`, lines **10–14** ("three things have to succeed in order").
**CAPTION:** `gate-rules.md:10 · 66 checks: DESIGN.md:108 (count generated from the code)`

> And the steps come **in order**, so each of our 66 checks has a stage: reach, read, extract, trust · and act, for visitors.

**SCREEN:** Tab 3 `ai-bots.json`, lines **12–14** ("we need to know what blocking each one COSTS"),
then `Ctrl+G 71` (`"GPTBot" … "category": "training"`) for GPTBot, then `Ctrl+G 26` for the retrieval
bot ("Blocking one of these removes the brand from that assistant's answers").
**CAPTION:** `ai-bots.json:12–14 · 29 crawlers: 14 retrieval, 10 training, 5 contested`

> Reach taught us rule one: lists say which AI bots to **block**; we asked what blocking each **costs**, and sorted 29 by role.
> Block GPTBot: you've opted out of **training**. Block a retrieval bot: you **vanish from its answers**.

**SCREEN:** Tab 4 `check_robots.py`, line **286** (`severity="critical"`), then line **318** (`severity="info"`).
**CAPTION:** `check_robots.py:286 critical · :318 info`

> Same rule · **critical** for one, line 286 · **info** for the other, line 318.

**SCREEN:** Tab 5 `geo-methods.md`, lines **14–19**, then line **24** ("fires at **low** severity").
**CAPTION:** `geo-methods.md:14–24 · GEO (KDD 2024): a benchmark gain, not a defect`

> Quote: GEO research says statistics help · **in a benchmark** · so their absence scores **low**.

### Act II · How bad, how sure (0:58–1:35)

**SCREEN:** Tab 6 `severity-model.md`, line **43** ("Severity answers 'how bad if true'. Confidence answers 'how sure'"),
then line **56** ("A clean report and a report that could not look are different things").
**CAPTION:** `severity-model.md:43 · :56`

> Severity asks: **how bad, if true?** Confidence is a separate field: **how sure?**
> A check that couldn't run says so: a clean report and one that couldn't look are **different things**.

**SCREEN:** Tab 7 `gate_model.py`, line **117** (`def apply_cascade`), then line **128–129**
(`# Rule 0: gates never touch engagement`).
**CAPTION:** `gate_model.py:117 apply_cascade · :42 ceiling "medium" · :129 Rule 0`

> A flat checklist gives a site blocking AI crawlers **fifteen criticals**, fourteen of them moot.
> `apply_cascade` caps those at medium and tags the **one** blocker. **Capped · never deleted.**
> Line 128: engagement is **never** gated. A visitor from an ad doesn't care if a crawler got in.

**SCREEN:** Tab 8 `tests/golden/site_b.report.md`, lines **58–60**
("11 finding(s) are recorded but capped at medium because F-001 … blocks them").
**CAPTION:** `tests/golden/site_b.report.md:60 · same in site_b.audit-report.json:109 ("blocked_by": "F-001")`

> Our golden: **one** critical, **eleven** findings waiting on F-001, engagement untouched.

### Act III · Every fix earns its place (1:35–2:01)

**SCREEN:** Tab 9 `orchestrate.py`, lines **242–253** (`validate_finding`, line 252 `mechanism`).
**CAPTION:** `orchestrate.py:242 validate_finding · rejection logged at :695`

> Every fix must say **why** it works: `validate_finding` rejects any finding without a mechanism, and logs it.

**SCREEN:** Tab 10 `extract_markup.py`, lines **203–210** (`"""… Never invented."""`).
**CAPTION:** `extract_markup.py:204 · "__FILL_IN__" when a value is absent (94 places in the engine)`

> Patches reuse values seen on the page · **never invented**. Anything missing stays **FILL_IN**.

**SCREEN:** Tab 11 `severity.py`, lines **26–29** (the three lookup tables), then **13–15**, then **68–71** (`sort_key`).
**CAPTION:** `severity.py:27–29 lookups · :13 impact from post-gate severity · :68 total order`

> Priority is **ICE**: impact, confidence, ease, from fixed lookups. Impact uses the **capped** severity, so a moot defect can't outrank its blocker.
> A total sort order: **same evidence, same ranking.**

### Act IV · The day the real web proved us wrong (2:01–2:47)

**SCREEN:** Tab 12 `DESIGN.md`, lines **369–380** (five sites, 365 findings, the false positives, 205).
**CAPTION:** `DESIGN.md:374–379 · field test on five live sites`

> Then the real web **humbled** us. Five live sites · **365 findings** · which was itself the finding.
> File sizes read as **phone numbers**. A free download page told to show a **price**.
> We named twelve false positives before touching a threshold, and got to **205**.

*Let "phone numbers" and "price" land. It's the one laugh in Part 1, so give it a beat.*

**SCREEN:** same tab, `Ctrl+G 322`, lines **322–325** ("fired **zero times** … **16 words**"), then
`Ctrl+G 332`, lines **332–335** ("A fixture proves a check does what you wrote").
**CAPTION:** `DESIGN.md:324, :334 · rewritten: dom.py:56 NOSCRIPT_JS_NOTICE · pinned: tests/test_regressions.py R1–R12`

> Worse: our empty-page detector fired **zero times** · even on a docs site with **sixteen words**. It was tuned to our own fixture.
> A fixture proves a check does what you wrote · **not that you wrote the right thing.**

**SCREEN:** `Ctrl+P` → `geo-methods.md:56` → `Enter` ("A citation that cannot be checked is worse than no citation, because it looks like evidence.").
**CAPTION:** `geo-methods.md:56`

> Our own code puts it best: a citation you can't check is worse than none · **because it looks like evidence.**
> So don't trust us. · **Watch.**

*Hard cut to Part 2 on "Watch."*

### If the timed run is long: the cut ladder

Time a full read-through with a stopwatch (tab switches included). **Over 2:50 → cut, in this order,
and only in this order.** Cut the shot with the words.

| step | cut | words | total after | ≈ at 145 wpm |
|---|---|---|---|---|
| — | full script | | 389 | 2:49 |
| 1 | the GEO line (skip tab 5's first shot: `Ctrl+PgDn` twice from tab 4; the closing `Ctrl+P` still works) | −14 | 375 | 2:43 |
| 2 | "Our golden: one critical…" (tab 8: `Ctrl+PgDn` twice from tab 7) | −11 | 364 | 2:39 |
| 3 | "File sizes read as phone numbers… show a price." | −15 | 349 | 2:32 |

*(Times at 145 wpm plus ~8 s for the title card and beat pauses. `tools/check_script_anchors.py`
recounts the full cut every run and fails if it would pass 3:00 even at a slow 140 wpm.)*

**Never cut:** the cold open, the crawler-roles lines, `apply_cascade`, "never gated",
`validate_finding`, ICE, the zero-recall story, the closing quote. Together they are the rubric's
*discovery, severity, fixes*.

### If the timed run is short (under 2:35): bonus lines

Add in this order, each with its shot:

1. **After "never gated…"**, `Ctrl+P` → `gate-rules.md:54` (tab 2). CAPTION `gate-rules.md:54–57 · Rule 0b`.
   Afterwards `Ctrl+P` → `site_b.report.md:58` puts you back on tab 8.
   > And if we never saw the page a visitor sees, those findings aren't softened, they're **suppressed**. Capping asserts a weaker claim. Suppression asserts **none**.
2. **After "…the right thing."**, `Ctrl+P` → `test_regressions.py:2` (the caption's `tests/test_regressions.py`, a new tab); highlight line 2.
   > Tests R1 to R12 keep fixed bugs fixed.

---

## 2 · PART 2 · Live trial run (hard cap 2:00 after trimming, target 1:55)

**On-camera URL:** `https://docs.pytest.org/` (never audited). **Harness:** Claude Code **2.1.282**.
**Model:** Claude Opus 5.5 (`claude-opus-5-5`). All three must match `REPLAY_IT_Professionals.txt`.
Retake → new URL, per run sheet §E. **Never splice two takes.**

**How to narrate it:** talk **live** during the take (the mic track is part of your proof), and
**stay silent while the agent is only waiting**, so trimming a wait never cuts a word. If the
live narration comes out messy, you may re-voice the *trimmed* cut afterwards with the same
lines, but the picture stays exactly as recorded. Keep the raw file.

**Pace:** these lines are short on purpose. Let the screen breathe. Judges want to *read* the
terminal.
**If the edit runs over 2:00:** trim idle waits harder first. Then drop the sentences marked
*(opt:)*. Never drop the typed URL, the harness/model line, the wiring line, the priority table,
the evidence check or the drill-down.

| time (after trim) | SCREEN | SAY |
|---|---|---|
| **0:00–0:02** | Title strip over the terminal: **PART 2 · LIVE · one continuous take · idle waits trimmed** | *(silent)* |
| **0:02–0:12** | Terminal in `demo-live\brand-ai-readiness-audit`. Run `python ..\..\tools\verify_engine.py ..\submission.zip .` → `byte-identical : 155` … `RESULT : ENGINE UNCHANGED`. Then `claude --version` → `2.1.282 (Claude Code)`. | > Part two: **live, one take.** This is our Round 3 zip, unzipped: **155 files, byte-identical** to what we submitted. The harness is **Claude Code 2.1.282**… |
| **0:12–0:18** | `claude --model claude-opus-5-5 --allowedTools "Skill" "Bash(python:*)" "PowerShell(python:*)" "Read"`. When it opens, type `/model` so **Opus 5.5** is on screen, then `Esc`. | > …running **Claude Opus 5.5.** |
| **0:18–0:28** | Paste the prompt (it ends in `URL: `). **Type** `https://docs.pytest.org/` by hand. Enter. | > I paste our REPLAY prompt, word for word · and type a site our engine has **never seen**. |
| **0:28–0:38** | **`Skill(ai-readiness-orchestrator)`** appears. **Hold 2 s.** Then `python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://docs.pytest.org/ --no-render --out ./audit-precheck`. **Hold 2 s.** Approve any permission prompt on camera. | > That's the **wiring**: the agent loads our entrypoint skill, *ai-readiness-orchestrator*, and runs its `orchestrate.py`. **No demo script, no canned results.** |
| — | *Trim the crawl.* On-screen badge: **⏩ crawl · ~40 s trimmed** | |
| **0:38–0:50** | The agent's `python -c` count on `pages.jsonl`, then its one line naming pass 2 and why, then the pass-2 command. **Hold 2 s on the "why" line.** | **If the count is 0:** > Pass one: no browser. The agent checks that crawl for any page only JavaScript could build. **None** · so pass two re-reads the **same evidence**, no second crawl. <br><br> **If the count is above 0:** > Pass one: no browser. The agent checks that crawl for pages only JavaScript could build. It found **[N]** · so pass two **renders** the site in Chromium. |
| — | *Trim the second pass and the agent's reading.* Badge: **⏩ ~Ns trimmed** | |
| **0:50–1:00** | Final answer, section (1): `audit_status`, counts by severity, "not assessed". | **If `partial`:** > **[N] findings** from six audit skills. Status **partial**, and it says why: **[the browser checks weren't run]**, so they're listed as **not assessed.** <br><br> **If `complete`:** > **[N] findings** from six audit skills. Status **complete**. The one blind spot it names is the edge probe, which stays off unless you own the site. |
| **1:00–1:10** | Section (2): the **table of the top 5 confirmed findings**, with the ICE column, and the line under it counting the likely ones. Scroll slowly. | > Here are the fixes, **sorted by impact**: severity first, then ICE. These are the ones a deterministic check **confirmed**; the **[N] likely** ones are counted right under the table, not hidden. *(opt:)* That's the **engine's** order, not the model's. |
| **1:10–1:22** | Section (3): the **verdict column**. The agent re-fetched **every row**. Hold on a line that says *supported*, with its numbers. | > Now the agent **audits the auditor.** It re-fetches **every row** itself: **[what it counted, e.g. "zero JSON-LD blocks"]**. **Supported.** That's commentary; the report stays exactly as the engine wrote it. <br><br> *If any row came back* **not supported**, *add Card F first (below).* |
| **1:22–1:48** | Section (4): the **drill-down**. Scroll it top to bottom: evidence, severity/confidence, mechanism, patch, ICE, `blocked_by` count, verification. Optionally flip to VS Code on `audit-output/audit-report.json`, `Ctrl+F` the `check_id` (run sheet §D). | **Read the card below that matches the finding on screen.** |
| **1:48–1:55** | Stay on the verification command, or the `fix_patches/` folder in VS Code. | > Evidence, severity, mechanism, patch, and a **command to verify it**, on every finding. It's all in **REPLAY_IT_Professionals.txt.** Pick your own URL · and **check us.** |

### Drill-down cards: read the one that matches the screen

The agent picks the drill-down itself: **the highest-ranked row of its table that its evidence check supported**.
Each card is ~45 words (~20 s). Swap in the real numbers from the screen.

**Card A · `extract.sd.absent_on_eligible_page`** ("… eligible page(s) carry no structured data at all"). The most likely card on a docs site.
Anchors: `extract_markup.py:174–175` (title, high/confirmed), `:189` (mechanism), `:204` (patch built from the page).
> Drill-down: **[16 of 16]** eligible pages carry no structured data. **High**: nothing is machine-typed. **Confirmed**: a deterministic check saw it. The mechanism: typed facts are read **without guessing from prose.** The patch is JSON-LD built from the page's own title, and whatever it couldn't see says **FILL_IN**. ICE **7.3**.

*(7.3 = impact 8, confidence 9, ease 5; say what's on screen if it differs.)*

**Card B · `reach.robots.ai_search_bot_blocked`** ("robots.txt blocks N AI retrieval crawler(s) …").
Anchors: `check_robots.py:286` (critical/confirmed), `:305` (the patch).
> Drill-down on **F-001**: robots.txt blocks **[N] retrieval crawlers**, quoting the exact rule and line. **Critical, confirmed**: these bots fetch pages at answer time, so the brand can't be cited. The patch: one Allow block per bot, training policy untouched. ICE **9.3**. And **[N] findings** point at it with `blocked_by`: **the cascade from Part 1, live.**

**Card C · `reach.index.noindex_on_content`** ("N content page(s) tell crawlers not to index them").
Anchors: `check_indexability.py:77–78` (critical/confirmed), `:90` (mechanism).
> Drill-down: **[N]** content pages tell crawlers **not to index them**, through **[the X-Robots-Tag header / a meta robots tag]**. A noindexed page is read, then **discarded**, so it can never be cited: critical, confirmed. The fix: drop the directive. ICE **9.3**.

*Only if the agent notes it may be deliberate, add:*
> And the agent flags it may be **on purpose**. That's the owner's call; the report says exactly what it saw.

**Card D · `read.render.raw_text_gap`** ("Most of this page's text only exists after JavaScript runs"). Only if pass 2 rendered.
Anchors: `diff_raw_rendered.py:163–164` (high/confirmed), `:179` (mechanism).
> Drill-down: the raw HTML has **[X] words**; after JavaScript runs, **[Y]**. A crawler that doesn't run JavaScript **never sees** that text: high, confirmed. And the agent **re-counted both sides in Playwright** itself. The fix is server-side or pre-rendering; the verify command counts the words again.

**Card E · `trust.date.absent_on_dated_content`** ("N page(s) of dated content carry no date at all"), or any other *confirmed* medium, if no high was supported.
Anchors: `date_consistency.py:143–144` (medium/confirmed), `:158` (mechanism), `:168–169` (`__FILL_IN__` dates).
> Drill-down: **[N]** pages of dated content carry **no date at all.** Freshness is weighed when sources disagree, and an undated page **can't compete** on it. Medium, confirmed. The patch adds datePublished and dateModified as **FILL_IN**, because we will **not invent a date.** ICE **7.7**.

**Card F · a row's verdict is *not supported*** (most likely on `read.render.nav_links_js_only`, or on `trust.integrity.prompt_injection` when the page only *discusses* AI). Read it **before** the card for the finding that *was* supported:
> Look, the agent says **this one doesn't hold** on the live page. So we'd verify before acting, and the report stays exactly as the engine wrote it. The drill-down is on **[F-00x]**, which **does.**

*This is a strength, not a stumble: it's the "check us" promise happening on camera. Don't trim it out.*

**Never drill into** `trust.integrity.prompt_injection` on a page that only *discusses* AI, or
`read.render.nav_links_js_only` unless the agent's same-host counts back it up (run sheet §C).
`act.orient.no_value_proposition` and `act.cta.absent_for_page_type` are *likely*, so they are no
longer in the table; they only appear if fewer than five findings are confirmed. Don't drill into them.

### If it goes sideways

Run sheet **§E** has the full table. The three that matter on camera:

- **Permission prompt:** approve it on camera ("yes"), trim the pause. It is part of the real run.
- **"no evidence bundle was produced":** wrong folder. Stop; new take on `https://www.sphinx-doc.org/`
  after updating the REPLAY and run sheet (§E). Never splice.
- **Output too long for 2:00:** scroll faster and trim the agent's thinking. **Never cut** the typed URL,
  the `Skill(...)` call, the pass-2 line, the priority table, the evidence check or the drill-down.

---

## 3 · Production notes (what makes it look and sound like a winner)

**Picture**
- 1920×1080, 30 fps. Terminal and VS Code both **font 18–20**, dark theme, high contrast.
- **Lower-third captions** on every Part 1 shot: monospace, bottom-left, `file:line` exactly as
  written in the CAPTION lines above. Keep them on screen for the whole shot.
- Part 1 cuts between tabs are fine; use quick 150 ms crossfades or plain cuts, no spinning transitions.
- Part 2: the only edits are **idle-time trims**, each marked with a small **⏩ … trimmed** badge
  (top-right). No other cuts, no zoom tricks that hide text. A slow push-in on the priority table
  and the drill-down is fine.
- Optional: a thin progress strip at the top of Part 1 reading **REACH · READ · EXTRACT · TRUST · ACT**,
  lighting the stage you're on. It costs no words and helps the viewer follow.

**Sound**
- Any USB mic, or a phone's voice recorder 15 cm from your mouth, in a room with soft furnishings.
  Record a 5-second silence first for noise reduction.
- Normalise to about −16 LUFS. **No music under Part 2's narration**; very low music under the
  title cards only, if at all.
- Smile while you talk: it's audible, and it's what makes it sound *lively* instead of read.
- Say "ICE" as a word ("ice"). Say F-001 as "F-zero-zero-one". Say `apply_cascade` as "apply cascade".

**Voices (optional, but it lifts the energy)**
One narrator is fine. If all three of you want to be heard, split by act so each voice owns a
chapter: **Voice 1** cold open + Act I, **Voice 2** Acts II–III, **Voice 3** Act IV. For Part 2,
the voice should be **the person at the keyboard**, since it's their live run.

**Timing discipline**
- Part 1 and Part 2 are each capped on their own. Check each part's length in the editor's timeline
  before export, and the total (≤ 5:00).
- Export once, watch it once with `REPLAY_IT_Professionals.txt` open: harness 2.1.282, model Claude
  Opus 5.5, URL `https://docs.pytest.org/`. All three must match what the video shows.

---

## 4 · Where each brief requirement is met

| brief requirement (Round 4, §3) | where in the video |
|---|---|
| Part 1: how you discovered the findings (field research, what separates cited from ignored, distilled into repeatable checks) | Cold open + Act I (handout's reach/read/quote, crawler roles, GEO) and Act IV (five-site field test, zero-recall miss) |
| Part 1: how you assigned severities | Act I (critical vs info by crawler role, GEO → low) + Act II (severity vs confidence, cascade, Rule 0, golden) |
| Part 1: how you derived the suggested actions (mechanism-sound, prioritised) | Act III (`validate_finding`, patches never invented, ICE, total order) |
| Part 1: anchor every claim to code | every shot: tab + highlighted line + `file:line` caption; §5 ledger, machine-checked |
| Part 2: unseen URL, typed on camera, real and continuous | 0:18–0:28, one take, trims badged |
| Part 2: agent invokes the entrypoint skill, fetches, reasons, produces findings | 0:28–0:50 (`Skill(ai-readiness-orchestrator)`, two passes, the agent's pass-2 reasoning) |
| Part 2: drill into ≥ 1 finding: evidence, severity, fix | 1:10–1:48 (evidence check + drill-down card) |
| Part 2: fixes sorted / prioritised by impact | 1:00–1:10 (top-5 table, severity then ICE) |
| Part 2: state harness and model on camera | 0:02–0:18 (`claude --version`, `/model`, spoken) |
| Part 2: one line on wiring | 0:28–0:38 ("That's the wiring…") + `ENGINE UNCHANGED` at 0:02 |
| Everything shown comes from the submitted engine | `verify_engine.py` on camera; the prompt forbids the agent to add findings or edit files |

---

## 5 · Anchor ledger (machine-checked)

Every Part 1 claim, and the support for each Part 2 card, with the file and line it lives on in
the **unzipped submission** (`round3-frozen/submission.zip`, sha256 `1c872c59…8dcf`). The last
column is text that must appear on that exact line; `tools/check_script_anchors.py` checks every
row against the zip itself.

| id | claim as spoken | file:line | text on that line |
|---|---|---|---|
| A01 | the handout: reach, read, quote, or it won't make the answer | `skills/answerability-audit/references/chunking-model.md:42` | `about a brand is easy to reach, read, and quote` |
| A02 | three things succeed in order | `skills/ai-readiness-orchestrator/references/gate-rules.md:10` | `three things have to succeed in order` |
| A03 | 66 checks, each at a stage | `DESIGN.md:108` | `**66 checks** across six audit skills` |
| A04 | we asked what blocking each bot costs | `skills/crawl-access-audit/references/ai-bots.json:13` | `we need to know what blocking each one COSTS` |
| A05 | GPTBot is a training crawler | `skills/crawl-access-audit/references/ai-bots.json:71` | `"token": "GPTBot", "vendor": "OpenAI", "category": "training"` |
| A06 | blocking a retrieval bot removes you from its answers | `skills/crawl-access-audit/references/ai-bots.json:26` | `Blocking one of these removes the brand from that assistant's answers.` |
| A07 | blocking training bots doesn't affect citation | `skills/crawl-access-audit/references/ai-bots.json:31` | `Blocking has no effect on whether the brand is retrieved or cited at answer time.` |
| A08 | critical for a retrieval bot, line 286 | `skills/crawl-access-audit/scripts/check_robots.py:286` | `severity="critical", confidence="confirmed", stage="reach",` |
| A09 | info for a training bot, line 318 | `skills/crawl-access-audit/scripts/check_robots.py:318` | `severity="info", confidence="confirmed", stage="reach",` |
| A10 | GEO: citations and statistics help | `skills/answerability-audit/references/geo-methods.md:15` | `citing sources, adding statistics, and adding` |
| A11 | …so their absence scores low | `skills/answerability-audit/references/geo-methods.md:24` | `three markers, and it fires at **low** severity.` |
| A12 | how bad if true / how sure | `skills/ai-readiness-orchestrator/references/severity-model.md:43` | `Severity answers "how bad if true". Confidence answers "how sure".` |
| A13 | a clean report vs one that couldn't look | `skills/ai-readiness-orchestrator/references/severity-model.md:56` | `A clean report and a report that could not look are` |
| A14 | a flat checklist: fifteen criticals, fourteen moot | `skills/ai-readiness-orchestrator/references/gate-rules.md:18` | `fifteen criticals and no indication which one to fix first. Fourteen of them are` |
| A15 | apply_cascade | `skills/ai-readiness-orchestrator/scripts/gate_model.py:117` | `def apply_cascade(findings: list[dict], id_of)` |
| A16 | caps at medium | `skills/ai-readiness-orchestrator/scripts/gate_model.py:42` | `BLOCKED_SEVERITY_CEILING = "medium"` |
| A17 | capped, never deleted | `skills/ai-readiness-orchestrator/scripts/gate_model.py:120` | `Rule 3: cap, never delete.` |
| A18 | line 128: engagement is never gated | `skills/ai-readiness-orchestrator/scripts/gate_model.py:128` | `if finding.get("category") != "discoverability":` |
| A19 | (same) | `skills/ai-readiness-orchestrator/scripts/gate_model.py:129` | `# Rule 0: gates never touch engagement` |
| A20 | golden: eleven findings waiting on F-001 | `tests/golden/site_b.report.md:60` | `11 finding(s) are recorded but capped at medium because F-001` |
| A21 | golden JSON: blocked_by F-001 | `tests/golden/site_b.audit-report.json:109` | `"blocked_by": "F-001",` |
| A22 | validate_finding | `skills/ai-readiness-orchestrator/scripts/orchestrate.py:242` | `def validate_finding(finding: dict)` |
| A23 | …rejects a finding without a mechanism | `skills/ai-readiness-orchestrator/scripts/orchestrate.py:253` | `return "suggested_action has no mechanism"` |
| A24 | …and logs the rejection | `skills/ai-readiness-orchestrator/scripts/orchestrate.py:695` | `was rejected as malformed` |
| A25 | patches never invented | `skills/structured-data-audit/scripts/extract_markup.py:204` | `A JSON-LD block built from values observed on the page. Never invented.` |
| A26 | FILL_IN when a value is absent | `skills/structured-data-audit/scripts/check_hierarchy.py:211` | `__FILL_IN__:organisation_name` |
| A27 | ICE: confidence lookup | `skills/ai-readiness-orchestrator/scripts/severity.py:27` | `CONFIDENCE_TO_ICE = {"confirmed": 9.0, "likely": 6.0, "hypothesis": 3.0}` |
| A28 | ICE: impact lookup | `skills/ai-readiness-orchestrator/scripts/severity.py:28` | `SEVERITY_TO_IMPACT = {"critical": 10.0, "high": 8.0, "medium": 5.0` |
| A29 | ICE: ease lookup | `skills/ai-readiness-orchestrator/scripts/severity.py:29` | `EFFORT_TO_EASE = {"low": 9.0, "medium": 5.0, "high": 2.0}` |
| A30 | impact uses the capped severity | `skills/ai-readiness-orchestrator/scripts/severity.py:13` | `Impact derives from post-gate severity` |
| A31 | total sort order | `skills/ai-readiness-orchestrator/scripts/severity.py:68` | `def sort_key(finding: dict):` |
| A32 | same evidence, same ranking | `skills/ai-readiness-orchestrator/scripts/severity.py:71` | `the ordering is total and therefore deterministic` |
| A33 | five live sites, architectural variance | `DESIGN.md:370` | `sites chosen for **architectural variance**` |
| A34 | 365 findings, itself the finding | `DESIGN.md:374` | `That run produced **365 findings**, which was itself the finding.` |
| A35 | file sizes flagged as phone numbers | `DESIGN.md:377` | `file sizes being reported as inconsistent phone` |
| A36 | a free download page asked for a price | `DESIGN.md:378` | `a free open-source download page being asked for a price` |
| A37 | twelve false positives named before tuning | `DESIGN.md:375` | `positives were identified and named before any threshold was touched` |
| A38 | …got to 205 | `DESIGN.md:379` | `brought the same five sites to **205**` |
| A39 | detector fired zero times, sixteen words | `DESIGN.md:324` | `**zero times** — including on a documentation site serving **16 words of body` |
| A40 | tuned to our own fixture | `DESIGN.md:332` | `The check had been tuned to a synthetic Next.js fixture` |
| A41 | a fixture proves a check does what you wrote | `DESIGN.md:334` | `A fixture proves a check does what you wrote; it cannot prove you wrote` |
| A42 | rewritten detector (caption) | `skills/site-evidence-collector/scripts/dom.py:56` | `NOSCRIPT_JS_NOTICE = re.compile(` |
| A43 | regression tests R1–R12 (caption, bonus line) | `tests/test_regressions.py:2` | `Regression tests for every false positive found and fixed` |
| A44 | a citation that can't be checked | `skills/answerability-audit/references/geo-methods.md:56` | `A citation that cannot be checked is worse than no citation, because it looks` |
| A45 | bonus: Rule 0b, suppression asserts none | `skills/ai-readiness-orchestrator/references/gate-rules.md:56` | `Capping asserts a weaker claim. Suppression asserts` |
| A46 | Part 2: six audit skills | `skills/ai-readiness-orchestrator/SKILL.md:73` | `Invoke each of the six audit skills as a subprocess` |
| A47 | Card A: title | `skills/structured-data-audit/scripts/extract_markup.py:174` | `eligible page(s) carry no structured data at all` |
| A48 | Card A: high / confirmed | `skills/structured-data-audit/scripts/extract_markup.py:175` | `severity="high", confidence="confirmed", stage="extract",` |
| A49 | Card A: mechanism | `skills/structured-data-audit/scripts/extract_markup.py:189` | `Structured data states a fact in a typed form` |
| A50 | Card B: the patch, one Allow per bot | `skills/crawl-access-audit/scripts/check_robots.py:305` | `patch="".join(f"User-agent: {n}\nAllow: /\n\n" for n in names)` |
| A51 | Card C: title | `skills/crawl-access-audit/scripts/check_indexability.py:77` | `content page(s) tell crawlers not to index them` |
| A52 | Card C: mechanism | `skills/crawl-access-audit/scripts/check_indexability.py:90` | `noindex instructs the crawler to drop the page after reading it` |
| A53 | Card D: high / confirmed | `skills/render-gap-audit/scripts/diff_raw_rendered.py:164` | `severity="high", confidence="confirmed", stage="read",` |
| A54 | Card D: mechanism | `skills/render-gap-audit/scripts/diff_raw_rendered.py:179` | `Retrieval crawlers fetch and parse the HTML response` |
| A55 | Card E: title | `skills/trust-freshness-audit/scripts/date_consistency.py:143` | `page(s) of dated content carry no date at all` |
| A56 | Card E: mechanism | `skills/trust-freshness-audit/scripts/date_consistency.py:158` | `Freshness is weighed when choosing between sources saying different things` |
| A57 | Card E: dates left as FILL_IN | `skills/trust-freshness-audit/scripts/date_consistency.py:168` | `"datePublished": "__FILL_IN__:YYYY-MM-DD"` |

The checker also recomputes three numbers the script speaks: **29** crawlers in `ai-bots.json`
(14 retrieval, 10 training, 5 contested), **155** files in the zip, and **11** findings with
`blocked_by: F-001` in the `site_b` golden.

---

## 6 · Claims we deliberately do not make

| tempting line | why it stays out |
|---|---|
| "13 findings are moot until F-001" | `gate-rules.md` and `DESIGN.md` say 13, but the checked-in golden has **11** (`summary.blocked_findings`). A judge opens the golden, so we say 11. |
| "Our engine produced fifteen criticals" | The fifteen-criticals line is the docs' illustration of a *flat checklist* (`gate-rules.md:16–19`). We say it about a flat checklist, never about our output. |
| "up to 40% more visibility" (GEO) | `geo-methods.md:31–39` refuses to extrapolate the benchmark figure. So do we. |
| "R1–R12 are the twelve live-site false positives" | `test_regressions.py:4` says they were found by the healthy control fixture. We only say they keep fixed bugs fixed. |
| "Browser on vs off: 24 true, 24 false…" | That study is in this repo (`SITE_MATRIX.md`), not in the submitted code. In Part 2 we only say what the agent does, and the numbers stay in the REPLAY commentary. |
| "No false positives" / "every check is precise" | Not true, and the frozen engine has known misfires (`NOTES.md`, REPLAY "KNOWN LIMITS"). The evidence check exists to catch them on camera. |
| Any number about docs.pytest.org before the take | The site is unseen. Every bracket in Part 2 is read off the screen. |
| "Links only exist after JavaScript" as a showcase | `read.render.nav_links_js_only` over-counts off-site links (`NOTES.md` §8). Never drill into it unless the agent's same-host count backs it up. |

---

## 7 · Final checklist

- [ ] `python tools/check_script_anchors.py` → `0 problem(s)`
- [ ] `python tools/check_replay.py` → `0 problem(s)` (harness still 2.1.282)
- [ ] The 2026-09-26 step-2 prompt rehearsed once on a seen site (run sheet §A 1b), transcript in `rehearsal/`: table of confirmed findings, a verdict on every row
- [ ] Part 1 timed read-through ≤ 2:50 (cut ladder applied if not)
- [ ] VS Code shows the **unzipped submission**, tabs 1–12 in order, captions prepared in the editor
- [ ] Run sheet §A done: fresh `demo-live/`, `ENGINE UNCHANGED`, prompt on the clipboard **without** the URL
- [ ] docs.pytest.org **not** audited by anyone before the take
- [ ] Part 2 recorded in **one** take; raw file kept, with its hash noted (run sheet §F)
- [ ] Edited Part 1 ≤ 3:00, Part 2 ≤ 2:00, total ≤ 5:00
- [ ] Final watch with the REPLAY open: harness, model and URL match the video
