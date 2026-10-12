#!/usr/bin/env python3
# This source file is part of the Schmiedmayer Lab open-source organization
# SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
# SPDX-License-Identifier: MIT

"""Exercise the real shared action and require successful public-probe verification."""

import argparse
import json
from pathlib import Path

import check_links as links


URLS = (
    "https://www.bluetooth.com/blog/a-developers-guide-to-bluetooth/",
    "https://zenodo.org",
)
MISSING = "does-not-exist.md"


def prepare(directory: Path) -> None:
    directory.mkdir()  # Never replace an existing fixture or caller's documentation.
    directory.joinpath("README.md").write_text(
        "# Link regression fixtures\n\n"
        + "\n".join(f"[Public documentation]({url})\n" for url in URLS)
        + f"\n[Existing local document](present.md)\n\n[Missing local document]({MISSING})\n"
    )
    directory.joinpath("present.md").write_text("# Existing document\n")
    directory.joinpath(".linkspector.yml").write_text("dirs:\n  - .\nuseGitIgnore: false\n")


def verify(directory: Path, outcome: str) -> None:
    raw = json.loads(directory.joinpath("linkspector.json").read_text())
    processed = json.loads(directory.joinpath("results.json").read_text())
    diagnostics = links.read_diagnostics(raw, 1)
    missing = [item for item in diagnostics if item["message"].startswith(f"Cannot reach {MISSING} Status: 404")]
    if outcome != "failure" or len(missing) != 1:
        raise ValueError("The action must fail on exactly one deliberate missing-file diagnostic")
    remaining = [item for item in processed["diagnostics"] if item["severity"] != "INFO"]
    if remaining != missing:
        raise ValueError("Unexpected failures or unverified links in the shared action's results")

    # Exercise the fallback even if the runner can reach both sites directly. These
    # synthetic 403s test the fallback path; they are not observations from Linkspector.
    forced = {"diagnostics": [
        {"severity": "ERROR", "message": f"Cannot reach {url} Status: 403"} for url in URLS
    ]}
    result = links.process(forced, 1, {"www.bluetooth.com", "zenodo.org"})
    directory.joinpath("live-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    links.emit(result)
    if set(result["fallbacks"]) != set(URLS) or any(
        item["outcome"] != links.Outcome.VERIFIED for item in result["fallbacks"].values()
    ):
        raise ValueError("Both live URLs must be verified; warnings do not pass this regression")
    print("Both public URLs verified; valid local links passed and missing local links still failed.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--outcome", default="")
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            prepare(args.directory)
        else:
            verify(args.directory, args.outcome)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"::error::{links.escape_annotation(str(error))}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
