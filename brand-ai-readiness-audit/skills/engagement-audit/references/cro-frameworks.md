# Where the engagement checks come from

Each check derives from a stated heuristic rather than a threshold someone liked
the look of. Where the basis is a body of practice rather than a single paper,
that is said plainly instead of dressed up as a citation.

## Orientation

A visitor decides whether a page is relevant to them from the first screen,
before reading properly. `act.orient.no_value_proposition` tests whether the
first 400 characters name an audience or an outcome — a phrase of the form
"for <who>", "helps <who> <do what>", or "<product> is a <category>".

The test is deliberately narrow. It does not judge quality: a page can fail it
and be excellent prose. What it cannot do is tell a stranger in one screen who
the page is for.

Page types whose job is not to pitch are exempt. An About page describes the
company, a Contact page gives contact details, a pricing page states cost. That
exemption list grew during development because the check fired on all three on a
well-built control site.

## Wayfinding and onward path

Most visitors to a deep page arrive from outside, not from the homepage. A deep
page with no upward path and no in-content link onward is a dead end regardless
of how good it is.

`act.context.no_onward_path` counts links **in main content only**. Navigation
and footer links are excluded: they are identical on every page and are not this
page's suggestion of what to read next. It applies only where reading ends and a
next step is needed. A homepage uses its navigation as its onward path, and
counting in-content links there produced false positives.

## Calls to action

Two distinct and common failures:

- **No action at all** on a page type that exists to produce one.
- **An action whose label names no outcome.** "Submit" tells the visitor nothing
  about what happens next; "Start free trial" does. The label is what a visitor
  evaluates before clicking, so a bare verb creates hesitation the page then has
  to overcome.

`act.cta.competing_primaries` fires when several actions are presented as
equally important, because the visitor then has to rank them, and that extra
decision costs more than the extra options gain. Repeats of one label count
once; chrome is excluded.

## Form friction

Every field is a separate decision and a separate chance to abandon. Three
things are distinguished:

- **Count**, against a page-type threshold, because a checkout legitimately
  needs more than a newsletter signup.
- **Kind.** Phone, company, job title, date of birth and full address demanded
  at the top of the funnel ask for personal detail before anything has been
  given in return. The same fields on a checkout or application page are
  necessary, and the check does not fire there.
- **Labelling.** A placeholder disappears on focus and is not exposed as a
  label, so a visitor who pauses mid-form loses the only description of what the
  field wanted. Placeholder-only reports at low rather than medium, because it
  is a weak label rather than none.

## Trust

`act.trust.no_social_proof` looks for evidence a visitor can weigh: a review or
rating, a customer count, a case study, or an attributed quotation. A
first-party claim is not evidence, because the party making the claim is the
party being assessed.

`act.trust.no_cost_signal` fires on commercial page types with no price, no
price range, and no path to one. Cost is the question a visitor on a commercial
page is trying to answer; leaving it unanswerable ends the visit rather than
deferring it.

`act.trust.no_policy_or_contact_path` is site-scoped: a visitor deciding whether
to transact looks for evidence there is a reachable organisation behind the site.

## Blockers

An interstitial that fires on arrival asks for a decision the visitor has no
basis to make. Cookie and consent banners are excluded, because they are
frequently a legal requirement rather than a marketing choice.

Missing viewport meta, disabled zoom, excessive weight, and content behind a
click are each measurable, and each stops a visitor who was otherwise willing.

## Accessibility basis

Three checks cite WCAG 2.2 directly, because the criteria are precise and
testable:

- `act.form.unlabelled_inputs` — SC 3.3.2 Labels or Instructions
- `act.blocker.not_mobile_ready` — SC 1.4.10 Reflow, SC 1.4.4 Resize Text
- `read.nontext.informative_image_no_alt` — SC 1.1.1 Non-text Content

These are engagement checks with an accessibility basis. This marketplace does
not claim to be an accessibility audit, and says so rather than implying broader
coverage than it has.
