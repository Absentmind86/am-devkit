<#
.SYNOPSIS
    AM-DevKit native Windows sanitization. No external downloads. No GUI.
.PARAMETER Preset
    Minimal  — 4 tweaks: telemetry, consumer features, service cleanup, WPBT disable.
    Standard — all Minimal tweaks plus: activity history, Game DVR, location services,
               Explorer auto-discovery, temp file deletion, DISM component cleanup,
               End Task on taskbar, system restore point, PowerShell 7 telemetry opt-out.
.NOTES
    Requires elevation for HKLM writes and service changes. Run via bootstrap/install.ps1
    or core/sanitize.py — both acquire admin before invoking this script.
#>
param(
    [Parameter(Mandatory)]
    [ValidateSet('Minimal', 'Standard')]
    [string]$Preset
)

$ErrorActionPreference = 'Continue'

$script:ErrCount = 0

function Set-Reg {
    param(
        [string]$Path,
        [string]$Name,
        $Value,
        [string]$Type = 'DWord'
    )
    try {
        if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }
        Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type $Type -Force
        Write-Host "  [reg] $Name = $Value  ($Path)"
    } catch {
        $script:ErrCount++
        Write-Host "  [warn] reg $Name failed: $_" -ForegroundColor Yellow
    }
}

function Set-Svc {
    param([string]$Name, [string]$Startup)
    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($null -eq $svc) { Write-Host "  [svc] $Name - not found, skipping"; return }
    try {
        Set-Service -Name $Name -StartupType $Startup -ErrorAction Stop
        if ($Startup -eq 'Disabled') {
            Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  [svc] $Name -> $Startup"
    } catch {
        $script:ErrCount++
        Write-Host "  [warn] svc $Name failed: $_" -ForegroundColor Yellow
    }
}

Write-Host ''
Write-Host "AM-DevKit Sanitization - Preset: $Preset" -ForegroundColor Cyan
Write-Host '============================================' -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Minimal tweaks (always applied)
# ---------------------------------------------------------------------------

Write-Host ''
Write-Host '[1/4] Disable Telemetry' -ForegroundColor White
Set-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo'         'Enabled'                                      0
Set-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy'                 'TailoredExperiencesWithDiagnosticDataEnabled' 0
Set-Reg 'HKCU:\Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy'    'HasAccepted'                                  0
Set-Reg 'HKCU:\Software\Microsoft\Input\TIPC'                                     'Enabled'                                      0
Set-Reg 'HKCU:\Software\Microsoft\InputPersonalization'                           'RestrictImplicitInkCollection'                1
Set-Reg 'HKCU:\Software\Microsoft\InputPersonalization'                           'RestrictImplicitTextCollection'               1
Set-Reg 'HKCU:\Software\Microsoft\InputPersonalization\TrainedDataStore'          'HarvestContacts'                              0
Set-Reg 'HKCU:\Software\Microsoft\Personalization\Settings'                       'AcceptedPrivacyPolicy'                        0
Set-Reg 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection' 'AllowTelemetry'                               0
Set-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'       'Start_TrackProgs'                             0
Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System'                        'PublishUserActivities'                        0
Set-Reg 'HKCU:\Software\Microsoft\Siuf\Rules'                                     'NumberOfSIUFInPeriod'                         0
Set-MpPreference -SubmitSamplesConsent 2 -ErrorAction Continue
Set-Svc 'DiagTrack'         Disabled
Set-Svc 'dmwappushservice'  Disabled

Write-Host ''
Write-Host '[2/4] Disable Consumer Features' -ForegroundColor White
Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent' 'DisableWindowsConsumerFeatures' 1

Write-Host ''
Write-Host '[3/4] Service Cleanup' -ForegroundColor White
$ramKB = (Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1KB
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control' -Name 'SvcHostSplitThresholdInKB' -Value $ramKB -Force
Write-Host "  [reg] SvcHostSplitThresholdInKB = $ramKB KB (matched to installed RAM)"
Set-Svc 'MapsBroker'       Manual
Set-Svc 'SharedAccess'     Disabled
Set-Svc 'TroubleshootingSvc' Manual
Set-Svc 'CscService'       Disabled

Write-Host ''
Write-Host '[4/4] Disable WPBT (Wake Platform Binary Table execution)' -ForegroundColor White
Set-Reg 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' 'DisableWpbtExecution' 1

if ($Preset -eq 'Standard') {

    Write-Host ''
    Write-Host '[5/13] Disable Activity History' -ForegroundColor White
    Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' 'EnableActivityFeed'    0
    Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' 'PublishUserActivities' 0
    Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System' 'UploadUserActivities'  0

    Write-Host ''
    Write-Host '[6/13] Disable Explorer Auto-Discovery (folder type cache)' -ForegroundColor White
    $bags    = 'HKCU:\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\Bags'
    $bagsMRU = 'HKCU:\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\BagMRU'
    Remove-Item -Path $bags    -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $bagsMRU -Recurse -Force -ErrorAction SilentlyContinue
    $allFolders = 'HKCU:\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\Bags\AllFolders\Shell'
    if (-not (Test-Path $allFolders)) { New-Item -Path $allFolders -Force | Out-Null }
    Set-ItemProperty -Path $allFolders -Name 'FolderType' -Value 'NotSpecified' -Type String -Force
    Write-Host '  [done] Explorer folder type cache cleared'

    Write-Host ''
    Write-Host '[7/13] Disable Game DVR / Game Bar capture' -ForegroundColor White
    Set-Reg 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR' 'AppCaptureEnabled' 0
    Set-Reg 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR'        'AllowGameDVR'      0

    Write-Host ''
    Write-Host '[8/13] Disable Location Services' -ForegroundColor White
    Set-Svc 'lfsvc' Disabled
    Set-Reg 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location' 'Value' 'Deny' 'String'
    Set-Reg 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}' 'SensorPermissionState' 0
    Set-Reg 'HKLM:\SYSTEM\Maps' 'AutoUpdateEnabled' 0

    Write-Host ''
    Write-Host '[9/13] Delete Temporary Files' -ForegroundColor White
    $count = 0
    Get-ChildItem -Path $Env:TEMP -Force -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        $count++
    }
    Get-ChildItem -Path "$Env:SystemRoot\Temp" -Force -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        $count++
    }
    Write-Host "  [done] Removed $count temporary items"

    Write-Host ''
    Write-Host '[10/13] DISM Component Cleanup (takes 2-5 minutes)' -ForegroundColor White
    dism.exe /online /Cleanup-Image /StartComponentCleanup
    Write-Host "  [done] DISM cleanup complete (exit $LASTEXITCODE)"

    Write-Host ''
    Write-Host '[11/13] Enable End Task on Taskbar right-click' -ForegroundColor White
    Set-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\TaskbarDeveloperSettings' 'TaskbarEndTask' 1

    Write-Host ''
    Write-Host '[12/13] Create System Restore Point' -ForegroundColor White
    Set-Reg 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore' 'SystemRestorePointCreationFrequency' 0
    try {
        Enable-ComputerRestore -Drive $Env:SystemDrive -ErrorAction SilentlyContinue
        Checkpoint-Computer -Description 'AM-DevKit sanitization checkpoint' -RestorePointType MODIFY_SETTINGS -ErrorAction Stop
        Write-Host '  [done] Restore point created'
    } catch {
        Write-Host "  [warn] Could not create restore point: $_" -ForegroundColor Yellow
    }

    Write-Host ''
    Write-Host '[13/13] Disable PowerShell 7 Telemetry' -ForegroundColor White
    [Environment]::SetEnvironmentVariable('POWERSHELL_TELEMETRY_OPTOUT', '1', 'Machine')
    Write-Host '  [done] POWERSHELL_TELEMETRY_OPTOUT=1 set machine-wide'
}

Write-Host ''
if ($script:ErrCount -eq 0) {
    Write-Host "Sanitization complete. ($Preset preset - no errors)" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Sanitization finished with $($script:ErrCount) warning(s). Check output above." -ForegroundColor Yellow
    exit 1
}
