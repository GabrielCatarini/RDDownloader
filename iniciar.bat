@echo off
REM ======================================================================
REM  RDDownloader - lancador para Windows (rodar a partir do codigo-fonte)
REM
REM  Jeito mais facil: baixe o RDDownloader-windows.exe na pagina de
REM  Releases do GitHub e de dois cliques. Nada para instalar.
REM
REM  Este arquivo faz tudo sozinho num PC recem-formatado:
REM    1. procura o Python; se nao houver, instala via winget (sem admin)
REM    2. cria um ambiente isolado em .venv e instala as dependencias
REM    3. abre o programa sem janela de console
REM ======================================================================
setlocal
title RDDownloader
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" goto :deps

set "PYCMD="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD python -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul && set "PYCMD=python"
if defined PYCMD goto :venv

echo Python nao encontrado. Instalando o Python 3.12 - isso acontece so uma vez...
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
set "PYCMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
if not exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" goto :nopython

:venv
echo Preparando o RDDownloader - somente na primeira vez...
%PYCMD% -m venv .venv
if errorlevel 1 goto :fail

:deps
".venv\Scripts\python.exe" -c "import PyQt5, requests" >nul 2>nul
if not errorlevel 1 goto :run
echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :fail

:run
start "" ".venv\Scripts\pythonw.exe" "%~dp0rddownloader.py"
exit /b 0

:nopython
echo.
echo Nao foi possivel instalar o Python automaticamente.
echo Baixe o RDDownloader-windows.exe em:
echo   https://github.com/GabrielCatarini/RDDownloader/releases/latest
echo ou instale o Python em https://www.python.org/downloads/
echo marcando a opcao "Add python.exe to PATH".
pause
exit /b 1

:fail
echo.
echo Algo deu errado ao preparar o ambiente. Verifique sua internet e
echo tente de novo. Se continuar, apague a pasta .venv e rode outra vez.
pause
exit /b 1
