#!/usr/bin/env python3
"""An auditor pointed at a public brand must not reach internal address space.

The handout scopes this marketplace to public websites and forbids
authenticated-area access. A crawler that follows any host it is handed is one
redirect away from an internal service, and the redirect is the interesting
case: the seed can be a perfectly ordinary public hostname whose 302 points at
169.254.169.254 or 10.x. So the guard runs on the seed AND on every hop.

The escape hatch (--allow-private-hosts) exists because auditing a site you
host locally is legitimate. It is off by default, which is the part that
matters.

Run: python tests/test_ssrf.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "site-evidence-collector" / "scripts"))

from fetch import (  # noqa: E402
    Fetcher,
    PrivateAddressRefused,
    check_public_host,
)

FAILURES: list[str] = []
COUNT = 0


def expect(cond: bool, label: str) -> None:
    global COUNT
    COUNT += 1
    if not cond:
        FAILURES.append(label)


def refuses(url: str) -> bool:
    try:
        check_public_host(url)
    except PrivateAddressRefused:
        return True
    return False


# ------------------------------------------------------- must be refused

REFUSE = [
    ("http://127.0.0.1/", "IPv4 loopback"),
    ("http://127.1/", "short-form loopback"),
    ("https://localhost/", "localhost by name"),
    ("http://10.0.0.1/", "RFC 1918 10/8"),
    ("http://172.16.0.1/", "RFC 1918 172.16/12"),
    ("http://192.168.1.1/", "RFC 1918 192.168/16"),
    ("http://169.254.169.254/latest/meta-data/", "link-local cloud metadata"),
    ("http://0.0.0.0/", "unspecified address"),
    ("http://[::1]/", "IPv6 loopback"),
    ("http://[fe80::1]/", "IPv6 link-local"),
    ("http://[fc00::1]/", "IPv6 unique-local"),
    ("http://[::ffff:127.0.0.1]/", "IPv4-mapped loopback smuggled through IPv6"),
    ("http://[::ffff:10.0.0.1]/", "IPv4-mapped RFC 1918 smuggled through IPv6"),
    ("http://224.0.0.1/", "multicast"),
    ("http://240.0.0.1/", "reserved"),
]
for url, label in REFUSE:
    expect(refuses(url), f"S1: {label} ({url}) must be refused")

# A literal address must never be resolved. If it were, a resolver that answers
# for numeric strings could launder a private address past the check.
expect(refuses("http://127.0.0.1:8080/anything?x=1#f"),
       "S2: port, path, query and fragment do not smuggle a literal past the guard")


# ------------------------------------------------------- must be allowed

for url in ("https://example.com/", "http://93.184.216.34/", "http://[2606:2800:220:1:248:1893:25c8:1946]/"):
    expect(not refuses(url), f"S3: public address {url} must be allowed")

# A host that does not resolve is not a private-address problem. Refusing it
# here would report the wrong cause; the fetch path reports the DNS failure.
expect(not refuses("https://this-host-does-not-exist.invalid/"),
       "S4: an unresolvable host is left for the fetch path to report as DNS")


# ------------------------------------------------------- wired into Fetcher

guarded = Fetcher(throttle=None)
expect(guarded.allow_private_hosts is False,
       "S5: the guard is ON by default, without being asked for")

result = guarded.fetch("http://169.254.169.254/latest/meta-data/")
expect(result.status is None and result.error and "refused" in result.error,
       "S6: a guarded fetch of cloud metadata returns a refusal, not a response")
expect(result.error and "not public" in result.error.lower() or
       result.error and "non-public" in result.error.lower(),
       "S6: the refusal says why, so it is not mistaken for a network error")

opted_in = Fetcher(throttle=None, allow_private_hosts=True)
expect(opted_in.allow_private_hosts is True,
       "S7: --allow-private-hosts is honoured for a site you host yourself")

# The guard must not be reachable only through the seed: a public seed that
# redirects inward is the attack that matters, and fetch() re-checks each hop.
src = (ROOT / "skills" / "site-evidence-collector" / "scripts" / "fetch.py").read_text(encoding="utf-8")
redirect_block = src.split("hops.append(")[0]
expect(redirect_block.count("check_public_host") >= 2,
       "S8: redirect hops are re-checked, not just the seed")

# Read-only is a construction property, not a convention: keep it asserted here
# so a future change to the transport cannot quietly widen it.
expect(guarded.fetch.__doc__ and "read-only" in src.lower(),
       "S9: the transport still documents and enforces read-only")
for verb in ("POST", "PUT", "PATCH", "DELETE"):
    try:
        guarded.fetch("https://example.com/", method=verb)
        ok = False
    except ValueError:
        ok = True
    expect(ok, f"S10: {verb} is rejected by the method allowlist")

if FAILURES:
    print(f"FAILED {len(FAILURES)} of {COUNT} assertions:\n")
    for f in FAILURES:
        print("  - " + f)
    sys.exit(1)
print(f"PASS: {COUNT} private-address and read-only transport assertions")
