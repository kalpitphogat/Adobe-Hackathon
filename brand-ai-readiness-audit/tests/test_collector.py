#!/usr/bin/env python3
"""S2 gate: evidence bundle schema plus all five hostile-seed cases.

Blocking fix B7 requires that a degenerate seed never crashes and always
produces a usable bundle. Blocking fix F6 requires that the exit code report
only whether a bundle was written, never what the bundle contains.

Run: python tests/test_collector.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECT = ROOT / "skills" / "site-evidence-collector" / "scripts" / "collect.py"
FIXTURES = ROOT / "tests" / "fixtures"

FAILURES: list[str] = []
COUNT = 0


def expect(cond: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not cond:
        FAILURES.append(label)


def run_collect(args: list[str], out: Path) -> tuple[int, str, str]:
    env = dict(os.environ, SOURCE_DATE_EPOCH="1780000000", PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, str(COLLECT), *args, "--out", str(out)],
        capture_output=True, text=True, env=env, cwd=str(ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr


def load_bundle(out: Path) -> tuple[dict, list[dict], dict, dict]:
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    pages = [json.loads(l) for l in (out / "pages.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    probes = json.loads((out / "probes.json").read_text(encoding="utf-8"))
    sitemap = json.loads((out / "sitemap.json").read_text(encoding="utf-8"))
    return meta, pages, probes, sitemap


REQUIRED_META = {
    "schema_version", "audited_at", "seed_url", "resolved_origin", "status",
    "notes", "tool_versions", "crawl", "degraded_capabilities",
}
REQUIRED_CRAWL = {
    "pages_requested", "pages_fetched", "pages_rendered", "workers",
    "per_host_delay_s", "sample_strategy", "robots_respected", "robots_status",
    "urls_skipped_by_robots", "urls_skipped_by_traps", "malformed_hrefs",
}
REQUIRED_PAGE = {
    "url", "status", "title", "wordcount", "main_wordcount", "headings", "links",
    "images", "forms", "markup", "meta_robots", "canonical", "dates", "page_type",
    "rendered_available",
}
REQUIRED_PROBES = {
    "soft_404", "real_404_sample", "llms_txt", "markdown_negotiation",
    "bot_reach", "ttfb_samples_ms",
}

tmp = Path(tempfile.mkdtemp(prefix="bara-s2-"))
try:
    # ---------------------------------------------------- bundle contract

    out = tmp / "site_a"
    code, stdout, stderr = run_collect(["--offline-root", str(FIXTURES / "site_a")], out)
    expect(code == 0, f"site_a exits 0 (got {code}; stderr={stderr[:300]})")
    meta, pages, probes, sitemap = load_bundle(out)

    expect(REQUIRED_META.issubset(meta), f"meta.json has all required keys (missing {REQUIRED_META - set(meta)})")
    expect(REQUIRED_CRAWL.issubset(meta["crawl"]), f"meta.crawl complete (missing {REQUIRED_CRAWL - set(meta['crawl'])})")
    expect(REQUIRED_PROBES.issubset(probes), f"probes.json complete (missing {REQUIRED_PROBES - set(probes)})")
    expect(all(REQUIRED_PAGE.issubset(p) for p in pages), "every page row has the required keys")
    expect(meta["status"] == "complete", f"healthy site is complete (got {meta['status']})")
    expect(len(pages) == 8, f"all 8 routes crawled (got {len(pages)})")
    expect(meta["crawl"]["robots_respected"] is True, "robots_respected flag set")
    expect((out / "robots.txt").read_text(encoding="utf-8").startswith("# Northwind"), "robots.txt stored verbatim")

    # ordering guarantees that make byte-identical output possible
    expect([p["url"] for p in pages] == sorted(p["url"] for p in pages), "pages.jsonl is sorted by url")
    expect(
        meta["crawl"]["urls_skipped_by_traps"] == sorted(meta["crawl"]["urls_skipped_by_traps"], key=lambda r: r["url"]),
        "trap skips are sorted",
    )

    # render pairs exist for rendered pages only
    rendered = [p for p in pages if p["rendered_available"]]
    expect(len(rendered) >= 3, f"at least 3 pages rendered from fixture pairs (got {len(rendered)})")
    expect(
        all((out / p["rendered_html_path"]).exists() for p in rendered),
        "every rendered page has its .rendered.html on disk",
    )
    expect(
        any(p["url"].endswith("/pricing") and p["rendered_available"] for p in pages),
        "render priority reaches /pricing rather than spending the budget on /about",
    )

    # the healthy site must not look like an SPA shell anywhere
    expect(not any(p.get("looks_like_spa_shell") for p in pages), "no false SPA-shell positive on the healthy site")
    expect(probes["bot_reach"]["enabled"] is False, "bot-UA probing is OFF by default")
    expect(len(probes["ttfb_samples_ms"]) == 3, "three TTFB samples collected, so the median rule can be honoured")
    expect(all(s["is_soft_404"] is False for s in probes["soft_404"]), "correct 404s are not soft-404 positives")

    # determinism: two runs of the same fixture are byte-identical
    out2 = tmp / "site_a_again"
    run_collect(["--offline-root", str(FIXTURES / "site_a")], out2)
    a = (out / "pages.jsonl").read_bytes()
    b = (out2 / "pages.jsonl").read_bytes()
    expect(a == b, "two collector runs produce byte-identical pages.jsonl")
    expect(
        (out / "meta.json").read_bytes() == (out2 / "meta.json").read_bytes(),
        "two collector runs produce byte-identical meta.json",
    )

    # ------------------------------------------- site_b: gate cascade input

    out_b = tmp / "site_b"
    code, _, stderr = run_collect(["--offline-root", str(FIXTURES / "site_b")], out_b)
    expect(code == 0, f"site_b exits 0 (got {code}; {stderr[:200]})")
    meta_b, pages_b, _, _ = load_bundle(out_b)
    expect(len(pages_b) == 4, f"site_b crawled 4 pages (got {len(pages_b)})")
    expect(
        meta_b["crawl"]["urls_skipped_by_robots"] == [],
        "our auditor is allowed by site_b robots.txt even though the AI bots are not",
    )
    robots_b = (out_b / "robots.txt").read_text(encoding="utf-8")
    expect("OAI-SearchBot" in robots_b, "site_b robots.txt captured for the reach checks")
    # site_b is the CASCADE fixture and deliberately carries no training or
    # dual-purpose directives; those live in site_e, the taxonomy fixture, so a
    # change to one proof cannot silently alter the other.
    expect(
        "GPTBot" not in robots_b and "Google-Extended" not in robots_b,
        "site_b stays cascade-only: taxonomy directives belong to site_e",
    )
    robots_e = (FIXTURES / "site_e" / "robots.txt").read_text(encoding="utf-8")
    expect(
        "GPTBot" in robots_e and "Google-Extended" in robots_e and "OAI-SearchBot" not in robots_e,
        "site_e stays taxonomy-only: it blocks no retrieval crawler",
    )

    # ------------------------------- site_c: blanket disallow, F6 exit code

    out_c = tmp / "site_c"
    code, _, stderr = run_collect(["--offline-root", str(FIXTURES / "site_c")], out_c)
    expect(code == 0, f"blanket-disallow site still exits 0 (got {code}; {stderr[:200]})")
    meta_c, pages_c, _, _ = load_bundle(out_c)
    expect(meta_c["status"] == "no_content_available", f"status is no_content_available (got {meta_c['status']})")
    expect(pages_c == [], f"NOT ONE page fetched when robots.txt forbids it (got {len(pages_c)})")
    expect(len(meta_c["degraded_capabilities"]) >= 1, "the blocked crawl is recorded as a degraded capability")
    expect(
        any("robots" in n.lower() for n in meta_c["notes"]),
        "notes explain that robots.txt is a hard constraint on our own crawling",
    )
    expect((out_c / "robots.txt").read_text(encoding="utf-8").strip().endswith("Disallow: /"),
           "robots.txt itself is still captured, so the policy can be reported")

    # ------------------------------------- site_d: all-SPA, no renderer (F4)

    out_d = tmp / "site_d"
    code, _, stderr = run_collect(["--offline-root", str(FIXTURES / "site_d")], out_d)
    expect(code == 0, f"all-SPA site exits 0 (got {code}; {stderr[:200]})")
    meta_d, pages_d, _, _ = load_bundle(out_d)
    expect(len(pages_d) >= 4, f"all-SPA site crawled (got {len(pages_d)})")
    expect(
        all(p["looks_like_spa_shell"] for p in pages_d if p["status"] == 200),
        "every 200 page on site_d is detected as an unhydrated shell",
    )
    expect(
        not any(p["rendered_available"] for p in pages_d),
        "site_d has no rendered pair for any page, which is what F4 needs",
    )
    expect(
        any(d["capability"] == "rendered_dom" for d in meta_d["degraded_capabilities"]),
        "missing renderer is recorded as a degraded capability, not silently skipped",
    )

    # ------------------------------------------------ B7 hostile seed cases

    hostile = FIXTURES / "hostile"
    cases = [
        ("nxdomain", "https://hostile.test/nxdomain", "no_content_available"),
        ("404 seed", "https://hostile.test/gone", "no_content_available"),
        ("500 seed", "https://hostile.test/broken", "no_content_available"),
        ("pdf seed", "https://hostile.test/brochure.pdf", "no_content_available"),
        ("offsite redirect", "https://hostile.test/offsite", None),
    ]
    for label, seed, expected_status in cases:
        out_h = tmp / ("hostile_" + label.replace(" ", "_"))
        code, stdout, stderr = run_collect([seed, "--offline-root", str(hostile)], out_h)
        expect(code == 0, f"[{label}] exits 0 because a bundle was written (got {code}; {stderr[:200]})")
        expect("Traceback" not in stderr, f"[{label}] no traceback leaked to stderr")
        expect((out_h / "meta.json").exists(), f"[{label}] wrote meta.json")
        expect((out_h / "pages.jsonl").exists(), f"[{label}] wrote pages.jsonl")
        m, _, pr, _ = load_bundle(out_h)
        expect(REQUIRED_META.issubset(m), f"[{label}] meta.json is still schema-complete")
        expect(REQUIRED_PROBES.issubset(pr), f"[{label}] probes.json is still schema-complete")
        if expected_status:
            expect(m["status"] == expected_status, f"[{label}] status is {expected_status} (got {m['status']})")
            expect(len(m["notes"]) >= 1, f"[{label}] records a human-readable note explaining what happened")
            expect(
                len(m["degraded_capabilities"]) >= 1,
                f"[{label}] records a degraded capability so downstream checks downgrade rather than skip",
            )

    # the offsite case must re-anchor rather than audit the wrong host
    out_o = tmp / "hostile_offsite_redirect"
    m_o, _, _, _ = load_bundle(out_o)
    expect(
        any("re-anchor" in n for n in m_o["notes"]),
        f"[offsite redirect] re-anchors the audit origin and says so (notes={m_o['notes']})",
    )
    expect(
        m_o["resolved_origin"] == "https://elsewhere.test",
        f"[offsite redirect] origin moved to the final host (got {m_o['resolved_origin']})",
    )

    # ------------------------------------------------------ CLI contract

    code, stdout, _ = run_collect(["--offline-root", str(FIXTURES / "site_a"), "--dry-run"], tmp / "dry")
    expect(code == 0, "--dry-run exits 0")
    plan = json.loads(stdout)
    expect(plan["writes_to_target_site"] is False, "--dry-run states plainly that nothing is written to the site")

    proc = subprocess.run([sys.executable, str(COLLECT), "--help"], capture_output=True, text=True, cwd=str(ROOT))
    expect(proc.returncode == 0 and "--probe-bot-ua" in proc.stdout, "--help works and documents the opt-in flag")

    proc = subprocess.run([sys.executable, str(COLLECT), "--out", str(tmp / "x")], capture_output=True, text=True, cwd=str(ROOT))
    expect(proc.returncode == 3, f"missing seed is a precondition failure, exit 3 (got {proc.returncode})")

    proc = subprocess.run(
        [sys.executable, str(COLLECT), "ftp://example.com", "--out", str(tmp / "y")],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    expect(proc.returncode == 3, f"non-http seed is exit 3 (got {proc.returncode})")

finally:
    shutil.rmtree(tmp, ignore_errors=True)

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} collector and hostile-seed assertions")
