@echo off
setlocal enabledelayedexpansion
title USeP OBE Syllabus-to-Class Record Generator - Local Server

cd /d "%~dp0"

echo ======================================================================
echo   USeP OBE Syllabus-to-Class Record Generator - Local Server Launcher
echo ======================================================================
echo.

:: 1. Detect Python Executable
set "PYTHON_EXE="

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [*] Using virtual environment (.venv)
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
    echo [*] Using virtual environment (venv)
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    ) else (
        where py >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_EXE=py"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not found on your system!
    echo Please install Python 3.10 or newer from https://www.python.org/
    echo and ensure "Add Python to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check and Install Required Dependencies
echo [*] Checking core Python dependencies...
%PYTHON_EXE% -c "import flask, werkzeug, pandas, openpyxl, fpdf, pypdf, requests" >nul 2>&1
if errorlevel 1 (
    echo [!] Missing dependencies detected. Installing required packages from requirements.txt...
    %PYTHON_EXE% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies. Please check your internet connection.
        pause
        exit /b 1
    )
    echo [*] Dependencies successfully installed.
) else (
    echo [*] All core dependencies verified.
)

echo.
echo [*] Launching local server on 0.0.0.0 ...
echo [*] Press Ctrl+C in this console window to stop the server at any time.
echo.

%PYTHON_EXE% app.py

if errorlevel 1 (
    echo.
    echo [ERROR] The server terminated unexpectedly.
    pause
)
