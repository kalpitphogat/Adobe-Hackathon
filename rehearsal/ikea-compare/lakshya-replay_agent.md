I ran the audit on https://www.ikea.com/ with `--no-render`. It exited 0 in 39.7 s. Everything below comes from `./audit-output/audit-report.json`, except the live check in section 4.

## 1. Status and severity counts

**`audit_status`: `partial`**. There are 52 findings in total.

| Severity | Count |
|---|---|
| critical | 0 |
| high | 6 |
| medium | 45 |
| low | 1 |
| info | 0 |

The report also records `blocked_findings: 0`. By category, 25 findings are discoverability and 27 are engagement. Some checks were listed as not assessed, including the two bot user-agent checks (the audit only runs those with `--probe-bot-ua`) and the render-gap checks.

## 2. Top 5 suggested actions, in priority order

| # | id | check_id | severity | ICE |
|---|---|---|---|---|
| 1 | F-001 | `extract.ans.fact_coverage_gap` (/at/en) | high | 7.7 |
| 2 | F-002 | `extract.ans.fact_coverage_gap` (/global/en/newsroom) | high | 7.7 |
| 3 | F-003 | `extract.ans.fact_coverage_gap` (/global/en/stories) | high | 7.7 |
| 4 | F-004 | `act.orient.no_value_proposition` (13 of 25 pages) | high | 7.7 |
| 5 | F-005 | `extract.sd.absent_on_eligible_page` (2 of 20 eligible pages) | high | 7.3 |

## 3. Drill-down on F-001

- **Title:** "fact_coverage 2/4: 2 claim(s) cannot be quoted from this page — on /at/en"
- **Affected URL:** https://www.ikea.com/at/en/
- **Evidence:** The page makes 4 claims about "IKEA Austria". The audit split the 1480 words a reader without JavaScript sees into 9 overlapping windows of about 300 tokens each. Only 2 of the 4 claims appear in a window that makes sense on its own. The two that don't:
  - "Fresh home furnishing ideas and affordable furniture." (from the title): no window contains it.
  - "Welcome to IKEA. Discover affordable furniture and home furnishing inspiration for all siz…" (from the meta description): no window contains it.
- **Confidence:** `likely`
- **ICE:** impact 8.0, confidence 6.0, ease 9.0, giving 7.7. Effort is low.
- **Mechanism:** "A passage that is quoted away from its page loses whatever its pronouns and back-references pointed at, so a claim that depends on them cannot be reproduced as an answer."
- **Paste-ready patch** (`fix_patches/F-001.extract.ans.fact_coverage_gap.txt`):
  ```html
  <!-- Make each claim self-contained IN PROSE. Do not split the page into
       smaller blocks: Google Search Central states there is no requirement
       to break content into tiny pieces for AI to understand it. -->

  <!-- claim: Fresh home furnishing ideas and affordable furniture.  (no window contains the claim at all) -->
  <p>IKEA Austria __FILL_IN__:state_this_claim_in_one_sentence_that_names_the_subject.</p>

  <!-- claim: Welcome to IKEA. Discover affordable furniture and home furnishing inspiration for all siz  (no window contains the claim at all) -->
  <p>IKEA Austria __FILL_IN__:state_this_claim_in_one_sentence_that_names_the_subject.</p>
  ```
  The `__FILL_IN__` placeholders are deliberate. The patch leaves the actual wording for the site owner to write.
- **Findings capped with `blocked_by: F-001`:** 0. No finding in the report has `blocked_by` set.

## 4. Checking F-001 against the live site

The report's verification step is: "Copy any single paragraph out of the page and read it cold: does it still name what it is about, without the paragraphs around it?" To check this, I fetched https://www.ikea.com/at/en/ once without JavaScript. I stripped out scripts, styles and `<head>`, then searched the remaining text for each claim.

- **Title** (live): "Fresh home furnishing ideas and affordable furniture. - IKEA Austria". The phrases "Fresh home furnishing ideas" and "affordable furniture" do not appear anywhere in the visible text.
- **Meta description** (live): "Welcome to IKEA. Discover affordable furniture and home furnishing inspiration for all sizes of wallets and homes. …". The phrase "home furnishing inspiration" does not appear in the visible text. Only a short heading, "Welcome to IKEA Austria", appears, and it sits among promo text ("Parcel delivery from €1,99…", "PAX wardrobe system: €15,- voucher…"). No full sentence states the claim.

This backs up the evidence: neither claim is stated in the body as a sentence that could be quoted on its own. One difference: my simple text extraction counted about 1,707 words against the report's 1,480, because the two methods split the text differently. That doesn't change whether the claims are present.

I didn't create or change any files; the only files written were the audit script's own output in `./audit-output`.
