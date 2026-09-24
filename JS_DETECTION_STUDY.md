# Can a Python-only run tell that a site needs JavaScript? (2026-09-25)

**Question.** If we run the frozen engine without a browser (`--no-render`, an existing flag), can
we tell from its own output that a crawler would see an empty or incomplete page, so we know when
Playwright is worth adding? Nothing in the engine was changed.

**Method.** 18 sites never used before (not pytest, not sphinx-doc), in four groups: JavaScript-only
apps, sites with JavaScript-added links, tiny pages, normal server-rendered sites.
1. **Prediction:** `tools/js_detection_study.py` runs the engine with `--no-render` and reads its
   own `evidence/pages.jsonl`: pages with 0 same-site links, pages under 50 main-content words,
   and the engine's `looks_like_spa_shell` flag / `empty_spa_shell` finding.
2. **Truth:** `tools/js_detection_truth.py` compares, for up to 5 pages per site, **the exact raw
   HTML the engine's crawler received** (its own User-Agent) with **the page a human sees** in
   Chromium. A page "needs JavaScript" if same-site links go raw → rendered with rendered ≥ 5 and
   raw < 60% (the engine's own threshold, counted fairly), or visible words grow ≥ 3× to ≥ 40.
   Meta-refresh redirect stubs are skipped.

A first pass that fetched pages with a browser User-Agent was wrong on three sites and was discarded.
python.org served that UA a bot-check page, Spotify serves crawlers pre-rendered HTML, and a
rust-lang.org blog URL is a meta-refresh redirect. Measuring from the crawler's own saved HTML
fixes all three.

## Results

| group | site | pages | 0-link pages | < 50-word pages | engine shell flag | needs JS? | what JavaScript adds (crawler raw → human) |
|---|---|---|---|---|---|---|---|
| JS-only | excalidraw.com | 1 | 1 | 1 | 2 | **yes** | links 0 → 3, words 3 → 65 |
| JS-only | open.spotify.com | 25 | 0 | 3 | 0 | **yes (partly)** | links 91 → 307; crawlers get pre-rendered HTML |
| JS-only | twitch.tv | 24 | 24 | 24 | 25 | **yes** | links 0 → 40, words 1 → 334 |
| JS-only | app.diagrams.net | 1 | 1 | 0 | 0 | no | canvas app; text about the same |
| JS-only | figma.com | 25 | 1 | 1 | 0 | **yes (one page)** | /signup: links 0 → 2, words 5 → 53 |
| JS links | vercel.com | 25 | 0 | 0 | 0 | **yes (partly)** | community page: words 554 → 3,672 |
| JS links | airbnb.com | 1 | 1 | 1 | 0 | **yes** | links 0 → 127, words 6 → 188 |
| JS links | netflix.com | 0 | – | – | – | n/a | no content available to the crawler |
| JS links | notion.com | 25 | 1 | 1 | 2 | no | /contact-sales: 0 → 1 link, 8 words |
| tiny | example.com | 1 | 1 | 1 | 0 | no | |
| tiny | info.cern.ch | 2 | 0 | 1 | 0 | no | |
| tiny | neverssl.com | 1 | 1 | 1 | 0 | no | |
| tiny | berkshirehathaway.com | 1 | 1 | 0 | 0 | **yes (not JS)** | crawler got **undecoded Brotli bytes**; human sees 15 links |
| normal | python.org | 25 | 0 | 2 | 0 | no | |
| normal | gov.uk | 22 | 0 | 0 | 0 | no | |
| normal | w3.org | 25 | 0 | 0 | 0 | no | |
| normal | craigslist.org/about | 16 | 0 | 4 | 0 | no | |
| normal | rust-lang.org | 22 | 1 | 4 | 2 | **yes (subdomains)** | forge: links 11 → 141 (JS-built sidebar); play.: 0-word app shell |

## How well each rule predicts it (17 scorable sites, 8 need JavaScript)

| rule, from the Python-only run | caught | missed | false alarm | correct "no" |
|---|---|---|---|---|
| **R1: any page with 0 same-site links** | **6** | 2 | 4 | 5 |
| R2: any page under 50 words | 6 | 2 | 6 | 3 |
| R3: the engine's own shell flag / finding | 3 | 5 | 1 | 8 |
| R1 and R2 on the same page | 5 | 3 | 3 | 6 |

## What it means

1. **Pages that are empty for a crawler are detected every time.** Every site where the crawler
   got an empty or unreadable page (Twitch, Airbnb, Excalidraw, Figma /signup, rust's playground,
   Berkshire's undecoded Brotli) had **0 same-site links** in the Python-only run. R1 caught all 6.
2. **Partly JavaScript sites are not detected.** Spotify (crawlers get pre-rendered HTML) and
   Vercel's community page (crawler gets 554 words, humans 3,672) have links in raw HTML, so R1
   misses them. The crawler isn't blind there, it just misses part of the content.
3. **False alarms are tiny or app pages:** example.com, neverssl.com, diagrams.net, Notion's
   contact-sales form. They have 0 links because they are small, not because of JavaScript.
   Rendering them finds nothing new, but costs a run.
4. **"Under 50 words" is a worse trigger** (6 false alarms), and **the engine's own shell
   detector is too strict** (it caught 3 of 8, and missed Airbnb and Excalidraw's home page).
5. Combined with the earlier 26-site check (R1 avoided all 8 sites where Playwright gave only
   false links findings), **R1 is a useful rule of thumb**: it reliably flags "the crawler sees
   nothing", it doesn't flag "the crawler sees most of it", and it has some harmless false alarms
   on tiny pages. It is a heuristic from 44 sites, not a guarantee.

## New engine limitation found

**Brotli.** berkshirehathaway.com answers with `content-encoding: br` although the engine only
asks for `gzip, deflate`. `fetch.py` `_decompress` (lines 197–207) handles gzip and deflate only,
so the page is read as compressed bytes: 0 links, 0 words. The engine is frozen, so this is
recorded in `NOTES.md` §11 and the REPLAY's known limits, not fixed.
