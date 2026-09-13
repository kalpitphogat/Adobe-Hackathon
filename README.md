# Brand AI-Readiness Audit

**Adobe University Hackathon 2026 — Round 3 · Build the Agent Skill Marketplace**

Team: Lakshya, Tanmay, Kalpit

Point it at any website. It reports **why AI assistants don't find, cite, or
correctly describe the brand**, and **why visitors who do arrive leave without
acting** — every claim backed by evidence, every fix paste-ready and ordered by
impact. Read-only. Never touches the live site.

> **The submission is [`brand-ai-readiness-audit/`](brand-ai-readiness-audit/)** — that
> folder is the marketplace root, and `submission.zip` is exactly its contents.
> Short tour in its [README](brand-ai-readiness-audit/README.md); full design notes in [DESIGN.md](brand-ai-readiness-audit/DESIGN.md).

```bash
cd brand-ai-readiness-audit
python3 skills/ai-readiness-orchestrator/scripts/orchestrate.py https://example.com --out ./audit-output
```

Writes `audit-report.json` (fixed schema) and `report.md` (written for someone
who is not an engineer).

---

## The one idea

The Round-2 appendix says three things must succeed **in order** for a page to
be visible to a machine: the crawler has to be let in, it has to be able to read
the page, and it has to be able to pick out the fact.

**In order** is the whole design.

A flat checklist ignores that and fires forty findings at any URL. Point it at a
site whose CDN refuses AI crawlers and it reports fifteen criticals, fourteen of
which are real defects that currently change nothing — because nothing is
reaching the page to be affected by them.

This marketplace encodes the ordering as a **gate cascade**. Every finding
carries a stage — `reach`, `read`, `extract`, `trust`, `act` — and when an
upstream stage fails, downstream findings are still recorded but capped and
tagged with the id of the one finding blocking them. You get the root cause
first, and the rest in the order fixing them will actually pay off.

---

## Nine skills, one entrypoint

| skill | question it answers | stage |
|---|---|---|
| **ai-readiness-orchestrator** | What matters most, and why? | — *(entrypoint)* |
| site-evidence-collector | What does the site actually serve? | — |
| site-profile-classifier | What kind of site and page is this? | — |
| crawl-access-audit | Can an AI crawler get in? | reach |
| render-gap-audit | Can it read the page without running JavaScript? | read |
| structured-data-audit | Is the fact machine-typed? | extract |
| answerability-audit | Is the fact quotable? | extract |
| trust-freshness-audit | Would a machine believe it, and is the page honest? | trust |
| engagement-audit | Does the visitor stay and act? | act |

The two skills that emit no findings are load-bearing, not padding: the
**collector** is the only component that touches the network, so six audit
skills can never disagree about what the site served; the **classifier** is
where generalisation lives, because no check anywhere hardcodes a threshold —
every one asks the profile for the site archetype it is looking at.

The entrypoint composes by **subprocess, never by import**:

```
orchestrate.py
  → collect.py           writes the evidence bundle          (network, once)
  → profile.py           archetype + page types + thresholds
  → 6 × run.py           each reads the bundle, prints one JSON object
  → gate cascade         cap, tag blocked_by, suppress per Rule 0b
  → dedupe, score, rank  severity → ICE → stage → check_id
  → emit                 audit-report.json + report.md + fix_patches/
```

No script imports from a sibling skill, so **any skill folder can be lifted out
of the marketplace and run on its own**. A test walks the AST of every script
and fails the build on a cross-skill import, including the `sys.path` dodge.

---

## Round 3 compliance

Every row is enforced by a test, not asserted in prose.
Run `python3 package_submission.py` to check all of them at once.

| Handout requirement | Where it is enforced |
|---|---|
| Marketplace manifest listing every skill, **exactly one** entrypoint | `package_submission.py`, `tests/validate_marketplace.py` |
| Every skill folder a valid agentskills.io `SKILL.md` (name, description, license) | `tests/validate_marketplace.py` — 9/9 |
| Each skill declares its tool needs (`allowed-tools`) | `tests/validate_marketplace.py` — 9/9 |
| Manifest self-contained, no external service to resolve it | `package_submission.py` — no URLs in the manifest |
| Entrypoint composes the rest into **one** report | `skills/ai-readiness-orchestrator` |
| Report floor: `site`, `audited_at`, counts-by-severity | `references/report-schema.json`, 6 golden reports |
| Per finding: `id`, `title`, `severity`, `evidence`, `suggested_action` | `validate_finding()` rejects malformed findings at the boundary |
| Detects **both** discoverability and engagement | 66 checks — 49 discoverability, 17 engagement |
| Proactive suggestions beyond detected defects | `proactive_recommendations` in every report |
| Recommend-only; never alters a live site | `tests/test_ssrf.py` — method allowlist is `{GET, HEAD}` |
| No authenticated areas, no credentials | opener built with no cookie processor and no auth handler |
| No rate abuse | `tests/test_politeness.py` — delay, backoff, `Retry-After`, 25-page cap |
| Respects `robots.txt` | `tests/test_politeness.py` — 71 RFC 9309 assertions; `site_c` fetches zero pages |
| Skills portable / provider-neutral | `tests/validate_marketplace.py` — zero cross-skill imports |
| Runtime **< 5 minutes** | `tests/test_deadline.py` — one shared clock bounds the whole run |
| Zip ≤ 50 MB, no model weights | `package_submission.py` — 394 KB, refuses weight formats |
| `README.md` at the marketplace root | `package_submission.py` |

Two guardrails go beyond the brief: the auditor **refuses hosts that resolve
into private, loopback or link-local space**, on the seed and on every redirect
hop (`--allow-private-hosts` opts out for a site you host yourself); and
**bot-user-agent probing is opt-in**, so we never silently impersonate a named
crawler at a site we don't own.

---

## Running it

```bash
cd brand-ai-readiness-audit

# audit a site
python3 skills/ai-readiness-orchestrator/scripts/orchestrate.py https://example.com --out ./audit-output

# auditing your own site? add the highest-value check in the marketplace
python3 skills/ai-readiness-orchestrator/scripts/orchestrate.py https://your-site.com \
    --out ./audit-output --probe-bot-ua

# no network needed — audit a fixture
python3 skills/ai-readiness-orchestrator/scripts/orchestrate.py \
    --offline-root tests/fixtures/site_b --out ./audit-output
```

`--probe-bot-ua` detects whether a CDN or WAF returns 403 to AI crawlers — a
rule that removes a brand from those assistants entirely while leaving no trace
in `robots.txt` and nothing visible to anyone browsing the site. It is off by
default because sending named-crawler user-agents at a site you do not own is
not something an audit should do unless asked.

Python 3.9+, standard library only for 63 of 66 checks. Playwright is optional
and upgrades the render-stage checks; without it the audit still runs and says
what it could not see.

Full command reference: [`COMMANDS.txt`](COMMANDS.txt).

---

## Tests

```bash
cd brand-ai-readiness-audit
python3 tests/validate_marketplace.py   # 73 structure / spec / doc-drift checks
python3 tests/run_offline.py            # 6 golden reports, byte-for-byte, + determinism matrix
for t in tests/test_*.py; do python3 "$t"; done   # 2,223 assertions across 10 suites
```

Six fixture sites, six separable claims, kept apart so a change to one mechanism
cannot silently alter the proof of another — including two dedicated
false-positive controls (`site_a`: zero high or critical; `site_f`: zero
findings at all).

---

## Packaging

```bash
python3 package_submission.py           # build submission.zip and verify it
python3 package_submission.py --check   # verify the existing zip without rebuilding
```

The zip is **flat** — `marketplace.json`, `README.md` and `skills/` sit at its
root — and the build is deterministic, so rebuilding from unchanged sources
produces a byte-identical artifact.

---

## Repository layout

```
Adobe-Hackathon/
├─ README.md                    ← this file
├─ COMMANDS.txt                 ← every command, with expected output
├─ package_submission.py        ← builds + validates submission.zip
├─ submission.zip               ← the deliverable (built from the folder below)
└─ brand-ai-readiness-audit/    ← THE MARKETPLACE ROOT
   ├─ marketplace.json          ← manifest: 9 skills, 1 entrypoint
   ├─ README.md                 ← design notes, check inventory, guardrails
   ├─ ATTRIBUTIONS.md
   ├─ LICENSE                   ← MIT
   ├─ skills/                   ← 9 skill folders, each independently runnable
   └─ tests/                    ← validator, 9 suites, 6 fixture sites, goldens
```

*License: MIT, declared per skill and at the marketplace root.*
