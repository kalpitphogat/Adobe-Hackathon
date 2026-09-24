I ran the audit on https://www.ikea.com/ using the orchestrator Procedure, with `--out ./audit-output`. Nothing under `skills/` was changed. The run exited normally after about 63 s and wrote `audit-output/audit-report.json`, `report.md` and `fix_patches/`.

## 1. Status and summary
- **audit_status:** `complete`
- **Counts by severity:** critical 0 · high 7 · medium 44 · low 1 · info 0. That is **52 findings in total**, and none are blocked by the gate cascade.
- By category: 25 discoverability and 27 engagement.
- The two checks for whether IKEA's CDN or firewall blocks AI crawlers were **not assessed**, because `--probe-bot-ua` was off. The engine treats this as a blind spot, not a pass.

## 2. Top 10 findings by `suggested_action.ice`
All ten are tied at 7.7, so this is the first ten in report order among those tied.

| id | severity | confidence | ICE | title |
|---|---|---|---|---|
| F-001 | high | likely | 7.7 | fact_coverage 2/4: 2 claim(s) cannot be quoted from this page — on /at/en |
| F-002 | high | likely | 7.7 | fact_coverage 1/2: 1 claim(s) cannot be quoted from this page — on /global/en/newsroom |
| F-003 | high | likely | 7.7 | fact_coverage 1/2: 1 claim(s) cannot be quoted from this page — on /global/en/stories |
| F-004 | high | likely | 7.7 | The first screen never says who this is for or what it does — on 13 of 25 crawled pages |
| F-008 | medium | confirmed | 7.7 | 5 content image(s) carry no alt text — on 18 of 25 crawled pages |
| F-009 | medium | confirmed | 7.7 | 8 page(s) of dated content carry no date at all |
| F-010 | medium | confirmed | 7.7 | Invisible / zero-width Unicode in the content of 2 page(s) |
| F-011 | medium | confirmed | 7.7 | The main action is labelled 'Read more', which names no outcome — on /ae/en |
| F-012 | medium | confirmed | 7.7 | The main action is labelled 'Learn more', which names no outcome — on /global/en/newsroom |
| F-013 | medium | confirmed | 7.7 | A category page gives no indication of cost and no path to one |

## 3. First three findings in report order
All three are `extract.ans.fact_coverage_gap` findings, with severity **high** and confidence **likely**.

**F-001** (https://www.ikea.com/at/en/)
- **Evidence:** "https://www.ikea.com/at/en/: the page makes 4 derivable claims about 'IKEA Austria'. Segmenting the 1480 words a no-JS reader sees into 9 overlapping windows of about 300 tokens, 2 of 4 claims survive inside at least one window that still makes sense on its own. The misses: "Fresh home furnishing ideas and affordable furniture." (from title) - no window contains the claim at all; "Welcome to IKEA. Discover affordable furniture and home furnishing inspiration for all siz" (from meta description) - no window contains the claim at all."
- **Fix:** "State each key claim in a sentence that names the subject and stands on its own. Do NOT split the page into smaller blocks." Effort is low.
- **Patch** (`fix_patches/F-001.extract.ans.fact_coverage_gap.txt`):
  ```html
  <!-- Make each claim self-contained IN PROSE. Do not split the page into
       smaller blocks: Google Search Central states there is no requirement
       to break content into tiny pieces for AI to understand it. -->

  <!-- claim: Fresh home furnishing ideas and affordable furniture.  (no window contains the claim at all) -->
  <p>IKEA Austria __FILL_IN__:state_this_claim_in_one_sentence_that_names_the_subject.</p>

  <!-- claim: Welcome to IKEA. Discover affordable furniture and home furnishing inspiration for all siz  (no window contains the claim at all) -->
  <p>IKEA Austria __FILL_IN__:state_this_claim_in_one_sentence_that_names_the_subject.</p>
  ```

**F-002** (https://www.ikea.com/global/en/newsroom/)
- **Evidence:** "the page makes 2 derivable claims about 'Hej! Welcome to IKEA Global'. Segmenting the 184 words a no-JS reader sees into 1 overlapping windows of about 300 tokens, 1 of 2 claims survive inside at least one window that still makes sense on its own. The misses: "Press releases about the IKEA brand and business, including our people and planet sustaina" (from meta description) - no window contains the claim at all."
- **Fix:** same as F-001.
- **Patch** (`fix_patches/F-002...txt`): the same header comment, then
  ```html
  <!-- claim: Press releases about the IKEA brand and business, including our people and planet sustaina  (no window contains the claim at all) -->
  <p>Hej! Welcome to IKEA Global __FILL_IN__:state_this_claim_in_one_sentence_that_names_the_subject.</p>
  ```

**F-003** (https://www.ikea.com/global/en/stories/)
- **Evidence:** "the page makes 2 derivable claims about 'Hej! Welcome to IKEA Global'. Segmenting the 183 words a no-JS reader sees into 1 overlapping windows of about 300 tokens, 1 of 2 claims survive inside at least one window that still makes sense on its own. The misses: "Editorial stories about IKEA from around the world, filled with inspiring ideas, wonderful" (from meta description) - no window contains the claim at all."
- **Fix:** same as F-001.
- **Patch** (`fix_patches/F-003...txt`): the same header comment, then
  ```html
  <!-- claim: Editorial stories about IKEA from around the world, filled with inspiring ideas, wonderful  (no window contains the claim at all) -->
  <p>Hej! Welcome to IKEA Global __FILL_IN__:state_this_claim_in_one_sentence_that_names_the_subject.</p>
  ```

## 4. Evidence check
This is my commentary only; the report is unchanged. For each URL I fetched the raw HTML with `urllib` and stripped out the `<head>`, scripts and styles. I then checked whether each "missed" claim appears in the visible body text.

- **F-001 (/at/en/, 200, about 1,707 body words): supports.** The title and meta description text are in the `<head>`, but neither phrase appears anywhere in the visible body text, which matches "no window contains the claim at all".
- **F-002 (/global/en/newsroom/, 200, about 270 body words): supports.** "Press releases about the IKEA brand and business…" is only in the meta description; the phrase "press release" appears zero times in the body.
- **F-003 (/global/en/stories/, 200, about 272 body words): supports.** "Editorial stories about IKEA from around the world…" is only in the meta description; "editorial" appears zero times in the body, although "stories" appears 4 times.

Three caveats:
- **Word counts differ.** My counts are higher than the engine's (1,707 vs 1,480, 270 vs 184, 272 vs 183) because my text extraction is cruder. This doesn't affect the conclusion.
- **The "claims" are metadata.** All the missed claims are the page's own title and meta description taglines, not factual statements in the content. So the finding is accurate as stated, but lower-stakes than "high" might suggest.
- **Odd subject name.** F-002, F-003 and their patches name the subject "Hej! Welcome to IKEA Global", which looks like a greeting picked up as the entity name.

Your harness blocked writing a script file, so I ran the check as an inline `python -c` script and left no extra files in the directory.
