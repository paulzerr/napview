# EXE Matrix Failure Summary (OS + Variant)

Source analyzed: `/home/rainfern/Downloads/exe-matrix-bundle.zip` (workflow run from 2026-02-18)

Important context: this run used `napview.napview_backend` directly for the old `system` variant, so those results do **not** represent the proper `napview` package entrypoint behavior.

- Total cells: 120
- Pass: 19
- Fail: 101

## Pass/fail meaning

- `PASS`: browser navigation reached `domcontentloaded` and screenshot was captured.
- `FAIL`: browser open/load was **not** confirmed, even if backend logs show the HTTP server responded.

## Failures grouped by OS + variant

| OS runner | Variant (`dll_mode`) | Failed | Passed | Primary failure reason |
|---|---|---:|---:|---|
| `macos-14` | `bundled` | 9 | 0 | `liblsl.dylib` architecture mismatch (`x86_64` library on `arm64` runner) |
| `macos-14` | `system` | 9 | 0 | `pylsl` cannot find `liblsl` in system path |
| `macos-15-intel` | `system` | 9 | 0 | `pylsl` cannot find `liblsl` in system path |
| `ubuntu-latest` | `system` | 9 | 0 | `pylsl` cannot find `liblsl` in system path |
| `ubuntu-22.04` | `system` | 9 | 0 | `pylsl` cannot find `liblsl` in system path |
| `windows-latest` | `bundled` | 12 | 0 | `Page.goto(... wait_until="domcontentloaded")` timeout after 45s |
| `windows-latest` | `system` | 12 | 0 | `Page.goto(... wait_until="domcontentloaded")` timeout after 45s |
| `windows-2022` | `bundled` | 11 | 1 | Mostly same 45s `Page.goto` timeout (one outlier pass) |
| `windows-2022` | `system` | 12 | 0 | `Page.goto(... wait_until="domcontentloaded")` timeout after 45s |

## Why these failed

1. `dll_mode=system` on Linux/macOS fails at backend startup because `pylsl` cannot load/find `liblsl`, so process exits before serving UI.
2. `macos-14 + bundled` fails at backend startup because packaged `liblsl.dylib` is x86_64 while runner is arm64.
3. Windows failures are not backend crashes. The server starts and serves `GET /`, `GET /static/gui.js`, and `/load_config`, but Playwright still times out waiting for `domcontentloaded`, so browser-open success is not confirmed.
4. There is a plausible interactive-browser side effect on Windows: backend currently calls `webbrowser.open(...)` (`napview/napview_backend.py:648`), which can trigger first-run/default-browser flows that are not clearly logged in these artifacts.

## Representative log files from the bundle

- `logs/exe-matrix-ubuntu-latest-chromium-1280x720-system__napview_server.log`
- `logs/exe-matrix-macos-14-chromium-1280x720-bundled__napview_server.log`
- `logs/exe-matrix-windows-latest-chromium-1280x720-bundled__runner.log`
- `logs/exe-matrix-windows-latest-chromium-1280x720-bundled__napview_server.log`
