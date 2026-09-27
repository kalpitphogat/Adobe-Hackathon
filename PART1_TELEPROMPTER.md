# Part 1 - teleprompter

Only the DO and the SAY, one step per block, separated by rules. Generated from Stage 2 of
`RECORDING_FLOW.md` on branch `final-3` - that file stays the source of truth, and the spoken
wording here is identical to it.

- **Bold** = lean on the word. `·` = a half-beat pause.
- 10 tabs, 12 spoken beats, 386 words, about 2:53 at 140 words a minute (cap 3:00).
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

**SAY** — "Ask an AI assistant about a brand, and it either **quotes** the site or acts as if it **doesn't exist**. The handout explains why: unless a page is easy to **reach, read and quote**, it never reaches the answer. Our agent finds **which step fails**."

---

## 0:21–1:00 · Act I · What separates the cited from the ignored

*Tab 2 `gate-rules.md` · CAPTION `gate-rules.md:10 · 66 checks: DESIGN.md:108 (count generated from the code)`*

### Step 2

**DO** — `Ctrl+PgDn` → tab 2, on line 10. Click **10**, Shift+click **14**.

**SAY** — "Those steps happen **in order**, so each of our 66 checks belongs to a stage: reach, read, extract, trust · and act, which is the visitor who arrives."

---

*Tab 3 `ai-bots.json` · CAPTION `ai-bots.json:12–14 · 29 crawlers: 14 retrieval, 10 training, 5 contested`*

### Step 3a

**DO** — `Ctrl+PgDn` → tab 3, on line 12. Click **12**, Shift+click **14**.

**SAY** — "Reach taught us our first rule. Lists tell you which AI crawlers to **block**; we asked what blocking each one **costs**, and sorted 29 by role."

---

### Step 3b

**DO** — `Ctrl+G` → type `71` → `Enter`. Click **71**: `"GPTBot"` … `"category": "training"`.

**SAY** — "Block GPTBot and you have opted out of **training**."

---

### Step 3c

**DO** — `Ctrl+G` → type `26` → `Enter`. Click **26**: "Blocking one of these removes the brand from that assistant's answers."

**SAY** — "Block a retrieval crawler and you **vanish from that assistant's answers**."

---

*Tab 4 `check_robots.py` · CAPTION `check_robots.py:286 critical · :318 info` · *cut-ladder step 1 skips 4a–4b**

### Step 4a

**DO** — `Ctrl+PgDn` → tab 4, on line 286. Click **286**: `severity="critical"`.

**SAY** — "So one robots.txt rule is **critical** against a retrieval crawler,"

---

### Step 4b

**DO** — `Ctrl+G` → type `318` → `Enter`. Click **318**: `severity="info"`.

**SAY** — "and merely **informational** against a training one."

---

## 1:00–1:35 · Act II · How bad, how sure

*Tab 5 `severity-model.md` · CAPTION `severity-model.md:43 · :56`*

### Step 5a

**DO** — `Ctrl+PgDn` → tab 5, on line 43. Click **43**.

**SAY** — "Severity asks **how bad this is if true**; confidence is separate, asking **how sure we are**."

---

### Step 5b

**DO** — `Ctrl+G` → type `56` → `Enter`. Click **56**, Shift+click **57**.

**SAY** — "A check that cannot run says so, because a clean report and one that **couldn't look** are different things."

> cut-ladder step 2 drops this row

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

**SAY** — "Engagement is never gated, because a visitor from an ad doesn't care whether a crawler got in."

---

## 1:35–2:05 · Act III · Every fix earns its place

*Tab 7 `orchestrate.py` · CAPTION `orchestrate.py:242 validate_finding · rejection logged at :695`*

### Step 7

**DO** — `Ctrl+PgDn` → tab 7, on line 242. Click **242**, Shift+click **253**.

**SAY** — "Every fix must say **why** it works, so `validate_finding` rejects any finding without a mechanism and logs the rejection."

---

*Tab 8 `extract_markup.py` · CAPTION `extract_markup.py:204 · "__FILL_IN__" when a value is absent (94 places in the engine)`*

### Step 8a

**DO** — `Ctrl+PgDn` → tab 8, on line 203. Click **203**, Shift+click **204**: `Never invented.`

**SAY** — "Our patches reuse values we saw on the page and **never invent one**;"

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

**SAY** — "Impact uses the **capped** severity, so a moot defect cannot outrank its blocker,"

---

### Step 9c

**DO** — `Ctrl+G` → type `68` → `Enter`. Click **68**, Shift+click **71**.

**SAY** — "and the order is total: **the same evidence always ranks the same way**."

> cut-ladder step 3 drops this row; end 9b on "blocker."

---

## 2:05–2:37 · Act IV · The day the real web proved us wrong

*Tab 10 `DESIGN.md`, the field test · CAPTION `DESIGN.md:374–379 · field test on five live sites`*

### Step 10a

**DO** — `Ctrl+PgDn` → tab 10, on line 369. Click **369**, Shift+click **374**.

**SAY** — "Then the real web **humbled** us. Five live sites produced **365 findings**, and that number was itself the finding."

---

### Step 10b

**DO** — Click **374**, Shift+click **379**: twelve false positives … **205**.

**SAY** — "We named twelve false positives before touching a threshold, and came down to **205**."

---

*Tab 10 `DESIGN.md`, the zero-recall story · CAPTION `DESIGN.md:324, :334 · rewritten: dom.py:56 NOSCRIPT_JS_NOTICE · pinned: tests/test_regressions.py R1–R12`*

### Step 10c

**DO** — `Ctrl+G` → type `322` → `Enter`. Click **322**, Shift+click **325**: "fired **zero times** … **16 words**".

**SAY** — "Worse, our empty-page detector fired **zero times**, even on a docs site of **sixteen words**, because we had tuned it to our own fixture."

---

### Step 10d

**DO** — `Ctrl+G` → type `332` → `Enter`. Click **332**, Shift+click **335**: "A fixture proves a check does what you wrote".

**SAY** — "A fixture proves a check does what you wrote · **not that you wrote the right thing**."

---

## 2:37–2:47 · Close

*`geo-methods.md`, opened fresh · CAPTION `geo-methods.md:56`*

### Step 11

**DO** — `Ctrl+P` → type `geo-methods.md:56` → `Enter`. Click **56**, Shift+click **57**.

**SAY** — "Our own code puts it best: a citation you can't check is worse than none, **because it looks like evidence**. So don't trust us. · **Watch.**"

---
