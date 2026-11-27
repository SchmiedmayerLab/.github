# This source file is part of the Schmiedmayer Lab open-source organization
# SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
# SPDX-License-Identifier: MIT

import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch
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
        report = {"diagnostics": [diagnostic(), second, diagnostic(code=404), diagnostic(code=401)]}
        original = copy.deepcopy(report)
        with patch.object(links, "verify", return_value=links.Finding(links.Outcome.VERIFIED, "OK")) as verify, \
                patch.object(links, "retry") as retry:
            result = links.process(report, 1, HOSTS)
        retry.assert_not_called()
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


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.addCleanup(patch.stopall)
        patch.object(links.time, "monotonic", side_effect=lambda: self.now).start()
        self.sleep = patch.object(links.time, "sleep", side_effect=self.advance).start()

    def advance(self, seconds):
        self.now += seconds

    def process(self, items, codes, hosts=frozenset(), follow_redirects=True):
        answers = iter([] if callable(codes) else codes)
        sequences = {}

        def answer(url, follow=True):
            if callable(codes):
                code = codes(url)
                if isinstance(code, list):
                    code = sequences.setdefault(url, iter(code)).__next__()
            else:
                code = next(answers)
            return code if isinstance(code, tuple) else (code, None)

        with patch.object(links, "probe", side_effect=answer) as probe:
            result = links.process({"diagnostics": items}, 1, set(hosts), follow_redirects)
        return result, probe

    def test_transient_statuses_are_retried_with_backoff(self):
        for code in (408, 429, 500, 503):
            with self.subTest(code=code):
                self.sleep.reset_mock()
                result, probe = self.process([diagnostic(code=code)], [503, None, 200])
                self.assertEqual(probe.call_count, 3)
                self.assertEqual([call.args[0] for call in self.sleep.call_args_list], list(links.RETRY_DELAYS))
                self.assertEqual(result["diagnostics"][0]["severity"], "INFO")
                self.assertEqual(result["retries"][URL]["outcome"], links.Outcome.VERIFIED)
                self.assertEqual(result["diagnostics"][0]["location"], diagnostic()["location"])

    def test_retry_outcomes(self):
        cases = [([200], "INFO"), ([404], "ERROR"), ([410], "ERROR"), ([400], "ERROR"), ([401], "ERROR"),
                 ([403], "WARNING"), ([301], "WARNING"), ([503, 503, 503], "WARNING"),
                 ([None, None, None], "WARNING"), ([429, 408, 502], "WARNING")]
        for codes, severity in cases:
            with self.subTest(codes=codes):
                result, probe = self.process([diagnostic(code=503)], codes)
                self.assertEqual(probe.call_count, len(codes))
                self.assertEqual(result["diagnostics"][0]["severity"], severity)

    def test_only_transient_external_errors_are_retried(self):
        items = [diagnostic(code=404), diagnostic(code=401), diagnostic(code=403),
                 {"severity": "ERROR", "message": f"Cannot reach {URL} Status: null net::ERR_NAME_NOT_RESOLVED"},
                 {"severity": "ERROR", "message": "Cannot reach docs/missing.md Status: 503"},
                 {"severity": "ERROR", "message": f"Cannot reach {URL} Status: 5030"},
                 {"severity": "WARNING", "message": f"Cannot reach {URL} Status: 503"}]
        result, probe = self.process(copy.deepcopy(items), [])
        probe.assert_not_called()
        self.assertEqual(result["diagnostics"], items)
        self.assertEqual(result["retries"], {})

    def test_deduplicates_and_bounds_retries(self):
        items = [diagnostic(code=503), diagnostic(code=429)] + [diagnostic(f"{URL}{index}", 503)
                                                         for index in range(links.MAX_RETRY_URLS)]
        result, probe = self.process(items, lambda url: 200)
        self.assertEqual(probe.call_count, links.MAX_RETRY_URLS)
        self.assertEqual(result["retries"][f"{URL}{links.MAX_RETRY_URLS - 1}"]["reason"], "Retry limit reached")
        self.assertEqual([item["severity"] for item in result["diagnostics"]],
                         ["INFO"] * (links.MAX_RETRY_URLS + 1) + ["WARNING"])

    def test_retry_after_extends_the_next_wait_within_the_budget(self):
        for code in (429, 503):
            with self.subTest(code=code):
                self.sleep.reset_mock()
                result, _ = self.process([diagnostic(code=code)], [(code, 20.0), 200])
                self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [2, 20.0])
                self.assertEqual(result["diagnostics"][0]["severity"], "INFO")

    def test_retry_after_does_not_delay_other_urls(self):
        other = URL + "x"
        result, probe = self.process([diagnostic(code=429), diagnostic(other, 503)],
                                     lambda url: [(429, 100.0), 200] if url == URL else [503, 200])
        self.assertEqual([call.args[0] for call in probe.call_args_list], [URL, other, other, URL])
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [2, 0.0, 8, 92.0])
        self.assertEqual(list(result["retries"]), [URL, other])

    def test_retry_after_arriving_past_the_deadline_is_still_unavailable(self):
        def late(url):
            self.now += links.RETRY_BUDGET
            return 429, 1.0

        result, _ = self.process([diagnostic(code=429)], late)
        self.assertEqual(result["retries"][URL]["reason"], "Still unavailable on retry (HTTP 429)")

    def test_retry_after_beyond_the_budget_gives_up_on_that_url_only(self):
        other = URL + "x"
        result, probe = self.process([diagnostic(code=429), diagnostic(other, 503)],
                                     lambda url: [(429, 1000.0)] if url == URL else [503, 200])
        self.assertEqual([call.args[0] for call in probe.call_args_list], [URL, other, other])
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [2, 0.0, 8])
        self.assertEqual(result["retries"][URL]["reason"], "Retry-After exceeds the retry budget (HTTP 429)")
        self.assertEqual([item["severity"] for item in result["diagnostics"]], ["WARNING", "INFO"])

    def test_parse_retry_after(self):
        for value, expected in [("5", 5.0), ("-3", 0.0), ("inf", None), ("nan", None), ("soon", None),
                                ("", None), (None, None)]:
            with self.subTest(value=value):
                self.assertEqual(links.parse_retry_after(value), expected)
        later = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + 60))
        self.assertAlmostEqual(links.parse_retry_after(later), 60, delta=2)

    def test_deadline_expiring_mid_round_stops_probing(self):
        def slow(url):
            self.now += links.RETRY_BUDGET
            return 200

        result, probe = self.process([diagnostic(code=503), diagnostic(URL + "x", 503)], slow)
        self.assertEqual(probe.call_count, 1)
        self.assertEqual([item["severity"] for item in result["diagnostics"]], ["INFO", "WARNING"])
        self.assertEqual(result["retries"][URL + "x"]["reason"], "Retry time budget reached")

    def test_retry_403_on_fallback_host_does_not_use_globalping(self):
        with patch.object(links, "verify") as verify:
            result, _ = self.process([diagnostic(code=503)], [403], hosts=HOSTS)
        verify.assert_not_called()
        self.assertEqual(result["diagnostics"][0]["severity"], "WARNING")
        self.assertEqual(result["fallbacks"], {})

    def test_disabled_redirects_make_a_retry_redirect_fail(self):
        result, probe = self.process([diagnostic(code=503)], [301], follow_redirects=False)
        self.assertEqual(probe.call_args.args, (URL, False))
        self.assertEqual(result["diagnostics"][0]["severity"], "ERROR")

    def test_follow_redirects_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / ".linkspector.yml"
            self.assertTrue(links.follows_redirects(config))
            following = ["dirs:\n  - .\n", "# followRedirects: false\n", "dirs: [.] # followRedirects: false\n",
                         "followRedirects: true\n", "followRedirects: TRUE # strict later\n",
                         "'followRedirects': True\n", '"followRedirects" : true\n',
                         'followRedirects: "false"\n', "followRedirects: 'false'\n",
                         "followRedirects: no\n", "followRedirects: OFF\n"]
            strict = ["followRedirects: false\n", "followRedirects: false # strict\n", "followRedirects: FALSE\n",
                      "followRedirects : false\n", "'followRedirects': false\n", '"followRedirects": false\n',
                      "{followRedirects: false}\n", "{dirs: [.], followRedirects: true}\n",
                      "followRedirects: !!bool false\n", 'followRedirects: !!bool "false"\n',
                      "\ufefffollowRedirects: false\n", "followRedirects: falsey\n", "followRedirects: 0\n",
                      "followRedirects:\n  false\n", "followRedirects: &value false\n",
                      "strict: &value false\nfollowRedirects: *value\n", "? followRedirects\n: false\n",
                      '"follow\\u0052edirects": false\n', '"follow\\x52edirects": false\n',
                      "followRedirects: true\nfollowRedirects: false\n"]
            for text, expected in [(text, True) for text in following] + [(text, False) for text in strict]:
                with self.subTest(text=text):
                    config.write_text(text, encoding="utf-8")
                    self.assertEqual(links.follows_redirects(config), expected)

    def test_main_exit_code_follows_retry_outcomes(self):
        report = {"diagnostics": [diagnostic(code=503), diagnostic(URL + "x", 408)]}
        for code, status in [(200, 0), (404, 1)]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                directory.joinpath("linkspector.json").write_text(json.dumps(report))
                arguments = ["check_links.py", "--report", str(directory / "linkspector.json"),
                             "--checker-exit-code", "1", "--output", str(directory / "results.json")]
                previous = os.getcwd()
                os.chdir(directory)
                try:
                    with patch.object(links, "probe", return_value=(code, None)), patch.object(sys, "argv", arguments), \
                            patch.dict(links.os.environ, {"GITHUB_STEP_SUMMARY": ""}), redirect_stdout(io.StringIO()):
                        self.assertEqual(links.main(), status)
                finally:
                    os.chdir(previous)

    def test_time_budget_is_bounded(self):
        with patch.object(links, "RETRY_BUDGET", 1):
            result, probe = self.process([diagnostic(code=503)], [])
        probe.assert_not_called()
        self.assertEqual(result["diagnostics"][0]["severity"], "WARNING")
        self.assertEqual(result["retries"][URL]["reason"], "Retry time budget reached")

    def test_summary_lists_retried_links(self):
        result, _ = self.process([diagnostic(code=503), diagnostic(URL + "x", 503)], [200, 503, 503, 503])
        self.assertEqual(result["retries"][URL + "x"]["reason"], "Still unavailable on retry (HTTP 503)")
        with tempfile.TemporaryDirectory() as temporary:
            summary = Path(temporary) / "summary.md"
            with redirect_stdout(io.StringIO()), patch.dict(links.os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
                links.emit(result)
            text = summary.read_text()
        self.assertIn("### Retried external links", text)
        self.assertIn(f"- verified: <code>{URL}</code>: HTTP 200 on retry\n", text)
        self.assertIn(f"- unverified: <code>{URL}x</code>: Still unavailable on retry (HTTP 503)\n", text)
        self.assertNotIn("\u2014", text)
        self.assertEqual(result["diagnostics"][0]["message"], f"verified: {URL}: HTTP 200 on retry")

    def test_summary_lists_fallback_outcome_values(self):
        with patch.object(links, "verify", return_value=links.Finding(links.Outcome.VERIFIED, "OK")):
            result = links.process({"diagnostics": [diagnostic()]}, 1, HOSTS)
        with tempfile.TemporaryDirectory() as temporary:
            summary = Path(temporary) / "summary.md"
            with redirect_stdout(io.StringIO()), patch.dict(links.os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
                links.emit(result)
            text = summary.read_text()
        self.assertIn(f"- verified: <code>{URL}</code>: OK\n", text)
        self.assertNotIn("Outcome.", text)

    def test_probe_reports_final_status_or_none(self):
        response = MagicMock(status=200)
        response.__enter__.return_value = response
        for effect, expected in [(None, (200, None)), (HTTPError(URL, 503, "Unavailable", {}, None), (503, None)),
                                 (HTTPError(URL, 429, "Quota", {"Retry-After": "7"}, None), (429, 7.0)),
                                 (HTTPError(URL, 503, "Unavailable", {"Retry-After": "9"}, None), (503, 9.0)),
                                 (HTTPError(URL, 404, "Missing", {"Retry-After": "9"}, None), (404, None)),
                                 (links.URLError("Name or service not known"), (None, None)),
                                 (TimeoutError(), (None, None)), (links.HTTPException(), (None, None))]:
            with self.subTest(expected=expected), patch.object(links, "build_opener") as opener:
                opener.return_value.open.side_effect = effect
                opener.return_value.open.return_value = response
                self.assertEqual(links.probe(URL), expected)
                request = opener.return_value.open.call_args.args[0]
                self.assertEqual(request.get_method(), "GET")
                self.assertNotIn("Authorization", request.headers)


class RequestUrlTests(unittest.TestCase):
    def test_request_url_uses_idna_for_hosts_and_drops_userinfo(self):
        self.assertEqual(links.request_url("https://b\u00fccher.example/\u00e4#t\u00e9"),
                         "https://xn--bcher-kva.example/%C3%A4#t%C3%A9")
        self.assertEqual(links.request_url("https://user:secret@[::1]:8443/a%20b"), "https://[::1]:8443/a%20b")

    def test_invalid_hosts_and_ports_get_no_response(self):
        for url in ["https://" + "a" * 64 + ".example/", "https://example.org:99999/"]:
            with self.subTest(url=url), patch.object(links, "build_opener") as opener:
                self.assertEqual(links.probe(url), (None, None))
                opener.return_value.open.assert_not_called()


class LocalServer(BaseHTTPRequestHandler):
    paths = []

    def do_GET(self):
        LocalServer.paths.append(self.path)
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.end_headers()
        elif self.path == "/loop":
            self.send_response(302)
            self.send_header("Location", "/loop")
            self.end_headers()
        elif self.path == "/drip":
            # Send the headers one byte every 0.2 s, so no single socket read reaches its timeout.
            self.wfile.write(b"HTTP/1.1 200 OK\r\nX-Drip: ")
            for _ in range(30):
                self.wfile.write(b"x")
                self.wfile.flush()
                time.sleep(0.2)
        else:
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def log_message(self, *arguments):
        pass


class ProbeServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), LocalServer)
        cls.server.daemon_threads = True
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_redirects_follow_the_configuration(self):
        self.assertEqual(links.probe(self.base + "/redirect"), (200, None))
        self.assertEqual(links.probe(self.base + "/redirect", False), (302, None))
        self.assertEqual(links.probe(self.base + "/loop"), (302, None))

    def test_non_ascii_is_encoded(self):
        LocalServer.paths.clear()
        self.assertEqual(links.probe(self.base + "/\u00e4?q=\u00fc&r=%20"), (200, None))
        self.assertEqual(LocalServer.paths, ["/%C3%A4?q=%C3%BC&r=%20"])

    def test_slow_responses_are_bounded_by_wall_clock(self):
        with patch.object(links, "RETRY_TIMEOUT", 1):
            started = time.monotonic()
            self.assertEqual(links.probe(self.base + "/drip"), (None, None))
            self.assertLess(time.monotonic() - started, 4)


class LiveRegressionTests(unittest.TestCase):
    def test_fixture_contains_live_sites_and_local_controls(self):
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
