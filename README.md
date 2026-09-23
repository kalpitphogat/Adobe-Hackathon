# Kalpit_round_4

Adobe University Hackathon 2026, Round 4: the Prototype Showcase (live agent demo).

Round 4 is a demonstration and reproducibility round, not a rebuild. The Round 3
marketplace is **frozen**: the live run in the video must use exactly what was
submitted in Round 3. If the engine differs, the submission fails the integrity check.

## Layout

| path | what |
|---|---|
| `round3-frozen/submission.zip` | The Round 3 upload, byte for byte. Never edit it. |
| `round3-frozen/SHA256SUMS` | Its hash. Check before every recording: `sha256sum -c round3-frozen/SHA256SUMS` |
| `NOTES.md` | Verified facts about the frozen engine that affect the demo; read before recording |
| `tools/summarize.py` | Reads an `audit-report.json` and prints a one-screen summary for comparing runs |

## Team and recording setup

- Team: **IT_Professionals**; manifest file `REPLAY_IT_Professionals.txt`
- Harness: **Claude Code 2.1.280**, model **Claude Opus 5.5** (`claude-opus-5-5`)
- Python **3.11.15** (via `uv`), Playwright **1.63.0** + Chromium

## Local setup (Windows, PowerShell)

```powershell
uv python install 3.11.15
uv venv --python 3.11.15 .venv
uv pip install --python .venv\Scripts\python.exe playwright==1.63.0
.venv\Scripts\python.exe -m playwright install chromium
Expand-Archive round3-frozen\submission.zip demo -Force
cd demo; ..\.venv\Scripts\python.exe tests\run_offline.py
```

## Deliverables

- [x] `REPLAY_IT_Professionals.txt`: the reproduction manifest (Section 5 of the brief), rehearsed from a clean unzip
- [x] `VIDEO_PART1_SCRIPT.md`: Part 1 narration, every claim tied to a file and line in the frozen engine
- [ ] Part 2 run sheet (live run on https://docs.pytest.org/)
- [ ] Video, 5:00 max: Part 1 methodology (up to 3:00), Part 2 live run (up to 2:00)

## Rule for this repo

Round 4 work lives here. Nothing in it modifies the engine; the demo runs from
a fresh unzip of `round3-frozen/submission.zip` into `demo/` (git-ignored).
