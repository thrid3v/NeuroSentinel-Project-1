@echo off
title NeuroSentinel

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  Python was not found on your PATH.
    echo  Install Python 3.10+ from https://python.org (check "Add
    echo  python.exe to PATH" during setup), then run this again.
    echo ============================================================
    echo.
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo.
    echo First run: installing dependencies, this can take a few minutes...
    echo.
    python -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo.
        echo Dependency install failed - see the error above.
        pause
        exit /b 1
    )
)

cd /d "%~dp0src"
set PYTHONIOENCODING=utf-8

rem Streamlit's one-time "Welcome, enter your email" prompt lives in a
rem per-user file separate from this project's .streamlit/config.toml, and
rem blocks a non-interactive/double-clicked launch outright if not already
rem dismissed once. Pre-seed it so first run isn't silently stuck waiting
rem for keyboard input the user has no reason to expect.
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    echo [general] > "%USERPROFILE%\.streamlit\credentials.toml"
    echo email = "" >> "%USERPROFILE%\.streamlit\credentials.toml"
)

echo.
echo Starting NeuroSentinel - your browser will open automatically.
echo Close this window (or press Ctrl+C) to stop the app.
echo.

python -m streamlit run app.py

echo.
echo NeuroSentinel stopped.
pause
