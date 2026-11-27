#!/usr/bin/env python3
# This source file is part of the Schmiedmayer Lab open-source organization
# SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
# SPDX-License-Identifier: MIT

"""Retry transient external failures and resolve opted-in public 403 diagnostics.

Linkspector 0.5 embeds URL/status in RDJSON messages. Unknown messages remain
errors. Globalping measurements are public; never submit credentials or queries.

External links that Linkspector reports with HTTP 408, 429, or 5xx are retried
with a direct GET of up to 15 seconds per attempt, after waits of 2, 8, and 30
seconds. A Retry-After on a 429 or 503 answer extends the next wait for that
link, and a link whose Retry-After exceeds the remaining budget is not retried
further. Retries cover at most 25 unique URLs within about 150 seconds.

- A 2xx answer resolves the finding.
- A 404 or other 4xx answer fails the check.
- A 403 answer, a redirect (retries do not follow redirects), a link that stays
  unavailable or gets no response, a link beyond the limits, and a host that
  needs IDNA 2008 (such as one with ß or ς) become unverified warnings.
- Missing local files, DNS or connection failures, browser timeouts without an
  HTTP status, and every other status in Linkspector's own report fail the check.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from enum import Enum
import html
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import re
import threading
import time
import unicodedata
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


API = "https://api.globalping.io/v1/measurements"
FORBIDDEN = re.compile(r"Cannot reach (https?://\S+) Status: 403(?: .*)?", re.DOTALL)
HOST = re.compile(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
MAX_URLS = 10
# Timeouts, rate limits, and server errors from external hosts are retried
# directly; local files, DNS failures, and other statuses keep Linkspector's result.
TRANSIENT = re.compile(r"Cannot reach (https?://\S+) Status: (408|429|5\d\d)(?: .*)?", re.DOTALL)
RETRY_DELAYS = (2, 8, 30)
RETRY_TIMEOUT = 15
RETRY_BUDGET = 150
MAX_RETRY_URLS = 25
USER_AGENT = "SchmiedmayerLab-link-check/1.0"
# IDNA 2003 maps these characters to a different host than browsers, which use IDNA 2008.
IDNA_DEVIATIONS = frozenset("ßς\u200c\u200d")
URL_SAFE = ":/?#[]@!$&'()*+,;=%~"


class Outcome(str, Enum):
    VERIFIED = "verified"
    BROKEN = "broken"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class Finding:
    outcome: Outcome
    reason: str
    measurement: str = ""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(url: str, payload: dict | None = None) -> dict:
    # Only contact the fixed API, never a URL supplied by a report or response.
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
    with build_opener(NoRedirects()).open(request, timeout=10) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise ValueError("Invalid Globalping response")
    return value


def allowed_hosts(value: str) -> set[str]:
    hosts = {host.strip().lower() for host in value.split(",") if host.strip()}
    if any(not HOST.fullmatch(host) or host.endswith((".localhost", ".local", ".internal")) for host in hosts):
        raise ValueError("Fallback hosts must be exact public DNS names, without wildcards or URLs")
    return hosts


def measurement_payload(url: str, hosts: set[str]) -> dict | None:
    try:
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.hostname not in hosts or parts.username is not None
                or parts.password is not None or parts.port not in (None, 443)
                or parts.query or parts.fragment or any(char.isspace() for char in url)):
            return None
    except ValueError:
        return None  # A malformed URL keeps Linkspector's error.
    return {"type": "http", "target": parts.hostname, "limit": 2,
            "locations": [{"magic": "eyeball-network"}],
            "measurementOptions": {"protocol": "HTTPS", "request": {"method": "GET", "path": parts.path or "/"}}}


def classify_measurement(report: dict) -> Finding:
    results = report.get("results", [])
    if report.get("status") != "finished" or not isinstance(results, list) or len(results) != 2:
        return Finding(Outcome.UNVERIFIED, "Incomplete measurement")
    codes = []
    for entry in results:
        result = entry.get("result", {})
        if result.get("status") != "finished" or (result.get("tls") or {}).get("authorized") is not True:
            return Finding(Outcome.UNVERIFIED, "Probe failed or TLS was not verified")
        code = result.get("statusCode")
        if type(code) is not int:
            return Finding(Outcome.UNVERIFIED, "Missing destination HTTP status")
        codes.append(code)
    if all(200 <= code < 300 for code in codes):
        return Finding(Outcome.VERIFIED, "Both probes reached the URL with verified TLS")
    if all(code in (404, 410) for code in codes):
        return Finding(Outcome.BROKEN, "Both probes returned 404/410")
    return Finding(Outcome.UNVERIFIED, "Probe HTTP statuses: " + ", ".join(map(str, codes)))


def verify(url: str, hosts: set[str]) -> Finding:
    payload = measurement_payload(url, hosts)
    if payload is None:
        return Finding(Outcome.UNVERIFIED, "URL not eligible for public measurement")
    measurement = ""
    try:
        created = request_json(API, payload)
        identifier = created.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identifier):
            raise ValueError("Invalid measurement ID")
        measurement = f"{API}/{identifier}"
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            report = request_json(measurement)
            if report.get("status") != "in-progress":
                finding = classify_measurement(report)
                return Finding(finding.outcome, finding.reason, measurement)
            time.sleep(1)
        return Finding(Outcome.UNVERIFIED, "Measurement timed out", measurement)
    except (URLError, TimeoutError, ValueError, TypeError, AttributeError):
        return Finding(Outcome.UNVERIFIED, "Globalping unavailable or returned invalid results", measurement)


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (TypeError, ValueError, IndexError, OverflowError):
            return None
    return max(0.0, seconds) if math.isfinite(seconds) else None


def request_url(url: str) -> str:
    """Return the link with an IDNA host, no userinfo, and a percent-encoded path, query, and fragment."""
    parts = urlsplit(url)
    # Python's idna codec implements IDNA 2003; hosts it rejects raise UnicodeError, a ValueError.
    host = (parts.hostname or "").encode("idna").decode("ascii")
    netloc = f"[{host}]" if ":" in host else host
    if parts.port is not None:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, *(quote(part, safe=URL_SAFE)
                                              for part in (parts.path, parts.query, parts.fragment))))


def fetch(url: str) -> tuple[int | None, float | None]:
    try:
        # Markdown links can contain non-ASCII characters, which urllib cannot send as written.
        request = Request(request_url(url), headers={"User-Agent": USER_AGENT})
        # Redirects are never followed, so a redirect answer is reported as its 3xx status.
        with build_opener(NoRedirects()).open(request, timeout=RETRY_TIMEOUT) as response:
            return response.status, None
    except HTTPError as error:
        wait = (parse_retry_after(error.headers.get("Retry-After"))
                if error.code in (429, 503) and error.headers else None)
        error.close()
        return error.code, wait
    except (URLError, HTTPException, OSError, ValueError):
        return None, None


def probe(url: str) -> tuple[int | None, float | None]:
    """Return the final HTTP status of a GET and any Retry-After delay; no status when nothing arrived in time."""
    answer: list = []

    def run() -> None:
        try:
            answer.append(fetch(url))
        except BaseException as error:  # Re-raised below so unexpected failures still fail the job.
            answer.append(error)

    # The socket timeout bounds each read, not the whole response; a server can drip bytes past it.
    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(RETRY_TIMEOUT)
    if not answer:
        return None, None
    if isinstance(answer[0], BaseException):
        raise answer[0]
    return answer[0]


def needs_idna_2008(url: str) -> bool:
    """Whether the host has characters that the IDNA 2003 codec maps to a different host."""
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        return False  # The probe reports a malformed URL as no response.
    return bool(IDNA_DEVIATIONS & set(unicodedata.normalize("NFKC", host)))


def retry(urls: list[str]) -> dict[str, Finding]:
    """Retry each URL with backoff until it answers with a non-transient status."""
    findings = {url: Finding(Outcome.UNVERIFIED, "Retry limit reached") for url in urls[MAX_RETRY_URLS:]}
    start = time.monotonic()
    deadline = start + RETRY_BUDGET
    due = {}
    for url in urls[:MAX_RETRY_URLS]:
        if needs_idna_2008(url):
            findings[url] = Finding(Outcome.UNVERIFIED, "Host needs IDNA 2008, so it is not retried")
        else:
            due[url] = start + RETRY_DELAYS[0]
    attempts = dict.fromkeys(due, 0)
    last = dict.fromkeys(due, "")
    while due:
        url = min(due, key=due.__getitem__)
        if max(due[url], time.monotonic()) > deadline:
            del due[url]
            findings[url] = Finding(Outcome.UNVERIFIED, f"Still unavailable on retry ({last[url]})" if last[url]
                                    else "Retry time budget reached")
            continue
        time.sleep(max(0.0, due[url] - time.monotonic()))
        code, wait = probe(url)
        attempts[url] += 1
        if code is None or code in (408, 429) or code >= 500:
            last[url] = "no response" if code is None else f"HTTP {code}"
            now = time.monotonic()
            delay = RETRY_DELAYS[attempts[url]] if attempts[url] < len(RETRY_DELAYS) else math.inf
            if now + max(delay, wait or 0.0) <= deadline:
                due[url] = now + max(delay, wait or 0.0)
                continue
            del due[url]
            findings[url] = Finding(Outcome.UNVERIFIED, f"Retry-After exceeds the retry budget ({last[url]})"
                                    if now + delay <= deadline else f"Still unavailable on retry ({last[url]})")
            continue
        del due[url]
        if 200 <= code < 300:
            findings[url] = Finding(Outcome.VERIFIED, f"HTTP {code} on retry")
        elif code == 403 or code < 400:
            # Deliberate exceptions: a direct request can be blocked (403) where the browser was
            # not, and a redirect (3xx) is not followed, so these warn. Every other 4xx fails.
            findings[url] = Finding(Outcome.UNVERIFIED, f"HTTP {code} on retry")
        else:
            findings[url] = Finding(Outcome.BROKEN, f"HTTP {code} on retry")
    return {url: findings[url] for url in urls}


def read_diagnostics(report: dict, exit_code: int) -> list[dict]:
    if not isinstance(report, dict) or not isinstance(report.get("diagnostics"), list):
        raise ValueError("Linkspector did not produce a complete RDJSON report")
    diagnostics = report["diagnostics"]
    for item in diagnostics:
        if (not isinstance(item, dict) or not isinstance(item.get("message"), str)
                or item.get("severity", report.get("severity")) not in ("ERROR", "WARNING", "INFO")):
            raise ValueError("Invalid Linkspector diagnostic")
        item.setdefault("severity", report.get("severity"))
    errors = any(item["severity"] == "ERROR" for item in diagnostics)
    if exit_code not in (0, 1) or (exit_code == 1) != errors:
        raise ValueError("Linkspector failed unexpectedly or returned inconsistent results")
    return diagnostics


def process(report: dict, exit_code: int, hosts: set[str]) -> dict:
    diagnostics = read_diagnostics(report, exit_code)
    transient = [(item, match[1]) for item in diagnostics if item["severity"] == "ERROR"
                 and (match := TRANSIENT.fullmatch(item["message"]))]
    urls = list(dict.fromkeys(url for _, url in transient))
    retries = retry(urls) if urls else {}
    for item, url in transient:
        annotate(item, url, retries[url])
    findings: dict[str, Finding] = {}
    for item in diagnostics:
        match = FORBIDDEN.fullmatch(item["message"])
        if item["severity"] != "ERROR" or not match:
            continue
        url = match[1]
        # Opt-in governs disclosure and downgrading of 403 results.
        # Retried diagnostics have a rewritten message and do not match.
        if measurement_payload(url, hosts) is None:
            continue
        if url not in findings:
            findings[url] = (verify(url, hosts) if len(findings) < MAX_URLS else
                             Finding(Outcome.UNVERIFIED, "Fallback limit reached"))
        annotate(item, url, findings[url])
    return {"diagnostics": diagnostics, "retries": {url: asdict(result) for url, result in retries.items()},
            "fallbacks": {url: asdict(result) for url, result in findings.items()}}


def annotate(item: dict, url: str, finding: Finding) -> None:
    item["severity"] = {Outcome.VERIFIED: "INFO", Outcome.BROKEN: "ERROR", Outcome.UNVERIFIED: "WARNING"}[finding.outcome]
    item["message"] = f"{finding.outcome.value}: {url}: {finding.reason}"


def escape_annotation(value: str, *, property_value: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return value.replace(",", "%2C").replace(":", "%3A") if property_value else value


def emit(result: dict) -> None:
    for item in result["diagnostics"]:
        level = {"ERROR": "error", "WARNING": "warning", "INFO": "notice"}[item["severity"]]
        location = item.get("location", {})
        properties = ""
        if isinstance(location.get("path"), str):
            properties = " file=" + escape_annotation(location["path"], property_value=True)
            line = location.get("range", {}).get("start", {}).get("line")
            if type(line) is int and line > 0:
                properties += f",line={line}"
        print(f"::{level}{properties}::{escape_annotation(item['message'])}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as file:
            if result.get("retries"):
                file.write("### Retried external links\n\n")
                for url, item in result["retries"].items():
                    file.write(f"- {Outcome(item['outcome']).value}: <code>{html.escape(url)}</code>: {html.escape(item['reason'])}\n")
                file.write("\n")
            file.write("### External link verification\n\n")
            for url, item in result["fallbacks"].items():
                file.write(f"- {Outcome(item['outcome']).value}: <code>{html.escape(url)}</code>: {html.escape(item['reason'])}\n")
                if item["measurement"]:
                    file.write(f"  [Measurement]({item['measurement']})\n")
            if not result["fallbacks"]:
                file.write("No eligible HTTP 403 results required secondary verification.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--checker-exit-code", type=int, required=True)
    parser.add_argument("--hosts", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text())
        result = process(report, args.checker_exit_code, allowed_hosts(args.hosts))
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        emit(result)
        return int(any(item["severity"] == "ERROR" for item in result["diagnostics"]))
    except (OSError, ValueError, TypeError, AttributeError) as error:
        print(f"::error::{escape_annotation(str(error))}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
