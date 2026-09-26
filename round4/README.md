# Round 4: Prototype Showcase (live agent demo)

**Team:** Lakshya, Tanmay, Kalpit · **Engine:** the Round 3 marketplace, unchanged

Round 4 asks us to show the Round 3 marketplace working live and to prove the run is
reproducible. It is a demonstration round, not a rebuild: **nothing inside
`brand-ai-readiness-audit/` or `submission.zip` has changed since Round 3**, and
`python round4/verify_round4.py` proves it byte for byte.

| we submit | what it is |
|---|---|
| the video (≤ 5:00) | Part 1 methodology (≤ 3:00) and Part 2 live run (≤ 2:00). Script and run sheet in [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md). |
| [`REPLAY_LakshyaTanmayKalpit.txt`](../REPLAY_LakshyaTanmayKalpit.txt) | the reproduction manifest, with the six fixed fields from brief §5 |
| *(not resubmitted)* | `submission.zip`, the Round 3 package the judges already hold. SHA-256 `1c872c598dcac741c712cbf9e671f024881a9ba251e2b4da66995f81b6cf8dcf` |

---

## Replay in one minute

Everything needed is the Round 3 `submission.zip` plus the disclosed harness. This repo
is optional.

```bash
cd <folder containing submission.zip>
claude --plugin-dir ./submission.zip --model claude-opus-5-5 \
    --allowedTools "Bash(python:*)" "Bash(python3:*)" "Bash(curl:*)" "Read"
# then paste the prompt from round4/PROMPT.txt (also verbatim in REPLAY step 3)
```

The agent invokes the entrypoint skill `ai-readiness-orchestrator`, which runs the Round 3
`orchestrate.py`. The report lands in `./audit-output/www.npr.org/audit-report.json`,
with `report.md`, `fix_patches/` and `evidence/` beside it. The audit takes ~40 s and the
whole session ~2 min.

**For a URL of your choice**, swap the URL and hostname in the prompt. **Without Claude
Code at all**, the engine runs alone and produces the same findings, because the agent only
invokes it and reads the report:

```bash
python -m zipfile -e submission.zip round3 && cd round3
python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://www.npr.org/ --out ../audit-output/www.npr.org
```

| disclosed | value |
|---|---|
| LLM | Claude Opus 5.5, model id `claude-opus-5-5` |
| harness | Claude Code **2.1.283** (`npm install -g @anthropic-ai/claude-code@2.1.283`) |
| engine runtime | Python 3.9+, standard library only. Recorded on Python 3.11.9, no Playwright. |
| wiring | `--plugin-dir ./submission.zip`: Claude Code loads the Round 3 package itself as a session plugin and exposes its nine skills as `submission:<skill>` |

---

## How we prove the demo runs the Round 3 engine

`python round4/verify_round4.py` (offline, seconds) checks:

| check | what it proves |
|---|---|
| `freeze.zip_sha256`, `freeze.zip_members` | `submission.zip` and all 155 files inside it are byte-identical to the Round 3 commit `ede3a6b` (2026-09-13, branch `final-submission`) |
| `freeze.folder_matches_zip` | the repo folder holds exactly those 155 files and nothing else (plus its `.gitattributes`) |
| `freeze.git_tree`, `freeze.no_uncommitted_edits` | git's own tree hash for the engine folder equals Round 3's, with no local edits |
| `replay.*` | the manifest has all six fields, full URLs, numbered steps, the pinned model, the zip hash, and exactly the prompt in `PROMPT.txt` |
| `script.anchors_resolve`, `script.claims_land_on_code` | every `path:line` narrated in Part 1 exists in the frozen engine, and 27 key claims land on the exact line of code they describe |

Add `--goldens` to also re-run the six Round 3 fixture audits offline. Their findings match
the checked-in goldens exactly, and every `report.md` is byte-identical.

[`ENGINE_FREEZE.json`](ENGINE_FREEZE.json) is generated **from git**, not from the working
tree (`--make-freeze`). Regenerating it from the Round 3 commit reproduces it byte for
byte, so it cannot be edited to match a changed engine.

Every archived run is also **re-derived**. `archive_run.py` re-runs the frozen engine on
the run's captured evidence bundle with `--bundle`, which makes no network calls, and
confirms it reproduces the report exactly. The findings shown on camera therefore follow
mechanically from what the crawl saw. See `rehearsal/www.npr.org/REDERIVATION.txt`.

---

## The demo site, and what a correct replay shows

**`https://www.npr.org/`** was chosen after running the frozen engine on 12 unseen sites
(table below). NPR has the most verifiable headline finding and the cleanest set of
uncapped findings, and one run shows the whole design.

- **F-001 critical, confirmed.** robots.txt disallows the answer-time retrieval crawlers
  ChatGPT-User, OAI-SearchBot, Claude-SearchBot, Claude-User and PerplexityBot. The
  evidence cites robots.txt line numbers (47, 54, 74, 77, 98 when we ran it), so a
  single `curl` corroborates it. The rehearsal agent did exactly that, and its live copy
  was byte-identical to the one the engine captured.
- **Taxonomy in one report.** GPTBot, CCBot, ClaudeBot and the other training-only
  crawlers are **info**, "recorded as an observation, not a defect". Google-Extended,
  Applebot-Extended and FacebookBot are **medium**, a contested trade-off.
- **Gate cascade.** Most discoverability findings are capped at medium and tagged
  `blocked_by: F-001` ("moot until F-001 is fixed"). Engagement findings are never capped
  by a crawler block (Rule 0).

**Expect the counts to move.** npr.org's homepage links different stories every hour, so
the 25 sampled pages differ between runs. Two of our runs 17 minutes apart had 35 and 48
findings. The top finding, the taxonomy and the cascade were identical in both.
`act.orient.no_value_proposition` fired on the homepage in one of them, on copy that
lacked the check's "for <audience>" pattern; the engine marks it `likely`, not
`confirmed`. The engine itself is deterministic for a fixed evidence bundle. To compare a
replay with ours:

```bash
python round4/verify_round4.py --compare round4/recorded-run/www.npr.org/audit-report.json ./audit-output/www.npr.org/audit-report.json
```

The script prints `SAME SUBSTANCE` when the top finding and every critical/high check agree.

### Every live site we ran the frozen engine on

All zero-install runs (no Playwright), default flags, 26 September 2026. None of these
sites appears anywhere in the Round 3 code or fixtures. `partial` means the render-stage
checks were declared *not assessed* because no headless browser was installed; the
report says so rather than passing them.

| site | archetype (classifier) | pages | time | C | H | M | L | I | capped | F-001 |
|---|---|---|---|---|---|---|---|---|---|---|
| www.npr.org | publisher | 25 | 37 s | 1 | 0 | 30 | 3 | 1 | 27 | `reach.robots.ai_search_bot_blocked` |
| www.npr.org (agent rehearsal) | publisher | 25 | 38 s | 1 | 1 | 41 | 4 | 1 | 38 | `reach.robots.ai_search_bot_blocked` |
| www.seriouseats.com | publisher | 25 | 32 s | 1 | 0 | 36 | 9 | 1 | 34 | `reach.robots.ai_search_bot_blocked` |
| www.theverge.com | publisher | 25 | 29 s | 1 | 0 | 44 | 3 | 1 | 39 | `reach.robots.ai_search_bot_blocked` |
| www.bonappetit.com | other | 24 | 72 s | 1 | 0 | 31 | 4 | 1 | 17 | `reach.robots.ai_search_bot_blocked` |
| www.investopedia.com | publisher | 25 | 40 s | 1 | 1 | 60 | 5 | 1 | 50 | `reach.robots.ai_search_bot_blocked` |
| www.thespruce.com | publisher | 25 | 31 s | 1 | 0 | 25 | 15 | 1 | 14 | `reach.robots.ai_search_bot_blocked` |
| www.scientificamerican.com | publisher | 25 | 29 s | 1 | 5 | 29 | 4 | 1 | 16 | `reach.robots.ai_search_bot_blocked` |
| www.economist.com | other | 0 | 2 s | 1 | 0 | 1 | 0 | 1 | 0 | `reach.robots.ai_search_bot_blocked` (`no_content_available`: robots.txt shuts our crawler out too, so only robots findings are possible) |
| www.sweetgreen.com | local-business | 18 | 46 s | 1 | 3 | 23 | 9 | 0 | 0 | `reach.index.noindex_on_content` |
| www.python.org | publisher | 25 | 27 s | 0 | 3 | 26 | 14 | 0 | 0 | `extract.ans.fact_coverage_gap` |
| plausible.io | publisher | 25 | 24 s | 0 | 2 | 34 | 4 | 0 | 0 | `extract.ans.fact_coverage_gap` |
| www.joespizzanyc.com | other | 6 | 12 s | 0 | 3 | 16 | 0 | 0 | 0 | `act.orient.no_value_proposition` |

What held up well: every robots.txt verdict, each with its line numbers, and the
taxonomy split, on all eight sites with a block. The JSON-LD parse failure on
`sweetgreen.com/locations` was reported with the line and column of the invalid control
character. Runtimes were 2–72 s against the 300 s budget.

Where it is noisy, stated plainly because judges will see it:
- `trust.entity.nap_inconsistent` reads a multi-location chain's store list as
  inconsistent addresses (sweetgreen, joespizzanyc).
- `act.orient.no_value_proposition` fires on news homepages.
- `act.context.assumes_prior_context` fires on legal boilerplate ("as described above").
- The classifier calls plausible.io, a SaaS product with a large blog, a publisher.

These are Round 3 behaviours. The engine is frozen for Round 4, so they are documented
here and not patched.

---

## Platform notes found while preparing Round 4

None of these change what the engine reports. They're recorded so a replay doesn't trip on them.

- **Relative `--out` only works from the marketplace root.** `orchestrate.py` starts its
  sub-skills with `cwd` set to the marketplace root (line 74), so from anywhere else a
  relative `--out` makes the collector write to one place while the orchestrator looks
  in another ("no evidence bundle"). The Round 3 docs always `cd` into the root first, so
  it never surfaced. The prompt passes an absolute `"$PWD/audit-output/..."`, and the
  rehearsal followed it first time.
- **Golden byte-comparison embeds the Python patch version.** `tests/run_offline.py`
  compares whole reports, including `generator.tool_versions.python` (the goldens say
  3.11.15). On any other interpreter that step reports drift even though every finding is
  identical, and that includes the Round 3 CI matrix (3.9, 3.12). `verify_round4.py
  --goldens` compares everything except that one metadata field and passes.
- **Don't rebuild `submission.zip` on Windows.** `package_submission.py` (without `--check`)
  rewrites the zip. Python's `zipfile` stamps every header with the host OS
  (`create_system` 0 on Windows, 3 on Linux), so a Windows rebuild of identical sources
  differs from the submitted Linux-built artifact. The contents, modes and timestamps
  match; only that byte differs. `verify_round4.py` reports it as `freeze.zip_rebuilt`,
  and `git checkout -- submission.zip` restores the original.
- **Windows resolver.** One of 2,223 Round 3 assertions (`tests/test_ssrf.py` S1, the
  short-form loopback `http://127.1/`) fails on Windows, because Windows' `getaddrinfo`
  refuses to resolve `127.1` at all. No connection is possible either way; on Linux and
  macOS it resolves and the refusal fires as designed.

---

## Files

| path | purpose |
|---|---|
| `../REPLAY_LakshyaTanmayKalpit.txt` | the reproduction manifest (submitted alongside the video) |
| `PROMPT.txt` | the exact prompt, byte-identical to REPLAY step 3 |
| `VIDEO_SCRIPT.md` | Part 1 narration with a code anchor per claim, and the Part 2 run sheet |
| `verify_round4.py` | engine freeze, manifest lint, narration anchors, goldens, run comparison |
| `ENGINE_FREEZE.json` | SHA-256 of `submission.zip` and all 155 files in it, from the Round 3 commit |
| `archive_run.py` | archives a run: report, robots.txt, evidence hashes, offline re-derivation |
| `rehearsal/www.npr.org/` | a pre-recording rehearsal of the exact REPLAY steps (headless), with the full agent transcript in `agent-session.md`. Not the video take. |
| `recorded-run/` | the video take's archived output, added after recording |

Nothing here is imported by the marketplace or writes inside it. It is harness-side
tooling that runs beside the engine and reads its output.
