@echo off
title Nugi Konten Kreator MCP Server (LAN / Network Mode)
chcp 65001 >nul

echo =====================================================================
echo   NUGI KONTEN KREATOR MCP SERVER — LAN / NETWORK MODE (SSE)
echo =====================================================================
echo.

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..

:: Detect Python
if exist "C:\Users\YANPRO-SERVER3\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" (
    set PYTHON_EXE=C:\Users\YANPRO-SERVER3\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
) else if exist "C:\Users\Nugi\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" (
    set PYTHON_EXE=C:\Users\Nugi\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
) else (
    set PYTHON_EXE=python
)

set HOST=0.0.0.0
set PORT=8000

echo [INFO] Repository Root: %REPO_ROOT%
echo [INFO] Python Executable: %PYTHON_EXE%
echo [INFO] Transport: SSE (Server-Sent Events)
echo [INFO] Binding: http://%HOST%:%PORT%/sse
echo.
echo [STATUS] Starting FastMCP Server...
echo [TIP] Connect from any computer on your network using:
echo       http://^<THIS_COMPUTER_IP^>:%PORT%/sse
echo.

"%PYTHON_EXE%" "%SCRIPT_DIR%server.py" --repo-root "%REPO_ROOT%" --transport sse --host %HOST% --port %PORT%

pause
