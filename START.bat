@echo off
title SyncStream v1.0
color 0B

echo.
echo ========================================
echo    SyncStream v1.0 - First Release
echo ========================================
echo.

REM Check if setup has been run
if not exist "config\profiles.json" (
    echo WARNING: profiles.json not found!
    echo.
    echo Running setup first...
    echo.
    call setup.bat
    if errorlevel 1 (
        echo.
        echo Setup failed. Please fix errors and try again.
        pause
        exit /b 1
    )
)

REM Run pre-flight check
echo Running pre-flight check...
echo.
python check_setup.py
if errorlevel 1 (
    echo.
    echo ========================================
    echo    Setup incomplete - see errors above
    echo ========================================
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Launching SyncStream...
echo ========================================
echo.

REM Launch SyncStream
python src\syncstream.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo    SyncStream encountered an error
    echo ========================================
    echo.
    pause
)
