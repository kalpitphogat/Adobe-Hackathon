# Rehearsal agent session — www.npr.org

Pre-recording rehearsal of the exact REPLAY steps, run headless (`claude -p`, prompt on stdin) so it
could be captured as a transcript. **This is not the video take.** Produced from the session's
`stream-json` output; nothing below was edited except truncating long tool results.

- Harness: Claude Code 2.1.283 · model `claude-opus-5-5`
- Plugin loaded: `['submission']` from `--plugin-dir ./submission.zip`
- Turns: 9 · wall time: 122s · API cost: $0.41

## Prompt (verbatim)

```text
Use the ai-readiness-orchestrator skill to audit https://www.npr.org/ . Stay in the current directory and run the skill's own script with default flags and an absolute output path, giving that command a 10-minute timeout: python "<skill base directory>/scripts/orchestrate.py" https://www.npr.org/ --out "$PWD/audit-output/www.npr.org" (use python3 if python is not on PATH). Report only what the engine wrote to ./audit-output/www.npr.org/audit-report.json and add no findings of your own. Then: (1) show the summary counts and a table of every finding in the report's own order: id, severity, stage, confidence, ICE, blocked_by, title; (2) drill into F-001: quote its evidence, say why it has that severity and how many findings it caps via blocked_by, and show its fix, mechanism, patch and verification; (3) corroborate F-001's evidence against the live site with one read-only request and show the raw lines; (4) list the fixes that are not blocked, sorted by ICE score, highest first.
```

## Tool calls, in order

1. **Skill** — `{"skill": "submission:ai-readiness-orchestrator", "args": "https://www.npr.org/"}`

2. **Bash** — Check which Python is on PATH

```bash
cd "F:/adobe_hackathin_77_round_final" && (command -v python || command -v python3) && python --version
```

3. **Bash** — Run the AI-readiness audit against npr.org

```bash
cd "F:/adobe_hackathin_77_round_final" && python "C:/Users/asus/AppData/Local/Temp/claude-plugin-session-21413d75f3fdb224/inline-0-submission/skills/ai-readiness-orchestrator/scripts/orchestrate.py" https://www.npr.org/ --out "$PWD/audit-output/www.npr.org"; echo "EXIT=$?"
```

4. **Bash** — Inspect report structure, summary and first finding

```bash
cd "F:/adobe_hackathin_77_round_final/audit-output/www.npr.org" && ls -la && python -c "
import json
r=json.load(open('audit-report.json',encoding='utf-8'))
print(list(r.keys()))
for k in r:
    if k not in ('findings','proactive_recommendations','limitations'):
        print(k, json.dumps(r[k],indent=1)[:3000])
print('limitations', len(r.get('limitations',[])))
print('proactive', len(r.get('proactive_recommendations',[])))
print(json.dumps(r['findings'][0],indent=1))
"
```

5. **Bash** — Tabulate all findings and blocked_by counts

```bash
cd "F:/adobe_hackathin_77_round_final/audit-output/www.npr.org" && python -c "
import json
r=json.load(open('audit-report.json',encoding='utf-8'))
print('| id | severity | stage | confidence | ICE | blocked_by | title |')
for f in r['findings']:
    sa=f.get('suggested_action',{})
    print('|',f['id'],'|',f['severity'],'|',f['stage'],'|',f['confidence'],'|',sa.get('ice'),'|',f.get('blocked_by') or '—','|',f['title'].replace('|','\\\\|'),'|')
print()
print('blocked_by F-001:', sum(1 for f in r['findings'] if f.get('blocked_by')=='F-001'))
from collections import Counter
print(Counter(f.get('blocked_by') for f in r['findings']))
print(json.dumps(r['limitations'],indent=1))
"
```

6. **Bash** — List unblocked fixes by ICE and view F-001 patch file

```bash
cd "F:/adobe_hackathin_77_round_final/audit-output/www.npr.org" && PYTHONIOENCODING=utf-8 python -c "
import json
r=json.load(open('audit-report.json',encoding='utf-8'))
fs=[f for f in r['findings'] if not f.get('blocked_by')]
fs=sorted(fs,key=lambda f:-f['suggested_action']['ice'])
for f in fs:
    sa=f['suggested_action']
    print(f['id'],'|',sa['ice'],'|',f['severity'],'|',sa.get('effort'),'|',sa['summary'])
print()
for f in r['findings']:
    if '\u2014' in f['title']: pass
print(r['findings'][7]['title'])
" ; ls fix_patches | head -60; cat "fix_patches/F-001.reach.robots.ai_search_bot_blocked.txt"
```

7. **Bash** — Fetch live robots.txt once and show numbered rule lines

```bash
curl -sS -A "Mozilla/5.0 (read-only corroboration)" https://www.npr.org/robots.txt -o /tmp/npr_robots.txt -w "HTTP %{http_code}  bytes=%{size_download}\n" && grep -n -E "^(User-agent|Disallow|Allow)" /tmp/npr_robots.txt | awk -F: '$1>=40 && $1<=100'
```

## Final answer (verbatim)

I ran the audit on https://www.npr.org/. The script exited with code 0 and wrote `./audit-output/www.npr.org/audit-report.json`. Everything below comes from that file, except part (3), which is the one live request you asked for.

## (1) Summary counts

**Audit status:** `partial`. It finished in about 38 seconds and fetched 25 pages. It rendered none of them, because Playwright isn't installed, so rendered-page checks were marked not assessed. The two CDN/WAF bot checks were also not assessed because `--probe-bot-ua` was off. 21 of 66 checks ran, and the report makes no proactive recommendations.

| Critical | High | Medium | Low | Info | **Total** | Blocked |
|---|---|---|---|---|---|---|
| 1 | 1 | 41 | 4 | 1 | **48** | 38 |

- **By stage:** reach 4, read 1, extract 32, trust 5, act 6.
- **By category:** discoverability 42, engagement 6.

| id | severity | stage | confidence | ICE | blocked_by | title |
|---|---|---|---|---|---|---|
| F-001 | critical | reach | confirmed | 9.3 | — | robots.txt blocks 5 AI retrieval crawler(s) that cite sources at answer time |
| F-002 | high | act | likely | 7.7 | — | The first screen never says who this is for or what it does |
| F-003 | medium | read | confirmed | 7.7 | F-001 | 45 content image(s) carry no alt text |
| F-004 | medium | extract | confirmed | 7.7 | F-001 | Table data on 1 page(s) carries no column or row labels |
| F-005 | medium | extract | confirmed | 7.7 | F-001 | The page title is 'Life Kit : NPR', which does not say what the page is about |
| F-006 | medium | extract | confirmed | 7.7 | F-001 | The site does not clearly state who publishes it |
| F-007 | medium | reach | likely | 6.7 | — | robots.txt blocks 3 crawler(s) whose role is contested |
| F-008 | medium | extract | likely | 6.7 | F-001 | 5 of 7 passages do not stand on their own — on /2022/07/11/1110926267/digital-minimalism-can-help-find-balance |
| F-009 | medium | extract | likely | 6.7 | F-001 | 6 of 7 passages do not stand on their own — on /2022/12/09/1141872654/build-a-healthy-relationship-with-your-in-laws |
| F-010 | medium | extract | likely | 6.7 | F-001 | 10 of 11 passages do not stand on their own — on /2026/09/24/nx-s1-5931971/trump-nih-science-funding-disruptions-charts |
| F-011 | medium | extract | likely | 6.7 | F-001 | 4 of 5 passages do not stand on their own — on /2026/09/24/nx-s1-5974336/teen-pregnancy-prevention-unspent-funding |
| F-012 | medium | extract | likely | 6.7 | F-001 | 4 of 5 passages do not stand on their own — on /2026/09/24/nx-s1-5978798/your-mother-your-mother-your-mother-review |
| F-013 | medium | extract | likely | 6.7 | F-001 | 5 of 6 passages do not stand on their own — on /2026/09/25/g-s1-144948/pandemic-prevention-treaty-agreement-world-health-organization |
| F-014 | medium | extract | likely | 6.7 | F-001 | 7 of 8 passages do not stand on their own — on /2026/09/25/nx-s1-5976804/supreme-court-trump-save-noncitizen-voting |
| F-015 | medium | extract | likely | 6.7 | F-001 | 5 of 6 passages do not stand on their own — on /2026/09/25/nx-s1-5978096/republicans-trump-midterm-elections |
| F-016 | medium | extract | likely | 6.7 | F-001 | 1 of 3 passages do not stand on their own — on /2026/09/25/nx-s1-5978875/midterms-redistricting-trump-missouri |
| F-017 | medium | extract | likely | 6.7 | F-001 | 5 of 6 passages do not stand on their own — on /2026/09/25/nx-s1-5979852/israels-prime-minister-addresses-u-n-general-assembly |
| F-018 | medium | extract | likely | 6.7 | F-001 | 1 of 3 passages do not stand on their own — on /about-npr/178660742/public-radio-finances |
| F-019 | medium | extract | likely | 6.7 | F-001 | 9 of 36 passages do not stand on their own — on /about-npr/179878450/privacy-policy |
| F-020 | medium | extract | likely | 6.7 | F-001 | fact_coverage 3/5: 2 claim(s) cannot be quoted from this page — on /2021/01/11/955692434/procrastination-is-more-than-putting-things-off-heres-how-to-kick-the-habit |
| F-021 | medium | extract | likely | 6.7 | F-001 | fact_coverage 5/6: 1 claim(s) cannot be quoted from this page — on /2026/09/25/nx-s1-5976939/primetime-review-robert-pattinson-to-catch-a-predator |
| F-022 | medium | extract | likely | 6.7 | F-001 | fact_coverage 5/6: 1 claim(s) cannot be quoted from this page — on /lifekit |
| F-023 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what Keisha "TK" Dutes is — on /2021/01/11/955692434/procrastination-is-more-than-putting-things-off-heres-how-to-kick-the-habit |
| F-024 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what Andee Tagle is — on /2022/12/09/1141872654/build-a-healthy-relationship-with-your-in-laws |
| F-025 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what Joseph Kim is — on /2026/09/24/nx-s1-5931971/trump-nih-science-funding-disruptions-charts |
| F-026 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what Justin Chang is — on /2026/09/24/nx-s1-5978798/your-mother-your-mother-your-mother-review |
| F-027 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what Josh Baker is — on /2026/09/24/nx-s1-5979058/where-is-austin-tice-a-meeting-in-muskat |
| F-028 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what Holly J. Morris is — on /2026/09/25/g-s1-144665/trump-arch-fat-bear-media-ai-news-quiz |
| F-029 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what Jonathan Lambert is — on /2026/09/25/g-s1-144948/pandemic-prevention-treaty-agreement-world-health-organization |
| F-030 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what Glen Weldon is — on /2026/09/25/nx-s1-5976939/primetime-review-robert-pattinson-to-catch-a-predator |
| F-031 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what Kat Lonsdorf is — on /2026/09/25/nx-s1-5979852/israels-prime-minister-addresses-u-n-general-assembly |
| F-032 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what NPR is — on /about-npr/179876898/terms-of-use |
| F-033 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what NPR is — on /about-npr/179878450/privacy-policy |
| F-034 | medium | extract | likely | 6.7 | F-001 | Nothing near the top of the page states plainly what NPR is — on /lifekit |
| F-035 | medium | trust | likely | 6.7 | F-001 | 4 page(s) state time-sensitive facts but have not been updated |
| F-036 | medium | trust | likely | 6.7 | F-001 | The name 'NPR' is ambiguous and nothing on the homepage distinguishes it |
| F-037 | medium | trust | likely | 6.7 | F-001 | The site states more than one address or phone number for itself |
| F-038 | medium | trust | likely | 6.7 | F-001 | Nothing connects this site to an independent record of the same entity |
| F-039 | medium | act | likely | 6.7 | — | 1 passage(s) assume context a first-time visitor does not have — on /about-npr/178660742/public-radio-finances |
| F-040 | medium | act | likely | 6.7 | — | 3 passage(s) assume context a first-time visitor does not have — on /about-npr/179876898/terms-of-use |
| F-041 | medium | act | likely | 6.7 | — | 2 passage(s) assume context a first-time visitor does not have — on /about-npr/179878450/privacy-policy |
| F-042 | medium | act | likely | 6.7 | — | 1 passage(s) assume context a first-time visitor does not have — on /lifekit |
| F-043 | medium | extract | confirmed | 6.3 | F-001 | 2 page(s) declare structured data of the wrong kind |
| F-044 | low | reach | confirmed | 7.0 | — | The sitemap does not usefully describe the site |
| F-045 | low | extract | confirmed | 7.0 | F-001 | The heading outline does not divide this page usefully — on 24 of 25 crawled pages |
| F-046 | low | trust | confirmed | 7.0 | F-001 | 11 article(s) name nobody as the author |
| F-047 | low | act | confirmed | 7.0 | — | A category page gives no indication of cost and no path to one |
| F-048 | info | reach | confirmed | 6.3 | — | robots.txt blocks 8 training-only crawler(s) — recorded as an observation, not a defect |

## (2) F-001 in detail

**Check:** `reach.robots.ai_search_bot_blocked`. Severity critical, confidence confirmed, ICE 9.3 (impact 10, confidence 9, ease 9). It affects `https://www.npr.org/`.

**Evidence, quoted from the report:**
> ChatGPT-User blocked by "Disallow: /" (line 47); Claude-SearchBot blocked by "Disallow: /" (line 74); Claude-User blocked by "Disallow: /" (line 77); OAI-SearchBot blocked by "Disallow: /" (line 54); PerplexityBot blocked by "Disallow: /" (line 98). Each of these fetches pages at answer time to ground or cite a response, so blocking them removes this brand from those assistants' answers entirely. 25 of 25 discovered paths are disallowed for these agents. Bot classification from a snapshot dated 2026-09-09 (upstream commit 0e111dcc24cb). 8 training-only bot(s) are also blocked, which is a separate and legitimate licensing choice.

**Why it's critical:** it fails at the reach stage, the first step in the engine's reach → read → extract → trust sequence. The blocked bots are retrieval crawlers, the ones that fetch pages when a user asks a question, and all 25 of 25 crawled paths are disallowed for them. The report treats that as removing the brand from those assistants' answers entirely. The 8 blocked training-only bots are kept separate as F-048 (info) and are not counted as a defect.

**How many findings it caps:** **38.** Each of those carries `blocked_by: "F-001"`, which matches `summary.blocked_findings = 38`. That includes all 32 extract findings, 5 of the 6 trust findings and the 1 read finding. They are capped at medium or lower but not deleted. The 6 act (engagement) findings are never gated on reach, so none of them are blocked.

- **Fix:** Allow ChatGPT-User, Claude-SearchBot, Claude-User, OAI-SearchBot, PerplexityBot in robots.txt, keeping any training-bot policy separate. (Effort: low. Source: RFC 9309 §2.2.2 plus vendor crawler documentation.)
- **Mechanism:** "Retrieval crawlers fetch the page at the moment a user asks a question; if they are refused, the brand cannot appear as a source no matter how good the page is."
- **Patch** (`fix_patches/F-001.reach.robots.ai_search_bot_blocked.txt`):
  ```
  User-agent: ChatGPT-User
  Allow: /

  User-agent: Claude-SearchBot
  Allow: /

  User-agent: Claude-User
  Allow: /

  User-agent: OAI-SearchBot
  Allow: /

  User-agent: PerplexityBot
  Allow: /
  ```
- **Verification:** "curl -s https://www.npr.org/robots.txt and confirm each of ChatGPT-User, Claude-SearchBot, Claude-User, OAI-SearchBot, PerplexityBot has an Allow rule that is at least as specific as any Disallow"

## (3) Check against the live site

I made one GET request to `https://www.npr.org/robots.txt`. It returned HTTP 200 and 4,736 bytes. These are the raw numbered lines for the five bots F-001 names:

```
46:User-agent: ChatGPT-User
47:Disallow: /
53:User-agent: OAI-SearchBot
54:Disallow: /
73:User-agent: Claude-SearchBot
74:Disallow: /
76:User-agent: Claude-User
77:Disallow: /
97:User-agent: PerplexityBot
98:Disallow: /
```

All five line numbers in the live file (47, 54, 74, 77, 98) match F-001's evidence exactly. Each one is `Disallow: /`.

## (4) Fixes that aren't blocked, by ICE score (highest first)

Where scores tie, the report's own order is kept.

| # | id | ICE | severity | effort | fix |
|---|---|---|---|---|---|
| 1 | F-001 | 9.3 | critical | low | Allow ChatGPT-User, Claude-SearchBot, Claude-User, OAI-SearchBot, PerplexityBot in robots.txt, keeping any training-bot policy separate. |
| 2 | F-002 | 7.7 | high | low | Open with one sentence naming the audience and the outcome. |
| 3 | F-044 | 7.0 | low | low | Regenerate the sitemap from the live route list with real lastmod values. |
| 4 | F-047 | 7.0 | low | low | State a price, a price range, or an explicit route to getting one. |
| 5 | F-007 | 6.7 | medium | low | Decide deliberately whether the AI-surface exposure Applebot-Extended, FacebookBot, Google-Extended controls is wanted. |
| 6 | F-039 | 6.7 | medium | low | Rewrite these passages so they stand on their own for a first-time reader. |
| 7 | F-040 | 6.7 | medium | low | Rewrite these passages so they stand on their own for a first-time reader. |
| 8 | F-041 | 6.7 | medium | low | Rewrite these passages so they stand on their own for a first-time reader. |
| 9 | F-042 | 6.7 | medium | low | Rewrite these passages so they stand on their own for a first-time reader. |
| 10 | F-048 | 6.3 | info | low | No change required. This is a content-licensing decision, and we report it only so it is visible. |

The full report is in `./audit-output/www.npr.org/`: `audit-report.json`, a readable `report.md`, the paste-ready fixes in `fix_patches/`, and the collected page data in `evidence/`.
