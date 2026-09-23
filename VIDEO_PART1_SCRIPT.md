# Video Part 1: Thought process (hard cap 3:00)

**Rubric line this part is scored on (35 points):** *"Signal discovery, severity logic, and fix
derivation are sound, non-obvious, and traceable to the submitted code."* And the rule that
bites: *"Narration that cannot be traced to the submitted code earns no credit."*

So **every sentence below has the file you show while you say it**. All paths are relative to
the marketplace root: the unzipped `round3-frozen/submission.zip`, i.e. `demo/`. Every line
number was checked against that exact copy (2026-09-23; new anchors 2026-09-24). If you cut a sentence, cut its anchor too.

**Pace:** 380 spoken words: about 2:43 at ~140 words per minute, leaving ~15 s for switching tabs.
Rehearse against a timer. Beat 4 is the one to cut if you run long.

**Screen setup before recording:** VS Code with `demo/` open, font size 18+, these tabs pre-opened
in this order, each already scrolled to its line:

| # | tab | scroll to |
|---|---|---|
| 1 | `skills/ai-readiness-orchestrator/references/gate-rules.md` | line 10 (the quoted handout text) |
| 2a | `skills/crawl-access-audit/references/ai-bots.json` | line 71 (GPTBot, `"category": "training"`) |
| 2b | `skills/crawl-access-audit/scripts/check_robots.py` | line 286 (`severity="critical"`); line 318 is `severity="info"` |
| 3 | `skills/answerability-audit/references/geo-methods.md` | line 23 |
| 4 | `skills/answerability-audit/references/chunking-model.md` | line 5 |
| 5 | `skills/ai-readiness-orchestrator/references/severity-model.md` | line 5 |
| 6 | `skills/ai-readiness-orchestrator/scripts/gate_model.py` | line 117 |
| 7 | `tests/golden/site_b.audit-report.json` | line 109 |
| 8 | `skills/ai-readiness-orchestrator/scripts/orchestrate.py` | line 242 |
| 9 | `skills/ai-readiness-orchestrator/scripts/severity.py` | line 26 |
| 10a | `DESIGN.md` | line 320 ("The shell detector had zero recall on real sites") |
| 10b | `skills/site-evidence-collector/scripts/dom.py` | line 53 (`NOSCRIPT_JS_NOTICE`) |
| 10c | `tests/test_regressions.py` | line 2 (docstring); then scroll past the `# R1.` … `# R12.` headers (lines 50–504) |

Tip: highlight the line you are talking about (click the line number) so the viewer's eye lands on it.

---

## Beat 1 · How we discovered the signals (0:00 – 1:05)

**[Tab 1: gate-rules.md, lines 10–14]**
> "We're IT_Professionals. Our audit rests on one sentence from the brief: three things must
> succeed *in order*. The crawler is let in, the page is read, the fact is picked out. So
> every check has a stage: reach, read, extract, trust, and act for the human visitor."

**[Tab 2a: ai-bots.json, line 71 → Tab 2b: check_robots.py, lines 286 and 318]**
> "Field research changed what we flag. We classified 29 AI crawlers by role. GPTBot collects
> training data; blocking it doesn't remove you from ChatGPT search. So a blocked retrieval bot
> is critical, line 286, and a blocked training bot is only info, line 318."

**[Tab 3: geo-methods.md, line 23 then line 41]**
> "Where the research is weaker, severity stays low: the GEO paper measured a benchmark gain,
> not a defect. And every number in a finding must trace to a source we actually read."

**[Tab 4: chunking-model.md, line 5]**
> "Some rules say what we must *not* recommend. Google says don't chop content up for AI, so
> no fix here ever tells you to split your page."

*(150 words)*

---

## Beat 2 · How we assign severity (1:05 – 1:55)

**[Tab 5: severity-model.md, lines 5–11]**
> "Severity answers *how bad if true*. Critical means the system can't see the page at all.
> Confidence is a separate field, *how sure are we*. Confirmed means a deterministic check
> observed it."

**[Tab 6: gate_model.py, line 117 `apply_cascade`, then line 128 and line 137]**
> "Then the ordering does the work. When an upstream stage fails, downstream findings are real
> but moot, so `apply_cascade` caps them at medium and tags the one finding blocking them.
> Line 128: engagement is never gated, because a visitor from an ad doesn't care whether a
> crawler got in."

**[Tab 7: tests/golden/site_b.audit-report.json, line 109]**
> "Here's that in our checked-in output. A site blocking AI retrieval crawlers gets one critical,
> eleven findings capped and pointing at F-001, and the engagement findings left untouched."

*(110 words)*

---

## Beat 3 · How we derive and prioritise fixes (1:55 – 2:30)

**[Tab 8: orchestrate.py, lines 242–253]**
> "Every fix must carry a mechanism, *why* it works. `validate_finding` rejects any finding
> without one and records the rejection in limitations. Where a patch needs a value the site
> doesn't give us, it says `__FILL_IN__` instead of inventing one."

**[Tab 9: severity.py, lines 26–29, then `sort_key` at line 68]**
> "Priority is ICE: impact from severity, confidence from the confidence field, ease from
> effort, all fixed lookups. Then a total sort order, so the same site always gives a
> byte-identical report."

*(70 words)*

---

## Beat 4 · Field-tested, and locked in (2:30 – 2:55) — cut first if over time

**[Tab 10a: DESIGN.md, line 320 → Tab 10b: dom.py, line 53]**
> "Field testing also found a miss: our empty-page detector never fired on live sites. The
> fix keys on the noscript 'enable JavaScript' message, which any framework shows."

**[Tab 10c: test_regressions.py, line 2, then scroll the R1–R12 headers]**
> "And every false positive we fixed is pinned by a regression test, R1 to R12, so it can't
> quietly come back. Now, live."

*(50 words)*

---

## Claims deliberately NOT in this script (and why)

| tempting claim | why it's out |
|---|---|
| "13 findings are moot until F-001" (from DESIGN.md) | The checked-in golden has **11** `blocked_by: F-001` (and `summary.blocked_findings` = 11). A judge who opens the golden sees 11; say 11. |
| "365 findings down to 205 on five live sites" (DESIGN.md) | Prose only; nothing in the submitted code reproduces it. Unanchored narration earns nothing. |
| "We audited five live sites and each false positive became R1–R12" (Lakshya's draft) | `test_regressions.py` says the R-tests were found via the healthy **control fixture**. We say only what the docstring says: every fixed false positive has a test that fails if it returns. |
| "Links only exist after JavaScript runs" as an example of a strong check | False positive in the frozen engine (see `SCOUTING.md`, `NOTES.md` §8). Do not feature it. |
| "Every check is precise" / "no false positives" | Not true (see `SCOUTING.md`). Say what the code does, not how good it is. |

## Checklist before hitting record

- [ ] `sha256sum -c round3-frozen/SHA256SUMS` passes (the engine on screen is the submitted one)
- [ ] VS Code is showing `demo/` (the unzip), not any other copy
- [ ] All 13 tabs open, in order, scrolled to the listed lines
- [ ] Timer: Beats 1–3 done by 2:30 in rehearsal; if not, drop Beat 4
