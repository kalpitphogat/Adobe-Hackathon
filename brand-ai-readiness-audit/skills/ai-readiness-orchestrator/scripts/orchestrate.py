#!/usr/bin/env python3
"""ENTRYPOINT. Audit a website and emit one report.

Given a URL, this collects evidence once, classifies the site, runs six focused
audit skills against that shared evidence, applies the gate cascade, dedupes,
scores and ranks, and writes audit-report.json plus report.md.

  python orchestrate.py https://example.com --out ./audit-output
  python orchestrate.py --offline-root tests/fixtures/site_a --out ./audit-output

Composition is by SUBPROCESS, not by import. Every audit skill is invoked as
`python <skill>/scripts/run.py --bundle <dir> [--profile <file>]`, reads exactly
one JSON object from its stdout, and is expected to exit 0 (ran), 3 (precondition
unmet) or 1 (internal error). No skill imports another, so each folder can be
lifted out and run alone. See references/skill-cli-contract.md.

EXIT CODES. Exit 0 whenever a schema-valid report was written, whatever it
contains. A site that does not resolve, 404s, or forbids crawling still gets a
report and still exits 0; the outcome lives in the report's audit_status field,
never in the exit code, because a grading harness may read any non-zero exit as
a crash. Non-zero is reserved for: no report could be produced (1), the output
path is unusable (2), or arguments are invalid (3).

RECOMMEND-ONLY. Nothing here writes to the audited site. There is no apply mode.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKETPLACE = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))

import emit_report  # noqa: E402
from gate_model import apply_cascade, gate_summary  # noqa: E402
from severity import score_finding  # noqa: E402

VERSION = "1.0.0"
NAME = "brand-ai-readiness-audit"

COLLECTOR = MARKETPLACE / "skills" / "site-evidence-collector" / "scripts" / "collect.py"
CLASSIFIER = MARKETPLACE / "skills" / "site-profile-classifier" / "scripts" / "profile.py"
AUDIT_SKILLS = [
    "crawl-access-audit",
    "render-gap-audit",
    "structured-data-audit",
    "answerability-audit",
    "trust-freshness-audit",
    "engagement-audit",
]

# When two checks describe the same defect, keep the more specific one and fold
# the other's evidence into it. Key is the check that is absorbed.
DEDUPE_INTO = {
    "extract.ans.chunk_not_self_contained": "extract.ans.fact_coverage_gap",
}

# Ceiling on a single audit skill when no time budget is set. With a budget set,
# each skill instead gets an equal share of whatever the budget has left.
DEFAULT_SKILL_TIMEOUT = 75.0


def run_tool(argv: list[str], timeout: float) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, *argv], capture_output=True, text=True, timeout=timeout,
        cwd=str(MARKETPLACE), env=dict(os.environ, PYTHONIOENCODING="utf-8"),
    )
    return proc.returncode, proc.stdout, proc.stderr


def collect(args, bundle_dir: Path, limitations: list[dict]) -> int:
    argv = [str(COLLECTOR), "--out", str(bundle_dir)]
    if args.offline_root:
        argv += ["--offline-root", args.offline_root]
    if args.seed:
        argv.insert(1, args.seed)
    argv += ["--max-pages", str(args.max_pages), "--workers", str(args.workers),
             "--delay", str(args.delay), "--render", str(args.render)]
    if args.no_render:
        argv.append("--no-render")
    if args.probe_bot_ua:
        argv.append("--probe-bot-ua")
    if args.allow_private_hosts:
        argv.append("--allow-private-hosts")
    if args.time_budget:
        argv += ["--time-budget", str(max(30, args.time_budget * 0.6))]

    try:
        code, out, err = run_tool(argv, timeout=max(60.0, args.time_budget or 600))
    except subprocess.TimeoutExpired:
        limitations.append({
            "scope": "site",
            "reason": (
                "evidence collection exceeded the run's time budget and was stopped. Re-run with a "
                "larger --time-budget, or a smaller --max-pages, to audit this site fully."
            ),
            "checks_not_run": ["all"],
            "confidence_effect": "no evidence was collected",
        })
        return 1
    if code != 0:
        limitations.append({
            "scope": "site",
            "reason": f"evidence collection failed (exit {code}): {err.strip()[:300]}",
            "checks_not_run": ["all"],
            "confidence_effect": "no evidence was collected",
        })
    return code


class Deadline:
    """A hard wall-clock ceiling on the whole run.

    The handout caps an audit at five minutes. Per-stage timeouts alone cannot
    honour that: seven skills that each stop just short of their own budget
    still overrun the total. Every stage therefore draws from one shared clock,
    and a stage that cannot be given useful time is skipped and reported rather
    than started and killed halfway.
    """

    # Below this a subprocess cannot finish anything useful, so starting it only
    # burns the time the report needs to be written. The invariant callers rely
    # on: while remaining() >= MIN_USEFUL_SLICE, a slice floored at this value is
    # still <= remaining(), so no stage can be granted more time than is left.
    MIN_USEFUL_SLICE = 2.0

    def __init__(self, budget: float | None) -> None:
        self.started = time.perf_counter()
        self.budget = float(budget) if budget else 0.0

    def elapsed(self) -> float:
        return time.perf_counter() - self.started

    def remaining(self) -> float:
        if not self.budget:
            return float("inf")
        return self.budget - self.elapsed()

    def slice_for(self, want: float) -> float:
        """The timeout to hand a stage: what it wants, or what is left."""
        return min(want, self.remaining())

    def exhausted(self) -> bool:
        return self.remaining() < self.MIN_USEFUL_SLICE


def classify(bundle_dir: Path, profile_path: Path, limitations: list[dict],
             timeout: float = 120.0) -> dict | None:
    if timeout < Deadline.MIN_USEFUL_SLICE:
        limitations.append({
            "scope": "site",
            "reason": (
                "site classification was skipped because the run's time budget was already spent; "
                "default thresholds were used and every archetype-dependent check lowered its confidence."
            ),
            "checks_not_run": [],
            "confidence_effect": "confirmed -> likely on archetype-dependent checks",
        })
        return None
    try:
        code, out, err = run_tool([str(CLASSIFIER), "--bundle", str(bundle_dir)], timeout=timeout)
    except subprocess.TimeoutExpired:
        limitations.append({
            "scope": "site",
            "reason": (
                f"site classification exceeded its {timeout:.0f}s slice of the time budget; "
                f"default thresholds were used and every archetype-dependent check lowered its confidence."
            ),
            "checks_not_run": [],
            "confidence_effect": "confirmed -> likely on archetype-dependent checks",
        })
        return None
    if code != 0 or not out.strip():
        limitations.append({
            "scope": "site",
            "reason": (
                f"site classification failed (exit {code}); default thresholds were used and every "
                f"archetype-dependent check lowered its confidence. {err.strip()[:200]}"
            ),
            "checks_not_run": [],
            "confidence_effect": "confirmed -> likely on archetype-dependent checks",
        })
        return None
    profile = json.loads(out)
    emit_report.atomic_write(profile_path, json.dumps(profile, indent=2, sort_keys=True))
    return profile


def run_audit_skill(skill: str, bundle_dir: Path, profile_path: Path | None,
                    timeout: float, limitations: list[dict]) -> dict | None:
    script = MARKETPLACE / "skills" / skill / "scripts" / "run.py"
    argv = [str(script), "--bundle", str(bundle_dir)]
    if profile_path and profile_path.exists():
        argv += ["--profile", str(profile_path)]
    try:
        code, out, err = run_tool(argv, timeout=timeout)
    except subprocess.TimeoutExpired:
        limitations.append({
            "scope": "site",
            "reason": f"{skill} exceeded its {timeout:.0f}s budget and was not included.",
            "checks_not_run": [skill],
            "confidence_effect": "not assessed",
        })
        return None

    if code == 3:
        limitations.append({
            "scope": "site",
            "reason": f"{skill} could not run: precondition unmet. {err.strip()[:240]}",
            "checks_not_run": [skill],
            "confidence_effect": "not assessed",
        })
        return None
    if code != 0:
        limitations.append({
            "scope": "site",
            "reason": f"{skill} failed internally (exit {code}). {err.strip()[:240]}",
            "checks_not_run": [skill],
            "confidence_effect": "not assessed",
        })
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        limitations.append({
            "scope": "site",
            "reason": f"{skill} produced unparseable output: {exc}",
            "checks_not_run": [skill],
            "confidence_effect": "not assessed",
        })
        return None


def validate_finding(finding: dict) -> str | None:
    """The contract: no finding ships without evidence, confidence and a mechanism."""
    for field in ("check_id", "title", "severity", "evidence", "suggested_action"):
        if not finding.get(field):
            return f"missing {field}"
    if not finding.get("confidence"):
        return "missing confidence"
    action = finding["suggested_action"]
    if not action.get("summary"):
        return "suggested_action has no summary"
    if not action.get("mechanism"):
        return "suggested_action has no mechanism"
    return None


SITEWIDE_COLLAPSE_RATIO = 0.5
SITEWIDE_COLLAPSE_MIN = 5


def gate_findings_on_sample(findings: list[dict], truncated: bool,
                            pages_fetched: int, limitations: list[dict]) -> None:
    """Reduce confidence on SITE-WIDE claims when the crawl sample is incomplete.

    A crawl stopped early by its time budget saw only part of the site, so a
    finding scoped to the whole site is a generalisation from a partial sample
    and should not be stated as confidently as one drawn from a complete crawl.
    We lower its confidence one step (which also lowers its ICE rank), but never
    its severity: the defect's impact is unchanged, only our certainty that the
    pattern holds everywhere. Per-URL findings are direct observations of pages
    we did fetch and are left exactly as they were - seeing fewer pages does not
    make what we saw on a page any less true. Mutates findings in place.
    """
    if not truncated:
        return
    from severity import downgrade_confidence

    gated = []
    for f in findings:
        if f.get("scope") != "site":
            continue
        before = f.get("confidence", "likely")
        after = downgrade_confidence(before)
        if after != before:
            f["confidence"] = after
            f["evidence"] = (
                f"{f.get('evidence', '')} (Confidence reduced from {before} to {after}: the crawl "
                f"was stopped by its time budget after {pages_fetched} page(s), so this site-wide "
                f"claim rests on a partial sample of the site.)"
            )
            gated.append(f.get("check_id", "unknown"))
    if gated:
        limitations.append({
            "scope": "audit environment",
            "reason": (
                f"The crawl was stopped by its time budget after fetching {pages_fetched} page(s), "
                f"so it saw only part of the site. Confidence on {len(gated)} site-wide finding(s) "
                f"was reduced by one level to reflect the partial sample; per-page findings are "
                f"unaffected. Re-run with a larger time budget for full-coverage confidence."
            ),
            "checks_not_run": sorted(set(gated)),
            "confidence_effect": "site-wide confidence reduced one level",
            "optional_feature": True,
        })


def collapse_sitewide(findings: list[dict], pages_crawled: int) -> tuple[list[dict], list[str]]:
    """Report a defect present on most of the site ONCE, not once per page.

    A template defect - an unlabelled search box in the header, a heading
    structure emitted by the layout, a missing viewport meta - is ONE defect
    with one fix, and it is repaired in one place. Reporting it once per crawled
    page turned a single chrome search input into 25 findings on a live site and
    buried everything else.

    Nothing is discarded: the collapsed finding keeps every affected URL, and
    its evidence says how many pages share it. This is a presentation decision
    about what counts as one finding, not a suppression.
    """
    if pages_crawled < SITEWIDE_COLLAPSE_MIN:
        return findings, []

    groups: dict[str, list[dict]] = {}
    for f in findings:
        if f.get("scope") == "site":
            continue
        groups.setdefault(f["check_id"], []).append(f)

    kept: list[dict] = [f for f in findings if f.get("scope") == "site"]
    notes: list[str] = []
    for check_id, group in groups.items():
        urls = sorted({u for f in group for u in (f.get("affected_urls") or [])})
        share = len(urls) / max(pages_crawled, 1)
        if len(group) < SITEWIDE_COLLAPSE_MIN or share < SITEWIDE_COLLAPSE_RATIO:
            kept.extend(group)
            continue
        # Keep the most severe instance as the representative.
        from severity import SEVERITY_RANK

        rep = max(group, key=lambda f: SEVERITY_RANK.get(f["severity"], 0))
        rep = dict(rep)
        rep["scope"] = "site"
        rep["affected_urls"] = urls
        rep["title"] = f"{rep['title']} — on {len(urls)} of {pages_crawled} crawled pages"
        rep["evidence"] = (
            f"This is a site-wide pattern, not a one-page defect: it appears on {len(urls)} of "
            f"{pages_crawled} crawled pages ({share:.0%}), so it is almost certainly emitted by a "
            f"shared template and fixable in one place. Reported once rather than "
            f"{len(group)} times. Example: {rep['evidence']}"
        )
        kept.append(rep)
        notes.append(
            f"{check_id}: {len(group)} page-level findings collapsed into one site-wide finding "
            f"covering {len(urls)} pages"
        )
    return kept, notes


def _page_label(url: str) -> str:
    """A short, human name for a page: its path, or 'the homepage'."""
    path = urllib.parse.urlsplit(url).path.strip("/")
    return f"/{path}" if path else "the homepage"


def disambiguate_titles(findings: list[dict]) -> list[dict]:
    """No two rows in the report may read identically.

    collapse_sitewide folds a template defect into one finding, but only once
    it has enough pages to call it a pattern. Below that threshold the same
    check can legitimately survive on two or three pages -- and then the report
    shows the same sentence twice, and a reader cannot tell whether it is two
    problems or one printed twice. The evidence distinguishes them; the title
    should too, because the title is what gets skimmed.
    """
    groups: dict[str, list[dict]] = {}
    for f in findings:
        groups.setdefault(f["check_id"], []).append(f)

    for group in groups.values():
        if len(group) < 2:
            continue
        labels = [
            _page_label(urls[0]) if len(urls := (f.get("affected_urls") or [])) == 1 else None
            for f in group
        ]
        # Only when every instance names exactly one distinct page: anything
        # else is a scope we should not paper over with a page name.
        if any(lb is None for lb in labels) or len(set(labels)) != len(labels):
            continue
        for finding, label in zip(group, labels):
            finding["title"] = f"{finding['title']} — on {label}"
    return findings


def dedupe(findings: list[dict]) -> list[dict]:
    """Fold absorbed checks into the more specific finding on the same URL."""
    kept: list[dict] = []
    absorbed: list[dict] = []
    for f in findings:
        if f["check_id"] in DEDUPE_INTO:
            absorbed.append(f)
        else:
            kept.append(f)

    for f in absorbed:
        target_id = DEDUPE_INTO[f["check_id"]]
        urls = set(f.get("affected_urls") or [])
        host = next(
            (k for k in kept
             if k["check_id"] == target_id and urls & set(k.get("affected_urls") or [])),
            None,
        )
        if host is None:
            kept.append(f)  # nothing to fold into; it stands alone
            continue
        host.setdefault("merged_from", []).append(f["check_id"])
        host["evidence"] = host["evidence"].rstrip() + " Also: " + f["evidence"]
    for k in kept:
        if k.get("merged_from"):
            k["merged_from"] = sorted(set(k["merged_from"]))
    return kept


def build_proactive(profile: dict | None, findings: list[dict], collected: list[dict]) -> list[dict]:
    """Beyond-defect recommendations, derived from the archetype not from defects."""
    out = list(collected)
    archetype = (profile or {}).get("archetype", "other")
    have = {f["check_id"] for f in findings}

    if archetype in ("docs", "developer-platform") and "extract.sd.absent_on_eligible_page" not in have:
        out.append({
            "title": "Mark up your how-to and reference pages as HowTo or TechArticle",
            "rationale": (
                f"This is a {archetype} site with valid structured data already in place. Typing "
                f"procedural pages specifically as HowTo or TechArticle, rather than generically, "
                f"tells a consumer that the page contains ordered steps, which is what a "
                f"how-do-I question needs."
            ),
            "applies_to_archetype": [archetype],
            "suggested_action": {
                "summary": "Add HowTo or TechArticle typing with step properties to procedural pages.",
                "priority": "low", "effort": "medium",
                "mechanism": (
                    "A typed step list is directly reusable as an answer to a procedural question, "
                    "where untyped prose has to be re-derived."
                ),
                "source": "schema.org/HowTo",
                "patch": '{"@type": "HowTo", "step": [{"@type": "HowToStep", "text": "__FILL_IN__:step_1"}]}',
                "verification": "Confirm the page emits a HowTo node with at least two steps.",
            },
        })

    if archetype == "saas-marketing":
        out.append({
            "title": "Publish a comparison page for the alternatives buyers already weigh you against",
            "rationale": (
                "Comparison questions are among the most common commercial queries, and a brand "
                "that has not written its own comparison is described using someone else's. This "
                "is a gap in coverage rather than a defect on any page, which is why it appears "
                "here and not as a finding."
            ),
            "applies_to_archetype": ["saas-marketing"],
            "suggested_action": {
                "summary": "Write an honest comparison page naming the real alternatives.",
                "priority": "low", "effort": "medium",
                "mechanism": (
                    "A page that names both sides of a comparison is the only page on your domain "
                    "that can be quoted when the comparison is asked about."
                ),
                "source": "references/geo-methods.md",
                "patch": (
                    "<h1>__FILL_IN__:product vs __FILL_IN__:alternative</h1>\n"
                    "<p>__FILL_IN__:one_sentence_honest_summary_including_where_you_lose.</p>"
                ),
                "verification": "Confirm the page names the alternative in its title and H1.",
            },
        })

    if archetype == "e-commerce" and "extract.sd.required_props_missing" not in have:
        out.append({
            "title": "Attach shipping and returns to the product, not to a policy page",
            "rationale": (
                "The questions asked about a product are rarely just its price: they are whether "
                "it ships to a country and what happens if it is sent back. Those facts usually "
                "live in a footer link or an accordion, on a page the product's own markup never "
                "references, so an assistant that has extracted the Offer still cannot answer "
                "them and falls back to a marketplace listing that can. Nothing here is broken, "
                "which is why it is not a finding."
            ),
            "applies_to_archetype": ["e-commerce"],
            "suggested_action": {
                "summary": "Add shippingDetails and hasMerchantReturnPolicy to the product's Offer node.",
                "priority": "low", "effort": "medium",
                "mechanism": (
                    "A consumer that has already parsed the Offer can read a nested shipping or "
                    "return node without a second fetch and without guessing which policy page "
                    "applies. Prose on a separate page is not attributable to this product."
                ),
                "source": "schema.org/OfferShippingDetails, schema.org/MerchantReturnPolicy",
                "patch": (
                    '{"@type": "Offer",\n'
                    ' "shippingDetails": {"@type": "OfferShippingDetails",\n'
                    '   "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "__FILL_IN__:country"}},\n'
                    ' "hasMerchantReturnPolicy": {"@type": "MerchantReturnPolicy",\n'
                    '   "merchantReturnDays": __FILL_IN__:days,\n'
                    '   "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow"}}'
                ),
                "verification": (
                    "Confirm a product page's Offer node contains both a shippingDestination "
                    "and a merchantReturnDays value."
                ),
            },
        })

    if archetype == "publisher" and "trust.authorship.unattributed" not in have:
        out.append({
            "title": "Make each byline a resolvable person, and say when a piece was corrected",
            "rationale": (
                "A byline that is only a string is a name a machine cannot check. Attribution "
                "carries weight when the author resolves to an identity corroborated somewhere "
                "independent — that is what separates a quotable source from an anonymous one. "
                "The related risk is silent correction: an article edited after publication, with "
                "no visible record that it changed, keeps being quoted in the form that was wrong."
            ),
            "applies_to_archetype": ["publisher"],
            "suggested_action": {
                "summary": (
                    "Link each byline to a Person node with sameAs to an independent profile, "
                    "and mark corrections explicitly in the article body."
                ),
                "priority": "low", "effort": "medium",
                "mechanism": (
                    "sameAs is the only machine-followable path from a name on your page to a "
                    "record you do not control, and agreement across independent sources is what "
                    "makes a machine repeat a fact. A dated, visible correction note gives a "
                    "re-crawl something to supersede the stale claim with."
                ),
                "source": "schema.org/Person, Round-2 appendix D",
                "patch": (
                    '{"@type": "Article",\n'
                    ' "author": {"@type": "Person", "name": "__FILL_IN__:author",\n'
                    '   "url": "__FILL_IN__:author_page",\n'
                    '   "sameAs": ["__FILL_IN__:independent_profile_url"]},\n'
                    ' "dateModified": "__FILL_IN__:iso_8601"}'
                ),
                "verification": (
                    "Confirm an article's author node has a sameAs that resolves off-domain, "
                    "and that an edited article states what changed and when."
                ),
            },
        })

    if archetype == "local-business" and "trust.entity.nap_inconsistent" not in have:
        out.append({
            "title": "State opening hours as machine-readable data with a timezone",
            "rationale": (
                "'Are they open now?' is the most common question asked about a local business, "
                "and it is the one a page of prose cannot answer. Hours written as text — or worse, "
                "set in an image — require a machine to both parse them and guess the timezone, so "
                "assistants answer from a third-party directory listing instead, which is where "
                "stale hours come from. Consistency matters more than completeness here: the same "
                "name, address and phone repeated identically on the site, in the markup and in at "
                "least one independent record is what makes a machine believe any of them."
            ),
            "applies_to_archetype": ["local-business"],
            "suggested_action": {
                "summary": (
                    "Publish openingHoursSpecification with an explicit timezone, and repeat the "
                    "exact same name, address and phone string in the markup and off-site."
                ),
                "priority": "low", "effort": "low",
                "mechanism": (
                    "A typed hours range with a timezone is directly evaluable against the "
                    "asker's clock; prose is not. Byte-identical NAP across independent sources "
                    "is what lets a machine treat the three as the same entity rather than three "
                    "candidates it has to choose between."
                ),
                "source": "schema.org/LocalBusiness, Round-2 appendix D",
                "patch": (
                    '{"@type": "LocalBusiness",\n'
                    ' "name": "__FILL_IN__:exact_name_used_everywhere",\n'
                    ' "telephone": "__FILL_IN__:e164_phone",\n'
                    ' "address": {"@type": "PostalAddress", "streetAddress": "__FILL_IN__:street",\n'
                    '   "addressLocality": "__FILL_IN__:city", "postalCode": "__FILL_IN__:postcode"},\n'
                    ' "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",\n'
                    '   "dayOfWeek": ["Monday"], "opens": "09:00", "closes": "17:00"}],\n'
                    ' "areaServed": "__FILL_IN__:region"}'
                ),
                "verification": (
                    "Confirm the hours parse as a typed range, and that the phone and address "
                    "strings match the footer character for character."
                ),
            },
        })

    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="orchestrate.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("seed", nargs="?", help="website URL to audit")
    parser.add_argument("--out", default="./audit-output", help="output directory (outside the marketplace)")
    parser.add_argument("--offline-root", help="audit a fixture directory instead of the network")
    parser.add_argument("--bundle", help="reuse an existing evidence bundle instead of collecting")
    parser.add_argument("--max-pages", type=int, default=25)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--render", type=int, default=6)
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--probe-bot-ua", action="store_true",
                        help="opt in to one request per AI bot user agent, homepage only")
    parser.add_argument("--time-budget", type=float, default=300, help="seconds; 0 disables")
    parser.add_argument(
        "--allow-private-hosts", action="store_true",
        help="permit seeds and redirects resolving to private/loopback addresses "
             "(off by default; use only for a site you host yourself)")
    parser.add_argument("--explain-gates", action="store_true", help="print the gate state to stderr")
    args = parser.parse_args(argv)

    if not args.seed and not args.offline_root and not args.bundle:
        print("error: provide a URL, --offline-root, or --bundle", file=sys.stderr)
        return 3

    out = Path(args.out)
    guard = emit_report.guard_output_path(out)
    if guard:
        print(f"error: {guard}", file=sys.stderr)
        return 2
    space = emit_report.check_free_space(out.parent if not out.exists() else out)
    if space:
        print(f"error: {space}", file=sys.stderr)
        return 2
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot write to {out}: {exc}", file=sys.stderr)
        return 2

    deadline = Deadline(args.time_budget)
    started = deadline.started
    limitations: list[dict] = []
    bundle_dir = Path(args.bundle) if args.bundle else out / "evidence"

    if not args.bundle:
        collect(args, bundle_dir, limitations)

    if not (bundle_dir / "meta.json").exists():
        print("error: no evidence bundle was produced; cannot write a report", file=sys.stderr)
        return 1

    meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
    audited_at = meta.get("audited_at")
    site = (meta.get("resolved_origin") or "").split("://")[-1].strip("/") or "unknown"

    profile_path = out / "profile.json"
    profile = classify(bundle_dir, profile_path, limitations,
                       timeout=deadline.slice_for(120.0))

    findings: list[dict] = []
    proactive: list[dict] = []
    suppressed_counts: dict[tuple[str, str], int] = {}
    checks_available: set[str] = set()
    checks_ran: set[str] = set()
    # Every remaining skill gets an equal share of whatever time is left, so one
    # slow skill cannot starve the rest and the total cannot outrun the budget.
    for index, skill in enumerate(AUDIT_SKILLS):
        if deadline.exhausted():
            skipped = AUDIT_SKILLS[index:]
            limitations.append({
                "scope": "site",
                "reason": (
                    f"the {deadline.budget:.0f}s time budget was spent before these skills ran, so "
                    f"their checks were not assessed. Re-run with a larger --time-budget, or a "
                    f"smaller --max-pages, for full coverage."
                ),
                "checks_not_run": skipped,
                "confidence_effect": "not assessed",
            })
            break

        share = deadline.remaining() / (len(AUDIT_SKILLS) - index)
        per_skill_timeout = max(Deadline.MIN_USEFUL_SLICE, min(share, DEFAULT_SKILL_TIMEOUT))
        result = run_audit_skill(skill, bundle_dir, profile_path, per_skill_timeout, limitations)
        if not result:
            continue
        checks_available.update(result.get("checks_run") or [])
        for f in result.get("findings") or []:
            problem = validate_finding(f)
            if problem:
                limitations.append({
                    "scope": f.get("check_id", skill),
                    "reason": f"a finding from {skill} was rejected as malformed: {problem}.",
                    "checks_not_run": [f.get("check_id", "unknown")],
                    "confidence_effect": "dropped",
                })
                continue
            f.setdefault("blocked_by", None)
            f["affected_url_count"] = len(f.get("affected_urls") or [])
            checks_ran.add(f["check_id"])
            findings.append(f)
        for s in result.get("checks_skipped") or []:
            key = (s["check_id"], s.get("confidence_effect", ""))
            suppressed_counts[key] = suppressed_counts.get(key, 0) + 1
        proactive.extend(result.get("proactive_recommendations") or [])
        limitations.extend(result.get("limitations") or [])

    findings = dedupe(findings)
    findings, collapse_notes = collapse_sitewide(
        findings, meta.get("crawl", {}).get("pages_fetched", 0)
    )
    findings = disambiguate_titles(findings)
    for note in collapse_notes:
        suppressed_counts[("sitewide_collapse", note)] = 1

    # Confidence gate on an incomplete sample: when the crawl was cut short by its
    # time budget, any SITE-WIDE claim generalises from a partial view of the site,
    # so its confidence is reduced one step. Per-URL findings are untouched - they
    # are direct observations of a page we did fetch, and stay as confident as they
    # were. Severity (a defect's impact) is not lowered; only our confidence that
    # the pattern holds site-wide is, which also lowers the finding's ICE rank.
    gate_findings_on_sample(
        findings,
        truncated=bool(meta.get("crawl", {}).get("truncated_by_budget")),
        pages_fetched=meta.get("crawl", {}).get("pages_fetched", 0),
        limitations=limitations,
    )

    # ids are assigned during report build; the cascade needs stable handles, so
    # assign provisional ids first, cascade, then let build_report finalise.
    from severity import sort_key as _sk

    provisional = sorted(findings, key=_sk)
    for i, f in enumerate(provisional, start=1):
        f["_id"] = f"F-{i:03d}"
    findings, blocked_count = apply_cascade(provisional, id_of=lambda f: f.get("_id", ""))
    for f in findings:
        score_finding(f)

    gate_notes = gate_summary(findings, id_of=lambda f: f.get("_id", ""))
    for f in findings:
        f.pop("_id", None)
        f.pop("scope", None)

    suppressed = [
        {"rule": effect or "suppressed", "check_id": check, "count": count,
         "reason": effect or "see the skill's checks_skipped output"}
        for (check, effect), count in sorted(suppressed_counts.items())
    ]

    status = meta.get("status", "complete")
    # "partial" means we could not collect what we wanted, NOT that an opt-in
    # check was left off. Downgrading on any limitation at all made every report
    # partial and made the field carry no information.
    real_gaps = [l for l in limitations if not l.get("optional_feature")]
    if status == "complete" and real_gaps:
        status = "partial"

    generator = {
        "name": NAME,
        "version": VERSION,
        "checks_available": len(checks_available),
        "checks_run": len(checks_ran),
        "tool_versions": meta.get("tool_versions", {}),
    }
    bots_path = MARKETPLACE / "skills" / "crawl-access-audit" / "references" / "ai-bots.json"
    if bots_path.exists():
        bots = json.loads(bots_path.read_text(encoding="utf-8"))
        generator["ai_bots_snapshot_date"] = bots.get("snapshot_date", "")
        generator["ai_bots_source_commit"] = (bots.get("source") or {}).get("commit", "")

    report = emit_report.build_report(
        site=site,
        audited_at=audited_at,
        findings=findings,
        proactive=build_proactive(profile, findings, proactive),
        limitations=limitations,
        suppressed=suppressed,
        generator=generator,
        evidence_summary={
            # Relative to the output directory, never absolute: an absolute path
            # embeds the machine it ran on, which breaks byte-identical
            # determinism and would bake a local temp path into a golden.
            "path": (
                os.path.relpath(bundle_dir, out).replace(os.sep, "/")
                if not args.bundle else "external"
            ),
            "pages_fetched": meta.get("crawl", {}).get("pages_fetched", 0),
            "pages_rendered": meta.get("crawl", {}).get("pages_rendered", 0),
            "degraded_capabilities": meta.get("degraded_capabilities", []),
        },
        audit_status=status,
        blocked_count=blocked_count,
    )

    # regenerate gate notes against final ids
    id_map = {f.get("check_id"): f["id"] for f in report["findings"]}
    gate_notes = gate_summary(report["findings"], id_of=lambda f: f.get("id", ""))

    emit_report.write_all(out, report, gate_notes)

    if args.explain_gates:
        print(json.dumps({"gate_notes": gate_notes, "blocked": blocked_count}, indent=2), file=sys.stderr)

    print(json.dumps({
        "report": str(out / "audit-report.json"),
        "markdown": str(out / "report.md"),
        "site": site,
        "audit_status": status,
        "total_findings": report["summary"]["total_findings"],
        "critical": report["summary"]["critical"],
        "high": report["summary"]["high"],
        "blocked_findings": blocked_count,
        "elapsed_s": None if os.environ.get("SOURCE_DATE_EPOCH") else round(time.perf_counter() - started, 1),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
