#!/usr/bin/env python3
# This source file is part of the Schmiedmayer Lab open-source organization
# SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
# SPDX-License-Identifier: MIT

"""Resolve opted-in public 403 diagnostics without suppressing other link errors.

Linkspector 0.5 embeds URL/status in RDJSON messages. Unknown messages remain
errors. Globalping measurements are public; never submit credentials or queries.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from enum import Enum
import html
import json
import os
from pathlib import Path
import re
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


API = "https://api.globalping.io/v1/measurements"
FORBIDDEN = re.compile(r"Cannot reach (https?://\S+) Status: 403(?: .*)?", re.DOTALL)
HOST = re.compile(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
MAX_URLS = 10


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
                      headers={"Content-Type": "application/json", "User-Agent": "SchmiedmayerLab-link-check/1.0"})
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
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname not in hosts or parts.username is not None
            or parts.password is not None or parts.port not in (None, 443)
            or parts.query or parts.fragment or any(char.isspace() for char in url)):
        return None
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
    findings: dict[str, Finding] = {}
    for item in diagnostics:
        match = FORBIDDEN.fullmatch(item["message"])
        if item["severity"] != "ERROR" or not match:
            continue
        url = match[1]
        # Opt-in governs disclosure AND downgrading. All other diagnostics stay errors.
        if measurement_payload(url, hosts) is None:
            continue
        if url not in findings:
            findings[url] = (verify(url, hosts) if len(findings) < MAX_URLS else
                             Finding(Outcome.UNVERIFIED, "Fallback limit reached"))
        finding = findings[url]
        item["severity"] = {Outcome.VERIFIED: "INFO", Outcome.BROKEN: "ERROR", Outcome.UNVERIFIED: "WARNING"}[finding.outcome]
        item["message"] = f"{finding.outcome.value}: {url} — {finding.reason}"
    return {"diagnostics": diagnostics, "fallbacks": {url: asdict(result) for url, result in findings.items()}}


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
            file.write("### External link verification\n\n")
            for url, item in result["fallbacks"].items():
                file.write(f"- {item['outcome']}: <code>{html.escape(url)}</code> — {html.escape(item['reason'])}\n")
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
