#Requires -Version 5.1
<#
.SYNOPSIS
  Re-apply AM-DevKit winget installs from devkit-manifest.json (Phase 2).

.DESCRIPTION
  Delegates to restore-winget-from-manifest.ps1 in this directory, which reads
  unique winget_id entries from the manifest next to the repo root.

.PARAMETER ManifestPath
  Optional path to devkit-manifest.json (default: <repo root>\devkit-manifest.json).
#>
param(
    [string] $ManifestPath = ''
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    $ManifestPath = Join-Path $RepoRoot 'devkit-manifest.json'
}
$WingetRestore = Join-Path $ScriptDir 'restore-winget-from-manifest.ps1'

if (-not (Test-Path -LiteralPath $ManifestPath)) {
    Write-Host "Manifest not found: $ManifestPath" -ForegroundColor Red
    Write-Host 'Run the installer once so devkit-manifest.json exists, or pass -ManifestPath.' -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path -LiteralPath $WingetRestore)) {
    Write-Host "Missing $WingetRestore" -ForegroundColor Red
    Write-Host 'Run core.installer finalize once to generate the helper script.' -ForegroundColor Yellow
    exit 1
}

Write-Host "AM-DevKit: restoring winget packages from manifest..." -ForegroundColor Cyan
& $WingetRestore -ManifestPath $ManifestPath
exit $LASTEXITCODE
