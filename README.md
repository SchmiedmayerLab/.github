<!--

This source file is part of the Schmiedmayer Lab open-source organization

SPDX-FileCopyrightText: 2026 Stanford University and the project authors (see CONTRIBUTORS.md)

SPDX-License-Identifier: MIT

-->

# Schmiedmayer Lab

This repository provides default community health files, reusable GitHub Actions workflows, templates, and shared documentation for the Schmiedmayer Lab organization.


## GitHub Actions

This repository contains reusable GitHub Actions workflows that automate common tasks across Schmiedmayer Lab projects.


### Build and Test with xcodebuild or fastlane

Allows GitHub Actions to build complex Swift packages supporting Apple platforms as well as Xcode projects with requirements ranging from custom commands and xcodebuild to Fastlane.
You can learn more about the arguments in the [`xcodebuild-fastlane.yml` GitHub Actions workflow file](https://github.com/SchmiedmayerLab/.github/blob/main/.github/workflows/xcodebuild-fastlane.yml).

```yml
jobs:
  buildandtest:
    name: Build and Test Swift Package
    uses: SchmiedmayerLab/.github/.github/workflows/xcodebuild-fastlane.yml@v0.1
    with:
      artifactname: TemplatePackage.xcresult
      runsonlabels: '["macOS", "self-hosted"]'
      scheme: TemplatePackage
```

### Merge and Upload Coverage

Merge and upload code coverage reports to display them on codecov.io.
You can learn more about the arguments in the [`coverage.yml` GitHub Actions workflow file](https://github.com/SchmiedmayerLab/.github/blob/main/.github/workflows/coverage.yml).

```yml
jobs:
  uploadcoveragereport:
    name: Merge and Upload Coverage
    uses: SchmiedmayerLab/.github/.github/workflows/coverage.yml@v0.1
    with:
      coveragereports: ResultBundle1.xcresult ResultBundle2.xcresult
```

### Check REUSE Compliance

Check that all your source files conform to the REUSE specification.
You can learn more about the arguments in the [`reuse.yml` GitHub Actions workflow file](https://github.com/SchmiedmayerLab/.github/blob/main/.github/workflows/reuse.yml).

```yml
jobs:
  reuse_action:
    name: Check REUSE Compliance
    uses: SchmiedmayerLab/.github/.github/workflows/reuse.yml@v0.1
```

### Run SwiftLint

Ensure that all Swift files conform to the defined style guide.
You can learn more about the arguments in the [`swiftlint.yml` GitHub Actions workflow file](https://github.com/SchmiedmayerLab/.github/blob/main/.github/workflows/swiftlint.yml).

```yml
  swiftlint:
    name: Run SwiftLint
    uses: SchmiedmayerLab/.github/.github/workflows/swiftlint.yml@v0.1
```

### Tag Action Release

A small GitHub Actions workflow that automatically tags releases based on semantic version tags, which is useful for GitHub Actions repositories. For example, if you tag a release as v2.4.2, the workflow also tags v2 and v2.4. You can learn more about the arguments in the [`action-release-tag.yml` GitHub Actions workflow file](https://github.com/SchmiedmayerLab/.github/blob/main/.github/workflows/action-release-tag.yml).

```yml
jobs:
  releasetag:
    name: Tag Action Release
    uses: SchmiedmayerLab/.github/.github/workflows/action-release-tag.yml@v0.1
    secrets:
      access-token: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
    with:
      user: PaulsAutomationBot
```

### Build XCArchive

A GitHub Actions workflow that builds an XCArchive based on an Xcode workspace file with a specific scheme. The resulting archive is uploaded and stored as an artifact.
You can learn more about the arguments in the [`xcarchive.yml` GitHub Actions workflow file](https://github.com/SchmiedmayerLab/.github/blob/main/.github/workflows/xcarchive.yml).

```yml
jobs:
  build-xcarchive:
    name: Build XCArchive
    uses: SchmiedmayerLab/.github/.github/workflows/xcarchive.yml@v0.1
    with:
      workspaceFile: example.xcworkspace
      xcArchiveName: exampleXCArchiveName
      scheme: exampleScheme
      version: 0.1.0
```

### Build XCFramework

A GitHub Actions workflow that creates an XCFramework from an Xcode workspace file with a specific scheme. As an intermediate step, the workflow uses [`xcarchive.yml`](https://github.com/SchmiedmayerLab/.github/blob/main/.github/workflows/xcarchive.yml) to create the XCArchives that are packaged within the XCFramework. The resulting XCFramework is uploaded as an artifact.
You can learn more about the arguments in the [`xcframework.yml` GitHub Actions workflow file](https://github.com/SchmiedmayerLab/.github/blob/main/.github/workflows/xcframework.yml).

```yml
jobs:
  create-xcframework-workflow:
    name: Build XCFramework
    uses: SchmiedmayerLab/.github/.github/workflows/xcframework.yml@v0.1
    with:
      workspaceFile: example.xcworkspace
      xcFrameworkName: exampleXCFrameworkName
      scheme: exampleScheme
      version: 0.1.0
```



## Our Research

For more information, visit the [Schmiedmayer Lab GitHub organization](https://github.com/SchmiedmayerLab).

![Stanford and Stanford Medicine logos](https://raw.githubusercontent.com/SchmiedmayerLab/.github/main/assets/stanford-footer-light.png#gh-light-mode-only)
![Stanford and Stanford Medicine logos](https://raw.githubusercontent.com/SchmiedmayerLab/.github/main/assets/stanford-footer-dark.png#gh-dark-mode-only)
