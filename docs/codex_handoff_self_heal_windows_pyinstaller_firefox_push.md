# Codex Handoff: Windows PyInstaller Firefox Push Self-Heal

Last updated: 2026-02-24

## Scope

- Repo: `paulzerr/napview`
- Branch: `dev`
- Workflow: `.github/workflows/windows_pyinstaller_firefox_push.yml`
- Goal: make `windows_pyinstaller_firefox_push.yml` pass on push to `dev`

## What Was Changed So Far

Recent workflow/debugging fixes already applied on `dev`:

1. Fixed PowerShell interpolation parse bug:
   - changed `$ProcessId:` to `${ProcessId}:`
2. Fixed debug helper contaminating pipeline values:
   - `Write-DebugLine` now pipes `Tee-Object` to `Out-Null`
3. Added deeper startup diagnostics:
   - `runner_debug.log`, `probe_attempts.log`, `tasklist_v.txt`, `netstat_*`, env dump, process snapshot
4. Added executable candidate logging and selection attempt:
   - writes `exe_candidates.txt` and `exe_path.txt`
5. Tightened probe behavior:
   - short request timeout, more explicit failure logging
6. Added automation scripts:
   - `scripts/run_windows_pyinstaller_firefox_push_cycle.sh`
   - `scripts/fetch_latest_windows_pyinstaller_firefox_push_artifact.sh`
   - cycle script now requires explicit `COMMIT_MESSAGE` when committing changes
7. Updated workflow run naming to be descriptive:
   - `run-name` now uses push commit message (or `workflow_dispatch` input `change_summary`)

## Current Workflow State

As of 2026-02-24:

- Latest run still in progress:
  - Run ID: `22368864305`
  - URL: `https://github.com/paulzerr/napview/actions/runs/22368864305`
  - Trigger: `push`
  - SHA: `8bc302a8340b424d5053db03c22ce90f1743bf69`
- Latest completed run:
  - Run ID: `22368306517`
  - Conclusion: `failure`
  - URL: `https://github.com/paulzerr/napview/actions/runs/22368306517`

## Last Confirmed Failure Signature

From downloaded artifact/logs of run `22368306517`:

1. `run_summary.json` shows timeout waiting for web UI.
2. `tasklist_v.txt` shows `NAPVIEW.exe` with `Window Title: Error`.
3. `runner_debug.log` shows only `attempt=1` then repeated probe timeouts.
4. `exe_path.txt` points to:
   - `D:\a\napview\napview\dist\NAPVIEW.exe`
5. `napview_stdout.log` and `napview_stderr.log` are empty.

Interpretation: process starts but likely fails very early (error dialog / startup error), never binds expected local port.

## Descriptive Run Name Change

Workflow header now uses:

- Push event: `github.event.head_commit.message`
- Manual dispatch: `github.event.inputs.change_summary` (default: `manual dispatch`)

So run names can look like:

- `ci(workflow): fix executable path selection | Windows PyInstaller Firefox Push Smoke | dev`

Instead of static:

- `Windows PyInstaller Firefox Push Smoke | dev | push | <sha>`

## How To Resume

```bash
cd "/home/rainfern/ALL_PROJECTS/2025 - napview2"
git checkout dev
git pull --ff-only git@github.com:paulzerr/napview.git dev
```

Watch in-progress run if needed:

```bash
gh run watch 22368864305 --repo paulzerr/napview --exit-status
```

Fetch latest artifact:

```bash
./scripts/fetch_latest_windows_pyinstaller_firefox_push_artifact.sh
```

Run full unattended cycle with descriptive commit title:

```bash
COMMIT_MESSAGE="ci(workflow): <actual fix summary>" ./scripts/run_windows_pyinstaller_firefox_push_cycle.sh
```

## Next Debugging Priorities

1. Verify which built executable should be launched in CI (`dist` root EXE vs nested one-dir EXE).
2. Capture the actual startup error dialog/content if possible (currently only `Window Title: Error` is visible).
3. Validate `exe_candidates.txt` on newest run and confirm selected path matches intended runtime layout.
4. Keep commits descriptive, since run names now mirror commit messages.
