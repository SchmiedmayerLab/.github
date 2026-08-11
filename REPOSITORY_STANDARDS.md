<!--
This source file is part of the Schmiedmayer Lab open-source organization

SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)

SPDX-License-Identifier: MIT
-->

# Repository Standards

Defines what every repository in the organization looks like, so the same conventions do not have
to be rediscovered per project.

## Required files

| File | Purpose |
|---|---|
| `README.md` | Overview, badge block, usage |
| `LICENSE.md` | Root license, detectable by GitHub and Zenodo |
| `LICENSES/` | REUSE license texts |
| `REUSE.toml` | When needed: annotations for files that cannot carry a header, **no wildcards** |
| `CITATION.cff` | Authorship and citation metadata, read by Zenodo |
| `CONTRIBUTORS.md` | Project authors referenced by SPDX headers |

`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, the pull request template,
and the issue templates are inherited from `SchmiedmayerLab/.github` and must **not** be
duplicated per repository.

> **A root `LICENSE.md` is required.** GitHub's license detector does not read `LICENSES/`, and
> Zenodo takes the license from GitHub's metadata. A root file named `LICENSE` is renamed.

## Badge block

Directly under the `# Project Name` heading, one per line, in the order below: health → compliance
→ identity. Labels are fixed; the check rejects any other label and any other order.

| # | Label | Show it when |
|---|---|---|
| 1 | `Build and Test` | the repository has a CI workflow; the badge points at that workflow |
| 2 | `Deployment` | a deployment, publish, or pages workflow exists |
| 3 | `CodeQL` | `codeql.yml` exists |
| 4 | `Codecov` | coverage is configured |
| 5 | `REUSE status` | always on a public repository |
| 6 | `License: MIT` | always on a public repository |
| 7 | `Release` | the product is consumed by version rather than by source |
| 8 | `DOI` | after the first Zenodo archive exists |

```markdown
[![Build and Test](https://github.com/SchmiedmayerLab/REPO/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/SchmiedmayerLab/REPO/actions/workflows/build-and-test.yml)
[![Deployment](https://github.com/SchmiedmayerLab/REPO/actions/workflows/deployment.yml/badge.svg)](https://github.com/SchmiedmayerLab/REPO/actions/workflows/deployment.yml)
[![CodeQL](https://github.com/SchmiedmayerLab/REPO/actions/workflows/codeql.yml/badge.svg)](https://github.com/SchmiedmayerLab/REPO/actions/workflows/codeql.yml)
[![Codecov](https://codecov.io/gh/SchmiedmayerLab/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/SchmiedmayerLab/REPO)
[![REUSE status](https://api.reuse.software/badge/github.com/SchmiedmayerLab/REPO)](https://api.reuse.software/info/github.com/SchmiedmayerLab/REPO)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.md)
[![Release](https://img.shields.io/github/v/release/SchmiedmayerLab/REPO)](https://github.com/SchmiedmayerLab/REPO/releases)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.CONCEPT_ID.svg)](https://doi.org/10.5281/zenodo.CONCEPT_ID)
```

### Rules

- Add a badge only once the service behind it answers.
- The workflow, Codecov and REUSE badge URLs name **this** repository.
- Every workflow badge points at a file that exists under `.github/workflows/`.
- Use the **concept DOI**, never a per-version DOI.
- Use the canonical `zenodo.org/badge/DOI/…` form, never `zenodo.org/badge/<id>.svg` or
  `zenodo.org/badge/latestdoi/…`.
- The badge DOI and the `CITATION.cff` DOI are the same, with `CONCEPT_ID` substituted.
- **Enable coverage reporting** wherever there is a test suite. A public repository uploads to
  Codecov without a token.
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

The first line names the **project**: `part of the PROJECT open-source project`.

`## Contributing`, `## License`, `## Citation` and `## Our Research` are fixed text. Provenance and
upstream credit go in `CONTRIBUTORS.md` under `## Attributions`; anything else a repository needs to
say goes above these sections. The license link is always `LICENSE.md`.

**Every file the project owns names the same project as the README.** A file whose
`SPDX-FileCopyrightText` names a third party keeps its own project line. A package merged in under
the project's own copyright is not third party: it takes the project name.

### Footer assets

`assets/footer-light.png` and `assets/footer-dark.png`, with the alt text `Schmiedmayer Lab`. The
filenames, the `#gh-light-mode-only` and `#gh-dark-mode-only` fragments and the alt text are fixed.

### `REUSE.toml` carries no wildcard

Every file carries its own SPDX header. Annotate only what cannot carry one; a blanket
`path = ["**"]` annotation fails the check. Vendored files keep their **own** licence. When several
annotations match the same path, the **last** one wins.

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

`api.reuse.software`, Zenodo and Codecov cannot see a private repository. Those badges become
required in the normal way once a repository is made public.

## `CITATION.cff`

```yaml
cff-version: 1.2.0
message: If you use this software, please cite it as below.
type: software
title: PROJECT
authors:
  - given-names: NAME
    family-names: NAME
license: MIT
url: https://github.com/SchmiedmayerLab/REPO
repository-code: https://github.com/SchmiedmayerLab/REPO
doi: 10.5281/zenodo.CONCEPT_ID
```

All of these are enforced:

1. Every key above except `doi` is required, and `type` is `software`.
2. `authors` is never empty, and every author carries `family-names`.
3. `url` and `repository-code` name this repository, and are updated after a rename.
4. No `abstract` and no `keywords`. Zenodo takes both from the repository description and topics.
5. `doi` is the concept DOI, added after the first archive.

## `CONTRIBUTORS.md` shape

```markdown
<!--

This source file is part of the PROJECT open-source project

SPDX-FileCopyrightText: YEAR Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)

SPDX-License-Identifier: MIT

-->

# PROJECT Contributors

* [Name](https://github.com/handle)
* [Name](https://github.com/handle)
```

All of these are enforced:

1. Opens with the standard SPDX comment header.
2. Exactly **one** title before the list.
3. Every contributor is a link entry, `* [Name](https://github.com/handle)`.
4. **No prose between the title and the list.** Anything explanatory goes under an optional
   `## Attributions` heading at the end, which is the only additional heading allowed.

Guidance for people editing the repository belongs in the README, not here.

## Copyright holder

```
SPDX-FileCopyrightText: <year> Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
```

`LICENSE.md` and `LICENSES/*.txt` carry the same holder, filled in:

```
Copyright (c) <year> Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)
```

Governed files (`README.md`, `CITATION.cff`, `CONTRIBUTORS.md`, `.github/workflows/*.yml`) name
`Schmiedmayer Lab` or `Stanford University` as the holder. No unfilled placeholder remains in the
README, `CITATION.cff`, `CONTRIBUTORS.md` or `LICENSE.md`: `<year>`, `<copyright holders>`, or the
stock `[yyyy] [name of copyright owner]`.

A file whose `SPDX-FileCopyrightText` names a third party keeps its own holder and its own licence,
recorded in `REUSE.toml` or a `.license` file. The check reports those holders as a notice and
never fails on them.

## Zenodo

Every repository is archived, this one included. A public repository with releases and no DOI badge
raises a warning.

1. **Paul Schmiedmayer** enables the repository at <https://zenodo.org/account/settings/github/>.
   The account that switches the integration on owns the resulting DOI records.
2. Land the `CITATION.cff` **before** the next release. Zenodo reads the file from the tarball at
   the tag, so metadata merged afterwards does not appear in that DOI record.
3. Publish a release. Only releases published *after* the integration is enabled are archived;
   existing tags are never picked up retroactively.
4. Copy the concept DOI into the README badge and into `CITATION.cff` as `doi:`.

## Repository settings

Settings live outside the repository, so they cannot travel in a pull request. The standards
workflow reports on them as warnings rather than failures, because a pull request author cannot
change them. Merge methods, branch deletion and the security settings are administrative fields
GitHub withholds from the read-only token a workflow runs with, so CI cannot check them. Run the
script below with an administrative token to check the whole baseline.

| Setting | Value | |
|---|---|---|
| Description | **set** | Zenodo takes the record description from it. |
| Topics | **four to seven, lowercase-hyphenated** | Zenodo takes the record keywords from them. |
| Issues | **enabled** | |
| Wiki | **disabled** | |
| Merge methods | **squash only** | |
| Auto-merge | **enabled** | |
| Delete branch on merge | **enabled** | |
| Secret scanning | **enabled** | Free on public repositories. |
| Push protection | **enabled** | |
| Dependabot security updates | **enabled** | |
| Branch ruleset | **`Main`, active** | Below. |

### The `Main` ruleset

Targets `~DEFAULT_BRANCH`; organization admins and the maintain role bypass.

| Rule | |
|---|---|
| `creation`, `deletion`, `non_fast_forward` | the default branch cannot be created, deleted or force-pushed |
| `required_linear_history` | matches squash-only merging |
| `required_signatures` | every commit on the default branch is signed |
| `pull_request` | one approval, conversation resolution required, squash only |
| `required_status_checks` | **per repository** |

### Applying it

[`scripts/apply-repository-settings.sh`](scripts/apply-repository-settings.sh) audits or applies the
whole baseline. Auditing is the default and changes nothing:

```bash
./scripts/apply-repository-settings.sh              # audit every public repository
./scripts/apply-repository-settings.sh apply        # bring them to the baseline
./scripts/apply-repository-settings.sh audit REPO   # one repository
```

Applying is idempotent, and it creates a `Main` ruleset only where none exists. Where the repository
already calls `repository-standards.yml`, the script adds the four `Standards / …` contexts to the
required checks, merging them into whatever is required already. It does that **only** where the
caller exists, because a required check that never reports blocks every merge. Audit mode exits
non-zero when it finds drift. Forks are skipped.

The script is the definition. When the baseline changes, change the script and this section
together.

### Dependabot grouping has no API

GitHub exposes no endpoint for it, so the script cannot set it. It is configured in
`.github/dependabot.yml` and travels in a pull request. One weekly pull request across every
ecosystem:

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

`repository-standards.yml` in this repository is a reusable workflow. It runs four jobs, Licensing,
Docs, Actions and Surface, and fails a pull request on any of them. It takes no inputs: every rule
applies to every repository. A repository that does not yet meet the standard is brought up to it;
it is not exempted from it.

Every file under `.github` passes `yamllint` and carries no trailing whitespace. A repository
`.yamllint.yml`, `.yamllint.yaml` or `.yamllint` is used if present, otherwise the default
configuration with `document-start` disabled, `truthy` limited to `true`, `false` and `on`, and a
150-character line-length warning.

Examples inside code fences are not read as the real thing, so a README can show badge markup or an
SPDX header.

Call the workflow from each repository's static-analysis workflow. Every reference to a
`SchmiedmayerLab/.github` shared workflow is pinned to the current release tag, the one shown here:

```yaml
jobs:
  standards:
    name: Standards
    uses: SchmiedmayerLab/.github/.github/workflows/repository-standards.yml@v0.5
    permissions:
      contents: read
      pull-requests: read
```
