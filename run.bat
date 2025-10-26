@echo off
echo ========================================
echo    SyncStream Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo Starting SyncStream...
echo.

REM Run SyncStream
python src\syncstream.py

if errorlevel 1 (
    echo.
    echo ERROR: SyncStream failed to start
    echo Check the error messages above
    pause
)
