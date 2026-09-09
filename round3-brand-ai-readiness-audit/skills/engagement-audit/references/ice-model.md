# ICE scoring

ICE ranks suggested actions. It is **Impact, Confidence, Ease**, each on 1–10,
reported as the mean rounded to one decimal, so the score sits on the same 0–10
scale as its components.

## Confidence is not a second judgement

This is the design decision worth stating plainly.

`confidence` is already a first-class field on every finding, with defined
semantics, and the gate cascade uses it. If ICE also asked for a free-floating
confidence estimate, the same property would be counted twice and the score
would stop being reproducible.

So ICE's C is a **deterministic map from the finding's own confidence enum**:

| finding confidence | ICE C |
|---|---|
| `confirmed` | 9 |
| `likely` | 6 |
| `hypothesis` | 3 |

The same finding always scores the same. No judgement is exercised at scoring
time.

## Impact derives from post-gate severity

| severity | ICE I |
|---|---|
| critical | 10 |
| high | 8 |
| medium | 5 |
| low | 3 |
| info | 1 |

**Post-gate**, deliberately. A finding capped by the cascade also drops down the
ranking. That is the point: a defect that is moot until something upstream is
fixed should not outrank the thing blocking it.

## Ease derives from effort

| effort | ICE E |
|---|---|
| low | 9 |
| medium | 5 |
| high | 2 |

Effort is set by the check that raised the finding, from what the fix actually
requires: editing a text file is low, changing a template is medium, changing a
rendering architecture is high.

## Sort order

Findings sort by severity descending, then ICE descending, then stage order,
then `check_id`, then first affected URL.

The last two exist to make the ordering **total**. Two findings that tie on
every meaningful axis still have exactly one possible order, which is what makes
the report byte-identical across runs.

## What ICE is not

It is not a prediction of business outcome. It is a consistent way of ordering a
list so the reader starts with the thing that is most certainly wrong, most
harmful, and cheapest to fix. Anyone who disagrees with a weighting can read the
components, which are published on every finding as `ice_components`.

This is our convention, not an industry constant. Other formulations multiply
rather than average, which spreads scores across orders of magnitude and makes
them harder to compare at a glance. Averaging keeps every score on one legible
scale.
