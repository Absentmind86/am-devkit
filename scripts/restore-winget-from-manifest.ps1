#Requires -Version 5.1
<#
.SYNOPSIS
  Re-apply winget installs recorded in devkit-manifest.json (AM-DevKit Phase 2).

.DESCRIPTION
  Reads unique winget_id rows (install_method = winget) and runs
  winget install for each. Safe to re-run; winget skips up-to-date packages.

.PARAMETER ManifestPath
  Path to devkit-manifest.json (default: <repo root>\devkit-manifest.json).
#>
param(
    [string] $ManifestPath = ''
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $ManifestPath = Join-Path $RepoRoot 'devkit-manifest.json'
}
if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw "Manifest not found: $ManifestPath"
}
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget is not available on PATH.'
}

$doc = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$tools = @($doc.tools)
if ($tools.Count -eq 0) {
    Write-Host 'No tools array in manifest.' -ForegroundColor Yellow
    exit 0
}

$seen = @{}
foreach ($t in $tools) {
    if ($null -eq $t) { continue }
    if ($t.install_method -ne 'winget') { continue }
    $id = [string]$t.winget_id
    if ([string]::IsNullOrWhiteSpace($id)) { continue }
    if ($seen.ContainsKey($id)) { continue }
    $seen[$id] = $true
    Write-Host "winget install --id $id" -ForegroundColor Cyan
    winget install --id $id -e --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) {
        Write-Host "winget exited $LASTEXITCODE for $id (continuing)" -ForegroundColor Yellow
    }
}
Write-Host 'Restore winget pass complete.' -ForegroundColor Green
exit 0
