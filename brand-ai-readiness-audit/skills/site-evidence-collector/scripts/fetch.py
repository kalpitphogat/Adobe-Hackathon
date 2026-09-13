#!/usr/bin/env python3
"""Read-only HTTP fetching with explicit redirect tracking. Standard library only.

Design constraints this module exists to enforce:

  * GET and HEAD only. There is no code path here that can POST, PUT, PATCH or
    DELETE, so no skill in the marketplace can alter a live site even by
    mistake. The `method` argument is validated against an allowlist.
  * No cookies, no credentials, no authentication, no redirect to a non-HTTP
    scheme. We never enter an authenticated area.
  * Hosts that resolve into private, loopback, link-local or otherwise
    non-public address space are refused, on the seed and on every redirect
    hop. An auditor pointed at a public brand has no business reaching an
    internal service, and a redirect is an attacker-controlled way to try.
  * Redirects are followed manually so the full hop chain, with statuses, is
    available as evidence rather than being collapsed by urllib.
  * Cross-host redirects are reported, not silently followed, so the caller can
    decide whether to re-anchor the audit origin.
  * Response bodies are capped. A crawler that streams an unbounded response is
    a crawler that hangs.
"""

from __future__ import annotations

import gzip
import http.client
import io
import ipaddress
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass, field

from politeness import parse_retry_after

__all__ = [
    "FetchResult", "Fetcher", "DEFAULT_UA", "AUDITOR_TOKEN",
    "PrivateAddressRefused", "check_public_host",
]

AUDITOR_TOKEN = "brand-ai-readiness-audit/1.0 (+read-only auditor)"
DEFAULT_UA = f"Mozilla/5.0 (compatible; {AUDITOR_TOKEN})"

ALLOWED_METHODS = frozenset({"GET", "HEAD"})
ALLOWED_SCHEMES = frozenset({"http", "https"})

MAX_BODY_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 10
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class PrivateAddressRefused(Exception):
    """A host resolved into address space an auditor must not reach."""


def _is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Public means routable on the internet and belonging to someone else.

    `is_global` alone is not enough: it is False for some ranges we want to
    refuse for different reasons, and CPython's definition has shifted between
    versions. Refusing each disqualifying property by name keeps the rule
    stable and readable.
    """
    if ip.is_loopback or ip.is_private or ip.is_link_local:
        return False
    if ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        return False
    # IPv4-mapped and 6to4 addresses smuggle a v4 address inside a v6 one.
    mapped = getattr(ip, "ipv4_mapped", None) or getattr(ip, "sixtofour", None)
    if mapped is not None:
        return _is_public(mapped)
    return True


def check_public_host(url: str) -> None:
    """Refuse a URL whose host resolves anywhere outside public address space.

    Called before the seed request and again before every redirect hop, because a
    redirect is the ordinary way a public host hands a crawler an internal one.
    Raises PrivateAddressRefused; a resolution failure is left alone so the
    normal fetch path can report it as the DNS error it is.
    """
    host = urllib.parse.urlsplit(url).hostname
    if not host:
        raise PrivateAddressRefused(f"{url!r} has no host")

    # A literal address needs no lookup, and must not get one: resolving it
    # would let a permissive resolver answer for it.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not _is_public(literal):
            raise PrivateAddressRefused(
                f"{host} is a non-public address; this auditor only audits public sites"
            )
        return

    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return  # not resolvable: let the fetch report the DNS failure itself

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr.split("%", 1)[0])
        except ValueError:
            continue
        if not _is_public(ip):
            raise PrivateAddressRefused(
                f"{host} resolves to {ip}, which is not public address space; "
                f"this auditor only audits public sites"
            )


@dataclass
class Hop:
    url: str
    status: int
    location: str | None = None


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int | None = None
    method: str = "GET"
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    encoding: str = "utf-8"
    hops: list[Hop] = field(default_factory=list)
    ttfb_ms: float | None = None
    elapsed_ms: float | None = None
    error: str | None = None
    tls_error: str | None = None
    truncated: bool = False
    attempts: int = 1

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    @property
    def content_type(self) -> str:
        return (self.headers.get("content-type") or "").split(";")[0].strip().lower()

    @property
    def is_html(self) -> bool:
        return self.content_type in ("text/html", "application/xhtml+xml")

    @property
    def cross_host_redirect(self) -> bool:
        if not self.hops:
            return False
        return _host(self.url) != _host(self.final_url)

    def text(self) -> str:
        if not self.body:
            return ""
        return self.body.decode(self.encoding, errors="replace")


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def _charset_from(headers: dict, body: bytes) -> str:
    ctype = headers.get("content-type") or ""
    m = re.search(r"charset=([A-Za-z0-9_.:-]+)", ctype)
    if m:
        candidate = m.group(1).strip().strip('"').lower()
        try:
            "".encode(candidate)
            return candidate
        except LookupError:
            pass
    head = body[:4096]
    m = re.search(rb'<meta[^>]+charset=["\']?([A-Za-z0-9_.:-]+)', head, re.IGNORECASE)
    if m:
        candidate = m.group(1).decode("ascii", errors="ignore").lower()
        try:
            "".encode(candidate)
            return candidate
        except LookupError:
            pass
    return "utf-8"


def _decompress(body: bytes, encoding: str) -> bytes:
    encoding = (encoding or "").lower().strip()
    try:
        if encoding == "gzip":
            return gzip.GzipFile(fileobj=io.BytesIO(body)).read(MAX_BODY_BYTES)
        if encoding == "deflate":
            try:
                return zlib.decompress(body)
            except zlib.error:
                return zlib.decompress(body, -zlib.MAX_WBITS)
    except (OSError, zlib.error, EOFError):
        return body
    return body


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Disable urllib's automatic redirect following so we can record hops."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


class Fetcher:
    """A polite, read-only HTTP client.

    `throttle` is a politeness.HostThrottle shared across workers. Pass None to
    disable throttling (used only for single-shot probes in tests).
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        timeout: float = 15.0,
        throttle=None,
        max_retries: int = 2,
        verify_tls: bool = True,
        allow_private_hosts: bool = False,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.throttle = throttle
        self.max_retries = max_retries
        self.verify_tls = verify_tls
        # Off by default: auditing a public brand never requires reaching
        # private address space. Opt in only to audit a site you host locally.
        self.allow_private_hosts = allow_private_hosts
        handlers = [_NoRedirect()]
        if not verify_tls:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=ctx))
        # No HTTPCookieProcessor and no auth handler: by construction this
        # opener cannot carry credentials or session state.
        self._opener = urllib.request.build_opener(*handlers)

    # ------------------------------------------------------------------ core

    def _single(self, url: str, method: str, extra_headers: dict | None) -> FetchResult:
        result = FetchResult(url=url, final_url=url, method=method)
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en",
        }
        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(url, method=method, headers=headers)
        started = time.perf_counter()
        try:
            response = self._opener.open(req, timeout=self.timeout)
            first_byte = time.perf_counter()
            status = response.status
            raw_headers = {k.lower(): v for k, v in response.headers.items()}
            body = b""
            if method == "GET":
                body = response.read(MAX_BODY_BYTES + 1)
                if len(body) > MAX_BODY_BYTES:
                    body = body[:MAX_BODY_BYTES]
                    result.truncated = True
            response.close()
        except urllib.error.HTTPError as exc:
            first_byte = time.perf_counter()
            status = exc.code
            raw_headers = {k.lower(): v for k, v in (exc.headers or {}).items()}
            body = b""
            if method == "GET":
                try:
                    body = exc.read(MAX_BODY_BYTES)
                except Exception:  # noqa: BLE001 - body is best-effort on an error response
                    body = b""
        except ssl.SSLCertVerificationError as exc:
            result.error = f"TLS certificate verification failed: {exc}"
            result.tls_error = str(exc)
            result.elapsed_ms = (time.perf_counter() - started) * 1000
            return result
        except ssl.SSLError as exc:
            result.error = f"TLS error: {exc}"
            result.tls_error = str(exc)
            result.elapsed_ms = (time.perf_counter() - started) * 1000
            return result
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            result.error = f"{type(reason).__name__}: {reason}"
            result.elapsed_ms = (time.perf_counter() - started) * 1000
            return result
        except (http.client.HTTPException, OSError, ValueError) as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            result.elapsed_ms = (time.perf_counter() - started) * 1000
            return result

        result.status = status
        result.headers = raw_headers
        result.ttfb_ms = (first_byte - started) * 1000
        body = _decompress(body, raw_headers.get("content-encoding", ""))
        result.body = body
        result.encoding = _charset_from(raw_headers, body)
        result.elapsed_ms = (time.perf_counter() - started) * 1000
        return result

    # ---------------------------------------------------------------- public

    def fetch(
        self,
        url: str,
        method: str = "GET",
        follow_redirects: bool = True,
        max_redirects: int = MAX_REDIRECTS,
        extra_headers: dict | None = None,
        follow_cross_host: bool = False,
    ) -> FetchResult:
        """Fetch one URL, recording the full redirect chain.

        Raises ValueError for a disallowed method or scheme; those are
        programming errors, not runtime conditions.
        """
        method = method.upper()
        if method not in ALLOWED_METHODS:
            raise ValueError(
                f"method {method!r} is not permitted; this auditor is read-only "
                f"and supports only {sorted(ALLOWED_METHODS)}"
            )
        scheme = urllib.parse.urlsplit(url).scheme.lower()
        if scheme not in ALLOWED_SCHEMES:
            raise ValueError(f"scheme {scheme!r} is not permitted")

        hops: list[Hop] = []
        current = url
        origin_host = _host(url)
        attempts_total = 0

        if not self.allow_private_hosts:
            try:
                check_public_host(url)
            except PrivateAddressRefused as exc:
                result = FetchResult(url=url, final_url=url, method=method)
                result.error = f"refused: {exc}"
                return result

        for _ in range(max_redirects + 1):
            result = self._attempt_with_retries(current, method, extra_headers)
            attempts_total += result.attempts
            result.hops = hops
            result.url = url
            result.final_url = current
            result.attempts = attempts_total

            if result.status is None:
                return result
            if not (300 <= result.status < 400) or not follow_redirects:
                return result

            location = result.headers.get("location")
            if not location:
                return result
            nxt = urllib.parse.urljoin(current, location)
            nxt_scheme = urllib.parse.urlsplit(nxt).scheme.lower()
            if nxt_scheme not in ALLOWED_SCHEMES:
                result.error = f"redirect to non-HTTP scheme {nxt_scheme!r} not followed"
                return result

            if not self.allow_private_hosts:
                try:
                    check_public_host(nxt)
                except PrivateAddressRefused as exc:
                    result.final_url = nxt
                    result.error = f"redirect refused: {exc}"
                    return result

            hops.append(Hop(url=current, status=result.status, location=nxt))

            if _host(nxt) != origin_host and not follow_cross_host:
                result.final_url = nxt
                result.error = "cross-host redirect not followed automatically"
                return result

            if nxt == current or any(h.url == nxt for h in hops):
                result.final_url = nxt
                result.error = "redirect loop detected"
                return result
            current = nxt

        result.error = f"exceeded {max_redirects} redirects"
        return result

    def _attempt_with_retries(self, url: str, method: str, extra_headers: dict | None) -> FetchResult:
        host = _host(url)
        backoff = 0.5
        last: FetchResult | None = None
        for attempt in range(self.max_retries + 1):
            if self.throttle is not None:
                self.throttle.wait(host)
            result = self._single(url, method, extra_headers)
            result.attempts = attempt + 1
            last = result

            retryable = result.status in RETRYABLE_STATUS or (
                result.status is None and result.tls_error is None and result.error is not None
            )
            if not retryable or attempt == self.max_retries:
                return result

            retry_after = parse_retry_after(result.headers.get("retry-after", "")) if result.headers else None
            if retry_after is not None and self.throttle is not None:
                self.throttle.penalise(host, retry_after)
                wait = min(retry_after, 30.0)
            else:
                wait = backoff
                backoff *= 2
            time.sleep(min(wait, 30.0))
        return last if last is not None else FetchResult(url=url, final_url=url, error="no attempt made")

    def sample_ttfb(self, url: str, samples: int = 3) -> list[float]:
        """Collect n TTFB samples with HEAD.

        The median of these is the only latency figure any finding may report.
        Reporting a single measurement, or a maximum, would fire on transient
        noise; that suppression rule is enforced at the check, and this method
        is why the check has the data to honour it.
        """
        out: list[float] = []
        for _ in range(max(1, samples)):
            r = self._attempt_with_retries(url, "HEAD", None)
            if r.ttfb_ms is not None:
                out.append(round(r.ttfb_ms, 1))
        return out


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2
