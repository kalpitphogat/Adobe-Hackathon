# Video Part 1: Thought process (hard cap 3:00)

> **Superseded by [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md)** (2026-09-26): both parts, shot by shot, with
> every anchor checked against the zip by `tools/check_script_anchors.py`. This earlier draft is kept
> for its history; record from `VIDEO_SCRIPT.md`.

**Rubric line this part is scored on (35 points):** *"Signal discovery, severity logic, and fix
derivation are sound, non-obvious, and traceable to the submitted code."* And the rule that
bites: *"Narration that cannot be traced to the submitted code earns no credit."*

So **every sentence below has the file you show while you say it**. All paths are relative to
the marketplace root: the unzipped `round3-frozen/submission.zip`, i.e. `demo/`. Every line
number was checked against that exact copy (2026-09-23; new anchors 2026-09-24). If you cut a sentence, cut its anchor too.

**Pace:** 390 spoken words: about 2:47 at ~140 words per minute, leaving ~13 s for switching tabs.
That is tight. **Cut order if a timed rehearsal passes 2:50:** (1) the GEO sentence in Beat 1,
(2) the dom.py sentence in Beat 4. Both cuts together bring it to 335 words (~2:24).
Never cut the DESIGN.md sentence in Beat 4: it is the field-research evidence the rubric asks for.
Rehearse against a timer, and cut only in the order given above.

**Screen setup before recording:** VS Code with `demo/` open, font size 18+, these tabs pre-opened
in this order, each already scrolled to its line:

| # | tab | scroll to |
|---|---|---|
| 0 | `skills/answerability-audit/references/chunking-model.md` | line 40 (the brief's "reach, read, and quote" sentence); line 5 later |
| 1 | `skills/ai-readiness-orchestrator/references/gate-rules.md` | line 10 (the quoted handout text) |
| 2a | `skills/crawl-access-audit/references/ai-bots.json` | line 71 (GPTBot, `"category": "training"`) |
| 2b | `skills/crawl-access-audit/scripts/check_robots.py` | line 286 (`severity="critical"`); line 318 is `severity="info"` |
| 3 | `skills/answerability-audit/references/geo-methods.md` | line 14 (what the GEO paper found) |
| 5 | `skills/ai-readiness-orchestrator/references/severity-model.md` | line 5 |
| 6 | `skills/ai-readiness-orchestrator/scripts/gate_model.py` | line 117 |
| 7 | `tests/golden/site_b.audit-report.json` | line 109 |
| 8 | `skills/ai-readiness-orchestrator/scripts/orchestrate.py` | line 242 |
| 9 | `skills/ai-readiness-orchestrator/scripts/severity.py` | line 26 |
| 10a | `DESIGN.md` | **line 374** (365 findings, twelve false positives, 205 after) |
| 10b | `skills/site-evidence-collector/scripts/dom.py` | line 53 (`NOSCRIPT_JS_NOTICE`) |
| 10c | `tests/test_regressions.py` | line 2 (docstring); then scroll past the `# R1.` … `# R12.` headers (lines 50–504) |

Tip: highlight the line you are talking about (click the line number) so the viewer's eye lands on it.

---

## Beat 1 · How we discovered the signals (0:00 – 0:58)

**[Tab 0: chunking-model.md, lines 40–43 (the brief's own sentence)]**
> "Ask an AI assistant about a brand: it either quotes the site or acts as if it doesn't exist.
> We're IT_Professionals, and our audit finds out why. What separates them? Sources get picked
> when a machine can easily reach, read, and quote a clear fact."

**[Tab 1: gate-rules.md, lines 10–14]**
> "In that order. So every check has a stage: reach, read, extract, trust, and act for the
> human visitor."

**[Tab 2a: ai-bots.json, line 71 → Tab 2b: check_robots.py, lines 286 and 318]**
> "Reach: we classified 29 crawlers by role. GPTBot only collects training data, so blocking
> it doesn't cost you ChatGPT search. A blocked retrieval bot is critical, line 286; a training
> bot is info, line 318."

**[Tab 3: geo-methods.md, lines 14–17]**
> "Quote: the GEO study found citing sources and statistics gets pages used more, and keyword
> stuffing doesn't. A benchmark gain is not a defect, so a missing evidence marker is only low."

*(129 words)*

---

## Beat 2 · How we assign severity (0:58 – 1:48)

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

## Beat 3 · How we derive and prioritise fixes (1:48 – 2:22)

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

## Beat 4 · What the field research actually cost us (2:22 – 2:47)

This beat is the rubric's *"how you discovered the findings"* in numbers. **Keep the DESIGN.md
sentence** whatever happens; if Part 1 runs long, follow the cut order under **Pace** above.

**[Tab 10a: DESIGN.md, lines 374–380]**
> "We audited five live sites picked for architectural variance. 365 findings — which was
> itself the finding. We named twelve false positives before touching a single threshold;
> tuning brought the same five sites to 205."

**[Tab 10b: dom.py, line 53]**
> "It found a miss too: our empty-page detector never fired on a real site. It now keys on
> the noscript 'enable JavaScript' notice."

**[Tab 10c: test_regressions.py, scroll the R1–R12 headers]**
> "And every false positive we fixed has a regression test, R1 to R12, so none of them
> comes back quietly. Now, live."

*(93 words)*

---

## Claims deliberately NOT in this script (and why)

| tempting claim | why it's out |
|---|---|
| "13 findings are moot until F-001" (from DESIGN.md) | The checked-in golden has **11** `blocked_by: F-001` (and `summary.blocked_findings` = 11). A judge who opens the golden sees 11; say 11. |
| "365 findings down to 205" as something the code reproduces | It's the field-research record in `DESIGN.md:374`, which is in the submitted zip, so Beat 4 quotes it **as a record of what we did**, with the file on screen. No code re-derives those numbers, so never say "the engine shows" or "you can reproduce". |
| "Each of those twelve (live-site) false positives became R1–R12" | `test_regressions.py` says the R-tests were found via the healthy **control fixture**. We say only what the docstring says: every fixed false positive has a test that fails if it returns. |
| "Links only exist after JavaScript runs" as an example of a strong check | False positive in the frozen engine (see `SCOUTING.md`, `NOTES.md` §8). Do not feature it. |
| "Every check is precise" / "no false positives" | Not true (see `SCOUTING.md`). Say what the code does, not how good it is. |

## Checklist before hitting record

- [ ] `.venv\Scripts\python.exe tools\verify_engine.py round3-frozen\submission.zip demo` ends `ENGINE UNCHANGED` (the engine on screen is the submitted one)
- [ ] VS Code is showing `demo/` (the unzip), not any other copy
- [ ] All 13 tabs open, in order, scrolled to the listed lines
- [ ] Timer: whole script under 2:50 in a timed rehearsal; if not, apply the cut order under **Pace** (GEO sentence, then the dom.py sentence), never the DESIGN.md sentence
