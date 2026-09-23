# Round 4 video script

**Hard cap 5:00.** Part 1 ≤ 3:00 (methodology), Part 2 ≤ 2:00 (trial run).
Going over is a cap breach, not a deduction — rehearse against a timer.

The rubric line that governs Part 1 is *"traceable to the submitted code"*, and
its teeth are: **"Narration that cannot be traced to the submitted code earns no
credit — a claim is only as real as the code behind it."** So every claim below
carries the file you put on screen while saying it. If you cut a claim, cut its
anchor with it; never keep a claim whose file you are not showing.

Paths are relative to the marketplace root (the unzipped Round 3 submission).

---

## Part 1 — Thought process (≤ 3:00)

Four beats. The budget is tight; the fourth is the one to cut if you overrun,
not the first.

### Beat 1 · The one idea — ordering (0:00–0:50)

> "Three things must succeed **in order** for a page to be visible to a machine:
> the crawler is let in, the page can be read, the fact can be picked out. Most
> auditors ignore the ordering and fire forty findings at any URL. Point one at a
> site whose CDN refuses AI crawlers and it reports fifteen criticals — fourteen
> of which are real defects that currently change nothing, because nothing is
> reaching the page to be affected by them.
>
> We encode the ordering as a gate cascade. Every finding carries a stage —
> reach, read, extract, trust, act — and when an upstream stage fails,
> downstream findings are still recorded but capped and tagged with the id of
> the finding blocking them. You get the root cause first."

**On screen, in this order:**
| show | why |
|---|---|
| `skills/ai-readiness-orchestrator/references/gate-rules.md` | the rule, written down |
| `skills/ai-readiness-orchestrator/scripts/gate_model.py` → `apply_cascade` | the rule, in code |
| `tests/golden/site_b.audit-report.json` → a finding with `"blocked_by": "F-001"` | the rule, in output |

Then the payoff, which is the non-obvious half:

> "Engagement is **not** causally downstream of reach — a visitor arriving from
> an ad does not care whether a crawler was let in. But it **is** evidentially
> downstream of read: if the page served an empty JavaScript shell and we never
> captured a rendered DOM, we never observed what the visitor sees. Those
> findings are not *probably wrong*, they are *unevidenced*. So they are
> suppressed entirely, not downgraded. Capping asserts a weaker claim.
> Suppression asserts none, which is what we actually have."

Show `gate-rules.md` → Rule 0b, and `tests/test_gate_cascade.py` (215 assertions).

### Beat 2 · Signal discovery — the check nobody else has (0:50–1:40)

Lead with the strongest non-obvious finding, not with a list.

> "The highest-value check in the marketplace is one you cannot see from the
> outside. A CDN or WAF rule that returns 403 to `OAI-SearchBot`,
> `PerplexityBot` or `Claude-SearchBot` removes a brand from those assistants
> entirely — and leaves **no trace in robots.txt and nothing visible to anyone
> browsing the site**. Bot-protection defaults do this routinely, to sites whose
> owners have no idea."

Show `skills/crawl-access-audit/scripts/check_edge_reach.py`.

Then the discipline that stops it becoming a false positive:

> "The naive version of this check fires on any blocked bot and is wrong most of
> the time. Blocking `GPTBot` is a **content-licensing decision**, not a defect —
> it is a training crawler, and a publisher who blocks it meant to. Blocking
> `OAI-SearchBot` is a defect — it fetches at answer time to cite you. So every
> crawler is classified retrieval / training-only / dual-purpose, and only the
> retrieval class produces a real finding."

Show `skills/crawl-access-audit/references/bot-taxonomy.md` and
`references/ai-bots.json` (note the dated snapshot + upstream commit — that's
why the evidence string can cite its own provenance).

### Beat 3 · Severity and suppression — computed, never hardcoded (1:40–2:25)

> "Severity is computed from the evidence, not written next to the check. The
> same defect on the homepage and on one deep page are not the same problem, so
> the rule reads the page role and the share of the site affected."

Show `skills/ai-readiness-orchestrator/references/severity-model.md` and
`scripts/severity.py` → `score_finding`.

Then the part that wins the false-positive half of the rubric:

> "Not firing is a feature. There are **64 documented suppression rules**, each
> with a test, and we don't hide them — the report tells you what we deliberately
> did not raise, in `summary.suppressed_by_rule`. A cookie banner is not an
> interstitial. Muted autoplay is not a blocker. An XML sitemap is not thin
> content. A free tool has no price to be missing."

Show `skills/ai-readiness-orchestrator/references/suppression-rules.md`,
`tests/test_suppression.py`, and a report's `suppressed_by_rule` block.

Land it on the control:

> "`site_f` is a well-built site we wrote specifically to try to make the auditor
> fire. It produces **zero findings**. `site_a` produces zero high or critical.
> Both are asserted in the build."

### Beat 4 · Fixes — mechanism-sound and ordered (2:25–3:00)

> "A finding that tells you something is wrong is half the work. Every suggested
> action carries the mechanism — *why* the fix works — a paste-ready patch, the
> command to verify it landed, and an ICE score that decides the order."

Show one finding's `suggested_action` in full, then `fix_patches/`.

> "Ranking is severity, then ICE, then stage, then check id — fully ordered, so
> two runs on the same input produce the same list in the same order."

Close on generalisation, because it is what Round 3 said it would be judged on:

> "No check anywhere hardcodes a threshold. Every one asks the site-profile
> classifier what kind of site this is, and gets the thresholds for that
> archetype. That is the component that turns *a site nobody has seen* into
> *known thresholds*."

Show `skills/site-profile-classifier/references/threshold-profiles.json`.

---

## Part 2 — Trial run (≤ 2:00)

One real, continuous run. Trimming idle wait is allowed and expected; splicing
is an integrity failure. Record the whole thing unbroken, then cut only dead
time — and **never cut between typing the URL and the findings appearing.**

### Shot list

The shots below use `round4/demo_cli.py`, which renders the engine's own report
and contains no checks of its own — see [README.md](README.md). Driving the
entrypoint directly works identically and is the documented fallback.

**0:00–0:15 — Disclose, on camera.** Run `demo_cli.py doctor` so the engine
fingerprint is on screen, then say it out loud; it is a scored field:

> "This is `<harness + version>` driving `<model + version/date>`. The session is
> reading `skills/ai-readiness-orchestrator/SKILL.md` out of the Round 3
> submission and running its entrypoint — nothing here is a hardcoded demo."

Have the unzipped submission visible in the shell. `ls` it.

**0:15–0:35 — Type the URL.** On camera, into the agent prompt, using the
verbatim prompt from `REPLAY_<TeamName>.txt`. Do not paste from a file the
viewer cannot see.

**0:35–1:00 — Let the agent work.** The viewer needs to see the agent *choose*
the entrypoint and shell out to it. Keep the line where
`orchestrate.py ... --out ./audit-output` appears. Trim the fetch wait.

**1:00–1:40 — Drill into one finding.** This is the scored part. Pick a finding
whose evidence is *visible*, and show the evidence, not just the title:

| if the site has… | show |
|---|---|
| a JS-rendered page | the raw-HTML vs rendered-DOM character counts in the evidence string |
| missing/invalid JSON-LD | the page source with no `application/ld+json`, next to the finding |
| disagreeing dates | schema date vs visible date vs `Last-Modified`, all three in the evidence |
| a blocked retrieval crawler | the `robots.txt` line number the evidence cites |

Say the severity **and why it is that severity** — tie it back to Beat 3. Then
show the `suggested_action`: mechanism, patch, verification.

**1:40–2:00 — Prioritisation + honesty.** The ranked list from `audit` is
already on screen; scroll back to it, or `show` the next two findings:

> "Ranked by what to fix first. And this block is what the audit could **not**
> assess — `limitations`. An unfetched page is not a pass, and we say so."

That last sentence is worth real marks under *few false positives*: it shows the
tool distinguishes *checked and clean* from *never looked*.

---

## Rehearsal checklist

- [ ] Total ≤ 5:00, Part 1 ≤ 3:00, Part 2 ≤ 2:00 — timed, not estimated
- [ ] Harness **and** model stated out loud, matching `REPLAY_<TeamName>.txt`
- [ ] Every Part 1 claim has its file visible on screen as you say it
- [ ] The URL is typed on camera and the run to findings is uncut
- [ ] The demoed engine is byte-identical to the submitted zip (see `RUNBOOK.md`)
- [ ] The URL in the video is one of `TEST_SITE_URLS` in the manifest
- [ ] Terminal font large enough to read at 720p — judges may not full-screen
