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

## Deliverables

- [ ] `REPLAY_<TeamName>.txt`: the reproduction manifest (Section 5 of the brief)
- [ ] Video, 5:00 max: Part 1 methodology (up to 3:00), Part 2 live run (up to 2:00)

## Rule for this repo

Round 4 work lives here. Nothing in it modifies the engine; the demo runs from
a fresh unzip of `round3-frozen/submission.zip` into `demo/` (git-ignored).
