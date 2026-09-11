# On-site engagement check catalog

Engagement is judged against what a page is **for**, not against a marketing-site
template. Every check below states the role it applies to and what it deliberately does
not conclude.

## Likely primary task, by role

| Role | What the visitor most likely came to do |
|------|------------------------------------------|
| homepage | understand what the site is and reach the section they need |
| product | understand the offering and act on it |
| article | read the piece and find related reading |
| documentation | find a specific answer and navigate to adjacent topics |
| contact | obtain a contact route and use it |
| directory | scan the list and open the right entry |
| utility | operate the tool |
| authentication | sign in or create an account |
| legal | read the policy |
| generic / unknown | read the page's content |

Only **homepage, product and contact** have a conversion-style next action in their
task. The others do not, and are never assessed for one.

## Checks

| # | Check | Applies to | Trigger | Band |
|---|-------|-----------|---------|------|
| 1 | Mobile viewport | every HTML page | no `<meta name=viewport>` | high if every sampled page, else medium (defect) |
| 2 | Task-relevant next step | homepage / product / contact, role confidence ≥ medium, >400 chars | no role-specific action wording, on ≥ half the candidates | low (improvement) |
| 3 | Route onward | orientation roles, role confidence ≥ medium, >300 chars | zero internal links **and** no nav/header/footer landmark **and** no form | medium (defect) |
| 4 | Crawler-observed latency | every HTML page | >3000 ms on ≥ a third of sampled pages | medium (defect, confidence medium) |
| 5 | Large HTML document | every HTML page | >1 MB of markup alone | low (improvement) |
| 6 | Unmuted autoplay | first 6 pages | parsed `<video>`/`<audio>` with `autoplay` and no `muted` | low (improvement) |
| 7 | Entry overlay | first 6 pages | element named newsletter / email-capture / paywall / exit-intent / welcome-mat, excluding consent and age gates | low (improvement, confidence low) |

## What is deliberately NOT a finding

- **No call-to-action.** Only roles whose purpose implies an action are assessed, and
  even then the result is an improvement, not a defect. A tool, an article, a
  documentation page or a legal notice with no CTA is working as intended.
- **No footer.** There is no footer check. A footer is a convention, not a requirement.
- **Few links.** There is no link-count rule. Only a total dead end is reported, and
  only when no navigation landmark exists either.
- **A cookie banner.** Consent, privacy and age-gate elements are excluded from the
  overlay check by name.
- **Muted autoplay.** Muted background video is standard practice and is read from the
  parsed attributes, so attribute order cannot cause a false positive.
- **A heading count, a header structure, or any particular HTML pattern.**

## Thresholds, and why they are where they are

- **1 MB of HTML.** The median HTML document is well under 100 KB. A megabyte of markup
  alone — excluding every image, script, stylesheet and font — is far outside the
  ordinary range and usually means inlined state or an unpaginated list. It is still
  reported as an improvement, because document size alone does not establish that any
  visitor experienced a slow page.
- **3000 ms.** Generous, because the measurement is one request from one location.

## Honest limits

- **Latency is not a Core Web Vital.** The finding names it as the auditor's own
  single-sample request time, states that it includes network distance to the crawler,
  states that it is not Largest Contentful Paint and not field data, and recommends
  measuring real-user vitals before acting. It is never labelled LCP.
- **Document size is not page weight.** The finding says the measurement excludes
  sub-resources and does not establish a slow experience.
- **Overlays are not executed.** The audit runs no JavaScript and applies no CSS, so it
  reports that overlay *markup* is present and that whether it is displayed on arrival
  was not verified.
- **Navigation is measured in the server HTML.** Navigation injected later by JavaScript
  would not appear, and the finding says so.
