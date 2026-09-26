# Round 4 video — script and run sheet

**Hard cap 5:00.** Part 1 (methodology) **≤ 3:00**, Part 2 (live trial run) **≤ 2:00**.
Part 2 is **one continuous take**: you may cut idle waiting (the ~40 s crawl, the model
thinking) and nothing else. If a take goes wrong, restart Part 2 from the prompt. Never
splice two takes together (brief §3 and the §6 integrity floor).

Everything said on camera must match [`REPLAY_LakshyaTanmayKalpit.txt`](../REPLAY_LakshyaTanmayKalpit.txt):

| on camera | must be exactly |
|---|---|
| harness | Claude Code **2.1.283** |
| model | Claude **Opus 5.5** (`claude-opus-5-5`) |
| URL typed | `https://www.npr.org/` |
| plugin loaded | `--plugin-dir ./submission.zip` (the unchanged Round 3 package) |

If anything in that table changes (for example Claude Code updates itself before you
record), update the REPLAY file to match and re-run `python round4/verify_round4.py`.

---

## 0. Before you press record (off camera, ~5 min)

1. `git checkout round4_lakshya_new_test` and open a terminal **at the repo root**.
2. `python round4/verify_round4.py`, which must end in `OK: engine is byte-identical…`.
3. `claude --version` must print `2.1.283`. If it prints something newer, either pin it
   back (`npm install -g @anthropic-ai/claude-code@2.1.283`) or update `AGENT_HARNESS`
   in the REPLAY file.
4. Delete any previous output: `rm -rf audit-output` (PowerShell: `Remove-Item -Recurse -Force audit-output`).
   **Never run `python package_submission.py` without `--check`.** It rebuilds
   `submission.zip`, and a rebuild on Windows differs from the submitted Linux-built
   artifact by one header byte per file. The verifier flags it; `git checkout -- submission.zip` restores it.
5. Terminal font ≥ 16 pt, window ~120 columns wide, dark theme, notifications off.
6. Open `round4/PROMPT.txt` in an editor so you can copy the prompt in one go (the URL
   is visible inside it on screen).
7. For Part 1, open the files below in VS Code. Every anchor is `path:line`, so
   `code -g <path>:<line>` jumps straight to it.

---

## Part 1 — How we built it (≤ 3:00, ~400 spoken words ≈ 2:40)

Speak at a normal pace. The right-hand column is what must be on screen while you say
the line, so every claim is anchored to submitted code (brief §3: "a claim is only as real
as the code behind it"). Paths are relative to `brand-ai-readiness-audit/`. The same
bytes are inside `submission.zip`.

### 0:00–0:10 · Who and what

| say | show |
|---|---|
| "We're Lakshya, Tanmay and Kalpit. Our marketplace is nine agentskills.io skills behind one entrypoint, and every claim here points at a file and line in it." | `marketplace.json:7-12` (the one `"entrypoint": true`) · `skills/ai-readiness-orchestrator/scripts/orchestrate.py:49-58` (it composes the other skills by subprocess) |

### 0:10–1:05 · How we discovered the findings

| say | show |
|---|---|
| "A machine has to reach a page, read it, and lift a quotable fact, in that order. We researched each step." | `skills/ai-readiness-orchestrator/references/gate-rules.md:5-25` |
| "Reach. Vendors document separate crawlers for training and for answer-time retrieval. Blocking GPTBot doesn't remove you from ChatGPT search, but blocking OAI-SearchBot does. So we classify each blocked bot by what blocking it costs, and match rules with our own RFC 9309 parser." | `skills/crawl-access-audit/references/bot-taxonomy.md:14-45` · `skills/crawl-access-audit/references/ai-bots.json:16-20` (dated snapshot) · `skills/crawl-access-audit/scripts/check_robots.py:248-269` · `skills/site-evidence-collector/scripts/politeness.py:4-16` |
| "Read. Non-JavaScript fetchers only see raw HTML. Our first shell detector passed every fixture but fired zero times on five live sites, so we rebuilt it around the empty mount point." | `DESIGN.md:320-342` · `skills/render-gap-audit/scripts/diff_raw_rendered.py:233-263` |
| "Extract. The GEO paper found that citations, statistics and quotes lift visibility, so we check for them, at low. We also simulate retrieval windows to test whether each claim survives out of context." | `skills/answerability-audit/references/geo-methods.md` · `skills/answerability-audit/scripts/citability.py:81-91` · `skills/answerability-audit/scripts/retrievability_sim.py:52-132` |
| "Across five live sites, 365 findings exposed twelve false positives. Tuning brought it to 205, and we cut one check entirely." | `DESIGN.md:367-387` · `tests/expected_inventory.json:610-615` |

### 1:05–1:55 · How we assigned severities

| say | show |
|---|---|
| "Severity is what a defect costs if it's true, and confidence is how sure we are. Critical means invisible to that system. A blocked training crawler is a licensing choice, so it's info, never escalated." | `skills/ai-readiness-orchestrator/references/severity-model.md:3-23` · `check_robots.py:271-311` (critical) vs `:313-343` (info) vs `:345-370` (contested, medium) |
| "When an upstream stage fails, downstream defects are real but moot. So the cascade caps them at medium and tags blocked_by. It never deletes them." | `skills/ai-readiness-orchestrator/scripts/gate_model.py:81-114` (gate closure) · `:136-138` (cap + `blocked_by`) |
| "Engagement is never capped by a crawler block, but it is suppressed when we never observed the rendered page." | `gate_model.py:128-129` (Rule 0) · `skills/ai-readiness-orchestrator/references/gate-rules.md:37-74` (Rule 0b) · `skills/engagement-audit/scripts/gating.py:51-56` |
| "Confidence has ceilings. From one site we can't prove nobody corroborates a brand, so that finding never reaches confirmed. Thresholds come from the site's archetype, never hard-coded." | `skills/trust-freshness-audit/scripts/corroboration.py:100-101` · `skills/site-profile-classifier/scripts/profile.py:266-289` · `skills/site-profile-classifier/references/threshold-profiles.json:2-15` |

### 1:55–2:40 · How we derived and prioritised the fixes

| say | show |
|---|---|
| "No finding ships without evidence, confidence and a mechanism." | `orchestrate.py:242-254` |
| "Patches use values observed on the site, like the exact blocked tokens. Where a value is missing we write FILL_IN rather than invent one." | `check_robots.py:296-310` (patch built from the blocked tokens at `:305`) · `corroboration.py:133` |
| "A fix has to act on the cause. Allow the retrieval agents but keep the training policy separate. Make prose self-contained, never fragmented, per Google's guidance." | `check_robots.py:297-303` (summary + mechanism) · `skills/answerability-audit/references/chunking-model.md:3-33` |
| "Priority is ICE, the average of three scores: impact from post-cascade severity, confidence mapped nine-six-three, and ease from effort. The sort is severity, ICE, stage, then check id. That's a total order, so the same evidence always yields the same report, and anything capped drops below its blocker." | `skills/ai-readiness-orchestrator/scripts/severity.py:27-29`, `:48-53`, `:68-81` · `skills/engagement-audit/references/ice-model.md` |

The 20 s of slack before 3:00 is for moving between files. Don't fill it with more claims.

---

## Part 2 — Live trial run (≤ 2:00 after trimming idle time)

One continuous take. Record the whole screen from the terminal prompt to the final answer.

| time | do | say (or caption) | must be visible |
|---|---|---|---|
| 0:00 | Run `python round4/verify_round4.py`. Trim the output down to its last lines. | "First, this is the unchanged Round 3 engine: submission.zip's SHA-256 matches our Round 3 commit byte for byte." | `freeze.zip_sha256 … 1c872c59…` and the `OK:` line |
| 0:08 | Run `claude --version`, then launch:<br>`claude --plugin-dir ./submission.zip --model claude-opus-5-5 --allowedTools "Bash(python:*)" "Bash(python3:*)" "Bash(curl:*)" "Read"` | "The harness is Claude Code 2.1.283 and the model is Claude Opus 5.5. We load the Round 3 submission.zip itself as the plugin." | `2.1.283`; the model name in Claude Code's header |
| 0:18 | Paste the prompt from `round4/PROMPT.txt` and press Enter. | "The target is npr.org, a site this audit has never seen." | `https://www.npr.org/` inside the prompt |
| 0:25 | Let it work. Trim the ~40 s crawl down to 2–3 s. | Wiring line: "That's our Round 3 entrypoint skill, running our orchestrate.py from the extracted submission. It's not a hard-coded demo." | `Skill(submission:ai-readiness-orchestrator)` and the Bash call to `…/scripts/orchestrate.py https://www.npr.org/` |
| 0:40 | Scroll to the summary and table. | "One critical, and N findings capped behind it." (read N off the screen) | summary counts; F-001 row; `blocked_by F-001` column |
| 0:55 | Scroll to the F-001 drill-down. | "The evidence cites robots.txt line numbers: ChatGPT-User, OAI-SearchBot, Claude-SearchBot, Claude-User and PerplexityBot are all `Disallow: /`. These are answer-time retrieval crawlers, so this is critical. GPTBot and CCBot are also blocked, but that's training, so it's reported separately as info, not a defect." | evidence quote; severity and why |
| 1:15 | Scroll to the live check. | "The agent re-fetched robots.txt live, and the same lines say `Disallow: /`." | curl output with line numbers 47, 54, 74, 77, 98 (or whatever the engine cited) |
| 1:30 | Scroll to the fix. | "The fix is a paste-ready patch built from those exact tokens, with its mechanism and a verification command." | patch block; mechanism; verification |
| 1:42 | Scroll to the ICE-sorted list. | "Fixes sorted by ICE: robots comes first at 9.3, ahead of everything it was blocking." | sorted table |
| 1:52 | Stop recording. | "The report is at audit-output/www.npr.org, and the same steps are in our REPLAY file." | — |

**What not to say.** Don't describe findings the screen doesn't show. Don't say the
model found the problems: the engine found them deterministically, and the model invoked
the engine and explained its report. If the table shows `act.orient.no_value_proposition`
on the homepage (it appears on some runs because npr.org's homepage copy changes), don't
hide it. Point out that the engine marks it `likely` rather than `confirmed`, because it's
a pattern-based check.

---

## After recording (5 min)

1. Archive the take's output (the evidence is hashed and the report is re-derived offline):

   ```bash
   python round4/archive_run.py audit-output/www.npr.org --label recorded-run \
       --note "Round 4 video take, Claude Code 2.1.283, claude-opus-5-5"
   ```

   It must print `re-derivation from the bundle: PASS`.
2. `python round4/verify_round4.py`, which must still end in `OK`.
3. Commit `round4/recorded-run/` and push the branch.
4. Submit the video plus `REPLAY_LakshyaTanmayKalpit.txt`. The Round 3 package is not
   resubmitted (brief §2).

## If something goes wrong on camera

| symptom | what to do |
|---|---|
| a permission prompt appears (e.g. for `ls` or `sed`) | approve it. That's live interaction, and it's fine to show. |
| the agent picks a relative `--out` and the engine says "no evidence bundle" | restart Part 2. The prompt asks for `$PWD/...`, and the rehearsal followed it first time. |
| the counts differ from the rehearsal | expected. npr.org's pages change hourly. Narrate what the screen shows. F-001 is the stable part. |
| npr.org is down, or its robots.txt has changed | stop. Pick a new URL, update `TEST_SITE_URLS`, the prompt, `round4/PROMPT.txt` and `EXPECTED_OUTPUT`, re-run the verifier, then record. |
| Part 2 runs past 2:00 after trimming | trim more idle time, or scroll faster through the table. Never cut from the prompt straight to the answer. |
