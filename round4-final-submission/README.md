# Round 4 final submission: IT_Professionals

Adobe University Hackathon 2026 · Round 4 (Prototype Showcase, Live Agent Demo)

Round 4 asks for **two things**. Judges already hold our Round 3 marketplace and
reuse it unchanged, so it is **not** resubmitted.

| # | Deliverable | Status |
|---|---|---|
| 1 | Recorded video, ≤ 5:00 (Part 1 reasoning ≤ 3:00, Part 2 live run ≤ 2:00) | **Record it** with `VIDEO_SCRIPT.md` |
| 2 | `REPLAY_IT_Professionals.txt`, the reproduction manifest | Ready, and dry-run verified from a clean unzip |

## What is in this folder

```
round4-final-submission/
├─ REPLAY_IT_Professionals.txt   ← SUBMIT alongside the video
├─ VIDEO_SCRIPT.md               ← timed narration with a code anchor for every claim, plus the live-run plan
├─ README.md                     ← this file
└─ live-demo/                    ← Round 3 submission.zip unzipped, byte-identical. Record Part 2 here.
                                   (git-ignored: a working copy, not a deliverable)
```

## Harness and model (must match the video)

- **Agent harness:** Claude Code v2.1.280
- **LLM:** Claude Opus 5.5 (`claude-opus-5-5`)
- **Test URL:** https://www.theguardian.com/
- **Engine:** the unchanged Round 3 `submission.zip`, sha256
  `1c872c598dcac741c712cbf9e671f024881a9ba251e2b4da66995f81b6cf8dcf`
  (branch `final-submission`, commit `ede3a6b`)

## What was verified before handing over

| Check | Result |
|---|---|
| `python package_submission.py --check` | OK, zip valid, 412 KB, exactly one entrypoint |
| `python tests/validate_marketplace.py` | 73 passed, 0 failed |
| `python tests/run_offline.py` | 6 of 6 fixtures reproduce the goldens finding-for-finding. It prints "DRIFTED" only because the goldens record Python 3.11.15 and this machine has 3.11.9 |
| `tests/test_*.py` (10 suites) | 9 pass. `test_ssrf.py` fails 1 of 30 **on Windows only**: `http://127.1/` doesn't resolve on Windows, so the request fails before the guard is reached. Nothing is fetched either way |
| Live audit of theguardian.com | 1 critical (`reach.robots.ai_search_bot_blocked`, `Disallow: /` at robots.txt line 102, confirmed with a live `curl`), 26–27 findings capped behind it, engagement untouched |
| Re-analysis of the saved evidence bundle (`--bundle`) | Byte-identical report, apart from `audited_at` and `evidence_bundle.path` |
| **REPLAY TEST_STEPS run headless** (`claude -p`) from a fresh unzip of `submission.zip` | Agent read the entrypoint `SKILL.md`, ran `orchestrate.py`, reported the counts, top 5 by ICE, and the F-001 drill-down, then corroborated it with `curl` |

## Recording checklist

- [ ] Delete `live-demo/audit-output/` if a rehearsal left one.
- [ ] Check the Guardian's robots.txt still has `Disallow: /` for the AI group (command in `VIDEO_SCRIPT.md`).
- [ ] Part 1: every claim spoken while its file is on screen at the listed line.
- [ ] Part 2: `claude --version` on screen; say "Claude Code 2.1.280, Claude Opus 5.5".
- [ ] Type the URL on camera. One continuous take from URL to findings; trim idle time only.
- [ ] Drill into F-001: evidence line, severity, mechanism, patch, live `curl` check.
- [ ] Show the priority order (top 5 by severity → ICE) and the `blocked_by` count.
- [ ] Say one line on wiring: the agent runs the Round 3 entrypoint, nothing hardcoded.
- [ ] Total ≤ 5:00; Part 1 ≤ 3:00; Part 2 ≤ 2:00.
- [ ] If the URL, model or harness changes, update `REPLAY_IT_Professionals.txt` to match **before** submitting.
- [ ] Optional: keep `live-demo/audit-output/` from the recorded take. It is the evidence behind the video.
