# Windows portable ZIP build

This build mode produces a fully portable Windows zip:

- bundled CPython runtime (NuGet package)
- napview + Python dependencies
- bundled NIDRA model files
- `run_napview.bat` launcher

Output:

- `dist/NAPVIEW_portable_win64.zip`

## Build in GitHub Actions

Run workflow:

- `.github/workflows/build_portable_windows_zip.yml`

Optional input:

- `python_runtime_version` (default: `3.11.9`)

## Build locally on Windows

From repository root:

```powershell
.\ci\windows\build_portable_zip.ps1
```

With explicit runtime version:

```powershell
.\ci\windows\build_portable_zip.ps1 -PythonVersion 3.11.9
```

## Package usage (end users)

1. Unzip `NAPVIEW_portable_win64.zip`
2. Double-click `run_napview.bat`

