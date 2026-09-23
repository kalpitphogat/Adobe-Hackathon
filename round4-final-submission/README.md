# Brand AI-Readiness Audit: Round 4 Prototype Showcase

**Team IT_Professionals:** Lakshya, Tanmay, Kalpit
Adobe University Hackathon 2026 · Round 4, Live Agent Demo

This folder is our Round 4 submission. The recorded video is submitted alongside
it. The engine in the video is our Round 3 Agent Skill Marketplace, **unchanged**.
An AI agent runs it live from the command line against a site it has never seen.

---

## In this folder

| File | What it is |
|---|---|
| `REPLAY_IT_Professionals.txt` | The reproduction manifest: harness, model, test URL, and copy-pasteable steps from a clean unzip to the finished report |
| `VIDEO_SCRIPT.md` | The video's narration, with the file and line on screen behind every claim |
| `README.md` | This overview |

## The run at a glance

| | |
|---|---|
| **Engine** | Round 3 `submission.zip`, unchanged. sha256 `1c872c598dcac741c712cbf9e671f024881a9ba251e2b4da66995f81b6cf8dcf` |
| **Entrypoint skill** | `skills/ai-readiness-orchestrator` (`SKILL.md` → `scripts/orchestrate.py`) |
| **Agent harness** | Claude Code v2.1.280 |
| **LLM** | Claude Opus 5.5 (`claude-opus-5-5`) |
| **Test URL** | https://www.theguardian.com/ |
| **Setup** | Python 3.9+, standard library only. No `pip install` |
| **Report** | `./audit-output/audit-report.json`, plus `report.md`, `fix_patches/` and `evidence/` |

## Replaying it

The exact commands and the verbatim prompt are in `REPLAY_IT_Professionals.txt`.
In short:

1. Unzip the Round 3 package and start the harness inside it:
   ```
   unzip -q submission.zip -d round3 && cd round3 && claude --model claude-opus-5-5 --allowedTools "Bash(python:*),Bash(python3:*),Bash(curl:*),Read"
   ```
2. Paste the step-2 prompt from the manifest. It points the agent at the
   entrypoint `SKILL.md` and ends with the website to audit. To test a URL of your
   own choosing, change only that last part.
3. The agent runs the entrypoint, reads `./audit-output/audit-report.json`, and
   reports the findings in priority order, with a drill-down on the top one that
   it checks against the live site.

**Without an agent**, the same report comes straight from the engine:
```
python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://www.theguardian.com/ --out ./audit-output --no-render
```

## What the run finds on the test URL

- **F-001 · critical · confirmed · ICE 9.3.** Line 102 of the site's `robots.txt`
  (`Disallow: /`) blocks six AI retrieval crawlers: PerplexityBot, Claude-SearchBot,
  Claude-User, DuckAssistBot, Amazonbot and Google-CloudVertexBot. These crawlers
  fetch pages when a user asks a question, so the brand cannot be cited by those
  assistants. The agent fetches the live `robots.txt` and confirms the line.
  The fix is a paste-ready robots.txt patch that leaves the training-crawler policy
  as it is.
- **The gate cascade.** Downstream discoverability findings are still reported,
  capped at medium and tagged `blocked_by: F-001`. They are real, but they change
  nothing until F-001 is fixed.
- **Engagement stays independent.** Visitor-facing findings, such as a homepage
  whose first screen never states what the site offers (high), are not capped.
  A visitor arriving from a link does not depend on crawlers.
- **Training-only crawlers** blocked on the same site are reported as `info`, a
  licensing choice rather than a defect.

The site publishes all day, so page-level counts differ from run to run. The root
cause, its evidence and the shape of the cascade stay the same while the site's
`robots.txt` is unchanged.

## Why a replay reaches the same substance

- **The engine computes every finding.** The model only invokes the entrypoint
  and reads the report back, so a different model changes the wording, not the
  findings. The agent-free command above produces the same report.
- **Ranking is a total order:** severity, then ICE, then stage, then check id.
  The same evidence always ranks the same.
- **`--no-render` is explicit**, so results don't depend on whether Playwright is
  installed on the replaying machine.
- **The evidence is saved.** Re-analysing `./audit-output/evidence` with `--bundle`
  gives a byte-identical report, apart from the timestamp and the bundle path.
- **Checked before submission.** We ran the manifest's steps headless
  (`claude -p`) with the disclosed harness and model, from a fresh unzip of
  `submission.zip`. The agent invoked the entrypoint, produced the same F-001 with
  the same evidence, and confirmed it against the live site.

## Where the reasoning lives in code

| Idea | Implemented in |
|---|---|
| Reach → read → extract → trust ordering, and the cascade | `skills/ai-readiness-orchestrator/scripts/gate_model.py`, `references/gate-rules.md` |
| Retrieval vs training crawlers | `skills/crawl-access-audit/references/ai-bots.json`, `scripts/check_robots.py` |
| What each severity means | `skills/ai-readiness-orchestrator/references/severity-model.md` |
| ICE score and ranking | `skills/ai-readiness-orchestrator/scripts/severity.py` |
| Every fix carries a mechanism, patch and verification | `skills/*/scripts/bundle.py` (`action()`), `orchestrate.py` (`validate_finding`) |
| Engagement never capped by crawler access | `gate_model.py` (Rule 0), `skills/engagement-audit/scripts/gating.py` |
| Thresholds chosen per site type, never hardcoded | `skills/site-profile-classifier/references/threshold-profiles.json` |
| Field-tested false positives, locked in | `tests/test_regressions.py` (R1–R12) |

The full narration, with line numbers, is in `VIDEO_SCRIPT.md`.

## Guardrails during the run

- **Read-only.** The engine only sends GET and HEAD requests and never changes
  the site.
- **robots.txt is obeyed** for our own crawl.
- **No crawler impersonation.** `--probe-bot-ua` stays off for sites we don't own.
- **Polite and bounded:** at most 25 pages, per-host delays, and a 300-second
  time budget for the whole run.
