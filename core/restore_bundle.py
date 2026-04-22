"""Emit winget restore script from ``devkit-manifest.json`` (Phase 2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _iter_winget_restore_ids(manifest: dict[str, Any]) -> list[str]:
    tools = manifest.get("tools")
    if not isinstance(tools, list):
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for row in tools:
        if not isinstance(row, dict):
            continue
        if row.get("install_method") != "winget":
            continue
        wid = row.get("winget_id")
        if not isinstance(wid, str) or not wid.strip():
            continue
        wid = wid.strip()
        if wid in seen:
            continue
        seen.add(wid)
        ordered.append(wid)
    return ordered


def write_restore_winget_script(*, repo_root: Path) -> Path:
    """Write ``scripts/restore-winget-from-manifest.ps1`` (repo-relative manifest default)."""
    dest = repo_root / "scripts" / "restore-winget-from-manifest.ps1"
    dest.parent.mkdir(parents=True, exist_ok=True)

    body = r"""#Requires -Version 5.1
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
"""
    dest.write_text(body, encoding="utf-8")
    return dest


def refresh_restore_script_from_disk(manifest_path: Path, repo_root: Path) -> Path:
    """Validate manifest JSON, then refresh the portable winget restore helper."""
    manifest_path = manifest_path.resolve()
    text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(text)
    _ = _iter_winget_restore_ids(manifest)
    return write_restore_winget_script(repo_root=repo_root)
