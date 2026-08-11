<!--

This source file is part of the Schmiedmayer Lab open-source organization

SPDX-FileCopyrightText: 2026 Schmiedmayer Lab and the project authors (see CONTRIBUTORS.md)

SPDX-License-Identifier: MIT

-->

# Secrets and Repository Setup

**Which secrets a workflow takes is documented with that workflow.** Every entry under
[Workflow Reference](README.md#workflow-reference) states its own secrets, and a check in
`self-standards.yml` fails when that list and the workflow's `workflow_call` block disagree. This
file covers the parts that are not per-workflow: where a value belongs, and what a repository has to
be set to.

There is deliberately no inventory of secret names here. A second list is a list that goes stale.

## Where a value belongs

| Scope | When to use it |
|---|---|
| Organization secret | The value is the same everywhere. Restrict it to the repositories that need it. |
| Repository secret | The value differs per repository and is not tied to a deployment target. |
| Environment secret | The value differs per deployment target, or the deployment should require approval. |
| Repository or environment variable | Not sensitive: project identifiers, bundle identifiers, feature flags. |

**Deployment credentials belong in an environment**, not in a repository secret. An environment is
the only one of these that can withhold a value until a reviewer approves the run, and it is the only
one that lets staging and production hold different values under the same name.

Two consequences worth knowing:

- A job that calls a reusable workflow **cannot set `environment:`**. Workflows that need an
  environment therefore declare it on their own jobs, which is what makes environment-scoped secrets
  and variables resolve. `secrets: inherit` passes organization and repository secrets; the
  environment's own values are read by the called job.
- The name a repository stores a secret under does not have to match the name the workflow takes.
  A repository with several deployment targets may hold `..._PRODUCTION_US` and `..._PRODUCTION_UK`
  and pass whichever one applies into the single secret the workflow declares. Those caller-side
  names are a repository's own business and are not part of the organization contract.

## Naming

Use the name the workflow declares wherever there is no reason to differ. `SCREAMING_SNAKE_CASE`
for secrets, the same for variables. Encode binary material — keystores, certificates, provisioning
profiles, service account keys, plist and JSON configuration — as Base64, and say so in the name with
a `_BASE64` suffix where the workflow does.

## Repository setup

Applied by [`scripts/apply-repository-settings.sh`](scripts/apply-repository-settings.sh), which
audits and re-applies the baseline. Run it after creating a repository.

| Setting | Value |
|---|---|
| Squash merge | the only merge method |
| Delete branch on merge | enabled |
| Wikis, Projects | disabled |
| Secret scanning and push protection | enabled on every public repository |
| Dependabot security updates | enabled |
| Dependabot version updates | grouped, weekly, via `.github/dependabot.yml` |
| Default workflow permissions | read |
| Required status checks | the four `Standards / …` contexts |

**Default workflow permissions are read.** A job starts with `contents: read` and `packages: read`
and nothing else. Any job calling a reusable workflow that needs more must say so, and declaring a
`permissions:` block **replaces** the default rather than adding to it — list every scope the job
needs, not just the extra one. `repository-standards.yml` fails a pull request when a caller grants
less than the workflow it calls requires.

## Coverage

Public repositories do not need a Codecov token: Codecov accepts tokenless uploads from public
repositories, and the shared workflows set `fail_ci_if_error: false` so a missing token cannot fail a
build. Private repositories still need one. Coverage reporting should be enabled wherever a project
has tests.
