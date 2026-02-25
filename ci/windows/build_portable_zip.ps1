param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$PythonVersion = "3.11.9",
    [string]$PackageName = "NAPVIEW_portable_win64"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$distDir = Join-Path $RepoRoot "dist"
$buildRoot = Join-Path $distDir "portable_windows_build"
$packageRoot = Join-Path $buildRoot $PackageName
$pythonRoot = Join-Path $packageRoot "python"
$zipPath = Join-Path $distDir "$PackageName.zip"
$modelsLogPath = Join-Path $packageRoot "NIDRA_models.sha256.tsv"

Write-Host "Repo root: $RepoRoot"
Write-Host "Package root: $packageRoot"
Write-Host "Python runtime version: $PythonVersion"

if (Test-Path -Path $buildRoot) {
    Remove-Item -Path $buildRoot -Recurse -Force
}
if (Test-Path -Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

$nugetUrl = "https://www.nuget.org/api/v2/package/python/$PythonVersion"
$nupkgPath = Join-Path $buildRoot "python.$PythonVersion.nupkg"
$nugetZipPath = Join-Path $buildRoot "python.$PythonVersion.zip"
$nugetExtractPath = Join-Path $buildRoot "python_nuget_extract"

Write-Host "Downloading Python runtime from: $nugetUrl"
Invoke-WebRequest -Uri $nugetUrl -OutFile $nupkgPath -TimeoutSec 900 -MaximumRedirection 5
Copy-Item -Path $nupkgPath -Destination $nugetZipPath -Force
Expand-Archive -Path $nugetZipPath -DestinationPath $nugetExtractPath -Force

$nugetPythonExe = Join-Path $nugetExtractPath "tools\python.exe"
if (-not (Test-Path -Path $nugetPythonExe)) {
    throw "Python runtime not found in NuGet package at $nugetPythonExe"
}

Copy-Item -Path (Join-Path $nugetExtractPath "tools\*") -Destination $pythonRoot -Recurse -Force
$pythonExe = Join-Path $pythonRoot "python.exe"

Write-Host "Bootstrapping pip"
& $pythonExe -m ensurepip --upgrade
& $pythonExe -m pip install --upgrade pip "setuptools<70.0.0" wheel

Write-Host "Installing napview and dependencies"
Push-Location -Path $RepoRoot
& $pythonExe -m pip install .
Pop-Location

$resourceCheck = @'
from napview.helpers import get_resource_root
root = get_resource_root()
required = ["assets", "templates", "static", "libs", "CONFIG_DEFAULTS.txt"]
missing = [entry for entry in required if not (root / entry).exists()]
if missing:
    raise SystemExit(f"Missing packaged assets: {missing} at {root}")
print(root)
'@

Write-Host "Validating packaged assets"
$resourceRootPath = (& $pythonExe -c $resourceCheck).Trim()
Set-Content -Path (Join-Path $packageRoot "resource_root.txt") -Value $resourceRootPath -Encoding ascii

$nidraModelsDir = (& $pythonExe -c "import pathlib, NIDRA; print(pathlib.Path(NIDRA.__file__).resolve().parent / 'models')").Trim()
if ([string]::IsNullOrWhiteSpace($nidraModelsDir)) {
    throw "Could not resolve NIDRA models directory"
}

Write-Host "Downloading NIDRA models to: $nidraModelsDir"
New-Item -ItemType Directory -Path $nidraModelsDir -Force | Out-Null
Set-Content -Path $modelsLogPath -Value "model`tsize_bytes`tsha256" -Encoding ascii

$modelDownloads = @(
    @{ Uri = "https://huggingface.co/pzerr/NIDRA_models/resolve/main/ez6.onnx"; Name = "ez6.onnx" },
    @{ Uri = "https://huggingface.co/pzerr/NIDRA_models/resolve/main/ez6moe.onnx"; Name = "ez6moe.onnx" },
    @{ Uri = "https://huggingface.co/pzerr/NIDRA_models/resolve/main/u-sleep-nsrr-2024.onnx"; Name = "u-sleep-nsrr-2024.onnx" },
    @{ Uri = "https://huggingface.co/pzerr/NIDRA_models/resolve/main/u-sleep-nsrr-2024_eeg.onnx"; Name = "u-sleep-nsrr-2024_eeg.onnx" }
)

foreach ($model in $modelDownloads) {
    $targetPath = Join-Path $nidraModelsDir $model.Name
    Write-Host "Downloading model: $($model.Name)"
    Invoke-WebRequest -Uri $model.Uri -OutFile $targetPath -TimeoutSec 900 -MaximumRedirection 5
    $fileInfo = Get-Item -Path $targetPath
    $hash = (Get-FileHash -Path $targetPath -Algorithm SHA256).Hash
    "$($model.Name)`t$($fileInfo.Length)`t$hash" | Add-Content -Path $modelsLogPath -Encoding ascii
}

Write-Host "Writing launcher"
$launcherPath = Join-Path $packageRoot "run_napview.bat"
@"
@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%ROOT%python\python.exe" -m napview.napview %*
exit /b %ERRORLEVEL%
"@ | Set-Content -Path $launcherPath -Encoding ascii

@"
NAPVIEW portable Windows package

1. Extract this zip to a writable folder.
2. Run run_napview.bat.
3. No system Python or admin installation required.

Notes
- Runtime source: CPython NuGet package version $PythonVersion.
- Includes NIDRA model files for offline-restricted environments.
"@ | Set-Content -Path (Join-Path $packageRoot "README_portable.txt") -Encoding ascii

Write-Host "Recording build metadata"
& $pythonExe -m pip freeze | Set-Content -Path (Join-Path $packageRoot "requirements.freeze.txt") -Encoding ascii

$buildInfo = [ordered]@{
    built_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    package_name = $PackageName
    python_nuget_version = $PythonVersion
    zip_path = $zipPath
    resource_root = $resourceRootPath
}
$buildInfo | ConvertTo-Json | Set-Content -Path (Join-Path $packageRoot "build_info.json") -Encoding ascii

Write-Host "Creating zip: $zipPath"
Compress-Archive -Path $packageRoot -DestinationPath $zipPath -CompressionLevel Optimal

$zipFile = Get-Item -Path $zipPath
Write-Host "Portable zip created: $($zipFile.FullName) ($([math]::Round($zipFile.Length / 1MB, 2)) MB)"
