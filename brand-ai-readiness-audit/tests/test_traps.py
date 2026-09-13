#!/usr/bin/env python3
"""Trap-guard, URL-hygiene and sampling tests. Standard library only, no network."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "site-evidence-collector" / "scripts"))

import traps  # noqa: E402

FAILURES: list[str] = []
COUNT = 0


def expect(cond: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not cond:
        FAILURES.append(label)


# ------------------------------------------------------------- normalisation

B = "https://example.com/shop/"
expect(traps.normalise_url("/a/b", B) == "https://example.com/a/b", "absolute path resolves")
expect(traps.normalise_url("item", B) == "https://example.com/shop/item", "relative path resolves")
expect(traps.normalise_url("/a#frag", B) == "https://example.com/a", "fragment dropped")
expect(
    traps.normalise_url("/a?utm_source=x&id=7", B) == "https://example.com/a?id=7",
    "tracking params stripped, real params kept",
)
expect(
    traps.normalise_url("/a?b=2&a=1", B) == traps.normalise_url("/a?a=1&b=2", B),
    "query parameter order is normalised",
)
expect(traps.normalise_url("HTTPS://EXAMPLE.COM/A", B) == "https://example.com/A", "host lowercased, path case kept")
expect(traps.normalise_url("https://example.com:443/a", B) == "https://example.com/a", "default port removed")
expect(traps.normalise_url("/a/../b", B) == "https://example.com/b", "dot segments collapsed")
expect(traps.normalise_url("/dir/", B) == "https://example.com/dir/", "trailing slash preserved")

# ------------------------------------------------------------ href classification

H = "example.com"
expect(traps.classify_href("/about", B, H).kind == "internal", "internal link")
expect(traps.classify_href("https://other.test/x", B, H).kind == "external", "external link")
expect(traps.classify_href("https://cdn.example.com/x", B, H).kind == "internal", "subdomain counts as internal")
expect(traps.classify_href("mailto:a@b.test", B, H).kind == "non_http", "mailto is non-http, not malformed")
expect(traps.classify_href("tel:+15551234", B, H).kind == "non_http", "tel is non-http")
expect(traps.classify_href("javascript:void(0)", B, H).kind == "non_http", "javascript scheme rejected")
expect(traps.classify_href("#", B, H).kind == "fragment", "bare fragment")
expect(traps.classify_href("#section", B, H).kind == "fragment", "in-page anchor")

# the cases naive crawlers turn into phantom pages
expect(traps.classify_href("sales@example.com", B, H).kind == "malformed", "bare email in href is malformed")
expect(traps.classify_href("+1 (555) 123-4567", B, H).kind == "malformed", "bare phone in href is malformed")
expect(
    traps.classify_href("221B Baker Street, London", B, H).kind == "malformed",
    "postal address pasted into href is malformed",
)
expect(
    traps.classify_href("sales@example.com", B, H).url is None,
    "a malformed href never yields a URL to crawl",
)

# ------------------------------------------------------------------- traps

def trapped(url: str) -> bool:
    return traps.trap_reason(url) is not None


expect(not trapped("https://example.com/products/widget"), "ordinary page is not a trap")
expect(not trapped("https://example.com/"), "homepage is not a trap")
expect(trapped("https://example.com/team/team/"), "immediately repeating segment")
expect(trapped("https://example.com/a/x/a/x/a/"), "segment repeated three times")
expect(trapped("https://example.com/a/b/c/d/e/f/g/h/i/j"), "excessive depth")
expect(trapped("https://example.com/blog/page/9/"), "deep pagination in path")
expect(not trapped("https://example.com/blog/page/2/"), "shallow pagination is allowed")
expect(trapped("https://example.com/shop?page=12"), "deep pagination in query")
expect(not trapped("https://example.com/shop?page=2"), "shallow pagination in query allowed")
expect(trapped("https://example.com/shop?color=red"), "facet parameter")
expect(trapped("https://example.com/shop?a=1&b=2&c=3&d=4"), "too many query parameters")
expect(trapped("https://example.com/feed/"), "feed endpoint")
expect(trapped("https://example.com/wp-json/wp/v2/posts"), "wp-json infrastructure")
expect(trapped("https://example.com/wp-admin/"), "wp-admin")
expect(trapped("https://example.com/?wc-ajax=get_refreshed_fragments"), "woocommerce ajax")
expect(trapped("https://example.com/?add-to-cart=99"), "cart mutation endpoint")
expect(trapped("https://example.com/cart/"), "cart page")
expect(trapped("https://example.com/checkout/step-2"), "checkout page")
expect(trapped("https://example.com/my-account/orders"), "authenticated area")
expect(trapped("https://example.com/logo.png"), "image extension")
expect(trapped("https://example.com/brochure.pdf"), "pdf extension")
expect(trapped("https://example.com/search?q=shoes"), "search results")
expect(trapped("https://example.com/2024/05/17/"), "date archive leaf")

# ------------------------------------------------------------- soft-404 probes

p1 = traps.probe_urls("https://example.com/")
p2 = traps.probe_urls("https://example.com/")
expect(p1 == p2, "probe URLs are deterministic across runs")
expect(len(p1) == 3, "three probes by default")
expect(traps.probe_urls("https://other.test/") != p1, "probes differ per origin")
expect(all("does-not-exist" in u for u in p1), "probe URLs are self-describing")

hit, why = traps.is_soft_404(404, "", None)
expect(not hit, "a correct 404 is not a soft 404")
hit, why = traps.is_soft_404(200, "Sorry, page not found", None)
expect(hit and "unbounded" in why, "200 with content is a soft 404")
hit, why = traps.is_soft_404(200, "Not found", "Not found")
expect(hit and "status code" in why, "identical-to-404 body is downgraded in wording")

# ------------------------------------------------------------------ sampling

def cand(url, typ, depth=1, inlinks=1):
    return {"url": url, "provisional_type": typ, "depth": depth, "inlinks": inlinks}


# 400 articles, 6 products: stratification must not return 25 articles
many = [cand(f"https://e.test/blog/{i}", "article", 2, 1) for i in range(400)]
many += [cand(f"https://e.test/p/{i}", "product", 2, 5) for i in range(6)]
many += [cand("https://e.test/", "home", 0, 99), cand("https://e.test/contact", "contact", 1, 9)]
sel, how = traps.stratified_sample(many, cap=25)
types = {c["provisional_type"] for c in sel}
expect(how.startswith("stratified"), f"4 types triggers stratification (got {how})")
expect(len(sel) == 25, f"cap respected (got {len(sel)})")
expect("product" in types and "home" in types, "under-represented types survive sampling")
products = sum(1 for c in sel if c["provisional_type"] == "product")
expect(products == 6, f"every available product page is sampled, none starved (got {products})")
expect(
    {"home", "contact", "product", "article"} == types,
    f"all four discovered types are represented (got {sorted(types)})",
)
# Articles legitimately absorb the leftover budget here: products (6/6), home (1/1)
# and contact (1/1) are exhausted, so the share cap has nothing left to protect.
# The invariant that matters is that a type is never starved WHILE another type
# still has unsampled candidates - exercised by the two-large-pools case below.
articles = sum(1 for c in sel if c["provisional_type"] == "article")
expect(articles + products + 2 == 25, f"leftover budget is spent, not wasted (articles={articles})")

# Two large competing pools: neither may crowd the other out.
competing = [cand(f"https://e.test/blog/{i}", "article", 2, 1) for i in range(400)]
competing += [cand(f"https://e.test/p/{i}", "product", 2, 1) for i in range(400)]
competing += [cand(f"https://e.test/d/{i}", "docs", 2, 1) for i in range(400)]
selc, howc = traps.stratified_sample(competing, cap=25)
counts = {t: sum(1 for c in selc if c["provisional_type"] == t) for t in ("article", "product", "docs")}
expect(howc.startswith("stratified"), "three large pools stratify")
expect(
    all(v <= 10 for v in counts.values()),
    f"no type exceeds 40% of budget while others have candidates left (got {counts})",
)
expect(min(counts.values()) >= 5, f"every competing type gets real representation (got {counts})")

# single-archetype blog: the 40% cap cannot bind, so fall back to prominence
blog = [cand(f"https://e.test/post/{i}", "article", depth=2, inlinks=i) for i in range(50)]
sel2, how2 = traps.stratified_sample(blog, cap=25)
expect(how2.startswith("prominence"), f"single type falls back to prominence (got {how2})")
expect(len(sel2) == 25, "cap respected in prominence mode")
expect(
    "https://e.test/post/49" in {c["url"] for c in sel2},
    "prominence mode keeps the most-linked page",
)

# determinism: same input, same output, regardless of input ordering
import random  # noqa: E402

shuffled = many[:]
random.Random(7).shuffle(shuffled)
sel3, _ = traps.stratified_sample(shuffled, cap=25)
expect([c["url"] for c in sel3] == [c["url"] for c in sel], "sampling is order-independent and deterministic")

sel4, how4 = traps.stratified_sample([], cap=25)
expect(sel4 == [] and how4 == "empty", "empty candidate set is handled")

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} trap-guard and sampling assertions")
