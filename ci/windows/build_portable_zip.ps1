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
New-Item -ItemType Directory -Path $pythonRoot -Force | Out-Null

$nugetUrl = "https://www.nuget.org/api/v2/package/python/$PythonVersion"
$nupkgPath = Join-Path $buildRoot "python.$PythonVersion.nupkg"
$nugetZipPath = Join-Path $buildRoot "python.$PythonVersion.zip"
$nugetExtractPath = Join-Path $buildRoot "python_nuget_extract"

Write-Host "Downloading Python runtime from: $nugetUrl"
Invoke-WebRequest -Uri $nugetUrl -OutFile $nupkgPath -TimeoutSec 900 -MaximumRedirection 5
$nupkgFile = Get-Item -LiteralPath $nupkgPath
if ($nupkgFile.Length -le 0) {
    throw "Downloaded NuGet package is empty: $nupkgPath"
}
Copy-Item -LiteralPath $nupkgPath -Destination $nugetZipPath -Force
Expand-Archive -LiteralPath $nugetZipPath -DestinationPath $nugetExtractPath -Force

$nugetPythonExe = Join-Path $nugetExtractPath "tools\python.exe"
if (-not (Test-Path -Path $nugetPythonExe)) {
    throw "Python runtime not found in NuGet package at $nugetPythonExe"
}

$nugetToolsDir = Join-Path $nugetExtractPath "tools"
if (-not (Test-Path -LiteralPath $nugetToolsDir)) {
    throw "NuGet tools directory not found at $nugetToolsDir"
}
Get-ChildItem -LiteralPath $nugetToolsDir -Force | Copy-Item -Destination $pythonRoot -Recurse -Force
$pythonExe = Join-Path $pythonRoot "python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Copied Python runtime missing executable at $pythonExe"
}

Write-Host "Bootstrapping pip"
& $pythonExe -m ensurepip --upgrade
& $pythonExe -m pip install --upgrade pip "setuptools<70.0.0" wheel

Write-Host "Installing napview and dependencies"
& $pythonExe -m pip install $RepoRoot
& $pythonExe -m pip check

$runtimeProbeScriptPath = Join-Path $buildRoot "probe_runtime_paths.py"
@'
import json
from pathlib import Path
import NIDRA
from napview.helpers import get_resource_root

payload = {
    "resource_root": str(Path(get_resource_root()).resolve()),
    "nidra_models_dir": str((Path(NIDRA.__file__).resolve().parent / "models").resolve()),
}
print(json.dumps(payload))
'@ | Set-Content -LiteralPath $runtimeProbeScriptPath -Encoding ascii

Write-Host "Validating packaged assets"
$runtimeProbeOutput = & $pythonExe $runtimeProbeScriptPath
$runtimeProbeJson = [string]($runtimeProbeOutput | Select-Object -Last 1)
if ([string]::IsNullOrWhiteSpace($runtimeProbeJson)) {
    throw "Runtime probe returned no JSON output"
}
if (-not $runtimeProbeJson.TrimStart().StartsWith("{")) {
    throw "Runtime probe did not return JSON on last line: $runtimeProbeJson"
}
$runtimeProbe = $runtimeProbeJson | ConvertFrom-Json
$resourceRootPath = [string]$runtimeProbe.resource_root
if ([string]::IsNullOrWhiteSpace($resourceRootPath) -or -not (Test-Path -LiteralPath $resourceRootPath)) {
    throw "Invalid resource root path returned by runtime: '$resourceRootPath'"
}
$requiredResourceEntries = @("assets", "templates", "static", "libs", "CONFIG_DEFAULTS.txt")
$missingResourceEntries = @()
foreach ($entry in $requiredResourceEntries) {
    if (-not (Test-Path -LiteralPath (Join-Path $resourceRootPath $entry))) {
        $missingResourceEntries += $entry
    }
}
if ($missingResourceEntries.Count -gt 0) {
    throw "Missing packaged assets: $($missingResourceEntries -join ', ') at $resourceRootPath"
}
$packageRootFullPath = [System.IO.Path]::GetFullPath($packageRoot)
$resourceRootFullPath = [System.IO.Path]::GetFullPath($resourceRootPath)
if (-not $resourceRootFullPath.StartsWith($packageRootFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Resource root resolved outside package root: $resourceRootFullPath"
}
$resourceRootRelativePath = $resourceRootFullPath.Substring($packageRootFullPath.Length).TrimStart('\', '/')
Set-Content -LiteralPath (Join-Path $packageRoot "resource_root.txt") -Value $resourceRootPath -Encoding utf8

$nidraModelsDir = [string]$runtimeProbe.nidra_models_dir
if ([string]::IsNullOrWhiteSpace($nidraModelsDir)) {
    throw "Could not resolve NIDRA models directory"
}
$pythonRootFullPath = [System.IO.Path]::GetFullPath($pythonRoot)
$nidraModelsFullPath = [System.IO.Path]::GetFullPath($nidraModelsDir)
if (-not $nidraModelsFullPath.StartsWith($pythonRootFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "NIDRA models directory resolved outside bundled runtime: $nidraModelsFullPath"
}

Write-Host "Downloading NIDRA models to: $nidraModelsDir"
New-Item -ItemType Directory -Path $nidraModelsDir -Force | Out-Null
Set-Content -LiteralPath $modelsLogPath -Value "model`tsize_bytes`tsha256" -Encoding utf8

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
    $fileInfo = Get-Item -LiteralPath $targetPath
    if ($fileInfo.Length -le 0) {
        throw "Downloaded model is empty: $targetPath"
    }
    $hash = (Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash
    "$($model.Name)`t$($fileInfo.Length)`t$hash" | Add-Content -LiteralPath $modelsLogPath -Encoding utf8
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
"@ | Set-Content -LiteralPath $launcherPath -Encoding ascii

@"
NAPVIEW portable Windows package

1. Extract this zip to a writable folder.
2. Run run_napview.bat.
3. No system Python or admin installation required.

Notes
- Runtime source: CPython NuGet package version $PythonVersion.
- Includes NIDRA model files for offline-restricted environments.
"@ | Set-Content -LiteralPath (Join-Path $packageRoot "README_portable.txt") -Encoding utf8

Write-Host "Recording build metadata"
& $pythonExe -m pip freeze | Set-Content -LiteralPath (Join-Path $packageRoot "requirements.freeze.txt") -Encoding utf8

$buildInfo = [ordered]@{
    built_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    package_name = $PackageName
    python_nuget_version = $PythonVersion
    zip_path = "dist/$PackageName.zip"
    resource_root = "portable_windows_build/$PackageName/$resourceRootRelativePath"
}
$buildInfo | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $packageRoot "build_info.json") -Encoding utf8

Write-Host "Creating zip: $zipPath"
Compress-Archive -LiteralPath $packageRoot -DestinationPath $zipPath -CompressionLevel Optimal

$zipFile = Get-Item -LiteralPath $zipPath
Write-Host "Portable zip created: $($zipFile.FullName) ($([math]::Round($zipFile.Length / 1MB, 2)) MB)"
