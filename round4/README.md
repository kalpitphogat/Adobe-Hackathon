# `round4/`

One file, and it is **not** part of the Round 3 engine.

| file | what it is |
|---|---|
| [`demo_cli.py`](demo_cli.py) | Fallback D in `REPLAY_IT_Professionals.txt`: a standard-library terminal view of a report the engine already wrote |

`demo_cli.py` **contains no checks.** It shells out to `orchestrate.py` in your
own unzipped marketplace and formats what that engine returns — progress per
skill, findings in the engine's own rank order, drill-down by finding id. Delete
it and the findings are identical.

It is **not used in the video.** The recorded run shows the agent driving the
entrypoint directly, because §3 asks to see the agent *"invoking your entrypoint
skill, fetching, reasoning, and producing findings"* — a rendering layer between
the agent and the engine would work against that. This exists for a judge who
wants a readable view without running an agent at all.

The manifest fetches it from a **pinned commit** and gives its SHA-256, so the
copy a judge runs is byte-checkable and cannot drift with this branch.

## What used to be here

Five earlier files were removed once the root-level deliverables superseded
them, because two versions of the same deliverable is a wrong-file risk:

| removed | superseded by |
|---|---|
| `REPLAY_TeamName.txt` (unfilled `<<FILL>>` template) | [`REPLAY_IT_Professionals.txt`](../REPLAY_IT_Professionals.txt) |
| `VIDEO_SCRIPT.md` (649 words ≈ 4:38, over the 3:00 cap) | [`VIDEO_PART1_SCRIPT.md`](../VIDEO_PART1_SCRIPT.md) + [`VIDEO_PART2_RUNSHEET.md`](../VIDEO_PART2_RUNSHEET.md) |
| `RUNBOOK.md` | [`VIDEO_PART2_RUNSHEET.md`](../VIDEO_PART2_RUNSHEET.md) |
| `check_engine_frozen.py` (whole-zip hash) | [`tools/verify_engine.py`](../tools/verify_engine.py) (per-file, plus the `.claude/skills` copy) |
| `verify_replay.py` (parsed only) | [`tools/verify_replay.py`](../tools/verify_replay.py) (parses **and replays**) |
