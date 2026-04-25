<#
.SYNOPSIS
    Restore Windows defaults — undo AM-DevKit sanitization tweaks.
.NOTES
    Self-elevates to admin if not already running elevated.
    Reverses registry and service changes made by scripts/sanitize.ps1.
    Deleted temp files and DISM component cleanup cannot be reversed.
#>

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Requesting elevation...' -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

$ErrorActionPreference = 'Continue'
$script:ErrCount = 0

function Restore-Reg {
    param([string]$Path, [string]$Name, $Value, [string]$Type = 'DWord')
    try {
        if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }
        Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type $Type -Force
        Write-Host "  [reg] $Name = $Value  ($Path)"
    } catch {
        $script:ErrCount++
        Write-Host "  [warn] $Name failed: $_" -ForegroundColor Yellow
    }
}

function Remove-RegProp {
    param([string]$Path, [string]$Name)
    try {
        if (Test-Path $Path) {
            Remove-ItemProperty -Path $Path -Name $Name -Force -ErrorAction SilentlyContinue
            Write-Host "  [reg] removed $Name  ($Path)"
        }
    } catch {
        $script:ErrCount++
        Write-Host "  [warn] remove $Name failed: $_" -ForegroundColor Yellow
    }
}

function Restore-Svc {
    param([string]$Name, [string]$Startup)
    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($null -eq $svc) { Write-Host "  [svc] $Name - not found, skipping"; return }
    try {
        Set-Service -Name $Name -StartupType $Startup -ErrorAction Stop
        Write-Host "  [svc] $Name -> $Startup"
    } catch {
        $script:ErrCount++
        Write-Host "  [warn] svc $Name failed: $_" -ForegroundColor Yellow
    }
}

Write-Host ''
Write-Host 'AM-DevKit - Restore Windows Defaults' -ForegroundColor Cyan
Write-Host '=====================================' -ForegroundColor Cyan
Write-Host ''

# ---------------------------------------------------------------------------
# Telemetry (Minimal tweak 1)
# ---------------------------------------------------------------------------
Write-Host '[1] Restore Telemetry settings' -ForegroundColor White
Restore-Reg    'HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo'          'Enabled'                                      1
Restore-Reg    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy'                  'TailoredExperiencesWithDiagnosticDataEnabled' 1
Restore-Reg    'HKCU:\Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy'     'HasAccepted'                                  1
Restore-Reg    'HKCU:\Software\Microsoft\Input\TIPC'                                      'Enabled'                                      1
Restore-Reg    'HKCU:\Software\Microsoft\InputPersonalization'                            'RestrictImplicitInkCollection'                0
Restore-Reg    'HKCU:\Software\Microsoft\InputPersonalization'                            'RestrictImplicitTextCollection'               0
Restore-Reg    'HKCU:\Software\Microsoft\InputPersonalization\TrainedDataStore'           'HarvestContacts'                              1
Remove-RegProp 'HKCU:\Software\Microsoft\Personalization\Settings'                        'AcceptedPrivacyPolicy'
Remove-RegProp 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection' 'AllowTelemetry'
Restore-Reg    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'        'Start_TrackProgs'                             1
Remove-RegProp 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System'                        'PublishUserActivities'
Remove-RegProp 'HKCU:\Software\Microsoft\Siuf\Rules'                                     'NumberOfSIUFInPeriod'
Set-MpPreference -SubmitSamplesConsent 1 -ErrorAction Continue
Restore-Svc 'DiagTrack'        Automatic
Restore-Svc 'dmwappushservice' Manual

# ---------------------------------------------------------------------------
# Consumer Features (Minimal tweak 2)
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[2] Restore Consumer Features' -ForegroundColor White
Remove-RegProp 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent' 'DisableWindowsConsumerFeatures'

# ---------------------------------------------------------------------------
# Service Cleanup (Minimal tweak 3)
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[3] Restore Service Cleanup' -ForegroundColor White
Remove-RegProp 'HKLM:\SYSTEM\CurrentControlSet\Control' 'SvcHostSplitThresholdInKB'
Write-Host '  [reg] SvcHostSplitThresholdInKB removed (Windows will use its default)'
Restore-Svc 'MapsBroker'         Automatic
Restore-Svc 'SharedAccess'       Manual
Restore-Svc 'TroubleshootingSvc' Manual
Restore-Svc 'CscService'         Manual

# ---------------------------------------------------------------------------
# WPBT (Minimal tweak 4)
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[4] Restore WPBT' -ForegroundColor White
Remove-RegProp 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' 'DisableWpbtExecution'

# ---------------------------------------------------------------------------
# Activity History (Standard tweak 5)
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[5] Restore Activity History' -ForegroundColor White
Remove-RegProp 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' 'EnableActivityFeed'
Remove-RegProp 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' 'UploadUserActivities'

# ---------------------------------------------------------------------------
# Explorer Auto-Discovery (Standard tweak 6) — not reversible
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[6] Explorer Auto-Discovery - skipped (Bags cache was cleared; cannot restore)' -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
# Game DVR (Standard tweak 7)
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[7] Restore Game DVR / Game Bar' -ForegroundColor White
Restore-Reg    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR' 'AppCaptureEnabled' 1
Remove-RegProp 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR'       'AllowGameDVR'

# ---------------------------------------------------------------------------
# Location Services (Standard tweak 8)
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[8] Restore Location Services' -ForegroundColor White
Restore-Svc 'lfsvc' Manual
Restore-Reg    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location' 'Value' 'Allow' 'String'
Remove-RegProp 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}' 'SensorPermissionState'
Restore-Reg    'HKLM:\SYSTEM\Maps' 'AutoUpdateEnabled' 1

# ---------------------------------------------------------------------------
# Temp files (Standard tweak 9) — not reversible
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[9] Temp files - skipped (deleted files cannot be restored)' -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
# DISM Cleanup (Standard tweak 10) — not reversible
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[10] DISM cleanup - skipped (component cleanup is irreversible)' -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
# End Task on Taskbar (Standard tweak 11)
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[11] Restore End Task on Taskbar' -ForegroundColor White
Restore-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\TaskbarDeveloperSettings' 'TaskbarEndTask' 0

# ---------------------------------------------------------------------------
# System Restore Point (Standard tweak 12) — use System Restore UI
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[12] System Restore Point - use System Restore (rstrui.exe) to revert to the AM-DevKit checkpoint' -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
# PowerShell 7 Telemetry (Standard tweak 13)
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '[13] Restore PowerShell 7 Telemetry opt-out' -ForegroundColor White
[Environment]::SetEnvironmentVariable('POWERSHELL_TELEMETRY_OPTOUT', $null, 'Machine')
Write-Host '  [done] POWERSHELL_TELEMETRY_OPTOUT removed'

Write-Host ''
if ($script:ErrCount -eq 0) {
    Write-Host 'Restore complete - no errors.' -ForegroundColor Green
} else {
    Write-Host "Restore finished with $($script:ErrCount) warning(s). Check output above." -ForegroundColor Yellow
}
Write-Host ''
Write-Host 'Note: A restart may be needed for all changes to take effect.' -ForegroundColor Cyan
Write-Host ''
