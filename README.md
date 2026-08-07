<!--

This source file is part of the Schmiedmayer Lab open-source organization

SPDX-FileCopyrightText: 2026 Stanford University and the project authors (see CONTRIBUTORS.md)

SPDX-License-Identifier: MIT

-->

# Schmiedmayer Lab

[![Validate Repository](https://github.com/SchmiedmayerLab/.github/actions/workflows/validate.yml/badge.svg)](https://github.com/SchmiedmayerLab/.github/actions/workflows/validate.yml)

This repository provides default community health files, reusable GitHub Actions workflows, templates, and shared documentation for the Schmiedmayer Lab organization.

## GitHub Actions

This repository publishes reusable GitHub Actions workflows for common Schmiedmayer Lab project tasks.
Use them from another repository with `jobs.<job_id>.uses` and a version tag.

### Workflow Catalog

#### Repository Checks

| Workflow | Use |
|---|---|
| [`actionlint.yml`](#lint-github-actions-workflows) | Lint GitHub Actions workflow files with actionlint. |
| [`eslint.yml`](#run-eslint) | Run ESLint for JavaScript and TypeScript projects. |
| [`markdown-links.yml`](#check-markdown-links) | Check Markdown links. |
| [`periphery.yml`](#run-periphery) | Run Periphery to detect unused Swift declarations. |
| [`reuse.yml`](#check-reuse-compliance) | Check REUSE license and copyright metadata. |
| [`swiftlint.yml`](#run-swiftlint) | Run SwiftLint for Swift style and quality checks. |

#### Swift and Apple Platforms

| Workflow | Use |
|---|---|
| [`coverage.yml`](#merge-and-upload-coverage) | Merge coverage artifacts and upload the result to Codecov. |
| [`docc-github-pages.yml`](#deploy-docc-documentation) | Build DocC documentation and deploy it to GitHub Pages. |
| [`swift-api-breaking-changes.yml`](#diagnose-swift-api-breaking-changes) | Diagnose Swift API breaking changes with package metadata detection. |
| [`swift-package-breaking-changes.yml`](#diagnose-swift-package-api-breaking-changes) | Diagnose Swift package API breaking changes with explicit product and platform inputs. |
| [`swift-package-ci.yml`](#swift-package-ci) | Run the standard Swift Package CI pipeline. |
| [`swift-package-setup.yml`](#set-up-swift-package) | Parse Swift package metadata for downstream workflows. |
| [`swift-package-static-analysis.yml`](#analyze-swift-package) | Run the standard static analysis checks for Swift packages. |
| [`swift-package-test.yml`](#test-swift-package) | Test a Swift package across the configured Apple and Linux matrices. |
| [`swift-test.yml`](#run-swift-tests) | Run SwiftPM tests and optionally export LCOV coverage. |
| [`xcodebuild.yml`](#build-and-test-with-xcodebuild) | Build and test Apple projects with xcodebuild. |
| [`firebase-emulators-exec.yml`](#run-command-with-firebase-emulator) | Run a trusted command through the Firebase Emulator. |
| [`xcode-deploy.yml`](#deploy-xcode-project) | Deploy Xcode projects with signing and file injection setup. |
| [`xcarchive.yml`](#build-xcarchive) | Build an XCArchive and upload it as an artifact. |
| [`xcframework.yml`](#build-xcframework) | Build an XCFramework from XCArchive artifacts. |
| [`xcframework-release.yml`](#release-xcframework) | Commit and release an XCFramework artifact. |

#### Web, Node.js, and Firebase

| Workflow | Use |
|---|---|
| [`firebase-deploy.yml`](#deploy-firebase) | Deploy Firebase projects. |
| [`nextjs-github-pages.yml`](#deploy-nextjs-site) | Build and deploy a static Next.js site to GitHub Pages. |
| [`npm-pages.yml`](#build-and-deploy-npm-project-pages) | Build and optionally deploy an npm project to GitHub Pages. |
| [`npm-publish.yml`](#publish-npm-package) | Publish an npm package. |
| [`npm-release.yml`](#publish-a-fixed-version-npm-release) | Safely publish a fixed-version npm package or workspace release. |
| [`npm-test-coverage.yml`](#test-npm-package-and-upload-coverage) | Test an npm package and upload coverage to Codecov. |

#### Containers

| Workflow | Use |
|---|---|
| [`docker-build-and-push.yml`](#build-and-push-docker-image) | Build and publish multi-architecture Docker images. |
| [`docker-compose-test.yml`](#test-docker-compose-stack) | Test a Docker Compose stack. |

#### Releases

| Workflow | Use |
|---|---|
| [`action-release-tag.yml`](#tag-action-release) | Maintain major and minor release tags for GitHub Actions repositories. |
| [`format-release-notes.yml`](#format-release-notes) | Format GitHub release notes. |

### Workflow Reference

#### Repository Checks

##### Lint GitHub Actions Workflows

[`actionlint.yml`](.github/workflows/actionlint.yml) installs actionlint and checks GitHub Actions workflow syntax.
Use it for repositories that maintain their own workflows.

```yml
jobs:
  actionlint:
    name: Lint GitHub Actions Workflows
    uses: SchmiedmayerLab/.github/.github/workflows/actionlint.yml@v0.3
    with:
      runs_on_labels: '["ubuntu-latest"]'
```

##### Run ESLint

[`eslint.yml`](.github/workflows/eslint.yml) installs Node.js dependencies, runs the repository lint command, annotates pull requests, and uploads the ESLint report.
Use it for JavaScript and TypeScript projects with `npm run lint:ci`.

```yml
jobs:
  eslint:
    name: Run ESLint
    uses: SchmiedmayerLab/.github/.github/workflows/eslint.yml@v0.3
```

##### Check Markdown Links

[`markdown-links.yml`](.github/workflows/markdown-links.yml) checks Markdown links with Linkspector.
Use it for documentation-heavy repositories. The workflow needs read access to pull requests so
Linkspector can map diagnostics to the pull request diff.

```yml
jobs:
  markdown-links:
    name: Check Markdown Links
    uses: SchmiedmayerLab/.github/.github/workflows/markdown-links.yml@v0.3
    permissions:
      contents: read
      pull-requests: read
```

##### Run Periphery

[`periphery.yml`](.github/workflows/periphery.yml) runs Periphery to detect unused Swift declarations.
Use it for Swift packages and Xcode projects that can be scanned from the repository root.

```yml
jobs:
  periphery:
    name: Run Periphery
    uses: SchmiedmayerLab/.github/.github/workflows/periphery.yml@v0.3
```

##### Check REUSE Compliance

[`reuse.yml`](.github/workflows/reuse.yml) checks that files carry REUSE-compliant license and copyright metadata.
Use it for repositories that follow the REUSE specification.

```yml
jobs:
  reuse:
    name: Check REUSE Compliance
    uses: SchmiedmayerLab/.github/.github/workflows/reuse.yml@v0.3
```

##### Run SwiftLint

[`swiftlint.yml`](.github/workflows/swiftlint.yml) runs SwiftLint in strict mode.
Use it for Swift repositories that define SwiftLint rules.

```yml
jobs:
  swiftlint:
    name: Run SwiftLint
    uses: SchmiedmayerLab/.github/.github/workflows/swiftlint.yml@v0.3
```

#### Swift and Apple Platforms

##### Merge and Upload Coverage

[`coverage.yml`](.github/workflows/coverage.yml) downloads coverage artifacts, merges `.xcresult` and `.lcov` reports, and uploads the result to Codecov.
Use it after test jobs that upload coverage artifacts.

```yml
jobs:
  coverage:
    name: Merge and Upload Coverage
    uses: SchmiedmayerLab/.github/.github/workflows/coverage.yml@v0.3
    with:
      coveragereports: ResultBundle1.xcresult ResultBundle2.xcresult
    secrets:
      token: ${{ secrets.CODECOV_TOKEN }}
```

##### Deploy DocC Documentation

[`docc-github-pages.yml`](.github/workflows/docc-github-pages.yml) builds DocC documentation with xcodebuild and deploys the generated site to GitHub Pages.
Use it for Swift packages and Xcode projects that publish API documentation.

```yml
permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  docc:
    name: Deploy DocC Documentation
    uses: SchmiedmayerLab/.github/.github/workflows/docc-github-pages.yml@v0.3
    with:
      scheme: ExamplePackage
```

##### Diagnose Swift API Breaking Changes

[`swift-api-breaking-changes.yml`](.github/workflows/swift-api-breaking-changes.yml) detects library products and platform metadata before running Swift API breakage diagnostics.
Use it for Swift packages that can rely on automatic metadata detection.

```yml
jobs:
  api-breaking-changes:
    name: Diagnose Swift API Breaking Changes
    uses: SchmiedmayerLab/.github/.github/workflows/swift-api-breaking-changes.yml@v0.3
```

##### Diagnose Swift Package API Breaking Changes

[`swift-package-breaking-changes.yml`](.github/workflows/swift-package-breaking-changes.yml) runs Swift API breakage diagnostics with explicit library product and platform inputs.
Use it when another workflow already knows the package metadata.

```yml
jobs:
  package-breaking-changes:
    name: Diagnose Swift Package API Breaking Changes
    uses: SchmiedmayerLab/.github/.github/workflows/swift-package-breaking-changes.yml@v0.3
    with:
      library_products: '["ExamplePackage"]'
      platform_name: ios
      platform_version: '18.0'
```

##### Swift Package CI

Use [`swift-package-ci.yml`](.github/workflows/swift-package-ci.yml) as the default entry point for Swift packages.
It detects package metadata, runs tests, uploads coverage when available, and runs static analysis.

```yml
jobs:
  swift-package-ci:
    name: Swift Package CI
    uses: SchmiedmayerLab/.github/.github/workflows/swift-package-ci.yml@v0.3
    secrets: inherit
```

##### Set Up Swift Package

[`swift-package-setup.yml`](.github/workflows/swift-package-setup.yml) parses Swift package metadata and exposes it as workflow outputs.
Use it as a setup job before lower-level Swift package workflows.

```yml
jobs:
  setup:
    name: Set Up Swift Package
    uses: SchmiedmayerLab/.github/.github/workflows/swift-package-setup.yml@v0.3
  test:
    name: Test Swift Package
    needs: setup
    uses: SchmiedmayerLab/.github/.github/workflows/swift-package-test.yml@v0.3
    with:
      package_name: ${{ needs.setup.outputs.package_name }}
      scheme: ${{ needs.setup.outputs.scheme }}
      platform_matrix: ${{ needs.setup.outputs.platform_matrix }}
      ui_platform_matrix: ${{ needs.setup.outputs.ui_platform_matrix }}
```

##### Analyze Swift Package

[`swift-package-static-analysis.yml`](.github/workflows/swift-package-static-analysis.yml) combines REUSE, SwiftLint, Markdown link checking, and Swift API breakage diagnostics.
Use it when package metadata is already available from `swift-package-setup.yml`.

```yml
jobs:
  analyze:
    name: Analyze Swift Package
    uses: SchmiedmayerLab/.github/.github/workflows/swift-package-static-analysis.yml@v0.3
    with:
      library_products: '["ExamplePackage"]'
      platform_name: ios
      platform_version: '18.0'
```

##### Test Swift Package

[`swift-package-test.yml`](.github/workflows/swift-package-test.yml) runs Apple platform test matrices, optional UI test matrices, optional Linux tests, and coverage upload.
Use it when package metadata and platform matrices are provided explicitly.

```yml
jobs:
  test:
    name: Test Swift Package
    uses: SchmiedmayerLab/.github/.github/workflows/swift-package-test.yml@v0.3
    with:
      package_name: ExamplePackage
      scheme: ExamplePackage
      platform_matrix: >-
        [{"name":"iOS","destination":"platform=iOS Simulator,name=iPhone 17 Pro"}]
      ui_platform_matrix: '[]'
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

##### Run Swift Tests

[`swift-test.yml`](.github/workflows/swift-test.yml) runs SwiftPM tests and can upload an LCOV artifact for later coverage merging.
Use it for Linux Swift package tests or simple SwiftPM test jobs.

```yml
jobs:
  swift-test:
    name: Run Swift Tests
    uses: SchmiedmayerLab/.github/.github/workflows/swift-test.yml@v0.3
```

##### Build and Test with xcodebuild

Use [`xcodebuild.yml`](.github/workflows/xcodebuild.yml) for Apple projects that need direct xcodebuild tests or builds.
When `scheme` is omitted, the workflow infers the Swift package scheme from `Package.swift` or the only shared Xcode scheme in the selected `path`.
Swift packages use the package name as the scheme, or `PackageName-Package` when the package defines multiple library products.
Swift package result bundles use `PackageName.xcresult` in both cases.
Test runs upload the resolved `.xcresult` bundle automatically; set `resultBundle` only when you need a custom bundle name.
The workflow intentionally does not declare its own `permissions` block because its CodeQL path is optional.
Callers that set `codeql: true` must grant `security-events: write`; normal build and test jobs can omit that permission.

```yml
jobs:
  app-tests:
    name: Build and Test App
    permissions:
      contents: read
    uses: SchmiedmayerLab/.github/.github/workflows/xcodebuild.yml@v0.3
    with:
      runsonlabels: '["macOS", "self-hosted"]'
  package-tests:
    name: Build and Test Swift Package
    uses: SchmiedmayerLab/.github/.github/workflows/xcodebuild.yml@v0.3
    with:
      path: ExamplePackage
      runsonlabels: '["macOS", "self-hosted"]'
```

CodeQL analysis uses the same workflow with `codeql: true`.
Because GitHub sets unspecified token scopes to `none` when any explicit permission is declared, grant both `contents: read` and `security-events: write` on the calling job.
When CodeQL runs on a GitHub-hosted runner, the workflow builds the project without running tests even though `test` defaults to `true`.

```yml
jobs:
  codeql:
    name: Build and Analyze with CodeQL
    permissions:
      contents: read
      security-events: write
    uses: SchmiedmayerLab/.github/.github/workflows/xcodebuild.yml@v0.3
    with:
      codeql: true
      scheme: TemplatePackage
```

##### Run Command with Firebase Emulator

Use [`firebase-emulators-exec.yml`](.github/workflows/firebase-emulators-exec.yml) for test or validation commands that must run while Firebase emulators are active.
The `command` input is executed through `firebase emulators:exec` and can be any trusted shell command.
Use `artifact_path` to upload command output such as an `.xcresult` bundle; the artifact name is inferred from the path.

```yml
jobs:
  firebase-ui-tests:
    name: Run UI Tests with Firebase Emulator
    uses: SchmiedmayerLab/.github/.github/workflows/firebase-emulators-exec.yml@v0.3
    with:
      command: bundle exec fastlane uitest
      artifact_path: fastlane/test_output/UITests.xcresult
      firebase_emulator_import: ./firebase-export
    secrets:
      GOOGLE_APPLICATION_CREDENTIALS_BASE64: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS_BASE64 }}
```

##### Deploy Xcode Project

Use [`xcode-deploy.yml`](.github/workflows/xcode-deploy.yml) for Xcode deployments that need code signing, App Store Connect environment variables, or a Base64-encoded secret file written before deployment.
The `injected_secret_file_path` input defines the injected file path, name, and extension.
The workflow does not start Firebase emulators and does not validate that `command` is a fastlane command.
Use `fastlane`, `bundle exec fastlane`, or another trusted deployment command.

```yml
jobs:
  deploy:
    name: Deploy Xcode Project
    permissions:
      contents: read
    uses: SchmiedmayerLab/.github/.github/workflows/xcode-deploy.yml@v0.3
    with:
      command: >-
        bundle exec fastlane deploy environment:"staging"
        versionname:"4.0.5" releasenotes:"Test Deployment."
      environment: staging
      setup_signing: true
      injected_secret_file_path: App/DeploymentConfiguration.json
    secrets:
      APP_STORE_CONNECT_API_KEY_BASE64: ${{ secrets.APP_STORE_CONNECT_API_KEY_BASE64 }}
      APP_STORE_CONNECT_API_KEY_ID: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
      APP_STORE_CONNECT_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_ISSUER_ID }}
      APPLE_ID: ${{ secrets.APPLE_ID }}
      BUILD_CERTIFICATE_BASE64: ${{ secrets.BUILD_CERTIFICATE_BASE64 }}
      BUILD_PROVISION_PROFILE_BASE64: ${{ secrets.BUILD_PROVISION_PROFILE_BASE64 }}
      INJECTED_SECRET_FILE_BASE64: ${{ secrets.DEPLOYMENT_CONFIGURATION_BASE64 }}
      P12_PASSWORD: ${{ secrets.P12_PASSWORD }}
```

##### Build XCArchive

[`xcarchive.yml`](.github/workflows/xcarchive.yml) builds an XCArchive and uploads it as an artifact.
Use it for binary distribution pipelines that package Apple platform archives.

```yml
jobs:
  xcarchive:
    name: Build XCArchive
    uses: SchmiedmayerLab/.github/.github/workflows/xcarchive.yml@v0.3
    with:
      workspaceFile: example.xcworkspace
      xcArchiveName: ExampleKit
      scheme: ExampleKit
      version: 0.1.0
```

##### Build XCFramework

Use [`xcframework.yml`](.github/workflows/xcframework.yml) to package XCArchive outputs into an XCFramework artifact.

```yml
jobs:
  xcframework:
    name: Build XCFramework
    uses: SchmiedmayerLab/.github/.github/workflows/xcframework.yml@v0.3
    with:
      workspaceFile: example.xcworkspace
      xcFrameworkName: ExampleKit
      scheme: ExampleKit
      version: 0.1.0
```

##### Release XCFramework

[`xcframework-release.yml`](.github/workflows/xcframework-release.yml) downloads built XCFramework artifacts, commits them to the repository, tags the release, and creates a GitHub release.
Use it after `xcframework.yml` has produced the XCFramework artifact.

```yml
permissions:
  actions: read
  contents: write

jobs:
  release-xcframework:
    name: Release XCFramework
    uses: SchmiedmayerLab/.github/.github/workflows/xcframework-release.yml@v0.3
    with:
      version: v0.2
    secrets:
      access-token: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
```

#### Web, Node.js, and Firebase

##### Deploy Firebase

[`firebase-deploy.yml`](.github/workflows/firebase-deploy.yml) installs Firebase tooling and deploys a Firebase project with service-account credentials.
Use it for Firebase Hosting, Functions, Firestore rules, or other Firebase deploy targets.

```yml
jobs:
  firebase:
    name: Deploy Firebase
    uses: SchmiedmayerLab/.github/.github/workflows/firebase-deploy.yml@v0.3
    with:
      arguments: --only hosting
    secrets:
      GOOGLE_APPLICATION_CREDENTIALS_BASE64: ${{ secrets.GOOGLE_APPLICATION_CREDENTIALS_BASE64 }}
```

##### Deploy Next.js Site

Use [`nextjs-github-pages.yml`](.github/workflows/nextjs-github-pages.yml) for static Next.js sites that publish to GitHub Pages.

```yml
permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  pages:
    name: Deploy Next.js Site
    uses: SchmiedmayerLab/.github/.github/workflows/nextjs-github-pages.yml@v0.3
```

##### Publish npm Package

[`npm-publish.yml`](.github/workflows/npm-publish.yml) sets the package version, runs version lifecycle scripts, builds the package, and publishes it to npm with provenance.
It uses npm Trusted Publishing by default and requires Node.js 22.14.0 or newer, npm 11.5.1 or newer, and `id-token: write` in both the caller and reusable workflow.
Set `workspaces: true` for npm workspaces and provide `npmVersion` only when the bundled npm version must be replaced with an exact stable version.

```yml
jobs:
  npm-publish:
    name: Publish npm Package
    uses: SchmiedmayerLab/.github/.github/workflows/npm-publish.yml@v0.3
    permissions:
      contents: read
      id-token: write
    with:
      packageVersion: 0.1.0
```

For packages that do not yet exist on npm, run the caller once with the following additions:

```yml
    with:
      bootstrapWithToken: true
      packageVersion: 0.1.0
    secrets:
      NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

The bootstrap refuses packages that already exist.
After it succeeds, configure a GitHub Actions trusted publisher for every package using the organization, repository, and top-level caller workflow filename, then remove the token and `bootstrapWithToken`.

##### Publish a Fixed-Version npm Release

Use [`npm-release.yml`](.github/workflows/npm-release.yml) for repositories that publish one package or a fixed-version npm workspace collection.
The workflow reads a published GitHub release tag, Node.js from `.nvmrc`, and npm from the exact `packageManager` entry in `package.json`, so release-event callers normally provide no inputs.
It validates bare semantic versions, orders workspace packages by runtime dependencies, synchronizes internal dependency versions, skips versions already present on npm, publishes existing packages through OIDC, and verifies the registry state.

Keep the top-level caller at `.github/workflows/deployment.yml`.
npm validates the caller workflow name when a reusable workflow performs the publication, and every Trusted Publisher must authorize `deployment.yml`.

```yml
permissions:
  contents: read
  id-token: write

jobs:
  publish:
    uses: SchmiedmayerLab/.github/.github/workflows/npm-release.yml@v0.4
```

Manual release callers pass their dispatch input as `packageVersion`.

For the first publication of a new package, temporarily pass its package name in `bootstrapPackages` and expose a short-lived granular `NPM_TOKEN` with read/write scope access and **Bypass two-factor authentication** enabled.
The token is available only to the bootstrap step.
After publication, the workflow summary provides the interactive `npm trust` commands required to authorize `deployment.yml`; remove the token after a subsequent OIDC publication succeeds.

Repositories may define an optional `release:prepare` script for package-specific preparation after versions are synchronized.
The workflow automatically runs `build`, `pack:check`, and `pack:lint` when those scripts exist.

##### Build and Deploy npm Project Pages

Use [`npm-pages.yml`](.github/workflows/npm-pages.yml) when an npm project can build its complete Pages artifact with `npm run pages:build`.
The script must create `deploy/index.html`; all routing and framework-specific build decisions stay in the caller repository.
Node.js and npm versions are inferred from `.nvmrc` and `packageManager`.

```yml
permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  pages:
    uses: SchmiedmayerLab/.github/.github/workflows/npm-pages.yml@v0.4
```

Set `deploy: false` to exercise the complete Pages build in pull-request CI without uploading or deploying the artifact.
`nodeVersionFile` and `artifactPath` are available only for repositories that cannot follow the default conventions.

##### Test npm Package and Upload Coverage

Use [`npm-test-coverage.yml`](.github/workflows/npm-test-coverage.yml) for npm projects that should run `npm ci`, `npm test`, and upload coverage to Codecov. The workflow uses the npm version bundled with the selected Node.js release by default; callers that need a specific npm release can provide an exact version such as `npmVersion: '12.0.2'`. Set `coverage-files` to a comma-separated list when a repository contains non-coverage files whose names could be discovered by Codecov. Firebase projects can enable emulator tooling with `setup-firebase-emulator: true`; callers must install `firebase-tools` through `package-lock.json`, which also keys the emulator cache.

```yml
jobs:
  npm-test:
    name: Test npm Package and Upload Coverage
    uses: SchmiedmayerLab/.github/.github/workflows/npm-test-coverage.yml@v0.3
    with:
      coverage-files: coverage/lcov.info
    secrets:
      token: ${{ secrets.CODECOV_TOKEN }}
```

#### Containers

##### Build and Push Docker Image

Use [`docker-build-and-push.yml`](.github/workflows/docker-build-and-push.yml) to publish a multi-architecture Docker image.

```yml
permissions:
  contents: read
  packages: write

jobs:
  docker:
    name: Build and Push Docker Image
    uses: SchmiedmayerLab/.github/.github/workflows/docker-build-and-push.yml@v0.3
    with:
      imageName: schmiedmayerlab/example
```

##### Test Docker Compose Stack

[`docker-compose-test.yml`](.github/workflows/docker-compose-test.yml) builds and starts a Docker Compose stack and can run an optional smoke-test script.
Use it for projects where integration tests run against local services.

```yml
jobs:
  docker-compose:
    name: Test Docker Compose Stack
    uses: SchmiedmayerLab/.github/.github/workflows/docker-compose-test.yml@v0.3
    with:
      testscript: scripts/smoke-test.sh
```

#### Releases

##### Tag Action Release

Use [`action-release-tag.yml`](.github/workflows/action-release-tag.yml) for GitHub Actions repositories that publish semantic version tags.
For example, publishing `v2.4.2` can also update `v2` and `v2.4`.

```yml
permissions:
  contents: write

jobs:
  release-tags:
    name: Tag Action Release
    uses: SchmiedmayerLab/.github/.github/workflows/action-release-tag.yml@v0.3
    secrets:
      access-token: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
    with:
      user: PaulsAutomationBot
```

##### Format Release Notes

[`format-release-notes.yml`](.github/workflows/format-release-notes.yml) fetches a GitHub release and formats its release notes for downstream release automation.
Use it when another job needs the formatted notes from the `releasenotes` output.

```yml
jobs:
  release-notes:
    name: Format Release Notes
    uses: SchmiedmayerLab/.github/.github/workflows/format-release-notes.yml@v0.3
    with:
      release-tag: ${{ github.ref_name }}
      repository: ${{ github.repository }}
```

## Our Research

For more information, visit the [Schmiedmayer Lab GitHub organization](https://github.com/SchmiedmayerLab).

![Stanford and Stanford Medicine logos](https://raw.githubusercontent.com/SchmiedmayerLab/.github/main/assets/stanford-footer-light.png#gh-light-mode-only)
![Stanford and Stanford Medicine logos](https://raw.githubusercontent.com/SchmiedmayerLab/.github/main/assets/stanford-footer-dark.png#gh-dark-mode-only)
