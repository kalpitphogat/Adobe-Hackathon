# Recorded run

This folder holds the archived output of the **video take**, the continuous Part 2 run shown on camera.

It is filled right after recording, from the folder the on-camera session wrote:

```bash
python round4/archive_run.py audit-output/www.npr.org --label recorded-run \
    --note "Round 4 video take, Claude Code 2.1.283, claude-opus-5-5"
```

That creates `recorded-run/www.npr.org/` with the engine's `audit-report.json`,
`report.md`, `fix_patches/`, the `robots.txt` the crawl saw, a SHA-256 of every file in
the evidence bundle, and `REDERIVATION.txt`. That file must read `PASS`: the frozen
engine, re-run offline on the captured bundle, reproduces every finding exactly.

Until the take is archived, `../rehearsal/www.npr.org/` shows what a run of the same
steps produces, along with its full agent transcript.
