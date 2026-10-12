# This source file is part of the Schmiedmayer Lab open-source organization
# SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
# SPDX-License-Identifier: MIT

import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

import check_links as links
import live_check


URL = "https://docs.example.org/guide/"
HOSTS = {"docs.example.org"}


def diagnostic(url=URL, code=403):
    return {"severity": "ERROR", "message": f"Cannot reach {url} Status: {code}",
            "location": {"path": "README.md", "range": {"start": {"line": 12}}}}


def measurement(*codes, authorized=True):
    return {"status": "finished", "results": [
        {"result": {"status": "finished", "statusCode": code, "tls": {"authorized": authorized}}}
        for code in codes]}


class FallbackTests(unittest.TestCase):
    def test_payload_preserves_exact_path(self):
        payload = links.measurement_payload(URL, HOSTS)
        self.assertEqual(payload["measurementOptions"]["request"], {"method": "GET", "path": "/guide/"})
        self.assertEqual(payload["target"], "docs.example.org")
        self.assertEqual(payload["locations"], [{"magic": "eyeball-network"}])
        self.assertEqual(payload["limit"], 2)

    def test_private_or_unsupported_urls_are_not_submitted(self):
        urls = ["http://docs.example.org/", URL + "?key=private", URL + "#heading",
                "https://user:password@docs.example.org/", "https://docs.example.org:8443/",
                "https://docs.example.org.attacker.example/", "https://127.0.0.1/",
                "https://169.254.169.254/", "https://other.example.org/"]
        for url in urls:
            with self.subTest(url=url), patch.object(links, "verify") as verify:
                result = links.process({"diagnostics": [diagnostic(url)]}, 1, HOSTS)
                verify.assert_not_called()
                self.assertEqual(result["diagnostics"][0]["severity"], "ERROR")

    def test_host_configuration(self):
        self.assertEqual(links.allowed_hosts("Docs.Example.org, docs.example.org"), HOSTS)
        self.assertEqual(links.allowed_hosts(""), set())
        for value in ["*.example.org", "https://example.org", "localhost", "127.0.0.1", "api.local"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                links.allowed_hosts(value)

    def test_destination_status_not_api_success_determines_outcome(self):
        cases = [((200, 200), links.Outcome.VERIFIED), ((404, 410), links.Outcome.BROKEN),
                 ((403, 403), links.Outcome.UNVERIFIED), ((200, 404), links.Outcome.UNVERIFIED),
                 ((301, 301), links.Outcome.UNVERIFIED), ((500, 500), links.Outcome.UNVERIFIED),
                 ((200,), links.Outcome.UNVERIFIED), ((), links.Outcome.UNVERIFIED)]
        for codes, expected in cases:
            with self.subTest(codes=codes):
                self.assertEqual(links.classify_measurement(measurement(*codes)).outcome, expected)

    def test_incomplete_or_untrusted_tls_cannot_verify(self):
        report = measurement(200, 200)
        report["status"] = "in-progress"
        self.assertEqual(links.classify_measurement(report).outcome, links.Outcome.UNVERIFIED)
        self.assertEqual(links.classify_measurement(measurement(200, 200, authorized=False)).outcome,
                         links.Outcome.UNVERIFIED)

    def test_deduplicates_and_preserves_locations_and_other_errors(self):
        second = diagnostic()
        second["location"]["path"] = "docs/guide.md"
        report = {"diagnostics": [diagnostic(), second, diagnostic(code=404), diagnostic(code=429)]}
        original = copy.deepcopy(report)
        with patch.object(links, "verify", return_value=links.Finding(links.Outcome.VERIFIED, "OK")) as verify:
            result = links.process(report, 1, HOSTS)
        verify.assert_called_once_with(URL, HOSTS)
        self.assertEqual([item["severity"] for item in result["diagnostics"]], ["INFO", "INFO", "ERROR", "ERROR"])
        self.assertEqual([item["location"] for item in result["diagnostics"]],
                         [item["location"] for item in original["diagnostics"]])
        self.assertEqual(result["diagnostics"][2:], original["diagnostics"][2:])

    def test_unverified_warns_but_confirmed_missing_fails(self):
        for outcome, severity in [(links.Outcome.UNVERIFIED, "WARNING"), (links.Outcome.BROKEN, "ERROR")]:
            with patch.object(links, "verify", return_value=links.Finding(outcome, "Result")):
                result = links.process({"diagnostics": [diagnostic()]}, 1, HOSTS)
            self.assertEqual(result["diagnostics"][0]["severity"], severity)

    def test_disabled_fallback_and_unknown_messages_stay_errors(self):
        for hosts, item in [(set(), diagnostic()), (HOSTS, {"severity": "ERROR", "message": "Browser crashed"})]:
            with patch.object(links, "verify") as verify:
                result = links.process({"diagnostics": [item]}, 1, hosts)
                verify.assert_not_called()
                self.assertEqual(result["diagnostics"][0]["severity"], "ERROR")

    def test_crashes_and_invalid_reports_fail_closed(self):
        for report, status in [({}, 0), ({"diagnostics": []}, 1), ({"diagnostics": [diagnostic()]}, 0),
                               ({"diagnostics": []}, 2), ({"diagnostics": ["bad"]}, 1)]:
            with self.subTest(report=report, status=status), self.assertRaises(ValueError):
                links.process(report, status, HOSTS)
        self.assertEqual(links.process({"diagnostics": []}, 0, HOSTS)["diagnostics"], [])

    def test_request_budget(self):
        report = {"diagnostics": [diagnostic(URL + str(index)) for index in range(12)]}
        with patch.object(links, "verify", return_value=links.Finding(links.Outcome.VERIFIED, "OK")) as verify:
            result = links.process(report, 1, HOSTS)
        self.assertEqual(verify.call_count, links.MAX_URLS)
        self.assertEqual(result["diagnostics"][-1]["severity"], "WARNING")

    def test_polling_uses_fixed_api_and_waits(self):
        responses = [{"id": "measurement-1"}, {"status": "in-progress"}, measurement(200, 200)]
        with patch.object(links, "request_json", side_effect=responses) as request, patch.object(links.time, "sleep") as sleep:
            result = links.verify(URL, HOSTS)
        self.assertEqual(result.outcome, links.Outcome.VERIFIED)
        self.assertEqual(result.measurement, links.API + "/measurement-1")
        self.assertEqual(request.call_count, 3)
        sleep.assert_called_once_with(1)

    def test_api_failure_and_invalid_identifier_are_not_passes(self):
        with patch.object(links, "request_json", side_effect=HTTPError(links.API, 429, "Quota", {}, None)):
            self.assertEqual(links.verify(URL, HOSTS).outcome, links.Outcome.UNVERIFIED)
        with patch.object(links, "request_json", return_value={"id": "https://attacker.example/"}) as request:
            self.assertEqual(links.verify(URL, HOSTS).outcome, links.Outcome.UNVERIFIED)
            self.assertEqual(request.call_count, 1)

    def test_timeout_is_bounded(self):
        with patch.object(links, "request_json", return_value={"id": "test"}) as request:
            with patch.object(links.time, "monotonic", side_effect=[0, 41]):
                self.assertEqual(links.verify(URL, HOSTS).outcome, links.Outcome.UNVERIFIED)
            self.assertEqual(request.call_count, 1)

    def test_annotations_escape_untrusted_content(self):
        report = {"diagnostics": [{"severity": "ERROR", "message": "message\n::warning::injected",
                                    "location": {"path": "file,unexpected=value"}}]}
        output = io.StringIO()
        with redirect_stdout(output), patch.dict(links.os.environ, {"GITHUB_STEP_SUMMARY": ""}):
            links.emit(report)
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        self.assertIn("file%2Cunexpected=value", output.getvalue())
        self.assertIn("%0A::warning", output.getvalue())


class LiveRegressionTests(unittest.TestCase):
    def test_fixture_contains_both_sites_and_local_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "fixture"
            live_check.prepare(directory)
            for url in live_check.URLS:
                self.assertIn(url, directory.joinpath("README.md").read_text())
            self.assertTrue(directory.joinpath("present.md").is_file())
            self.assertFalse(directory.joinpath(live_check.MISSING).exists())
            with self.assertRaises(FileExistsError):
                live_check.prepare(directory)

    def test_live_regression_requires_verified_results_and_a_real_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            report = {"diagnostics": [diagnostic(live_check.MISSING, 404)]}
            directory.joinpath("linkspector.json").write_text(json.dumps(report))
            directory.joinpath("results.json").write_text(json.dumps(report))
            for outcome in links.Outcome:
                with self.subTest(outcome=outcome), patch.object(links, "emit"):
                    with patch.object(links, "verify", return_value=links.Finding(outcome, "Test")):
                        if outcome == links.Outcome.VERIFIED:
                            with redirect_stdout(io.StringIO()):
                                live_check.verify(directory, "failure")
                        else:
                            with self.assertRaises(ValueError):
                                live_check.verify(directory, "failure")
            with self.assertRaises(ValueError):
                live_check.verify(directory, "success")
            report["diagnostics"].append(diagnostic(code=429))
            directory.joinpath("results.json").write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                live_check.verify(directory, "failure")


if __name__ == "__main__":
    unittest.main()
