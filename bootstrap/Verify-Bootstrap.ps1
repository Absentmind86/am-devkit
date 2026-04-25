#Requires -Version 5.1
<#
.SYNOPSIS
    Download and SHA256-verify AM-DevKit's bootstrap script before running it.

.DESCRIPTION
    The standard one-liner (irm | iex) is convenient but pipes a script
    directly into memory with no integrity check. This script is the
    alternative for anyone who wants to verify what they are running:

      1. Downloads fresh.ps1 to a temp file.
      2. Computes its SHA256 hash.
      3. Compares it against the published hash in bootstrap/CHECKSUMS.sha256
         (also fetched fresh from the same commit).
      4. Prints both hashes so you can verify them yourself.
      5. Asks for confirmation before running.

    If the hashes do not match, the script stops and deletes the temp file.

.PARAMETER Branch
    Git branch to download from. Defaults to 'main'.

.PARAMETER AutoRun
    Skip the confirmation prompt and run immediately if hashes match.
    Only use this in automated environments after you have manually
    verified the hash once.

.EXAMPLE
    # Paste into an elevated PowerShell:
    irm https://raw.githubusercontent.com/Absentmind86/am-devkit/main/bootstrap/Verify-Bootstrap.ps1 | iex

.EXAMPLE
    # Or download this verifier itself first and read it:
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Absentmind86/am-devkit/main/bootstrap/Verify-Bootstrap.ps1" -OutFile "$env:TEMP\Verify-Bootstrap.ps1"
    notepad "$env:TEMP\Verify-Bootstrap.ps1"
    # Then: & "$env:TEMP\Verify-Bootstrap.ps1"

.NOTES
    HTTPS ensures transport security (TLS certificate pinned to GitHub's CA).
    SHA256 verification adds content integrity on top of that.
#>

[CmdletBinding()]
param(
    [string]$Branch   = 'main',
    [switch]$AutoRun
)

$ErrorActionPreference = 'Stop'

$BaseUrl     = "https://raw.githubusercontent.com/Absentmind86/am-devkit/$Branch/bootstrap"
$ScriptUrl   = "$BaseUrl/fresh.ps1"
$ChecksumUrl = "$BaseUrl/CHECKSUMS.sha256"

$TempScript  = Join-Path $env:TEMP "am-devkit-fresh-$(Get-Random).ps1"
$script:KeepFile = $false   # set to $true when user says N so finally doesn't delete

try {

    Write-Host ''
    Write-Host 'AM-DevKit Verified Bootstrap' -ForegroundColor Cyan
    Write-Host '============================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host "Branch   : $Branch"
    Write-Host "From     : $ScriptUrl"
    Write-Host ''

    # ── Step 1: Download the bootstrap script ────────────────────────────
    Write-Host 'Downloading fresh.ps1 ...' -NoNewline
    Invoke-WebRequest -Uri $ScriptUrl -OutFile $TempScript -UseBasicParsing
    Write-Host ' done' -ForegroundColor Green

    # ── Step 2: Compute hash ──────────────────────────────────────────────
    $actualHash = (Get-FileHash -Path $TempScript -Algorithm SHA256).Hash.ToUpper()
    Write-Host ''
    Write-Host "Downloaded SHA256 : $actualHash"

    # ── Step 3: Fetch published checksum ─────────────────────────────────
    Write-Host 'Fetching published checksum ...' -NoNewline
    $checksumContent = (Invoke-WebRequest -Uri $ChecksumUrl -UseBasicParsing).Content
    Write-Host ' done' -ForegroundColor Green

    # Format: "SHA256HASH  fresh.ps1" (sha256sum / CertUtil style)
    $publishedLine = ($checksumContent -split "`n") | Where-Object { $_ -match 'fresh\.ps1' } | Select-Object -First 1
    if (-not $publishedLine) {
        throw "Could not find a 'fresh.ps1' entry in CHECKSUMS.sha256. File contents:`n$checksumContent"
    }
    $publishedHash = ($publishedLine -split '\s+')[0].Trim().ToUpper()
    Write-Host "Published SHA256  : $publishedHash"
    Write-Host ''

    # ── Step 4: Compare ───────────────────────────────────────────────────
    if ($actualHash -ne $publishedHash) {
        Write-Host 'HASH MISMATCH — the downloaded script does not match the published checksum.' -ForegroundColor Red
        Write-Host 'This could mean:'  -ForegroundColor Red
        Write-Host '  - The file was modified in transit (unlikely over HTTPS).'
        Write-Host '  - The CHECKSUMS file has not been updated yet after a push.'
        Write-Host '  - You are on an unusual network that intercepts TLS.'
        Write-Host ''
        Write-Host 'The temp file has been deleted. Do not run it.' -ForegroundColor Red
        Remove-Item $TempScript -Force -ErrorAction SilentlyContinue
        exit 1
    }

    Write-Host 'Hash verified.' -ForegroundColor Green
    Write-Host ''

    # ── Step 5: Show file location + ask permission ───────────────────────
    Write-Host "Script saved to : $TempScript"
    Write-Host 'You can inspect it with: notepad "' + $TempScript + '"'
    Write-Host ''

    if (-not $AutoRun) {
        $answer = Read-Host 'Hashes match. Run fresh.ps1 now? [Y/N]'
        if ($answer -notmatch '^[Yy]') {
            $script:KeepFile = $true
            Write-Host ''
            Write-Host "Script kept at $TempScript — run it yourself when ready." -ForegroundColor Yellow
            Write-Host "  & `"$TempScript`""
            return
        }
    }

    # ── Step 6: Run ───────────────────────────────────────────────────────
    Write-Host ''
    Write-Host 'Running fresh.ps1 ...' -ForegroundColor Cyan
    & $TempScript

} finally {
    if (-not $script:KeepFile -and (Test-Path $TempScript)) {
        Remove-Item $TempScript -Force -ErrorAction SilentlyContinue
    }
}
