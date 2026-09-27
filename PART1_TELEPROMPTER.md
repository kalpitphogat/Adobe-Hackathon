# Part 1 - teleprompter

Only the DO and the SAY, one step per block, separated by rules. Generated from Stage 2 of
`RECORDING_FLOW.md` on branch `final-3` - that file stays the source of truth, and the spoken
wording here is identical to it.

- **Bold** = lean on the word. `·` = a half-beat pause.
- 10 tabs plus the llms.txt file, thirteen spoken beats, 392 words, about 2:56 at 140 words a minute (cap 3:00).
- Say nothing while you press keys: every split falls on a pause or between two sentences.
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

**SAY** — "Ask an AI assistant about a brand, and it either **quotes** the site or acts as if it **doesn't exist**. The handout says why: a page that isn't easy to **reach, read and quote** never reaches the answer. Our agent finds **which step fails**."

> *Slow down on "doesn't exist", and smile on the last sentence.*

---

## 0:21–0:56 · Act I · What separates the cited from the ignored

*Tab 2 `gate-rules.md` · CAPTION `gate-rules.md:10 · 66 checks: DESIGN.md:108 (count generated from the code)`*

### Step 2

**DO** — `Ctrl+PgDn` → tab 2, on line 10. Click **10**, Shift+click **14**.

**SAY** — "Those steps happen **in order**, so each of our 66 checks belongs to a stage: reach, read, extract, trust · and act, the visitor who arrives."

---

*Tab 3 `ai-bots.json` · CAPTION `ai-bots.json:12–14 · 29 crawlers: 14 retrieval, 10 training, 5 contested`*

### Step 3a

**DO** — `Ctrl+PgDn` → tab 3, on line 12. Click **12**, Shift+click **14**.

**SAY** — "Lists tell you which AI crawlers to **block**; we asked what blocking each one **costs**, and sorted 29 by role."

---

### Step 3b

**DO** — `Ctrl+G` → type `71` → `Enter`. Click **71**: `"GPTBot"` … `"category": "training"`.

**SAY** — "Block GPTBot and you have opted out of **training**."

---

### Step 3c

**DO** — `Ctrl+G` → type `26` → `Enter`. Click **26**: "Blocking one of these removes the brand from that assistant's answers."

**SAY** — "Block a retrieval crawler and you **vanish from that assistant's answers**."

---

*Tab 4 `check_robots.py` · CAPTION `check_robots.py:286 critical · :318 info`*

> *cut-ladder step 1 skips 4a–4b*

### Step 4a

**DO** — `Ctrl+PgDn` → tab 4, on line 286. Click **286**: `severity="critical"`.

**SAY** — "So one robots.txt rule is **critical** against a retrieval crawler,"

---

### Step 4b

**DO** — `Ctrl+G` → type `318` → `Enter`. Click **318**: `severity="info"`.

**SAY** — "**info** against a training one."

---

*`suppression-rules.md`, opened with `Ctrl+P` · CAPTION `suppression-rules.md:22–27 · enforced: check_agent_files.py:24 docs sites only, :62 severity="low" · tests/test_suppression.py`*

### Step 4c

**DO** — `Ctrl+P` → type `suppression-rules.md:22` → `Enter`. Click **22**, Shift+click **27**. It opens as a new tab just right of tab 4, so the next `Ctrl+PgDn` still reaches tab 5.

**SAY** — "Hype inflates severity: Google says llms.txt neither helps nor harms, and nearly **300,000 domains** showed no link to citations. Ours: **low**."

---

## 0:56–1:33 · Act II · How bad, how sure

*Tab 5 `severity-model.md` · CAPTION `severity-model.md:43`*

### Step 5

**DO** — `Ctrl+PgDn` → tab 5, on line 43. Click **43**.

**SAY** — "Severity asks **how bad this is if true**; confidence asks **how sure we are**."

---

*Tab 6 `gate_model.py` · CAPTION `gate_model.py:117 apply_cascade · :42 ceiling "medium" · :120 cap, never delete · :129 Rule 0`*

### Step 6a

**DO** — `Ctrl+PgDn` → tab 6, on line 117. Click **117**, Shift+click **118**.

**SAY** — "A flat checklist hands a site that blocks AI crawlers **fifteen criticals**, and fourteen are moot."

---

### Step 6b

**DO** — Click **120**, two lines down: `Rule 3: cap, never delete.`

**SAY** — "`apply_cascade` caps those at medium and tags the **one** blocker that matters: **capped, never deleted**."

---

### Step 6c

**DO** — `Ctrl+G` → type `128` → `Enter`. Click **128**, Shift+click **129**.

**SAY** — "Engagement is never gated: a visitor from an ad doesn't care whether a crawler got in."

---

*Rule 0b, back in `gate-rules.md` (tab 2) · CAPTION `gate-rules.md:54–57 · Rule 0b`*

### Step 6d

**DO** — `Ctrl+P` → type `gate-rules.md:54` → `Enter`. This is tab 2 again, no new tab. Click **54**, Shift+click **55**.

**SAY** — "And when we never even saw the page a visitor sees, those findings aren't capped, they're **suppressed**."

---

> *Capping says "real, but moot"; suppression says "we never looked". You are now on tab 2, so step 7 uses `Ctrl+P`, not `Ctrl+PgDn`.*

---

## 1:33–1:59 · Act III · Every fix earns its place

*Tab 7 `orchestrate.py` · CAPTION `orchestrate.py:242 validate_finding · rejection logged at :695`*

### Step 7

**DO** — `Ctrl+P` → type `orchestrate.py:242` → `Enter` (**not** `Ctrl+PgDn`: 6d left you on tab 2). Click **242**, Shift+click **253**.

**SAY** — "Every fix must say **why** it works, so `validate_finding` rejects any finding without a mechanism."

---

*Tab 8 `extract_markup.py` · CAPTION `extract_markup.py:204 · "__FILL_IN__" when a value is absent (94 places in the engine)`*

### Step 8a

**DO** — `Ctrl+PgDn` → tab 8, on line 203. Click **203**, Shift+click **204**: `Never invented.`

**SAY** — "Our patches reuse values from the page and **never invent one**;"

---

### Step 8b

**DO** — Click **209**, Shift+click **210**, five lines down: `__FILL_IN__`.

**SAY** — "whatever we couldn't find stays **FILL_IN**."

---

*Tab 9 `severity.py` · CAPTION `severity.py:27–29 lookups · :13 impact from post-gate severity · :68 total order`*

### Step 9a

**DO** — `Ctrl+PgDn` → tab 9, on line 26. Click **26**, Shift+click **29**.

**SAY** — "Priority is **ICE**: impact, confidence, ease."

---

### Step 9b

**DO** — `Ctrl+G` → type `13` → `Enter`. Click **13**, Shift+click **15**.

**SAY** — "Impact uses the **capped** severity, so a moot defect cannot outrank its blocker."

---

## 1:59–2:39 · Act IV · The day the real web proved us wrong

*Tab 10 `DESIGN.md`, the field test · CAPTION `DESIGN.md:374–379 · field test on five live sites`, then `DESIGN.md:377–378`*

### Step 10a

**DO** — `Ctrl+PgDn` → tab 10, on line 369. Click **369**, Shift+click **374**.

**SAY** — "Then the real web **humbled** us. Five live sites produced **365 findings**, and that number was itself the finding."

---

### Step 10b

**DO** — Click **374**, Shift+click **379**: twelve false positives … **205**.

**SAY** — "We named twelve false positives before touching a threshold, and came down to **205**."

---

### Step 10c

**DO** — Click **377**, Shift+click **378**, already on screen: file sizes as phone numbers, a free download page asked for a price.

**SAY** — "Two of them: we were reading file sizes as **phone numbers**, and telling a free download page to publish a **price**."

> *cut-ladder step 2 drops this row*

> *Let 10c breathe. It is the one laugh in Part 1, and it turns "twelve false positives" into something a judge can picture.*

---

*Tab 10 `DESIGN.md`, the zero-recall story · CAPTION `DESIGN.md:324, :334 · rewritten: dom.py:56 NOSCRIPT_JS_NOTICE · pinned: tests/test_regressions.py R1–R12`*

### Step 10d

**DO** — `Ctrl+G` → type `322` → `Enter`. Click **322**, Shift+click **325**: "fired **zero times** … **16 words**".

**SAY** — "Worse, our empty-page detector fired **zero times**, even on a docs site of **sixteen words**, because we'd tuned it to our own fixture."

---

### Step 10e

**DO** — `Ctrl+G` → type `332` → `Enter`. Click **332**, Shift+click **335**: "A fixture proves a check does what you wrote".

**SAY** — "A fixture proves a check does what you wrote · **not that you wrote the right thing**."

> *Don't rush 10d–10e. The admission is what earns the closing line.*

---

## 2:39–2:50 · Close

*`geo-methods.md`, opened fresh · CAPTION `geo-methods.md:56`*

### Step 11

**DO** — `Ctrl+P` → type `geo-methods.md:56` → `Enter`. Click **56**, Shift+click **57**.

**SAY** — "Our own code puts it best: a citation you can't check is worse than none, **because it looks like evidence**. So don't trust us. · **Watch.**"

> *Hard cut to Part 2 on "Watch."*

---
