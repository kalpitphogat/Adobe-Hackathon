# Demo-URL scouting (2026-09-23)

**Purpose.** Round 4 Part 2 must run on "a site the audit has never seen". So we did
not rehearse on the demo URL. We ran the frozen engine on 25 sites across 6 site types to learn
**which kinds of site** it audits with real, evidence-backed findings and few false
positives. The on-camera URL will be a new site of the best-performing kind that we have
never run.

Setup: Windows 11, Python 3.11.15, Playwright 1.63.0 (Chromium), engine unzipped from
`round3-frozen/submission.zip`, default flags, run with `tools/scout.py` (cwd = marketplace root).

## Results

"high" counts findings at high severity; the bracket says how many of those (plus criticals)
are `confirmed`, meaning directly observed by a deterministic check.

| type | url | secs | findings | critical | high |
|---|---|---|---|---|---|
| saas | https://basecamp.com/ | 37 | 23 | 0 | 6 (0 confirmed) |
| saas | https://plausible.io/ | 27 | 40 | 0 | 2 (1 confirmed) |
| saas | https://cal.com/ | 88 | 61 | 0 | 12 (4 confirmed) |
| saas | https://www.linear.app/ | 124 | 52 | 2 | 3 (3 confirmed) |
| ecom | https://www.allbirds.com/ | 117 | 81 | 1 | 12 (3 confirmed) |
| ecom | https://www.tentree.com/ | 112 | 51 | 0 | 10 (1 confirmed) |
| ecom | https://www.bellroy.com/ | 116 | 66 | 0 | 6 (2 confirmed) |
| news | https://www.smashingmagazine.com/ | 65 | 39 | 0 | 2 (1 confirmed) |
| news | https://www.theverge.com/ | 101 | 56 | 1 | 1 (1 confirmed) |
| news | https://www.eff.org/ | 54 | 32 | 0 | 3 (1 confirmed) |
| docs | https://flask.palletsprojects.com/ | 52 | 49 | 0 | 6 (2 confirmed) |
| docs | https://fastapi.tiangolo.com/ | 43 | 21 | 0 | 3 (1 confirmed) |
| docs | https://docs.djangoproject.com/ | 33 | 24 | 0 | 4 (4 confirmed) |
| docs | https://requests.readthedocs.io/ | 22 | 13 | 0 | 1 (1 confirmed) |
| docs | https://docs.pydantic.dev/ | 34 | 48 | 1 | 7 (2 confirmed) |
| docs | https://pip.pypa.io/ | 22 | 5 | 0 | 0 (0 confirmed) |
| docs | https://htmx.org/ | 34 | 55 | 0 | 10 (5 confirmed) |
| docs | https://www.sqlite.org/ | 47 | 32 | 0 | 5 (2 confirmed) |
| docs | https://docs.astral.sh/uv/ | 29 | 31 | 0 | 13 (1 confirmed) |
| docs | https://www.gnu.org/ | 300 | **no report (exit 1)** | | |
| local | https://www.katzsdelicatessen.com/ | 20 | 0 (`no_content_available`) | 0 | 0 |
| local | https://www.joespizzanyc.com/ | 28 | 24 | 0 | 7 (4 confirmed) |
| local | https://www.bluebottlecoffee.com/ | 45 | 54 | 1 | 12 (2 confirmed) |
| edu | https://www.mozilla.org/ | 42 | 54 | 1 | 14 (8 confirmed) |
| edu | https://www.khanacademy.org/ | 28 | 21 | 0 | 4 (2 confirmed) |

## Confirmed findings hold up under an independent check

We re-fetched 10 pages with a separate script (not the engine) and counted JSON-LD, microdata,
RDFa, raw `<a>` links and robots `noindex`. **All 10 matched what the engine reported**:
smashingmagazine (2 pages), eff.org, fastapi, djangoproject, flask, allbirds, khanacademy
(0 raw links, as reported), linear.app and mozilla (noindex present, as reported).

## False-positive classes we observed

| check | confidence | what goes wrong | where |
|---|---|---|---|
| `act.orient.no_value_proposition` | likely | Fires on clear homepages, product pages, docs reference pages. The regex wants "for <who>" / "helps <who>" wording. | stripe, flask, fastapi, allbirds products, htmx, sqlite (almost every site) |
| `act.cta.absent_for_page_type` | likely | Counts links in the **raw** HTML; on a JS-rendered page it sees 0 links though the visitor sees many. | khanacademy (raw 0 vs rendered 217), cal.com/de/pricing, marketplace.stripe.com |
| `trust.integrity.prompt_injection` | **critical**/confirmed | Fires on pages that *talk about* prompt injection. | linear.app/legal/aup, pydantic.dev/docs/ai |
| `reach.index.noindex_on_content` | **critical**/confirmed | The directive is really there, but it's often deliberate (deprecated docs, cart-upsell collections, "about this site"). Critical overstates it. | linear, allbirds, mozilla |
| any `act.*` | likely | A bot-protection block page ("Sorry, you have been blocked") is audited as if it were content. | bluebottlecoffee |
| `read.nontext.key_fact_image_only` | likely | "Price only in an image" when the price is actually rendered by JS. | tentree products |

The crawl also follows **subdomains** (status.cal.com, swag.htmx.org, de/fr/es.bellroy.com,
pydantic.dev from docs.pydantic.dev), which adds findings about sites the viewer did not ask about.

## Correction: `read.render.nav_links_js_only` is a false positive (found by the agent's evidence check)

An earlier version of this file listed this check as a strength. **That was wrong.** On the
clean-room REPLAY rehearsal (docs.djangoproject.com), the agent's evidence check disputed all
three nav-links findings. An independent count (raw HTML via urllib, rendered DOM via
Playwright, same-host `<a href>` only) agreed with the agent:

| page | raw same-host | rendered same-host | engine said |
|---|---|---|---|
| docs.djangoproject.com/el/1.11/_modules/…/api/ | 35 | 35 | raw 34, rendered 72 |
| www.mozilla.org/en-US/about/ | 19 | 19 | raw 19, rendered 70 |
| htmx.org/ | 11 | 11 | raw 17, rendered 59 |

Cause, in the frozen engine: `site-evidence-collector/scripts/collect.py` line 739 builds
`rendered_internal_link_count` from **every** classified href, while the raw count (line 632)
keeps only `kind == "internal"`. The rendered side therefore includes off-site links, so any page
with many outbound links fires at high/confirmed. **Never drill into this check on camera**; if it
appears, the agent's evidence check will say it is unsupported, which is the honest outcome.

## What the engine does well (the demo should show this)

- `extract.sd.absent_on_eligible_page`: confirmed, verified independently on 10 pages, comes with
  a paste-ready JSON-LD patch. **This is the finding to drill into.**
- `read.render.raw_text_gap`: raw-vs-rendered **word count** (not links), e.g. khanacademy raw 0
  words vs 1155 rendered (raw HTML independently confirmed at 3 KB with 0 links). Needs Playwright.
- `reach.robots.ai_search_bot_blocked`: theverge.com, with line numbers from robots.txt.
- `pip.pypa.io` got 0 high findings, which fits a well-built site (control behaviour on a live site).

## Recommendation for the on-camera URL

**A static documentation site** (Sphinx / MkDocs / hand-written HTML) that is:
1. on **one host** (no docs.X → X, no status./swag. subdomains in its nav),
2. **not about AI** (avoids the prompt-injection false positive),
3. **not behind bot protection** (Cloudflare challenge pages),
4. **without a large `Crawl-delay`** in robots.txt (see NOTES.md §6).

Django docs was the cleanest run: 4 highs, all confirmed, all verified true. Use it as the
second `TEST_SITE_URLS` entry (the "already seen" control). The first entry is the on-camera site.

For the walkthrough, drill into **missing structured data** with its JSON-LD patch, or a
`raw_text_gap` if one fires. Not `nav_links_js_only` (see the correction above).
