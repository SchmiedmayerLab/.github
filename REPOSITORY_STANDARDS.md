<!--
This source file is part of the Schmiedmayer Lab open-source organization

SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)

SPDX-License-Identifier: MIT
-->

# Repository Standards

Defines what every repository in the organization looks like, so the same conventions do not have
to be rediscovered per project.

## Required files

| File | Purpose | Enforced by |
|---|---|---|
| `README.md` | Overview, badge block, usage | `repository-standards.yml` |
| `LICENSE.md` | Root license, **detectable by GitHub and Zenodo** | `repository-standards.yml` |
| `LICENSES/` | REUSE license texts | `reuse.yml` |
| `REUSE.toml` | annotations for files that cannot carry a header — **no wildcards** | `reuse.yml` |
| `CITATION.cff` | Authorship and citation metadata, read by Zenodo | `repository-standards.yml` |
| `CONTRIBUTORS.md` | Project authors referenced by SPDX headers | `repository-standards.yml` |

`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, the pull request template,
and the issue templates are inherited from `SchmiedmayerLab/.github` and must **not** be
duplicated per repository.

> **A root `LICENSE.md` is not optional.** GitHub's license detector does not read `LICENSES/`,
> and Zenodo takes the license from GitHub's metadata. A repository with only `LICENSES/MIT.txt`
> is archived as having no license.

## Badge block

Directly under the `# Project Name` heading, one per line, in this order. Labels are fixed — the
checker rejects anything else, because "Main", "CI", "Main Validation" and "Build and Test" all
meant the same thing before this was written down.

| # | Label | Show it when |
|---|---|---|
| 1 | `Build and Test` | always — points at the repository's primary CI workflow |
| 2 | `Deployment` | a deployment, publish, or pages workflow exists |
| 3 | `CodeQL` | `codeql.yml` exists |
| 4 | `Codecov` | the repository reports coverage — which every repository with a test suite should |
| 5 | `REUSE status` | `REUSE.toml` exists **and** the repository is registered with the REUSE API |
| 6 | `License: MIT` | always |
| 7 | `Release` | the product is consumed by version rather than by source |
| 8 | `DOI` | after the first Zenodo archive exists |

```markdown
[![Build and Test](https://github.com/SchmiedmayerLab/REPO/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/SchmiedmayerLab/REPO/actions/workflows/build-and-test.yml)
[![Deployment](https://github.com/SchmiedmayerLab/REPO/actions/workflows/deployment.yml/badge.svg)](https://github.com/SchmiedmayerLab/REPO/actions/workflows/deployment.yml)
[![CodeQL](https://github.com/SchmiedmayerLab/REPO/actions/workflows/codeql.yml/badge.svg)](https://github.com/SchmiedmayerLab/REPO/actions/workflows/codeql.yml)
[![Codecov](https://codecov.io/gh/SchmiedmayerLab/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/SchmiedmayerLab/REPO)
[![REUSE status](https://api.reuse.software/badge/github.com/SchmiedmayerLab/REPO)](https://api.reuse.software/info/github.com/SchmiedmayerLab/REPO)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/SchmiedmayerLab/REPO/blob/main/LICENSE.md)
[![Release](https://img.shields.io/github/v/release/SchmiedmayerLab/REPO)](https://github.com/SchmiedmayerLab/REPO/releases)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.CONCEPT_ID.svg)](https://doi.org/10.5281/zenodo.CONCEPT_ID)
```

Ordering is **health → compliance → identity**: what CI says, then what the licensing says, then
how to cite. A badge added before its service is registered advertises a failure rather than a
success, so add each one only once the service behind it answers.

### Rules

- Use the **concept DOI**, never a per-version DOI. The concept DOI is stable across releases.
- Use the canonical `zenodo.org/badge/DOI/…` form, never the legacy
  `zenodo.org/badge/<github-repo-id>.svg` form. The legacy form keeps rendering when copied into a
  different repository, which is exactly how two wrong DOIs entered this organization.
- **Enable coverage reporting** wherever there is a test suite. A public repository uploads to
  Codecov without a token, so there is no secret to manage and no reason to skip it.
- Screenshots and figures go below the badge block, never interleaved with it.

## README structure

Every public README has the same skeleton:

```markdown
<!--

This source file is part of the PROJECT open-source project

SPDX-FileCopyrightText: YEAR Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)

SPDX-License-Identifier: MIT

-->

# Project Name

<badge block>

<project content>

## Contributing

Contributions to this project are welcome. Please make sure to read the [contribution guidelines](https://github.com/SchmiedmayerLab/.github/blob/main/CONTRIBUTING.md) and the [contributor covenant code of conduct](https://github.com/SchmiedmayerLab/.github/blob/main/CODE_OF_CONDUCT.md) first. You can find a list of contributors in the [CONTRIBUTORS.md](CONTRIBUTORS.md) file.

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md) for more information.

## Citation

If you use this software, please cite it using the metadata in [CITATION.cff](CITATION.cff), which GitHub surfaces through the [*Cite this repository*](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files) button.

## Our Research

For more information, visit the [Schmiedmayer Lab GitHub organization](https://github.com/SchmiedmayerLab).

![Schmiedmayer Lab](https://raw.githubusercontent.com/SchmiedmayerLab/.github/main/assets/footer-light.png#gh-light-mode-only)
![Schmiedmayer Lab](https://raw.githubusercontent.com/SchmiedmayerLab/.github/main/assets/footer-dark.png#gh-dark-mode-only)
```

The first line names the **project**: `part of the PROJECT open-source project`. This repository is
the one exception — it is not a project, so its own files say `open-source organization`. Do not
copy that wording into a repository.

Project-specific notes — provenance, documentation links, issue trackers — belong inside
`## Contributing`, after the standard paragraph. Everything else in the footer is fixed text so it
can be checked mechanically.

The license link is always `LICENSE.md`. A repository whose root license file is named `LICENSE`
should be renamed, so that one link works everywhere.

### Footer assets are deliberately generically named

`assets/footer-light.png` and `assets/footer-dark.png`, with the alt text `Schmiedmayer Lab`.

Nothing in the name or the alt text describes which logos the image contains, so adding, removing
or reordering logos is a change in this repository alone — no README anywhere needs to be touched.

### `REUSE.toml` carries no wildcard

Every file carries its own SPDX header. A blanket `path = ["**"]` annotation makes `reuse lint`
pass whether or not anyone writes one, so the repository stops being self-describing and nobody
notices. Annotate only what genuinely cannot carry a header.

Two rules that are easy to get wrong: vendored files keep their **own** licence rather than the
project's, and when several annotations match the same path the **last** one wins.

### Documentation is not content

The checker strips fenced code blocks before scanning the README, so a repository can document
badge markup or an SPDX header without those examples being read as the real thing.

## Private repositories

The checker reads visibility from the API and adapts; nothing is configured per repository.

| | Public | Private |
|---|---|---|
| Required files, README structure, footer, copyright | required | required |
| `CITATION.cff` | required | required |
| `License: MIT` badge | required | optional |
| `REUSE status` badge | required | **forbidden** |
| `DOI` badge | after first archive | **forbidden** |
| `Codecov` badge | when coverage is configured | **forbidden** |

`api.reuse.software`, Zenodo and Codecov cannot see a private repository, so those badges render an
error rather than a status. They become required in the normal way once a repository is made public.

## `CITATION.cff` and `CONTRIBUTORS.md` must match

`CITATION.cff` is the authority for **authorship** — who to cite. `CONTRIBUTORS.md` lists
**everyone who contributed**, which is a superset, and it is where upstream attributions live under
`## Attributions`. The check requires every `CITATION.cff` author to appear in `CONTRIBUTORS.md`; it
does not require the reverse, and it does not care about order.


## `CONTRIBUTORS.md` shape

Minimal and uniform, so it can be read and checked at a glance:

```markdown
<!--

This source file is part of the PROJECT open-source project

SPDX-FileCopyrightText: YEAR Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)

SPDX-License-Identifier: MIT

-->

# PROJECT Contributors

* [Name](https://github.com/handle)
* [Name](https://github.com/handle)

## Attributions

One or two sentences pointing at the upstream repositories this project builds on.
```

Four rules, all enforced:

1. Opens with the standard SPDX comment header.
2. Exactly **one** title before the list.
3. The list matches `CITATION.cff` exactly — same people, same order.
4. Every contributor is a link entry, `* [Name](https://github.com/handle)`; only link entries are
   compared.
5. **No prose between the title and the list.** Anything explanatory goes under an optional
   `## Attributions` heading at the end, which is the only additional heading allowed.

Guidance for people editing the repository belongs in the README, not here.

## Copyright holder

```
SPDX-FileCopyrightText: <year> Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
```

`LICENSE.md` and `LICENSES/*.txt` carry the same holder, filled in — this organization does not
ship the SPDX placeholder text:

```
Copyright (c) <year> Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
```

The checker fails a governed file (`README.md`, `CITATION.cff`, `CONTRIBUTORS.md`,
`.github/workflows/*.yml`) with an unrecognised holder, an unfilled `<year>` or
`<copyright holders>` placeholder, or a `LICENSE.md` with no filled copyright line.

### Third-party files keep their own holder

Vendored assets — build tooling, fonts, vendor-supplied media, third-party logos — legitimately
carry other holders and other licences, including proprietary ones. The checker reports them as a
notice so they stay visible, and never fails on them. Claiming the project licence over redistributed third-party files is a false
statement, not a tidy-up.

## Zenodo

1. **Paul Schmiedmayer** enables the repository at <https://zenodo.org/account/settings/github/>.
   The account that switches the integration on owns the resulting DOI records, so this is not
   delegated.
2. Land the `CITATION.cff` **before** the next release. Zenodo reads the file from the tarball at
   the tag, so metadata merged afterwards does not appear in that DOI record.
3. Publish a release. Only releases published *after* the integration is enabled are archived —
   existing tags are never picked up retroactively.
4. Copy the concept DOI into the README badge and into `CITATION.cff` as `doi:`.

## No opt-out

The workflow takes no inputs. Every rule applies to every repository — REUSE compliance, the
Markdown link check, and `CITATION.cff` included. A repository that does not yet meet the standard
is brought up to it; it is not exempted from it.

## Repository settings

Settings live outside the repository, so they cannot travel in a pull request. The standards
workflow reports on them as warnings rather than failures, because a pull request author cannot
change them.

It can only see part of them. Merge methods, branch deletion and the security settings are
administrative fields that GitHub withholds from the read-only token a workflow runs with, so those
are never checked in CI — the description, topics, wiki and issues are. Run the script below with an
administrative token to check the rest.

| Setting | Value | Why |
|---|---|---|
| Merge methods | **squash only** | Merge commits break linear history; rebase merges lose the pull request as the unit of change. |
| Auto-merge | **enabled** | A pull request lands when its checks pass, without a second visit. |
| Delete branch on merge | **enabled** | Otherwise the branch list becomes an archaeology exercise. |
| Secret scanning | **enabled** | Free on public repositories. |
| Push protection | **enabled** | Blocks a credential before it lands rather than reporting it afterwards. |
| Dependabot security updates | **enabled** | Advisories become pull requests without anyone watching a feed. |
| Branch ruleset | **`Main`, active** | Below. |

### The `Main` ruleset

Targets `~DEFAULT_BRANCH`; organization admins and the maintain role bypass.

| Rule | |
|---|---|
| `creation`, `deletion`, `non_fast_forward` | the default branch cannot be created, deleted or force-pushed |
| `required_linear_history` | matches squash-only merging |
| `required_signatures` | every commit on the default branch is signed |
| `pull_request` | one approval, conversation resolution required, squash only |
| `required_status_checks` | **per repository** — the one part that differs, because the checks differ |

### Applying it

[`scripts/apply-repository-settings.sh`](scripts/apply-repository-settings.sh) audits or applies the
whole baseline. Auditing is the default and changes nothing:

```bash
./scripts/apply-repository-settings.sh              # audit every public repository
./scripts/apply-repository-settings.sh apply        # bring them to the baseline
./scripts/apply-repository-settings.sh audit REPO   # one repository
```

Applying is idempotent, and it creates a `Main` ruleset only where none exists — replacing an
existing one would discard that repository's status checks. Where the repository already calls
`repository-standards.yml`, the script also adds the four `Standards / …` contexts to the required
checks, merging them into whatever is required already. It does that **only** where the caller
exists, because a required check that never reports blocks every merge. Audit mode exits non-zero when it finds
drift, so it also works as a scheduled check. Forks are skipped; they mirror an upstream project.

The script is the definition. When the baseline changes, change the script and this section
together.

### Dependabot grouping has no API

The script cannot set it, because GitHub does not expose it: `security_and_analysis` has no grouping
field, neither does the organization code-security configuration, and there is no endpoint under
`repos/{owner}/{repo}/dependabot/`. It is configured in `.github/dependabot.yml`, so it travels in a
pull request. One weekly pull request across every ecosystem:

```yaml
version: 2
multi-ecosystem-groups:
  weekly-dependencies:
    schedule:
      interval: "weekly"
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    patterns: ["*"]
    multi-ecosystem-group: "weekly-dependencies"
```

Add one entry per ecosystem the repository has, all pointing at the same group. Using `groups:`
inside a single `updates:` entry instead produces one pull request **per ecosystem**, and omitting
the file entirely means version updates never run at all.

### On a private repository

Auto-merge, secret scanning, push protection and rulesets all require GitHub Pro or Team. On the
Free plan the auto-merge request returns 200 and silently leaves the flag `false`. That is a plan
limit, not drift.

## Enforcement

Documentation alone drifts. `repository-standards.yml` in this repository is a reusable workflow
that fails a pull request when a required file is missing, when `CITATION.cff` does not parse,
when the badge block is out of order, or when the legacy Zenodo badge form is used. Call it from
each repository's static-analysis workflow:

```yaml
jobs:
  standards:
    name: Standards
    uses: SchmiedmayerLab/.github/.github/workflows/repository-standards.yml@v0.5
    permissions:
      contents: read
      pull-requests: read
```
