# =============================================================================
# unlock.ps1 -- Nugi AI Workspace Unlock
# Requires: Run as Administrator
# =============================================================================
#Requires -RunAsAdministrator

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$REPO_ROOT  = Split-Path -Parent $PSScriptRoot
$STATE_FILE = Join-Path $PSScriptRoot "lock.state"
$LOCK_JSON  = Join-Path $PSScriptRoot "AI_LOCK.json"

# -- Check lock state ---------------------------------------------------------
if (-not (Test-Path $STATE_FILE)) {
    Write-Host "INFO: No lock state found. Workspace may already be UNLOCKED." -ForegroundColor Yellow
    exit 0
}

$state = Get-Content $STATE_FILE -Raw | ConvertFrom-Json
if ($state.locked -ne $true) {
    Write-Host "INFO: Workspace is already UNLOCKED." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "+---------------------------------------------+" -ForegroundColor Magenta
Write-Host "|  NUGI AI WORKSPACE LOCK -- UNLOCK REQUEST  |" -ForegroundColor Magenta
Write-Host "+---------------------------------------------+" -ForegroundColor Magenta
Write-Host ""
Write-Host ("  Locked at  : {0}" -f $state.locked_at) -ForegroundColor Gray
Write-Host ("  Locked by  : {0}" -f $state.locked_by) -ForegroundColor Gray
Write-Host ("  Backup dir : {0}" -f $state.backup_path) -ForegroundColor Gray
Write-Host ""

# -- Explicit confirmation required -------------------------------------------
$confirm = Read-Host "  Type UNLOCK to confirm and restore write permissions"
if ($confirm -ne "UNLOCK") {
    Write-Host ""
    Write-Host "  ABORTED -- confirmation mismatch. Workspace remains LOCKED." -ForegroundColor Red
    exit 1
}
Write-Host ""

$BACKUP_PATH  = $state.backup_path
$CURRENT_USER = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$config = Get-Content $LOCK_JSON -Raw | ConvertFrom-Json

$restored_paths = @()
$failed_paths   = @()

foreach ($rel in $config.protected_paths) {
    $target = Join-Path $REPO_ROOT $rel

    if (-not (Test-Path $target)) {
        Write-Host ("  SKIP (not found): {0}" -f $rel) -ForegroundColor DarkYellow
        continue
    }

    $safe_name   = $rel -replace '[\\\/]', '__'
    $backup_file = Join-Path $BACKUP_PATH "$safe_name.acl"

    try {
        # Step 1: Remove explicit DENY entries
        icacls $target /remove:d "$($CURRENT_USER)" /T /Q 2>&1 | Out-Null

        # Step 2: Restore ACL backup if available
        if (Test-Path $backup_file) {
            $parent = Split-Path -Parent $target
            icacls $parent /restore $backup_file /Q 2>&1 | Out-Null
            Write-Host ("  [RESTORED]  {0}  (from backup)" -f $rel) -ForegroundColor Green
        }
        else {
            Write-Host ("  [DENY-REMOVED]  {0}  (no backup file)" -f $rel) -ForegroundColor Green
        }

        $restored_paths += $rel
    }
    catch {
        Write-Host ("  [FAILED]  {0} -- {1}" -f $rel, $_) -ForegroundColor Red
        $failed_paths += $rel
    }
}

# -- Verify output/ writable --------------------------------------------------
Write-Host ""
$output_path = Join-Path $REPO_ROOT "output"
if (Test-Path $output_path) {
    $test_file = Join-Path $output_path ".ai-guard-write-test"
    try {
        [System.IO.File]::WriteAllText($test_file, "write-test") | Out-Null
        Remove-Item $test_file -Force
        Write-Host "  [OK] output/ is WRITABLE." -ForegroundColor Green
    }
    catch {
        Write-Host "  [WARNING] output/ write test FAILED." -ForegroundColor Red
    }
}

# -- Verify a protected path is writable again --------------------------------
if ($restored_paths.Count -gt 0) {
    $sample    = Join-Path $REPO_ROOT $restored_paths[0]
    $test_file = Join-Path $sample ".ai-guard-write-test"
    try {
        [System.IO.File]::WriteAllText($test_file, "write-test") | Out-Null
        Remove-Item $test_file -Force
        Write-Host "  [OK] Protected paths are WRITABLE again." -ForegroundColor Green
    }
    catch {
        Write-Host "  [WARNING] Protected path write test failed -- check manually." -ForegroundColor Yellow
    }
}

# -- Update lock state --------------------------------------------------------
$new_state = @{
    locked         = $false
    unlocked_at    = (Get-Date -Format "o")
    unlocked_by    = $CURRENT_USER
    restored_paths = $restored_paths
    failed_paths   = $failed_paths
}
$new_state | ConvertTo-Json -Depth 5 | Set-Content -Path $STATE_FILE -Encoding UTF8

# -- Summary ------------------------------------------------------------------
Write-Host ""
Write-Host "==============================================" -ForegroundColor Magenta
Write-Host ("  UNLOCKED : {0} paths" -f $restored_paths.Count) -ForegroundColor Green
if ($failed_paths.Count -gt 0) {
    Write-Host ("  FAILED   : {0} paths" -f $failed_paths.Count) -ForegroundColor Red
}
Write-Host ("  User     : {0}" -f $CURRENT_USER) -ForegroundColor Gray
Write-Host "==============================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "  All protected paths are now WRITABLE." -ForegroundColor White
Write-Host "  You can now modify project files manually." -ForegroundColor White
Write-Host ""
