# Round 4 runbook

Round 4 is a **demonstration and reproducibility round, not a rebuild.** The
marketplace is frozen. Everything in this folder sits outside
`brand-ai-readiness-audit/` and is excluded from `submission.zip` by
`package_submission.py`, which packs only the marketplace directory.

---

## 0. The integrity gate, first

> *"The live run in your video must exercise that same submitted marketplace; if
> the engine shown differs from what you submitted in Round 3, the submission
> fails on integrity grounds."* — Section 2

So before recording, **prove** the engine on the recording machine is the one
that was submitted:

```bash
sha256sum submission.zip
```

Compare against the file that was uploaded to the Round 3 form. If they differ,
stop and record against the uploaded one instead — not against `main`.

### The freeze is enforced, not remembered

Nobody edits the marketplace meaning to break the integrity gate. They fix a
typo in a SKILL.md, regenerate a golden, let an editor rewrite line endings —
and the tree silently stops matching the artifact the judges hold.

```bash
python3 round4/check_engine_frozen.py
```

Asserts every file in `brand-ai-readiness-audit/` is byte-identical to the
corresponding entry in `submission.zip`, with nothing added and nothing missing.
A single stray newline fails it. CI runs it on every push.

Pin the artifact once, against the file you actually uploaded:

```bash
sha256sum <the zip you uploaded>            # confirm it is the right file
python3 round4/check_engine_frozen.py --pin --against <the zip you uploaded>
```

That catches the one case a tree-vs-zip comparison cannot: rebuilding the zip
makes both sides agree with each other and disagree with the judges' copy.

**Everything for Round 4 is additive.** `round4/` sits outside the marketplace
and `package_submission.py` packs only the marketplace directory, so nothing
here can reach the submitted artifact. Build on the existing files; do not edit
them.

To demo from the exact submitted artifact rather than the working tree:

```bash
mkdir demo && cd demo
unzip ../submission.zip
python3 skills/ai-readiness-orchestrator/scripts/orchestrate.py --help
```

That directory *is* the submission. Record from inside it. It removes any
argument about whether the working tree had drifted.

---

## 1. Wiring the agent harness to the entrypoint

The handout wants an agent session, not a bare script run: *"A CLI-based session
in which an AI agent runs your marketplace and reports its findings is exactly
what we want to see. The 'interface' is the agent interaction itself."*

Two paths. **Record path A; document both**, because the brief asks for a
fallback when judges may not run your harness identically.

### Path A — the agent reads the SKILL.md (record this)

Provider-neutral, works in any harness, nothing to install. Start the harness
with the marketplace root as the working directory and give it the prompt
verbatim from `REPLAY_<TeamName>.txt`:

```
Read skills/ai-readiness-orchestrator/SKILL.md and follow its Procedure to
audit <URL>. Write the report to ./audit-output. Then read
audit-output/audit-report.json and tell me the top three findings, each with
its evidence and its suggested fix, in the order the report ranks them.
```

The agent reads the entrypoint SKILL.md, finds the documented command under
`## Procedure`, and shells out to it. That shell-out line is what proves on
camera that the session is driving the submitted engine.

Why this path and not native skill auto-discovery: auto-discovery needs the
skills copied into a harness-specific directory (`.claude/skills/` for Claude
Code), which means the thing the judge runs is no longer the submitted layout.
Path A points at the submission exactly as shipped.

Either way, `round4/demo_cli.py` renders the run for camera. It drives the same
entrypoint and holds no checks, so what a judge sees is the engine's own output
— see [README.md](README.md).

### Path B — fallback, no harness at all

```bash
python3 skills/ai-readiness-orchestrator/scripts/orchestrate.py <URL> --out ./audit-output
```

Identical substance; the harness only drives the engine. Document this in the
manifest so a judge who cannot run your harness is never `ran-blocked`.

---

## 2. Choosing the demo URL

Constraints from the brief: a site **the audit has never seen**, entered on
camera, and judges *"will also run a URL of their own choosing to test
generalization."*

Pick for *visible evidence*, not for a high finding count. A good demo URL has
at least one finding whose evidence you can point at on screen — a real
raw-vs-rendered gap, an absent `application/ld+json`, dates that disagree.

Rules of thumb:

- **Small-to-medium marketing or local-business site.** Big sites hit the
  25-page cap and the report gets long to scroll inside 2 minutes.
- **Not a site with a cookie wall or aggressive WAF** — the audit will correctly
  report that it could not see much, which is honest but makes a dull demo.
- **Never** a site you do not have permission to probe with `--probe-bot-ua`.
  Leave that flag off unless the site is yours.
- Run it privately **first**. See §3 — this is the main risk in Round 4.

---

## 3. The dress rehearsal that actually matters

Part 2 is 35 points on live behaviour against an unseen URL, and the
reproducibility criterion says findings must *"hold up under a judge-chosen
URL."* Every fixture the engine has been tested against, we wrote ourselves.
That is the one gap.

Close it before recording:

```bash
# from the marketplace root
for url in <15-20 real URLs across archetypes>; do
  python3 skills/ai-readiness-orchestrator/scripts/orchestrate.py "$url" \
      --out "runs/$(echo "$url" | tr -c 'a-zA-Z0-9' '_')"
done
```

Then read the reports adversarially and ask, per site:

- Did one check produce most of the findings? That is a flooding bug, not a
  site with one dominant defect. Fix the dedupe or the threshold.
- Is any critical **wrong**? A false critical on a judge's URL costs more than
  five misses.
- Does any evidence string read like debug output rather than a sentence?
- Did the run finish inside the time budget on a real site?

Cover archetypes the classifier knows, because thresholds switch on them: docs,
developer-platform, saas-marketing, e-commerce, publisher, local-business.

---

## 4. Recording

- Terminal font large. Judges may watch at 720p in a browser tab.
- Record the whole run unbroken, then trim **idle time only**. Trimming waits is
  explicitly allowed; splicing takes is an integrity failure.
- Never cut between typing the URL and the findings appearing.
- Say the harness and model out loud. It is a scored disclosure, and a silent
  one is a mismatch risk against the manifest.

---

## 5. Pre-submission check

```bash
python3 round4/verify_replay.py round4/REPLAY_<TeamName>.txt
```

Parses the manifest, checks every mandatory field is present and filled, and
executes the fallback path end to end against the declared URLs, asserting the
report lands where `EXPECTED_OUTPUT` says and satisfies the Round 3 schema
floor. If that script passes, a judge following the manifest cannot be
`ran-blocked`.

Final list:

- [ ] `sha256sum submission.zip` matches the file uploaded for Round 3
- [ ] `REPLAY_<TeamName>.txt` renamed, every `<<FILL>>` replaced
- [ ] `verify_replay.py` passes
- [ ] Manifest URL, harness and model match what the video shows and says
- [ ] Video ≤ 5:00, Part 1 ≤ 3:00, Part 2 ≤ 2:00
- [ ] Marketplace unchanged since Round 3 — `git diff` against the submitted tag
