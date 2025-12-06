@echo off
REM Quick start script for Butler system (Windows)

echo 🚀 Starting Butler Agent System
echo ================================
echo.

REM Check if .env exists
if not exist .env (
    echo ❌ .env file not found!
    echo    Please create .env with required variables
    echo    See .env.example for template
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found!
    exit /b 1
)

echo ✅ Environment OK
echo.
echo 📋 Choose what to run:
echo.
echo 1) Butler CLI (interactive interface)
echo 2) Worker Agent (job executor)
echo 3) Test NeoFS connection
echo 4) Both (open two terminals manually)
echo.
set /p choice="Enter choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo 🤖 Starting Butler CLI...
    python butler_cli.py
) else if "%choice%"=="2" (
    echo.
    echo 👷 Starting Worker Agent...
    python simple_worker.py
) else if "%choice%"=="3" (
    echo.
    echo 🧪 Testing NeoFS...
    python -c "from neofs_helper import test_neofs; test_neofs()"
) else if "%choice%"=="4" (
    echo.
    echo 🚀 Starting both components...
    echo.
    echo Please open TWO PowerShell windows and run:
    echo.
    echo Terminal 1: cd agents; python simple_worker.py
    echo Terminal 2: cd agents; python butler_cli.py
    echo.
    pause
) else (
    echo Invalid choice
    exit /b 1
)
