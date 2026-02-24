# Codex Handoff: Windows PyInstaller Firefox Push Self-Heal

Last updated: 2026-02-24 (local session date, handover refresh)

## What Happens If This Window Closes

- This Codex process stops immediately.
- Any GitHub Actions run already started keeps running on GitHub.
- Nothing is lost if changes were committed/pushed.

## Current State

- Repo: `paulzerr/napview`
- Branch: `dev`
- Current local commit: `44b0f07`
- Workflow: `windows_pyinstaller_firefox_push.yml`
- Expected artifact: `windows-pyinstaller-firefox-push-debug`
- Latest completed run:
  - Run ID: `22366223960`
  - Event: `push`
  - Status: `completed`
  - Conclusion: `failure`
  - URL: `https://github.com/paulzerr/napview/actions/runs/22366223960`
- Latest failure root cause:
  - Launch step parser error (`InvalidVariableReferenceWithDrive`) before probing loop starts.
  - Failing patterns are debug strings containing `$ProcessId:` (colon immediately after variable in double-quoted string).
  - Example from run log: `Write-DebugLine "Get-NetTCPConnection failed for PID $ProcessId: $($_.Exception.Message)"`

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
gh run watch <RUN_ID> --repo paulzerr/napview --exit-status
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

Immediate next fix to apply:

1. In workflow PowerShell, replace debug strings that use `$ProcessId:` with `${ProcessId}:` (or equivalent non-ambiguous interpolation).
2. Re-run unattended cycle script.

Why the loop paused:

- User explicitly requested handover-only documentation and to not continue the loop in this pass.
