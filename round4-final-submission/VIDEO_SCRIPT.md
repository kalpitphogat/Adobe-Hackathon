# Video script: IT_Professionals, Round 4

The narration of our Round 4 video, with the code on screen behind every claim.

- **Part 1**, how we built it: 3:00 or less.
- **Part 2**, the live run: 2:00 or less.

Paths are relative to the root of the Round 3 marketplace (the top level of
`submission.zip`). Line numbers refer to that unchanged package.

---

## Part 1: how we built it

### 0:00–0:15 · What it is
**On screen:** `marketplace.json`, the `"entrypoint": true` entry

> We're IT_Professionals. Our Round 3 marketplace takes any URL and reports why AI
> assistants don't find or cite the brand, and why visitors leave without acting.
> Nine skills, one entrypoint, ai-readiness-orchestrator, declared right here in
> marketplace.json.

### 0:15–1:20 · How we discovered the findings
**On screen, in order:**
1. `skills/ai-readiness-orchestrator/references/gate-rules.md:5-19`: the Round-2 appendix quote
2. `skills/crawl-access-audit/references/ai-bots.json`: one retrieval entry and one training entry
3. `skills/crawl-access-audit/scripts/check_robots.py:249-300`: retrieval → `severity="critical"` (:286)
4. `DESIGN.md:367-380`: the live-site field test
5. `tests/test_regressions.py:49-58`: regression R1, then the `# R1.` … `# R12.` headers
6. `skills/site-evidence-collector/scripts/dom.py:53-58`: the noscript signal
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
> findings, with false positives we named before touching a threshold. Each one is
> now a numbered regression test, R1 to R12, in test_regressions.py. We also found a
> false negative: our SPA-shell detector fired zero times, even on a 16-word page.
> We rewrote it around the noscript "enable JavaScript" message in dom.py, which
> every framework emits. Those five sites went to 205.
>
> And no check hardcodes a number: thresholds come from threshold-profiles.json,
> picked by site archetype.

### 1:20–2:10 · How we assigned severities
**On screen, in order:**
1. `skills/ai-readiness-orchestrator/references/severity-model.md`: the severity table
2. `skills/render-gap-audit/scripts/diff_raw_rendered.py:97-104`: `default_severity` in a `CHECKS` registry
3. `skills/ai-readiness-orchestrator/scripts/gate_model.py:81-114`, then `:117-148` (`:42` ceiling, `:129` Rule 0, `:138` `blocked_by`)
4. `skills/engagement-audit/scripts/gating.py:32`: `RULE_0B_SUPPRESSIBLE`

> Severity is what a finding costs if it's true. Critical means the machine can't
> see the page at all. High means a specific capability is lost. Info means a
> choice, not a defect. Every check declares its default in its CHECKS registry,
> and confidence (confirmed, likely, hypothesis) is a separate field.
>
> Then the cascade in gate_model.py. A critical, or two highs in one stage, closes
> that gate. Downstream discoverability findings stay in the report, capped at
> medium and tagged blocked_by the root cause, so you see one cause first instead
> of fifteen criticals. Engagement is never capped by crawler access, because a
> visitor from an ad doesn't care about robots.txt.

### 2:10–2:55 · How we derived and prioritised the fixes
**On screen, in order:**
1. `skills/answerability-audit/scripts/bundle.py:175-190`: `action()` (summary, effort, mechanism, source, patch, verification)
2. `skills/ai-readiness-orchestrator/scripts/orchestrate.py:242-254`: `validate_finding`
3. `skills/structured-data-audit/scripts/check_hierarchy.py:208-225`: `__FILL_IN__`
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

## Part 2: the live run

The run follows `REPLAY_IT_Professionals.txt` step by step, from the unzipped Round
3 package. From entering the URL to the findings it is one continuous take. Only
idle waiting while the agent fetches and reads is trimmed.

### 0:00–0:12 · Harness and model
**On screen:** `claude --version` → `2.1.280 (Claude Code)`, then
```
claude --model claude-opus-5-5 --allowedTools "Bash(python:*),Bash(python3:*),Bash(curl:*),Read"
```
> Harness: Claude Code 2.1.280. Model: Claude Opus 5.5. This folder is our
> unzipped Round 3 submission.zip, unchanged.

### 0:12–0:25 · The URL, entered on camera
**On screen:** the step-2 prompt from the REPLAY file, with
`Website: https://www.theguardian.com/` typed live.
> One line on wiring: the agent is about to read our entrypoint SKILL.md and run
> its orchestrate.py. That runs the collector, the classifier and six audit
> skills as subprocesses. Nothing is precomputed; every finding comes from what
> the site serves right now.

### 0:25–0:45 · The agent works
**On screen:** the agent reading `SKILL.md`, the full
`orchestrate.py … --no-render` command, and the JSON summary it prints.

### 0:45–1:30 · Drill-down: F-001
**On screen:** the agent's drill-down and its live `curl` of the site's robots.txt.
> The top finding is critical and confirmed. Evidence: the exact robots.txt line,
> line 102, `Disallow: /`, blocking PerplexityBot, Claude-SearchBot and four other
> retrieval crawlers. The agent just fetched the live file and confirmed it. It's
> critical because a retrieval crawler that's refused can't cite the brand at all.
> The training-only bots on the same site are reported separately as info, because
> that's a licensing choice. The fix is a paste-ready robots.txt patch that keeps
> the training policy separate. We're recommend-only: the report states what the
> block costs in AI visibility, and lifting it is the owner's decision.

### 1:30–1:52 · Prioritised by impact
**On screen:** the agent's top-5 table (priority, then ICE).
> Fixes are sorted by impact: severity, then ICE. F-001 is 9.3. The findings
> capped behind it carry blocked_by F-001: real, but moot until it's fixed. The
> engagement finding just below isn't capped, because visitors don't depend on
> crawlers.

### 1:52–2:00 · Close
> Everything is in audit-output/audit-report.json, the path in our REPLAY file.
