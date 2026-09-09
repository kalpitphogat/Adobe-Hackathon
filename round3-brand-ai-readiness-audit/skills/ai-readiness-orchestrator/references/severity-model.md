# Severity and confidence

## Severity: what the finding costs if true

| severity | meaning |
|---|---|
| `critical` | The page or site is invisible to the system in question. A crawler refused entry, a page served empty, a noindex on content. Nothing downstream can compensate. |
| `high` | A specific, load-bearing capability is lost. The fact cannot be extracted, the visitor cannot orient, the markup misinforms. |
| `medium` | A real defect that measurably weakens the page without disabling it. |
| `low` | Worth doing, would not change an outcome on its own. |
| `info` | An observation, deliberately not a defect. Reported so a choice is visible. |

`info` is not a weaker `low`. It is a different kind of statement. A site that
blocks GPTBot has made a licensing decision, and reporting it as a defect would
be wrong, not merely over-severe.

## Confidence: how sure we are it is true

| confidence | meaning |
|---|---|
| `confirmed` | Directly observed by a deterministic check. The evidence string quotes what was seen. |
| `likely` | Inferred from two or more signals, or observed through a degraded capability. |
| `hypothesis` | Model or heuristic judgement. Flagged for human review. |

**No finding is ever emitted without a confidence.** The orchestrator rejects a
finding that lacks one, records the rejection in `limitations[]`, and does not
silently drop it.

### Confidence ceilings

Two checks can never reach `confirmed`, and the ceiling is enforced rather than
left to discipline:

- `trust.entity.no_external_corroboration` — absence of corroboration cannot be
  proven from inside the site being corroborated. Capped at `likely`, dropping
  to `hypothesis` without the optional Wikidata cross-check.
- `read.render.empty_spa_shell` in CORE-only mode — without a renderer we can
  see the shell signature but cannot measure what the visitor would have seen.
  Capped at `likely`, and severity capped at `high`.

## How the two interact

Severity answers "how bad if true". Confidence answers "how sure". They are
independent, and collapsing them into one number would hide the distinction that
matters most to a reader deciding what to act on.

The gate cascade may **lower** either. It never raises either. A downstream
finding blocked by an upstream failure keeps its confidence unless the blocked
path is what produced the evidence, in which case confidence drops one notch
too.

## Degradation, not silence

When a dependency is missing, the affected check does not quietly pass. It
either lowers its confidence and says why, or reports itself as *not assessed*
in `limitations[]`. A clean report and a report that could not look are
different things, and the reader is entitled to know which one they have.
