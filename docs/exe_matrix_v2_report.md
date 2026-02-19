# EXE Matrix V2 Report (Filtered Scope)

Source bundle: `/home/rainfern/Downloads/exe-matrix-bundle-v2.zip`  
Run date in artifacts: 2026-02-19

## Scope used for this report

Excluded on purpose:
- All ARM runners (`ubuntu-24.04-arm`, macOS arm64 runners)
- `macos-13` (per your note: never expected to work)

Included runners:
- `ubuntu-latest`
- `ubuntu-22.04`
- `windows-latest`
- `windows-2025`
- `macos-15-intel`

## Results (in-scope only)

- Total cells: 14
- Pass: 10
- Fail: 4

| Runner | Variant | Chromium | Firefox | Notes |
|---|---|---|---|---|
| `ubuntu-latest` | `python_package` | PASS | PASS | Stable |
| `ubuntu-22.04` | `python_package` | PASS | PASS | Stable |
| `macos-15-intel` | `python_package` | PASS | PASS | Stable |
| `windows-latest` | `python_package` | PASS | PASS | Stable |
| `windows-2025` | `python_package` | PASS | PASS | Stable |
| `windows-latest` | `installer` | FAIL | FAIL | Timeout waiting for server URL |
| `windows-2025` | `installer` | FAIL | FAIL | Timeout waiting for server URL |

## Failure analysis (in-scope)

Installer failures are isolated to Windows:
- Error: `Timed out waiting for server URL in logs`
- `napview_server.log` is empty in these installer cells, so there is no startup trace from the built executable.

Interpretation:
- V2 package-entrypoint path works on all in-scope non-ARM platforms.
- V2 installer path is the blocker and should be debugged independently on Windows.
