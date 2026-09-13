# Page and site typing

## Why typing comes first

Almost every threshold worth applying depends on what kind of page this is. A
120-word product page is normal; a 120-word article is thin. A checkout form
with 14 fields is necessary; a newsletter form with 14 fields is friction.

So classification runs before any check, and every check asks the profile rather
than carrying a number of its own.

## Page types

`home` `product` `category` `article` `docs` `pricing` `contact` `about`
`utility` `other`

### Order of evidence, and why the obvious order is wrong

1. **Unambiguous path names first.** `/`, `/contact`, `/pricing`, `/login`,
   `/privacy`. These are statements of intent that outrank a generic schema type.
2. **Then declared schema types**, because the site said so itself.
3. **Then softer URL patterns.**
4. **Then content shape** — length, presence of a publication date, form
   dominance — at correspondingly lower confidence.

Step 1 exists because of a real misclassification. A SaaS site that marks up its
`/pricing` page as `schema.org/Product` with an `Offer` is doing something
correct and idiomatic. Letting the schema type win produced a "product" page,
which then attracted e-commerce thresholds and misfired the cost-signal and
thin-content checks. When path and schema disagree, the classifier records both
in its signals rather than silently choosing one.

## Site archetypes

`docs` `developer-platform` `saas-marketing` `e-commerce` `publisher`
`local-business` `other`

Scored from weighted site-wide signals, with **necessary conditions** for the
archetypes easiest to claim by accident. Every condition below was added after a
real misclassification during development:

| archetype | necessary signal | why |
|---|---|---|
| e-commerce | a cart path, add-to-cart language, or many product URLs | product schema plus a price is how SaaS marks up a plan |
| local-business | opening hours or LocalBusiness schema | a footer address and phone are universal and identify nothing |
| publisher | articles at volume | one bylined post is a company blog, which nearly every site has |
| docs | documentation as a real share of the site | one docs page does not make a documentation site |

## Confidence as margin

Archetype confidence is the winner's margin over the runner-up, not its absolute
score. A site that looks equally like two archetypes is reported as uncertain
rather than arbitrarily typed.

Below a floor the archetype is `other`, default thresholds apply, and every
check depending on archetype lowers its own confidence. Saying "I do not know
what kind of site this is" is a legitimate and useful output. Guessing is not.

## What is deliberately absent

There is **no list of known sites** anywhere in this skill, and no special-casing
of any domain, CMS or platform. A lookup table would score well on the sites we
happened to think of and badly on the ones we did not, and this audit is graded
on sites nobody has seen.

Every signal here is a property a site exhibits, never a name we recognise.
