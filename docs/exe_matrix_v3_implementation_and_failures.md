# EXE Matrix V3: Intended Behavior and Why It Failed

Source bundle: `/home/rainfern/Downloads/exe-matrix-bundle-v3.zip`  
Run date in artifacts: 2026-02-19

## Intended behavior in V3

Per cell, V3 was designed to:
1. Open GUI in Playwright
2. Wait 5 seconds
3. Click `START napview`
4. Wait 5 minutes
5. Save screenshot
6. Copy Napview-created session log file
7. Require the string `prediction successful` in:
   - process output log (`napview_server.log`)
   - Napview session log

## What happened

- Total cells: 24
- Pass: 0
- Fail: 24

## Scope used for diagnosis

Excluded from investigation (as requested):
- ARM runners
- `macos-13`

In-scope runners:
- `ubuntu-latest`, `ubuntu-22.04`, `windows-latest`, `windows-2025`, `macos-15-intel`

In-scope result:
- 14 / 14 failed

## Root causes from logs

### 1) Python package cells failed due the strict prediction-string gate

Observed error in summary rows:
- `Missing "prediction successful" in logs: terminal=False, session=False`

Reason this happened:
- The exact string `prediction successful` does not appear in this codebase.
- Analyzer logs show repeated failures, so successful prediction path is not reached.
- Server/session logs show repeated `Analyzer.predict_sleep_stage` failures (`'NoneType' object is not subscriptable`).
- Logs also show NIDRA model-load failures (`u-sleep-nsrr-2024.onnx` missing in runner home NIDRA model directory), which aligns with analyzer failing repeatedly.

### 2) Installer cells failed before URL detection

Observed error in summary rows:
- `Timed out waiting for server URL in logs`

Details:
- Windows installer `napview_server.log` files are empty for failed cells.
- So V3 could not discover startup URL via log parsing, and the HTTP probe also never found a live GUI endpoint in time.

## Bottom line

- V3 failure is not one issue; it is two stacked issues:
  1. Installer startup/observability issue on Windows.
  2. Python-package success criterion that requires a string not currently emitted, while analyzer is failing due model/prediction path errors.
