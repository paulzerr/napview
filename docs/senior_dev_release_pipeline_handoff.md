# Senior Dev Handoff: Unified Rehearsal/Release Workflow

## Goal
Implement one GitHub Actions workflow that can run in two modes:

1. `rehearsal` (default)
2. `release`

It must cover all three publication outputs:

1. Windows installer release asset: `NAPVIEW_installer.exe`
2. Windows standalone release asset: `NAPVIEW_standalone.zip`
3. Python package publication to TestPyPI

For now, default behavior must be rehearsal and usable without tags.

## Source Workflows To Reuse (Do not redesign)

Use logic directly from these known-good scripts:

1. `backup/build_self_extracting_installer_and_release.yml.bak`
2. `backup/build_portable_windows_zip.yml` + `.github/workflows/build_portable_winows_zip.ps1`
3. `backup/publish_testpypi.yml.bak`

Only minimal glue/condition changes should be introduced.

## Required Behavior

### Triggers

- `push`: run automatically in rehearsal mode
- `workflow_dispatch`: allow manual runs with mode flags
- later for production release: enable tag trigger (`v*`) with release mode

### Default mode

- Default mode is `rehearsal`.
- On push, it should run rehearsal without publishing GitHub Release assets.

### Rehearsal mode outputs

- Build installer (`NAPVIEW_installer.exe`)
- Build standalone zip (`NAPVIEW_standalone.zip`)
- Build Python package
- Upload all outputs as GitHub Actions artifacts
- Optional TestPyPI publish should be flag-controlled (off by default on push)

### Release mode outputs

- Attach both binaries to GitHub Release in one run:
  - `NAPVIEW_installer.exe`
  - `NAPVIEW_standalone.zip`
- Publish package to TestPyPI

Expected release URLs:

- `https://github.com/paulzerr/napview/releases/latest/download/NAPVIEW_installer.exe`
- `https://github.com/paulzerr/napview/releases/latest/download/NAPVIEW_standalone.zip`

## Minimal Implementation Plan

1. Add new workflow, e.g. `.github/workflows/release_rehearsal.yml`.
2. Add workflow inputs:
   - `mode` (`rehearsal` or `release`, default `rehearsal`)
   - `publish_testpypi` (`true|false`, default `false`)
   - `testpypi_version` (default `0.1.1rc1`)
3. Keep existing Windows build commands from source workflows:
   - PyInstaller + self-extracting installer stage from `build_self_extracting...`
   - standalone ZIP build from `build_portable_windows_zip.yml` + existing `.ps1`
4. Rename/copy standalone output to exact filename `NAPVIEW_standalone.zip`.
5. In rehearsal mode:
   - upload artifacts only (`actions/upload-artifact`)
   - skip `softprops/action-gh-release`
6. In release mode:
   - call `softprops/action-gh-release@v2` with both files
7. Add separate TestPyPI job on ubuntu:
   - build with `python -m build`
   - publish using `pypa/gh-action-pypi-publish@release/v1`
   - gated by mode/flag logic
8. For rehearsal versioning:
   - set package version to `0.1.1rc1` (or higher pre-release) before publish step
   - do not attempt reuse of already-uploaded versions

## Versioning rule (important)

Do not reuse `0.1.0` on TestPyPI.

- Deleting/yanking does not reliably allow re-upload of same filename/version.
- Use new versions for each publish attempt.
- Start with `0.1.1rc1`.

## Recommended mode gates

Use boolean expressions roughly equivalent to:

- `is_release = (inputs.mode == 'release') || startsWith(github.ref, 'refs/tags/v')`
- `is_rehearsal = !is_release`

And:

- on push: force rehearsal behavior unless explicitly release-tag flow is enabled

## Acceptance Criteria

1. Push to branch triggers workflow and produces artifacts for installer + standalone + python dist.
2. Rehearsal run does not create GitHub Release assets unless explicitly requested.
3. Release mode attaches both files to a single release with exact names:
   - `NAPVIEW_installer.exe`
   - `NAPVIEW_standalone.zip`
4. TestPyPI publish works with `0.1.1rc1`.
5. Switching to real release requires only:
   - tag push enablement / tag creation
   - mode flag adjustment (if needed)

