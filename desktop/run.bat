@echo off
REM BlackBugsAI Quick Start Script for Windows

echo.
echo ===============================================
echo   BlackBugsAI Desktop - Quick Start
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org
    pause
    exit /b 1
)

echo ? Python detected
echo.

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ? Virtual environment created
    echo.
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)
echo ? Virtual environment activated
echo.

REM Install/update requirements
echo Installing dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies
    echo Please check your internet connection
    pause
    exit /b 1
)
echo ? Dependencies installed
echo.

REM Run tests (optional)
echo ===============================================
echo Running tests...
echo ===============================================
echo.
python test_all.py
if %errorlevel% neq 0 (
    echo Some tests failed. This might be OK if you don't have all optional dependencies.
    echo.
)

REM Launch application
echo.
echo ===============================================
echo Launching BlackBugsAI...
echo ===============================================
echo.
python main.py

REM Deactivate venv on exit
deactivate

pause
