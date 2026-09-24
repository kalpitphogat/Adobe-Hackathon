"""Does the JSON-LD offer price appear on the product page (raw HTML text and rendered text)?"""
import json
import re
import sys
import urllib.request

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
url = sys.argv[1]
raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "replace")
prices = []
for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', raw, re.S | re.I):
    try:
        data = json.loads(block)
    except ValueError:
        continue
    for node in data if isinstance(data, list) else [data]:
        offers = node.get("offers") if isinstance(node, dict) else None
        if isinstance(offers, dict):
            prices.append((node.get("@type"), offers.get("price"), offers.get("priceCurrency")))
print("schema offers:", prices)
body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
text = re.sub(r"<[^>]+>", " ", body)
with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    p = b.new_page()
    p.goto(url, wait_until="load", timeout=60000); p.wait_for_timeout(5000)
    rendered = p.inner_text("body")
    b.close()
for _, price, _ in prices:
    whole = str(price).split(".")[0]
    pat = re.compile(rf"(?<!\d){whole}(?:[.,]\d\d)?(?!\d)")
    print(f"price {price}: raw-text hits={len(pat.findall(text))}  rendered-text hits={len(pat.findall(rendered))}")
    for m in list(pat.finditer(rendered))[:3]:
        print("   rendered context:", rendered[max(0, m.start() - 60):m.end() + 20].replace("\n", " | "))

