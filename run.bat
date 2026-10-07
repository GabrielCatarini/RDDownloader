@echo off
REM ======================================================================
REM  RDDownloader - Windows launcher (run from source)
REM
REM  Easiest option: download RDDownloader-windows.exe from the Releases
REM  page and double-click it. Nothing to install.
REM
REM  This script sets everything up on a freshly installed PC:
REM    1. finds Python; if missing, installs it with winget (no admin)
REM    2. creates an isolated .venv and installs the dependencies
REM    3. starts the app without a console window
REM ======================================================================
setlocal
title RDDownloader
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" goto :deps

set "PYCMD="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD python -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul && set "PYCMD=python"
if defined PYCMD goto :venv

echo Python not found. Installing Python 3.12 - this only happens once...
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
set "PYCMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
if not exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" goto :nopython

:venv
echo Setting up RDDownloader - first run only...
%PYCMD% -m venv .venv
if errorlevel 1 goto :fail

:deps
".venv\Scripts\python.exe" -c "import PyQt5, requests" >nul 2>nul
if not errorlevel 1 goto :run
echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :fail

:run
start "" ".venv\Scripts\pythonw.exe" "%~dp0rddownloader.py"
exit /b 0

:nopython
echo.
echo Python could not be installed automatically.
echo Download RDDownloader-windows.exe instead:
echo   https://github.com/GabrielCatarini/RDDownloader/releases/latest
echo or install Python from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH".
pause
exit /b 1

:fail
echo.
echo Setup failed. Check your internet connection and try again.
echo If it keeps failing, delete the .venv folder and run this again.
pause
exit /b 1
