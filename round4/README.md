# Round 4 — prototype showcase

Round 4 is a **demonstration and reproducibility round, not a rebuild.** The
Round 3 marketplace is reused exactly as submitted. Everything in this folder
sits outside `brand-ai-readiness-audit/`, and `package_submission.py` packs only
the marketplace directory, so nothing here can reach the submitted artifact.

| file | what it is for |
|---|---|
| [`demo_cli.py`](demo_cli.py) | the terminal front end used on camera |
| [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md) | Part 1 beats with per-claim code anchors, Part 2 shot list |
| [`RUNBOOK.md`](RUNBOOK.md) | harness wiring, demo-URL choice, dress rehearsal, recording |
| [`REPLAY_TeamName.txt`](REPLAY_TeamName.txt) | the reproduction manifest — **rename and fill** |
| [`verify_replay.py`](verify_replay.py) | proves the manifest replays, before a judge finds out it doesn't |
| [`check_engine_frozen.py`](check_engine_frozen.py) | proves the demoed engine is the submitted engine |

---

## The CLI

```bash
python3 round4/demo_cli.py doctor                                  # preflight
python3 round4/demo_cli.py audit https://example.com               # run + summarise
python3 round4/demo_cli.py audit --offline-root tests/fixtures/site_b
python3 round4/demo_cli.py show ./audit-output --id F-001          # drill in
python3 round4/demo_cli.py prove ./audit-output                    # determinism
```

Standard library only. A judge needs nothing installed that the marketplace does
not already need.

### It contains no checks

This matters more than it sounds, because Round 4's integrity gate turns on it.
`demo_cli.py` shells out to the submitted entrypoint and renders the report that
engine writes. Nothing in it inspects a website, scores a finding, or decides a
severity. Delete it and the findings are identical — they are just harder to
read at 720p in a two-minute video.

It prints the exact command before running it, so a viewer sees the engine being
*driven*, not imitated:

```
  engine      3251f79064da
  invoking    brand-ai-readiness-audit/skills/ai-readiness-orchestrator/scripts/orchestrate.py

  python3 skills/ai-readiness-orchestrator/scripts/orchestrate.py https://... --out ./audit-output
```

The **engine fingerprint** hashes every `SKILL.md` and every script in the
marketplace. Say it on camera during the preflight and show it again during the
run: the same number twice means the same engine drove both, which is the claim
the video has to make out loud.

### What each command is for on camera

**`doctor`** — the pre-roll. Python version, entrypoint present, Playwright
present or honestly absent, and whether the working tree still matches
`submission.zip`. Run it before recording; if it is not green, do not record.

**`audit`** — Part 2's spine. Progress is read off the filesystem the engine is
writing to, so each step lights up only when the artifact proving it appears.
Nothing is a decorative timer: a step that never lights up genuinely did not
happen. Ends on the ranked list, gates shown inline (`← moot until F-001 is
fixed`), plus the counts of findings deliberately *not* raised and of what could
not be assessed.

**`show --id F-00N`** — the drill-down the rubric asks for. Evidence as observed,
affected URLs, why it hurts (mechanism), the fix with priority / effort / ICE,
the paste-ready patch, the command to verify it landed, and the `check_id` so a
judge can find the code that produced it.

**`prove`** — the reproducibility criterion, in one screen. Engine identity,
the six golden reports compared byte-for-byte, and a re-run of the audit you
just did with the findings diffed against it.

---

## Before you record

```bash
python3 round4/check_engine_frozen.py     # the demoed engine is the submitted one
python3 round4/demo_cli.py doctor         # the machine is ready
python3 round4/verify_replay.py round4/REPLAY_<TeamName>.txt
```

Then work through the checklist at the end of [`RUNBOOK.md`](RUNBOOK.md).

The one item that is not a checkbox: **rehearse on real sites first.** Part 2 is
35 points on live behaviour against an unseen URL, and judges run a URL of their
own too. Every fixture the engine has been tested against, we wrote ourselves.
`RUNBOOK.md` §3 covers what to look for.
