# Video Part 2: Live trial run (hard cap 2:00 after trimming)

**Rubric (35 points):** *"On an unseen URL, the live agent run surfaces real, evidence-backed
findings — few misses, few false positives."*
**Integrity gate:** one real, continuous run. Trimming idle waits is allowed; splicing is not.
The URL typed on camera, the model and the harness must match `REPLAY_IT_Professionals.txt`.

On-camera URL: **https://docs.pytest.org/**. It has never been audited by our engine; it was
only pre-screened for robots.txt and homepage links with `tools/prescreen.py`.
**Do not run the audit on it before recording.** Every run after the first is a "seen" site.

---

## A. Before recording (off camera, ~10 min)

1. **Fresh folder, exactly as REPLAY step 1** (Windows PowerShell):
   ```powershell
   cd C:\Users\kalpi\Kalpit_round_4
   Remove-Item -Recurse -Force demo-live -ErrorAction SilentlyContinue
   mkdir demo-live; cd demo-live
   Expand-Archive ..\round3-frozen\submission.zip .
   ..\.venv\Scripts\Activate.ps1
   python --version            # must print Python 3.11.15
   ```
   `demo-live/` is a new unzip, so there is no leftover `audit-output/`. It's git-ignored.
2. **Integrity:** `(Get-FileHash ..\round3-frozen\submission.zip).Hash` must be
   `1C872C598DCAC741C712CBF9E671F024881A9BBA251E2B4DA66995F81B6CF8DCF`.
3. **Network:** open https://docs.pytest.org/ once in a browser to confirm it's up.
   (A browser visit isn't an audit run.)
4. **Screen:** Windows Terminal maximised, font size 16+, dark theme. Close notifications
   (Focus Assist on). Have VS Code open on `demo-live/` in a second window for step D.
5. **Recorder:** OBS (or Xbox Game Bar, `Win+Alt+R`), full screen, microphone on. **Keep the
   raw, untrimmed file**: it's your proof the run was continuous if anyone asks.
6. **Clipboard:** copy the prompt from `REPLAY_IT_Professionals.txt` step 2, **without the
   final `<URL>`**, i.e. ending in `URL: ` (with the trailing space).
   You'll type the URL by hand on camera.

---

## B. The run (what's on screen, what you say)

Times are **after trimming**. The raw recording will be ~3–5 min; the agent's thinking and the
engine's crawl are the parts you cut.

| time | on screen | you say |
|---|---|---|
| 0:00 | Terminal in `demo-live/`. Type `claude --version` → `2.1.281 (Claude Code)`. | "Part two, live. The harness is Claude Code 2.1.281…" |
| 0:05 | Type `claude --model claude-opus-5-5 --allowedTools "Bash(python:*)" "Read"`. Once it opens, type `/model` so the model is visible, then Esc. | "…driving Claude Opus 5.5. It starts inside the unzipped Round 3 submission, the same zip, hash unchanged." |
| 0:15 | Paste the prompt, **type** `https://docs.pytest.org/` at the end, press Enter. | "I paste the prompt from our REPLAY file and type a site our audit has never seen." |
| 0:25 | Agent reads `skills/ai-readiness-orchestrator/SKILL.md`, then runs `python skills/ai-readiness-orchestrator/scripts/orchestrate.py https://docs.pytest.org/ --out ./audit-output`. **Pause on this command for 2 s.** | "Wiring: it reads our entrypoint SKILL.md and calls our orchestrator script. No demo code, no hardcoded results." |
| — | *(trim the crawl wait; put a small on-screen caption "⏩ crawl, ~60 s trimmed")* | |
| 0:35 | Orchestrator finishes, agent reads `audit-output/audit-report.json`, prints status + counts. | "The collector crawled the site once, our six audit skills ran over it, and here's the status and the counts by severity." |
| 0:45 | Agent's **ICE-sorted table** (top 10). | "Here are the fixes sorted by ICE: impact, confidence and ease. This is the order to work in." |
| 1:00 | Agent's walkthrough of the first three findings. | Pick the drill-in finding (section C) and say its title. |
| 1:10 | **Drill-in (section D)** in the VS Code window. | See section D. |
| 1:40 | Agent's **evidence check** section. | "Finally, the agent re-fetches the raw HTML itself and says whether each finding holds up. The report stays as the engine wrote it." |
| 1:55 | — | "Same steps, same URL, in REPLAY_IT_Professionals.txt." |

**Wording rule:** say only what's on screen. If the report says `partial`, say partial. Don't
claim a number of checks or pages the output doesn't show.

---

## C. Which finding to drill into (decide live, in this order)

1. **`extract.sd.absent_on_eligible_page` ("… carry no structured data at all")**, the first
   choice. It was confirmed on 10 of 10 pages checked independently, and comes with a paste-ready JSON-LD patch.
2. **`read.render.raw_text_gap` ("Most of this page's text only exists after JavaScript runs")**
   if it fires. It compares word counts from the raw HTML with the Chromium-rendered page.
3. Any other **`confirmed`** finding whose evidence names a URL and a count you can check.

**Never drill into:**
- `read.render.nav_links_js_only` ("internal link graph only exists after JavaScript runs"): an
  engine bug; it counts off-site links on the rendered side (`NOTES.md` §8).
- `act.orient.no_value_proposition`, `act.cta.absent_for_page_type`: `likely`, and misfire often.
- `trust.integrity.prompt_injection` on a page that merely discusses AI.

---

## D. The drill-in (~30 s)

In VS Code (`demo-live/`), open `audit-output/audit-report.json`, `Ctrl+F` the finding's
`check_id`, and point at four fields in turn:

| field | say |
|---|---|
| `evidence` | "What was observed, with the URLs: these pages carry no JSON-LD, microdata or RDFa." |
| `severity` / `confidence` | "High, because the fact can't be extracted in typed form. Confirmed: a deterministic check saw it." |
| `suggested_action.mechanism` | "Why the fix works: typed data can be extracted without guessing from prose." |
| `suggested_action.patch` and `ice` | "The paste-ready patch. Any value we couldn't read from the site says `__FILL_IN__`, not a guess. ICE is the priority score from the table." |

Then show the proof in 5 s: in the terminal, the agent's evidence-check line for this finding.
If you have time, run the finding's own `verification` command (it's in the JSON). On
Windows use the python form rather than `grep`:
```powershell
python -c "import urllib.request as u;print(u.urlopen('https://docs.pytest.org/en/stable/').read().decode().count('application/ld+json'))"
```
(Use the URL named in the evidence; `0` = the finding holds.)

---

## E. If something goes wrong

| what happens | do this |
|---|---|
| The agent's evidence check says a finding is **not supported** (likely for `nav_links_js_only`) | **Keep it in.** Say: "The evidence check disagrees here, so we'd verify before acting. The report stays exactly as the engine wrote it." That's an honest, strong moment. Don't drill into that finding. |
| Claude Code asks permission for a command | Approve it on camera ("yes"). It's part of the real run; trim the pause. |
| Run exits with `no evidence bundle was produced` | You aren't in the marketplace root. Stop, `cd` into `demo-live`, and **start a new take on the backup URL** (below). |
| Run takes past 5 min / crashes on a crawl delay | New take on the backup URL; REPLAY troubleshooting mentions `--time-budget 600`. |
| Any retake | pytest is now "seen". Use **https://www.sphinx-doc.org/** (pre-screened, never audited), and **change `TEST_SITE_URLS` and step 2 of the REPLAY file to match**. Never splice two takes. |
| Output is too long for 2:00 | Scroll faster in the edit; trim the agent's thinking. Don't cut the URL entry, the command, the ICE table or the drill-in. |

---

## F. After recording

1. Watch the trimmed video once against the REPLAY file: harness `Claude Code v2.1.281`, model
   `Claude Opus 5.5`, URL `https://docs.pytest.org/` (or the backup, if you switched). All three must match.
2. Copy `demo-live/audit-output/` to `recorded-run/` in this repo and commit it, along with the
   raw recording's filename, length and SHA-256 in `recorded-run/README.md` (the video file
   itself stays out of git).
3. Total video (Part 1 + Part 2) ≤ 5:00. Part 1 ≤ 3:00, Part 2 ≤ 2:00, each on its own.
