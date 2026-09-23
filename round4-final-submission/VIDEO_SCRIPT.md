# Round 4 video script: IT_Professionals

**Hard cap: 5:00 total.** Part 1 ≤ 3:00 (reasoning), Part 2 ≤ 2:00 (live run).
Paths are relative to the marketplace root, which is `brand-ai-readiness-audit/`
in the repo and the top level of `submission.zip`. Every line number was checked
against the Round 3 engine at commit `ede3a6b`.

Part 1 narration is 420 words without the *[bracketed]* sentences, about 2:48 at
150 words per minute. With them it is 464 words, about 3:05, which is over the
cap. **Leave the brackets out by default.** Add them back only if a timed
rehearsal comes in under 2:40.

---

## Part 1: how we built it (≤ 3:00)

Split the screen: your face or voice, plus an editor showing the file named in the
**SHOW** line. Open each file at the given line **before** you start speaking that
block. Judges score claims they can trace to code.

### 0:00–0:15 · What it is
**SHOW:** `marketplace.json`, with `"entrypoint": true` highlighted

> We're IT_Professionals. Our Round 3 marketplace takes any URL and reports why AI
> assistants don't find or cite the brand, and why visitors leave without acting.
> Nine skills, one entrypoint, ai-readiness-orchestrator, declared right here in
> marketplace.json.

### 0:15–1:20 · How we discovered the findings
**SHOW, in order:**
1. `skills/ai-readiness-orchestrator/references/gate-rules.md:5-19`, the appendix quote
2. `skills/crawl-access-audit/references/ai-bots.json`, one retrieval and one training entry
3. `skills/crawl-access-audit/scripts/check_robots.py:249-300` (retrieval → `severity="critical"` at :286)
4. `DESIGN.md:320-341` and `DESIGN.md:367-380`
5. `skills/site-evidence-collector/scripts/dom.py:53-58` (the noscript signal)
6. `skills/answerability-audit/scripts/retrievability_sim.py:25-35` and `:79`
7. `skills/site-profile-classifier/references/threshold-profiles.json:1-15`

> Our signals start from one sentence in the Round-2 appendix: a crawler has to be
> let in, read the page, and then pick out the fact, *in that order*. So every
> check belongs to a stage: reach, read, extract, trust, act.
>
> Research changed *what* we check. "Is an AI bot blocked?" is the wrong question,
> because training crawlers and answer-time retrieval crawlers are separate
> pipelines. ai-bots.json classifies 29 crawlers, and check_robots.py reports a
> blocked retrieval bot as critical, a training bot as info, and a contested one
> as medium.
>
> Then we audited five live sites with different architectures. That produced 365
> findings. We named twelve false positives before touching a threshold, and one
> false negative: our SPA-shell detector fired zero times, even on a 16-word page.
> We rewrote it around the noscript "enable JavaScript" message in dom.py, which
> every framework emits. Those five sites went to 205.
>
> *[For quotability, retrievability_sim.py splits the text a no-JavaScript reader
> sees into 300-token windows, and checks whether each key fact survives in a
> window that names its own subject.]* And no check hardcodes a number:
> thresholds come from threshold-profiles.json, picked by site archetype.

### 1:20–2:10 · How we assigned severities
**SHOW, in order:**
1. `skills/ai-readiness-orchestrator/references/severity-model.md`, the severity table
2. `skills/render-gap-audit/scripts/diff_raw_rendered.py:97-104` (`default_severity` in the `CHECKS` registry)
3. `skills/ai-readiness-orchestrator/scripts/gate_model.py:81-114` then `:117-148` (`:42` ceiling, `:129` Rule 0, `:138` `blocked_by`)
4. `skills/engagement-audit/scripts/gating.py:32` (`RULE_0B_SUPPRESSIBLE`)

> Severity is what a finding costs if it's true. Critical means the machine can't
> see the page at all. High means a specific capability is lost. Info means a
> choice, not a defect. Every check declares its default in its CHECKS registry,
> and confidence (confirmed, likely, hypothesis) is a separate field.
>
> Then the cascade in gate_model.py. A critical, or two highs in one stage, closes
> that gate. Downstream discoverability findings stay in the report, capped at
> medium and tagged blocked_by the root cause, so you see one cause first instead
> of fifteen criticals. Engagement is never capped by crawler access, because a
> visitor from an ad doesn't care about robots.txt. *[But if we never saw the
> rendered page, gating.py suppresses engagement checks entirely: they'd be
> unevidenced.]*

### 2:10–2:55 · How we derived and prioritised the fixes
**SHOW, in order:**
1. `skills/answerability-audit/scripts/bundle.py:175-190` (`action()`: summary, effort, mechanism, source, patch, verification)
2. `skills/ai-readiness-orchestrator/scripts/orchestrate.py:242-254` (`validate_finding`)
3. `skills/structured-data-audit/scripts/check_hierarchy.py:208-225` (`__FILL_IN__`)
4. `skills/ai-readiness-orchestrator/scripts/severity.py:27-29`, `:48-53`, `:68-83`

> Every fix goes through one action() contract: a mechanism for why it works, a
> source, a paste-ready patch, and a command to verify it. validate_finding rejects
> any finding without a mechanism. Patches reuse values from the site's own
> evidence, and where a value is missing we write FILL_IN rather than invent one.
>
> Priority is ICE in severity.py. Impact comes from the post-cascade severity,
> confidence maps to 9, 6 or 3, and ease comes from effort. The sort is severity,
> then ICE, then stage, then check id. That's a total order, so the same evidence
> always ranks the same.

### 2:55–3:00 · Hand-off
> Seventy-three validator checks and six golden reports hold all of this in place.
> Now, live.

---

## Part 2: live run (≤ 2:00)

### Off camera, before you press record
1. `live-demo/` (next to this file) is the **Round 3 `submission.zip` already
   unzipped**, which is exactly what judges have. Record from there. To rebuild it:
   delete the folder's contents, then
   `Expand-Archive F:\adobe_hackathon\submission.zip -DestinationPath .\live-demo`.
2. Open a terminal **in `live-demo/`**. Use a large font and a dark theme. Close
   everything else.
3. Confirm there is no `audit-output` folder in it yet. Delete any left over from
   a rehearsal.
4. Keep `REPLAY_IT_Professionals.txt` open off screen, so you can copy the step-2
   prompt **without** its last part (`Website: https://www.theguardian.com/`).
5. Check the Guardian's robots.txt still blocks the crawlers (PowerShell):
   `curl.exe -s https://www.theguardian.com/robots.txt | Select-String '^Disallow: /$'`.
   It should print one line. If it prints nothing, pick another URL **and change it
   in REPLAY** (see below).

### On camera

**0:00–0:12 · State the harness and model**
Run `claude --version` so `2.1.280 (Claude Code)` is visible, then:
```
claude --model claude-opus-5-5 --allowedTools "Bash(python:*),Bash(python3:*),Bash(curl:*),Read"
```
> Harness: Claude Code 2.1.280. Model: Claude Opus 5.5. This folder is our
> unzipped Round 3 submission.zip, unchanged.

**0:12–0:25 · Enter the URL on camera**
Paste the prompt, then **type** `Website: https://www.theguardian.com/` live and
press Enter.
> One line on wiring: the agent is about to read our entrypoint SKILL.md and run
> its orchestrate.py. That runs the collector, the classifier and six audit
> skills as subprocesses. Nothing is precomputed; every finding comes from what
> the site serves right now.

**0:25–0:45 · Agent works** (trim idle waiting only)
Keep the agent reading `SKILL.md`, the full `orchestrate.py … --no-render`
command, and the JSON summary it prints (`"critical": 1`, `"blocked_findings": …`)
on screen.

**0:45–1:30 · Drill into F-001**
Let the agent's answer scroll to the drill-down and the `curl` verification.
> The top finding is critical and confirmed. Evidence: the exact robots.txt line,
> line 102, `Disallow: /`, blocking PerplexityBot, Claude-SearchBot and four other
> retrieval crawlers. The agent just fetched the live file and confirmed it. It's
> critical because a retrieval crawler that's refused can't cite the brand at all.
> The training-only bots on the same site are reported separately as info, because
> that's a licensing choice. The fix is a paste-ready robots.txt patch that keeps
> the training policy separate.

**1:30–1:52 · Show it is prioritised**
Point at the agent's top-5 table (priority, then ICE).
> Fixes are sorted by impact: severity, then ICE. F-001 is 9.3. And *(read the
> number off the screen)* findings are capped with blocked_by F-001: real, but
> moot until it's fixed. The engagement finding just below isn't capped, because
> visitors don't depend on crawlers.

Optional, if time allows: `dir audit-output\fix_patches` to show one patch file
per finding.

**1:52–2:00 · Close**
> Everything is in audit-output/audit-report.json, the path in our REPLAY file.

### Integrity rules (Section 6: breaking any of these sinks the submission)
- **One continuous take** from typing the URL to the findings. You may cut only
  idle waiting, never splice runs together.
- **Read the numbers off the screen.** The Guardian publishes all day, so page-level
  counts change between runs. Our rehearsals gave 35 and 34 findings, 27 and 26
  capped. Never say a number from this script that isn't on screen.
- Harness, model and URL on camera **must equal** `REPLAY_IT_Professionals.txt`.
  If you change the URL, change it in `TEST_SITE_URLS` **and** at the end of the
  step-2 prompt.
- Don't touch anything under `skills/`. The engine must be byte-identical to Round 3.

### Things to avoid on camera
- **Don't open a JSON-LD patch that contains a page title.** Four Round 3
  templates format the title with Python's `repr()`, so the patch shows
  `'single quotes'`, which is invalid JSON-LD (`validate_types.py:105,154`,
  `date_consistency.py:167`, `non_text_facts.py:176`). The engine can't change in
  Round 4, so drill into F-001, whose patch is plain robots.txt. If a judge asks,
  the honest answer is "known template bug; the value is correct but needs
  double quotes."
- Don't quote "13 capped" for `site_b` from DESIGN.md or gate-rules.md. The golden
  report the code produces says **11**.
- Don't use `--probe-bot-ua`. It is for sites you own.
