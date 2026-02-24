# Codex Handoff: Windows PyInstaller Firefox Push Self-Heal

Last updated: 2026-02-24 (local session date)

## What Happens If This Window Closes

- This Codex process stops immediately.
- Any GitHub Actions run already started keeps running on GitHub.
- Nothing is lost if changes were committed/pushed.

## Current State

- Repo: `paulzerr/napview`
- Branch: `dev`
- Current local commit: `56cfdd9`
- Workflow: `windows_pyinstaller_firefox_push.yml`
- Expected artifact: `windows-pyinstaller-firefox-push-debug`
- Latest known run at handoff creation:
  - Run ID: `22361662755`
  - Event: `push`
  - Status: `in_progress`
  - URL: `https://github.com/paulzerr/napview/actions/runs/22361662755`

## Scripts Added

- `scripts/run_windows_pyinstaller_firefox_push_cycle.sh`
  - Fully automatic cycle:
    1. commit + push to `dev` (if dirty)
    2. trigger workflow (push trigger if pushed; otherwise workflow_dispatch)
    3. wait for completion
    4. download logs + artifact output
- `scripts/fetch_latest_windows_pyinstaller_firefox_push_artifact.sh`
  - Downloads latest artifact for this workflow/branch.

## Resume Commands (for new Codex instance)

```bash
cd "/home/rainfern/ALL_PROJECTS/2025 - napview2"
git checkout dev
git pull --ff-only git@github.com:paulzerr/napview.git dev
```

If a run is already in progress, continue watching it:

```bash
gh run watch 22361662755 --repo paulzerr/napview --exit-status
```

Then fetch latest outputs:

```bash
./scripts/fetch_latest_windows_pyinstaller_firefox_push_artifact.sh
```

To run a full unattended cycle again:

```bash
./scripts/run_windows_pyinstaller_firefox_push_cycle.sh
```

## Output Location

- Default download dir: `/tmp/windows-pyinstaller-firefox-push-latest`
- Contains:
  - `_download_summary.json`
  - `workflow.log`
  - artifact files when available

## Instruction for New Codex Instance

Use this objective:

1. Keep self-healing loop fully automatic for `windows_pyinstaller_firefox_push.yml` on branch `dev`.
2. Do not ask the user to run push/trigger/fetch manually.
3. On each failure, collect logs/artifacts, apply fix, commit, and push.
4. Repeat until workflow is green.
