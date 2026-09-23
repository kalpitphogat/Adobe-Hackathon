"""Screen a candidate demo URL WITHOUT running the audit engine.

Checks the conditions in SCOUTING.md: robots.txt Crawl-delay, bot-protection
challenge, and how many homepage links leave the host (other subdomains). Fetches
robots.txt and the homepage only, once each.

Usage: python tools/prescreen.py https://candidate.example/ [...]
"""
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
AI_WORDS = re.compile(r"\b(prompt injection|LLM|large language model|AI agent|generative AI)\b", re.I)


def get(url: str) -> tuple[int, dict, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    for url in sys.argv[1:]:
        host = urlparse(url).netloc
        _, _, robots = get(urljoin(url, "/robots.txt"))
        delay = re.findall(r"(?im)^\s*crawl-delay\s*:\s*([\d.]+)", robots)
        status, headers, html = get(url)
        server = (headers.get("Server") or headers.get("server") or "").lower()
        challenge = bool(re.search(r"just a moment|cf-chl|you have been blocked|captcha", html, re.I))
        hrefs = [urljoin(url, h) for h in re.findall(r'<a\s[^>]*href=["\']([^"\'#]+)', html, re.I)]
        hosts = {urlparse(h).netloc for h in hrefs if h.startswith("http")}
        base = ".".join(host.split(".")[-2:])
        sibling = sorted(h for h in hosts if h != host and h.endswith(base))
        ai_hits = len(AI_WORDS.findall(html))
        print(f"{url}\n    status={status} server={server or '-'} crawl_delay={delay or 'none'} "
              f"challenge={challenge} raw_links={len(hrefs)} sibling_subdomains={sibling} ai_terms={ai_hits}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
