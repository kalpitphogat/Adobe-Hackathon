---
name: site-profile-classifier
description: Detect what kind of site and page this is, then select the threshold profile every other audit skill scores against. Classifies site archetype - documentation, developer platform, SaaS marketing, e-commerce, publisher, local business, or other - and assigns a type and confidence to every crawled page from observed signals such as URL shape, declared structured-data types, content length and commerce markers, never from a list of known sites. Use before running any audit check, so thresholds match the kind of site being audited rather than applying one generic standard to every page. This is where generalisation to unseen sites lives.
license: MIT
compatibility: Python 3.9+ standard library only. Reads an evidence bundle; performs no network I/O.
allowed-tools: Bash(python:*) Read
---

# site-profile-classifier

**One question: what kind of site and page is this?**

No check in this marketplace hardcodes a number. Each asks this profile for its
thresholds, and the profile is selected from what the site actually looks like.
That is the whole generalisation strategy: the audit is graded on sites nobody
has seen, so nothing may depend on recognising a specific one.

## When to use

After collection, before any audit skill.

## Inputs

```bash
python scripts/profile.py --bundle ./evidence
```

## Procedure

1. **Type each page.** Order matters, and the obvious order is wrong.
   - **Unambiguous path names first** (`/`, `/contact`, `/pricing`, `/login`).
     A SaaS site that marks up `/pricing` as `schema.org/Product` with an Offer
     is doing something correct and idiomatic; typing it as a product page would
     then apply e-commerce thresholds to a pricing page and misfire the
     cost-signal and thin-content checks. When path and schema disagree, the
     classifier records both in its signals rather than silently picking one.
   - **Then declared schema types**, because the site said so itself.
   - **Then softer URL patterns**, then content shape.
2. **Score archetypes** from weighted site-wide signals.
3. **Apply necessary conditions.** Several archetypes need their *defining*
   signal, not an incidental one. Each of these was added after a
   misclassification on a real fixture:
   - **e-commerce** needs a way to buy: a cart path, add-to-cart language, or
     many product URLs. Product schema plus a price is how SaaS marks up a plan.
   - **local business** needs opening hours or LocalBusiness schema. A postal
     address and phone number in the footer are universal and identify nothing.
   - **publisher** needs articles at volume. One bylined post is a company blog,
     which nearly every site has.
   - **docs** needs documentation to be a real share of the site, not one page.
4. **Report confidence as the margin** over the runner-up, so a site that looks
   equally like two archetypes is reported as uncertain rather than arbitrarily
   typed. Below a floor the archetype is `other`, and every check that depends
   on archetype lowers its own confidence accordingly.
5. **Merge thresholds**: archetype overrides layered onto the defaults in
   `references/threshold-profiles.json`.

## Output

```json
{
  "archetype": "saas-marketing", "archetype_confidence": 0.81,
  "archetype_signals": ["pricing_page (+2.0)", "trial_cta (+2.0)"],
  "pages": { "https://…/pricing": { "page_type": "pricing", "confidence": 0.9,
                                     "signals": ["…"] } },
  "page_type_counts": { "home": 1, "pricing": 1 },
  "thresholds": { "thin_content_words": {…}, "form_fields_max": {…} },
  "notes": []
}
```

Exit 0 ran, 3 precondition unmet, 1 internal error.

## Checks

This skill emits **no findings**. It is infrastructure: it produces the profile
the six audit skills score against. Counting it among the check-bearing skills
would misrepresent what it does.

## Reference material

- `references/page-types.md` — the signal-to-type rules and why each exists.
- `references/threshold-profiles.json` — every threshold, with the archetype
  overrides and a stated reason for each override.

## Guardrails

Read-only, no network. Classification uses observed signals only. There is no
list of known sites anywhere in this skill, because a lookup table would score
well on the sites we happened to choose and badly on the ones we did not.
