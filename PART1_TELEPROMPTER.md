# Part 1 - teleprompter

Only the DO and the SAY, one step per block, separated by rules. Generated from Stage 2 of
`RECORDING_FLOW.md` on branch `final-3` - that file stays the source of truth, and the spoken
wording here is identical to it.

- **Bold** = lean on the word. `·` = a half-beat pause.
- 10 tabs plus two files opened with `Ctrl+P`, 429 words, about 2:59 at 150 words a minute (cap 3:00). Every SAY is one or more complete sentences. Steps marked **BONUS** (B1–B7) are optional extras: skip them, and their keys, for the 3:00 take.
- Say nothing while you press keys: every step ends on a full stop, so keys go between steps.
- A `>` note under a step is direction, not speech.

---

## 0:00–0:02 · Title card

**DO** — Black card, 2 s: **INVISIBLE TO THE MACHINE** · *Brand AI-Readiness Audit* · IT_Professionals · Round 4

**SAY** — *(silent)*

---

## 0:02–0:21 · Cold open

*Tab 1 `chunking-model.md` · CAPTION `chunking-model.md:40–43 · the handout, quoted in our code`*

### Step 1

**DO** — Tab 1 is on screen, on line 40. Click **40**, Shift+click **43**.

**SAY** — "Ask an AI assistant about a brand, and it either **quotes** the site or acts as if it **doesn't exist**. The handout says why: a page that isn't easy to **reach, read and quote** never makes it into the answer. Our agent finds **which step fails**."

> *Slow down on "doesn't exist", and smile on the last sentence.*

---

## 0:21–1:17 · Act I · What separates the cited from the ignored

*Tab 2 `gate-rules.md` · CAPTION `gate-rules.md:10–19 · 66 checks by stage: DESIGN.md:108–111 (reach 18, read 5, extract 16, trust 10, act 17)`*

### Step 2a

**DO** — `Ctrl+PgDn` → tab 2, on line 10. Click **10**, Shift+click **14**: "three things have to succeed in order".

**SAY** — "Those steps have to succeed **in order**, so we group our **66 checks** into stages in the same order."

---

### Step 2b

**DO** — Click **16**, Shift+click **19**, a few lines down: "fifteen criticals … Fourteen of them are real defects that currently change nothing."

**SAY** — "A flat checklist ignores that order: a site blocking AI crawlers gets **fifteen critical** findings, and **fourteen** don't matter yet."

---

*Tab 3 `ai-bots.json` · CAPTION `ai-bots.json:12–14 · 29 crawlers: 14 retrieval, 10 training, 5 contested`*

### BONUS B1

**DO** — `Ctrl+PgDn` → tab 3, on line 12. Click **12**, Shift+click **14**.

**SAY** — **BONUS** "Reach is the first stage, and it taught us our first rule."

---

### Step 3a

**DO** — Same screen as B1. If you skipped B1: `Ctrl+PgDn` → tab 3, on line 12. Click **12**, Shift+click **14**.

**SAY** — "Most lists tell you which AI crawlers to **block**. We asked what blocking each one **costs**, and sorted 29 by role."

---

### Step 3b

**DO** — `Ctrl+G` → type `71` → `Enter`. Click **71**, Shift+click **72**: `"GPTBot"` … `"category": "training"`, then "Blocking it does not remove a site from ChatGPT search results".

**SAY** — "Block GPTBot, and you have only opted out of **training**."

---

### Step 3c

**DO** — `Ctrl+G` → type `26` → `Enter`. Click **26**: "Blocking one of these removes the brand from that assistant's answers."

**SAY** — "Block a **retrieval** crawler, and you **vanish from that assistant's answers**."

---

*Tab 4 `check_robots.py` · CAPTION `check_robots.py:285–286 critical · :317–318 info`*

> *cut-ladder step 1 skips 4a–4b*

### Step 4a

**DO** — `Ctrl+PgDn` → tab 4, on line 286. Click **285**, Shift+click **286**: "AI retrieval crawler(s) that cite sources at answer time", `severity="critical"`.

**SAY** — "So one robots.txt rule is **critical** against a retrieval crawler."

---

### Step 4b

**DO** — `Ctrl+G` → type `317` → `Enter`. Click **317**, Shift+click **318**: "recorded as an observation, not a defect", `severity="info"`.

**SAY** — "Against a training crawler, the same rule is only **info**."

---

*`suppression-rules.md`, opened with `Ctrl+P` · CAPTION `suppression-rules.md:22–27 · enforced: check_agent_files.py:24 docs sites only, :62 severity="low" · tests/test_suppression.py`*

### Step 4c

**DO** — `Ctrl+P` → type `suppression-rules.md:22` → `Enter`. Click **22**, Shift+click **27**. It opens as a new tab just right of tab 4, so the next `Ctrl+PgDn` still reaches tab 5.

**SAY** — "Hype doesn't set our severity. Google says llms.txt neither helps nor harms visibility, and a study of nearly **300,000 domains** found no link to AI citations. Most tools rate a missing llms.txt **high**; we rate it **low**."

---

*BONUS: `geo-methods.md`, opened with `Ctrl+P` · CAPTION `geo-methods.md:5–7 GEO, KDD 2024 · :14–16 the three rewrites · :23–27 fires at low: a benchmark gain, not a defect`*

### BONUS B2a

**DO** — `Ctrl+P` → type `geo-methods.md:14` → `Enter`. Click **14**, Shift+click **16** (the paper's name and KDD 2024 are on lines 5–7, just above). It opens next to the llms.txt tab, so the next `Ctrl+PgDn` still reaches tab 5.

**SAY** — **BONUS** "We calibrate against research, not instinct. The GEO paper, from KDD 2024, found that citing sources, adding statistics and adding quotations made a page more prominent in AI answers."

---

### BONUS B2b

**DO** — `Ctrl+G` → type `23` → `Enter`. Click **23**, Shift+click **27**: "fires at **low** severity" … "in a benchmark".

**SAY** — **BONUS** "That gain was measured in a benchmark, not on any real brand, so a page with none of the three gets only a **low** finding."

---

## 1:17–1:47 · Act II · How bad, how sure

*Tab 5 `severity-model.md` · CAPTION `severity-model.md:43`*

### Step 5

**DO** — `Ctrl+PgDn` → tab 5, on line 43. Click **43**.

**SAY** — "Each finding has two ratings: **severity**, how bad if true, and **confidence**, how sure we are."

---

### BONUS B3

**DO** — `Ctrl+G` → type `56` → `Enter`. Click **56**, Shift+click **57**: "A clean report and a report that could not look are different things".

**SAY** — **BONUS** "A check that cannot run says so, because a clean report and a report that **couldn't look** are different things."

---

*Tab 6 `gate_model.py` · CAPTION `gate_model.py:117–122 apply_cascade · :42 ceiling "medium" · :120 cap, never delete · :129 Rule 0, why: gate-rules.md:31–32`*

### Step 6a

**DO** — `Ctrl+PgDn` → tab 6, on line 117. Click **117**, Shift+click **122**: `apply_cascade` … `Rule 3: cap, never delete.` … "The finding stays in the report".

**SAY** — "Our `apply_cascade` function fixes the flat checklist: it caps findings behind the **one** blocker at **medium**, and never deletes them."

---

### Step 6b

**DO** — `Ctrl+G` → type `128` → `Enter`. Click **128**, Shift+click **129**: `# Rule 0: gates never touch engagement`.

**SAY** — "Engagement is **never** capped: a visitor from an ad doesn't care whether a crawler got in."

---

*Rule 0b, back in `gate-rules.md` (tab 2) · CAPTION `gate-rules.md:54–57 · Rule 0b`*

### Step 6c

**DO** — `Ctrl+P` → type `gate-rules.md:54` → `Enter`. This is tab 2 again, no new tab. Click **54**, Shift+click **57**: "`read` failures suppress engagement findings because the evidence is absent."

**SAY** — "But if we never saw the page a visitor sees, we **suppress** its engagement findings, because we have no evidence."

---

### BONUS B4

**DO** — No key press: lines **56–57** are already highlighted: "Capping asserts a weaker claim. Suppression asserts none."

**SAY** — **BONUS** "A cap still makes a weaker claim; a suppression makes **no claim** at all."

---

*BONUS: `site_b.report.md`, opened with `Ctrl+P` · CAPTION `tests/golden/site_b.report.md:58–60 · site_b.audit-report.json: 1 critical, 11 blocked_by F-001, 8 engagement findings, none capped`*

### BONUS B5

**DO** — `Ctrl+P` → type `site_b.report.md:58` → `Enter`. Click **58**, Shift+click **60**: "11 finding(s) are recorded but capped at medium because F-001".

**SAY** — **BONUS** "Our golden test report shows the cascade: **one** critical blocker, **eleven** findings capped behind it, and all **eight** engagement findings left untouched."

> *Capping says "real, but moot"; suppression says "we never looked". You are now on tab 2 (or on `site_b.report.md` after B5), so step 7 uses `Ctrl+P`, not `Ctrl+PgDn`.*

---

## 1:47–2:10 · Act III · Every fix earns its place

*Tab 7 `orchestrate.py` · CAPTION `orchestrate.py:242 validate_finding · rejection logged at :695`*

### Step 7

**DO** — `Ctrl+P` → type `orchestrate.py:242` → `Enter` (**not** `Ctrl+PgDn`: 6c left you on tab 2). Click **242**, Shift+click **253**.

**SAY** — "Every fix must say **why** it works, so `validate_finding` rejects any finding without a mechanism."

---

### BONUS B6

**DO** — No key press: the caption already cites `orchestrate.py:695`, where the rejection is logged.

**SAY** — **BONUS** "It also logs every rejection, so no finding is dropped silently."

---

*Tab 8 `extract_markup.py` · CAPTION `extract_markup.py:204 · "__FILL_IN__" when a value is absent (94 places in the engine)`*

### Step 8a

**DO** — `Ctrl+PgDn` → tab 8, on line 203. Click **203**, Shift+click **204**: `Never invented.`

**SAY** — "Our patches reuse values from the page; we **never invent** one."

---

### Step 8b

**DO** — Click **209**, Shift+click **210**, five lines down: `__FILL_IN__`.

**SAY** — "Whatever we couldn't find is left as **FILL_IN**."

---

*Tab 9 `severity.py` · CAPTION `severity.py:27–29 lookups · :13 impact from post-gate severity · :68 total order`*

### Step 9a

**DO** — `Ctrl+PgDn` → tab 9, on line 26. Click **26**, Shift+click **29**.

**SAY** — "We rank fixes by **ICE**: impact, confidence and ease."

---

### Step 9b

**DO** — `Ctrl+G` → type `13` → `Enter`. Click **13**, Shift+click **15**.

**SAY** — "Impact uses the **capped** severity, so a blocked finding never outranks its blocker."

---

### BONUS B7

**DO** — `Ctrl+G` → type `68` → `Enter`. Click **68**, Shift+click **71**: `def sort_key` … "the ordering is total and therefore deterministic".

**SAY** — **BONUS** "The order is total, so the same evidence always ranks the **same way**."

---

## 2:10–2:48 · Act IV · The day the real web proved us wrong

*Tab 10 `DESIGN.md`, the field test · CAPTION `DESIGN.md:374–379 · field test on five live sites`, then `DESIGN.md:377–378`*

### Step 10a

**DO** — `Ctrl+PgDn` → tab 10, on line 369. Click **369**, Shift+click **374**.

**SAY** — "Then the real web **humbled** us. Five live sites produced **365 findings**, and that number was itself the finding."

---

### Step 10b

**DO** — Click **374**, Shift+click **379**: twelve false positives … **205**.

**SAY** — "We named **twelve false positives** before touching any threshold, and fixing them cut the count to **205**."

---

### Step 10c

**DO** — Click **377**, Shift+click **378**, already on screen: file sizes as phone numbers, a free download page asked for a price.

**SAY** — "Two were embarrassing: we read file sizes as **phone numbers**, and asked a free download page for a **price**."

> *cut-ladder step 2 drops this row*

> *Let 10c breathe. It is the one laugh in Part 1, and it turns "twelve false positives" into something a judge can picture.*

---

*Tab 10 `DESIGN.md`, the zero-recall story · CAPTION `DESIGN.md:324, :332–334 · rewritten: dom.py:56 NOSCRIPT_JS_NOTICE · pinned: tests/test_regressions.py R1–R12`*

### Step 10d

**DO** — `Ctrl+G` → type `322` → `Enter`. Click **322**, Shift+click **325**: "fired **zero times** … **16 words**".

**SAY** — "Worse, our empty-page detector fired **zero times**, even on a **sixteen-word** docs site."

---

### Step 10e

**DO** — `Ctrl+G` → type `332` → `Enter`. Click **332**, Shift+click **335**: "tuned to a synthetic Next.js fixture" … "A fixture proves a check does what you wrote".

**SAY** — "We'd tuned it to our own fixture, and a fixture proves a check does what you wrote · **not that you wrote the right thing**."

> *Don't rush 10d–10e. The admission is what earns the closing line.*

---

## 2:48–3:00 · Close

*`geo-methods.md`, opened fresh · CAPTION `geo-methods.md:56`*

### Step 11

**DO** — `Ctrl+P` → type `geo-methods.md:56` → `Enter`. Click **56**, Shift+click **57**.

**SAY** — "Our own code puts it best: a citation you can't check is worse than none, **because it looks like evidence**. So don't trust us. · **Watch.**"

> *Hard cut to Part 2 on "Watch."*

---
