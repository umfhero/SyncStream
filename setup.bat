@echo off
echo ========================================
echo    SyncStream Installation
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

echo Running installation script...
echo.

python install.py

echo.
echo ========================================
echo    Installation Complete
echo ========================================
echo.
echo Run 'run.bat' to start SyncStream
pause
