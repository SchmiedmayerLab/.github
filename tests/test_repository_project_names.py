# This source file is part of the Schmiedmayer Lab open-source organization
# SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
# SPDX-License-Identifier: MIT

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/repository-standards.yml"
PROJECT = "Example open-source project"
OTHER_PROJECT = "Other Example open-source project"
HOLDER = "# SPDX-FileCopyrightText: 2026 Stanford University and the project authors\n"


def declaration(project=PROJECT):
    return "This source file is part of the " + project


def validator_source(workflow):
    """Exercise the inline workflow implementation, without copying its regex."""
    step = workflow.split("      - name: One project name per repository\n", 1)[1]
    source = step.split("          python3 - <<'PY'\n", 1)[1].split("\n          PY\n", 1)[0]
    return textwrap.dedent(source)


def header_styles(project=PROJECT):
    line = declaration(project)
    return {
        "hash": "# " + line + "\n",
        "indented hash": "\t  #\t" + line + "\n",
        "slash": "// " + line + "\n",
        "doc slash": "/// " + line + "\n",
        "C single line": "/* " + line + " */\n",
        "C block": "/*\n * " + line + "\n */\n",
        "C doc block": "/**\n * " + line + "\n */\n",
        "HTML single line": "<!-- " + line + " -->\n",
        "HTML block": "<!--\n\n" + line + "\n\n-->\n",
        "SQL": "-- " + line + "\n",
        "bare block line": line + "\n",
        "CRLF": "#\r\n# " + line + "\r\n#\r\n",
    }


class ProjectHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = validator_source(WORKFLOW.read_text())

    def run_validator(self, files=None):
        with tempfile.TemporaryDirectory(prefix="project-headers-") as temporary:
            root = Path(temporary)
            fixture = {"README.md": "<!--\n" + declaration() + "\n-->\n"}
            fixture.update(files or {})
            for filename, content in fixture.items():
                target = root / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content.encode("utf-8"))
            result = subprocess.run(
                [sys.executable, "-c", self.validator],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            # The validator must leave upstream evidence and every other input unchanged.
            for filename, content in fixture.items():
                self.assertEqual((root / filename).read_bytes(), content.encode("utf-8"))
            return result

    def assert_passes(self, files=None):
        result = self.run_validator(files)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("::error", result.stdout)

    def assert_fails(self, files, filename, message):
        result = self.run_validator(files)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("::error file=" + filename + "::", result.stdout)
        self.assertIn(message, result.stdout)

    def test_standard_header_styles_pass(self):
        for label, header in header_styles().items():
            with self.subTest(style=label):
                self.assert_passes({"source.txt": header + HOLDER})

    def test_different_project_in_real_header_still_fails(self):
        for label, header in header_styles(OTHER_PROJECT).items():
            with self.subTest(style=label):
                self.assert_fails({"source.txt": header + HOLDER}, "source.txt", OTHER_PROJECT)

    def test_organization_header_is_supported(self):
        organization = "Example open-source organization"
        self.assert_passes({
            "README.md": "<!--\n" + declaration(organization) + "\n-->\n",
            "source.py": "# " + declaration(organization) + "\n" + HOLDER,
        })

    def test_serialized_upstream_citation_headers_are_data(self):
        cff = "#\n# " + declaration(OTHER_PROJECT) + "\n" + HOLDER + "title: Other Example\n"
        snapshot = [{"repository": "example/other", "cff": cff,
                     "cffSha256": hashlib.sha256(cff.encode()).hexdigest()}]
        for indent in (None, 2):
            with self.subTest(indent=indent):
                self.assert_passes({"data/citation-sources.json": json.dumps(snapshot, indent=indent)})

    def test_quoted_declarations_are_not_headers(self):
        line = declaration(OTHER_PROJECT)
        for text in (json.dumps(line), 'message = "' + line + '"',
                     "A field contains " + line, r"\n# " + line + r"\n"):
            with self.subTest(text=text):
                self.assert_passes({"source.txt": text + "\n" + HOLDER})

    def test_standalone_citation_header_still_fails(self):
        self.assert_fails(
            {"CITATION.cff": "# " + declaration(OTHER_PROJECT) + "\n" + HOLDER},
            "CITATION.cff", OTHER_PROJECT,
        )

    def test_readme_requires_a_real_header(self):
        line = declaration()
        for text in ("# Example\n", json.dumps(line), "```text\n" + line + "\n```\n"):
            with self.subTest(text=text):
                self.assert_fails({"README.md": text}, "README.md", "README header must name the project")

    def test_malformed_or_split_readme_declarations_fail(self):
        for text in ("# This source file is part of the",
                     "# This source is part of the " + PROJECT,
                     "# This source file is part of the Example\nopen-source project",
                     "# This source file is\npart of the " + PROJECT):
            with self.subTest(text=text):
                self.assert_fails({"README.md": text}, "README.md", "README header must name the project")

    def test_existing_markdown_fence_exception_is_preserved(self):
        self.assert_passes({"docs/example.md": "```text\n" + declaration(OTHER_PROJECT) + "\n```\n"})

    def test_real_header_outside_markdown_fence_still_fails(self):
        self.assert_fails(
            {"docs/example.md": declaration(OTHER_PROJECT) + "\n\n```text\nexample\n```\n"},
            "docs/example.md", OTHER_PROJECT,
        )

    def test_existing_third_party_holder_exception_is_preserved(self):
        self.assert_passes({
            "vendor.py": "# " + declaration(OTHER_PROJECT) +
                         "\n# SPDX-FileCopyrightText: 2026 Example External Foundation\n",
        })

    def test_missing_copyright_does_not_hide_a_mismatched_header(self):
        self.assert_fails({"source.py": "# " + declaration(OTHER_PROJECT)}, "source.py", OTHER_PROJECT)

    def test_git_metadata_is_not_scanned(self):
        self.assert_passes({".git/example": "# " + declaration(OTHER_PROJECT) + "\n" + HOLDER})


if __name__ == "__main__":
    unittest.main()
