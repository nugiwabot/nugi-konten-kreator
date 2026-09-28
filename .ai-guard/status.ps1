# =============================================================================
# status.ps1 -- Nugi AI Workspace Lock Status
# No elevation required -- read-only inspection
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "SilentlyContinue"

$REPO_ROOT  = Split-Path -Parent $PSScriptRoot
$STATE_FILE = Join-Path $PSScriptRoot "lock.state"
$LOCK_JSON  = Join-Path $PSScriptRoot "AI_LOCK.json"

Write-Host ""
Write-Host "+---------------------------------------------+" -ForegroundColor Cyan
Write-Host "|    NUGI AI WORKSPACE LOCK -- STATUS         |" -ForegroundColor Cyan
Write-Host "+---------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# -- Lock state ---------------------------------------------------------------
if (Test-Path $STATE_FILE) {
    $state = Get-Content $STATE_FILE -Raw | ConvertFrom-Json
    if ($state.locked -eq $true) {
        Write-Host "  Status    : [LOCKED]" -ForegroundColor Red
        Write-Host "  Locked at : $($state.locked_at)" -ForegroundColor Gray
        Write-Host "  Locked by : $($state.locked_by)" -ForegroundColor Gray
        Write-Host "  Backup    : $($state.backup_path)" -ForegroundColor Gray
    }
    else {
        Write-Host "  Status    : [UNLOCKED]" -ForegroundColor Green
        Write-Host "  Unlocked at : $($state.unlocked_at)" -ForegroundColor Gray
    }
}
else {
    Write-Host "  Status    : [UNKNOWN] (no lock.state found)" -ForegroundColor Yellow
    Write-Host "             Workspace has never been locked via this system." -ForegroundColor DarkGray
}

Write-Host ""

# -- Live ACL check per protected path ----------------------------------------
if (-not (Test-Path $LOCK_JSON)) {
    Write-Host "  WARNING: AI_LOCK.json not found. Cannot check individual paths." -ForegroundColor Yellow
    exit 0
}

$config = Get-Content $LOCK_JSON -Raw | ConvertFrom-Json

Write-Host "  Protected paths (live write-test):" -ForegroundColor White
Write-Host "  ---------------------------------------------" -ForegroundColor DarkGray

foreach ($rel in $config.protected_paths) {
    $target = Join-Path $REPO_ROOT $rel

    if (-not (Test-Path $target)) {
        Write-Host ("  {0,-45} [NOT FOUND]" -f $rel) -ForegroundColor DarkYellow
        continue
    }

    $is_dir = (Get-Item $target).PSIsContainer
    if ($is_dir) {
        $test_path = Join-Path $target ".ai-guard-write-test"
    }
    else {
        $test_path = $target + ".write-test-tmp"
    }

    $writable = $false
    try {
        [System.IO.File]::WriteAllText($test_path, "test") | Out-Null
        Remove-Item $test_path -Force -ErrorAction SilentlyContinue
        $writable = $true
    }
    catch {
        $writable = $false
    }

    if ($writable) {
        Write-Host ("  {0,-45} [WRITABLE]   not locked" -f $rel) -ForegroundColor Yellow
    }
    else {
        Write-Host ("  {0,-45} [READ-ONLY]  locked" -f $rel) -ForegroundColor Green
    }
}

# -- output/ check ------------------------------------------------------------
Write-Host ""
Write-Host "  Always-writable paths:" -ForegroundColor White
Write-Host "  ---------------------------------------------" -ForegroundColor DarkGray
foreach ($rel in $config.always_writable) {
    $target = Join-Path $REPO_ROOT $rel
    $test_path = Join-Path $target ".ai-guard-write-test"
    $writable = $false
    try {
        [System.IO.File]::WriteAllText($test_path, "test") | Out-Null
        Remove-Item $test_path -Force -ErrorAction SilentlyContinue
        $writable = $true
    }
    catch {
        $writable = $false
    }

    if ($writable) {
        Write-Host ("  {0,-45} [WRITABLE]   (expected)" -f $rel) -ForegroundColor Green
    }
    else {
        Write-Host ("  {0,-45} [ERROR]      not writable!" -f $rel) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  lock.ps1   --> Lock workspace   (run as Admin)" -ForegroundColor Gray
Write-Host "  unlock.ps1 --> Unlock workspace (run as Admin)" -ForegroundColor Gray
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
