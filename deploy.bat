@echo off
setlocal enabledelayedexpansion

echo Jenkins UI - Alternative Interface
echo ==================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH. Please install Python 3.7 or higher.
    pause
    exit /b 1
)

REM Check if pip is installed
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip is not installed. Please install pip.
    pause
    exit /b 1
)

echo ✅ Python and pip are installed

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Check if .env file exists
if not exist ".env" (
    echo ⚙️  Creating .env file from template...
    copy env.example .env
    echo 📝 Please edit .env file with your Jenkins configuration
    echo    - JENKINS_URL: Your Jenkins server URL
    echo    - JENKINS_USERNAME: Your Jenkins username
    echo    - JENKINS_PASSWORD: Your Jenkins password
    echo    - SECRET_KEY: A random secret key
    echo.
    echo Press Enter to continue after editing .env file...
    pause
)

REM Test connection
echo 🔗 Testing Jenkins connection...
python run.py --test-only >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Warning: Could not connect to Jenkins
    echo    Make sure your Jenkins server is running and credentials are correct
    echo    You can still run the application, but some features may not work
    echo.
    set /p continue="Continue anyway? (y/N): "
    if /i not "!continue!"=="y" (
        exit /b 1
    )
)

echo 🚀 Starting Jenkins UI...
echo    Access the application at: http://localhost:5000
echo    Press Ctrl+C to stop the server
echo.

REM Run the application
python run.py

pause 