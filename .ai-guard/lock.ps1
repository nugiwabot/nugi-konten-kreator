# =============================================================================
# lock.ps1 -- Nugi AI Workspace Lock
# Requires: Run as Administrator
# =============================================================================
#Requires -RunAsAdministrator

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$REPO_ROOT  = Split-Path -Parent $PSScriptRoot
$LOCK_JSON  = Join-Path $PSScriptRoot "AI_LOCK.json"
$BACKUP_DIR = Join-Path $PSScriptRoot "backups"
$TIMESTAMP  = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$BACKUP_PATH = Join-Path $BACKUP_DIR $TIMESTAMP

# -- Read config --------------------------------------------------------------
if (-not (Test-Path $LOCK_JSON)) {
    Write-Error "AI_LOCK.json not found at $LOCK_JSON. Aborting."
    exit 1
}
$config = Get-Content $LOCK_JSON -Raw | ConvertFrom-Json

# -- Check current lock state -------------------------------------------------
$STATE_FILE = Join-Path $PSScriptRoot "lock.state"
if (Test-Path $STATE_FILE) {
    $state = Get-Content $STATE_FILE -Raw | ConvertFrom-Json
    if ($state.locked -eq $true) {
        Write-Host "WARNING: Workspace is already LOCKED (locked at $($state.locked_at))." -ForegroundColor Yellow
        Write-Host "         Run unlock.ps1 first." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Write-Host "+---------------------------------------------+" -ForegroundColor Cyan
Write-Host "|   NUGI AI WORKSPACE LOCK -- APPLYING LOCK  |" -ForegroundColor Cyan
Write-Host "+---------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# -- Create backup directory --------------------------------------------------
New-Item -ItemType Directory -Force -Path $BACKUP_PATH | Out-Null
Write-Host "  Backup dir : $BACKUP_PATH" -ForegroundColor Gray

# -- Resolve current user -----------------------------------------------------
$CURRENT_USER = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Host "  User       : $CURRENT_USER" -ForegroundColor Gray
Write-Host ""

$locked_paths  = @()
$failed_paths  = @()

foreach ($rel in $config.protected_paths) {
    $target = Join-Path $REPO_ROOT $rel

    if (-not (Test-Path $target)) {
        Write-Host ("  SKIP (not found): {0}" -f $rel) -ForegroundColor DarkYellow
        continue
    }

    $safe_name   = $rel -replace '[\\\/]', '__'
    $backup_file = Join-Path $BACKUP_PATH "$safe_name.acl"

    try {
        # Save existing ACL
        icacls $target /save $backup_file /T /Q 2>$null
        Write-Host ("  [BACKUP]  {0}" -f $rel) -ForegroundColor DarkGray

        # Deny Write, Delete, WriteAttributes for current user
        icacls $target /deny "$($CURRENT_USER):(W,D,WATTR,WDAC)" /T /Q 2>&1 | Out-Null
        icacls $target /deny "$($CURRENT_USER):(OI)(CI)(W,D)" /T /Q 2>&1 | Out-Null

        Write-Host ("  [LOCKED]  {0}" -f $rel) -ForegroundColor Green
        $locked_paths += $rel
    }
    catch {
        Write-Host ("  [FAILED]  {0} -- {1}" -f $rel, $_) -ForegroundColor Red
        $failed_paths += $rel
    }
}

# -- Verify output/ is still writable -----------------------------------------
Write-Host ""
$output_path = Join-Path $REPO_ROOT "output"
if (Test-Path $output_path) {
    $test_file = Join-Path $output_path ".ai-guard-write-test"
    try {
        [System.IO.File]::WriteAllText($test_file, "write-test") | Out-Null
        Remove-Item $test_file -Force
        Write-Host "  [OK] output/ is still WRITABLE -- AI can work normally." -ForegroundColor Green
    }
    catch {
        Write-Host "  [WARNING] output/ write test FAILED. Check ACLs manually." -ForegroundColor Red
    }
}

# -- Write lock state ---------------------------------------------------------
$lock_state = @{
    locked       = $true
    locked_at    = (Get-Date -Format "o")
    locked_by    = $CURRENT_USER
    backup_path  = $BACKUP_PATH
    locked_paths = $locked_paths
    failed_paths = $failed_paths
}
$lock_state | ConvertTo-Json -Depth 5 | Set-Content -Path $STATE_FILE -Encoding UTF8

# -- Summary ------------------------------------------------------------------
Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ("  LOCKED  : {0} paths" -f $locked_paths.Count) -ForegroundColor Green
if ($failed_paths.Count -gt 0) {
    Write-Host ("  FAILED  : {0} paths" -f $failed_paths.Count) -ForegroundColor Red
}
Write-Host ("  Backup  : {0}" -f $BACKUP_PATH) -ForegroundColor Gray
Write-Host ("  User    : {0}" -f $CURRENT_USER) -ForegroundColor Gray
Write-Host ("  Time    : {0}" -f $TIMESTAMP) -ForegroundColor Gray
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  AI agents can READ protected files but cannot MODIFY them." -ForegroundColor White
Write-Host "  To unlock: .ai-guard\unlock.ps1  (as Admin)" -ForegroundColor White
Write-Host ""
