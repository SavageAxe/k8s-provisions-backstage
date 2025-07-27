@echo off
setlocal enabledelayedexpansion
set "ERRORLEVEL="

REM 📁 Determine script location
SET "SCRIPT_DIR=%~dp0"
REM Remove trailing backslash
SET "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
SET "HOME_DIR=%SCRIPT_DIR%\.."
pushd %HOME_DIR%
SET "HOME_DIR=%CD%"
popd

SET "VENV_DIR=%HOME_DIR%\.venv"
SET "REQUIREMENTS_FILE=%HOME_DIR%\requirements.txt"
SET "BASE_REQUIREMENTS_FILE=%SCRIPT_DIR%\base_requirements.txt"

echo 🧪 Checking for Python 3...
where python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Python 3 is not installed or not in PATH.
    exit /b 1
)

FOR /F "tokens=*" %%i IN ('python --version') DO SET PYTHON_VERSION=%%i
echo ✅ Python version: %PYTHON_VERSION%

REM 📦 Create virtual environment
IF NOT EXIST "%VENV_DIR%" (
    echo 📦 Creating virtual environment in %VENV_DIR%...
    python -m venv "%VENV_DIR%"
    echo ✅ Virtual environment created.
)

REM 🔁 Activate virtual environment
CALL "%VENV_DIR%\Scripts\activate.bat"

REM 📥 Install uv package
echo 📥 Installing 'uv' package in virtual environment...
python.exe -m pip install --upgrade pip
python.exe -m pip install uv

FOR /F "tokens=*" %%i IN ('uv --version') DO SET UV_VERSION=%%i
echo ✅ uv version: %UV_VERSION%

REM 📚 Install base requirements if present
IF EXIST "%BASE_REQUIREMENTS_FILE%" (
    echo 📚 Installing base dependencies from %BASE_REQUIREMENTS_FILE%...
    uv pip install -r "%BASE_REQUIREMENTS_FILE%"
) ELSE (
    echo ⚠️ %BASE_REQUIREMENTS_FILE% not found. Skipping base dependency installation.
)

REM 📚 Install main requirements
IF EXIST "%REQUIREMENTS_FILE%" (
    echo 📚 Installing dependencies from %REQUIREMENTS_FILE%...
    uv pip install -r "%REQUIREMENTS_FILE%"
) ELSE (
    echo ⚠️ %REQUIREMENTS_FILE% not found. Skipping dependency installation.
)

echo ✅ Setup complete. To activate your environment later:
echo     CALL "%VENV_DIR%\Scripts\activate.bat"

endlocal
