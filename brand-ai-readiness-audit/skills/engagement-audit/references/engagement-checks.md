# On-site engagement check catalog

Getting cited brings a visitor to the door; engagement decides whether they stay. This
skill audits the on-page factors most tied to immediate bounce.

## Checks & thresholds
| # | Check | Signal | Threshold | Severity |
|---|-------|--------|-----------|----------|
| 1 | Mobile viewport | `<meta name=viewport>` absent | any page | high if sitewide, else medium |
| 2 | Heavy HTML | raw document bytes | >2 MB | medium |
| 3 | Slow response | fetch elapsed time | >3000 ms | medium |
| 4 | No CTA | no CTA phrase in page text | majority of pages | medium |
| 5 | Sparse nav | link count | <5 links | majority of pages | low |
| 6 | Intrusive UI | overlay/popup/interstitial or autoplay markup | any sampled page | low |

CTA phrases: get started, sign up, start free, try, buy, book, contact, request,
subscribe, download, learn more, add to cart, demo, get a quote, shop.

## Rationale
- **Viewport**: without it, mobile users get a zoomed-out desktop layout — a top bounce
  cause on phones.
- **Weight/latency**: document size and time-to-first-byte are proxies for Largest
  Contentful Paint; slower first paint correlates strongly with abandonment.
- **CTA / next step**: a visitor who can't tell what to do next leaves. One obvious
  primary action per key page.
- **Navigation**: enough internal links to orient and go deeper.
- **Interstitials/autoplay**: full-screen entry pop-ups and autoplaying media are
  classic immediate-exit triggers (and interstitials are penalized on mobile search).

## Limits (honesty over false precision)
Page-weight and fetch latency are **first-response proxies**, not real-user LCP/TTFB or
Core Web Vitals field data. Findings say so, and stay at medium/low. For authoritative
performance numbers, pair this with a Lighthouse/CrUX run — out of scope for a read-only,
<5-minute audit.

## False-positive guards
- CTA and sparse-nav findings require the condition on a **majority** of pages, not one.
- Intrusive-UI check is a markup heuristic, capped at low severity.
