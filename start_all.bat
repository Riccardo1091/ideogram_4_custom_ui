@echo off
title Ideogram 4 Local Studio
color 0A
cls

:: Garantisce CWD corretto anche con doppio clic da Explorer
cd /d "%~dp0"

echo(
echo  ============================================
echo   Ideogram 4 Local Studio
echo  ============================================
echo(

:: -------------------------------------------------------
::  SINGOLA ISTANZA - Controllo intelligente della porta 8000
:: -------------------------------------------------------
netstat -an | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    powershell -NoProfile -Command "try{$r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2 -EA Stop; exit 0}catch{exit 1}" >nul 2>&1
    if %errorlevel% == 0 (
        echo  [INFO] Il server Ideogram e' gia' in esecuzione sulla porta 8000.
        echo  [INFO] Apertura del browser...
        start http://127.0.0.1:8000/frontend/ideogram-studio.html
        echo(
        pause
        exit /b 0
    ) else (
        echo  [ERRORE] La porta 8000 e' gia' occupata da un'altra applicazione!
        echo  Chiudi il programma che occupa la porta 8000 e riavvia lo script.
        echo(
        goto :FATAL_EXIT
    )
)

:: -------------------------------------------------------
::  FASE 1 - Verifica reale di Python
:: -------------------------------------------------------
python -c "import sys; sys.exit(0)" >nul 2>&1
if %errorlevel% neq 0 (
    call :INSTALL_PYTHON
    if %errorlevel% neq 0 goto :FATAL_EXIT
)

:: -------------------------------------------------------
::  FASE 2 - Gestione Venv Rigorosa (Senza blocchi If nestati complessi)
:: -------------------------------------------------------
if not exist "%~dp0venv\Scripts\python.exe" goto :DO_SETUP

:: Test moduli core
"%~dp0venv\Scripts\python.exe" -c "import fastapi, torch, uvicorn, einops" >nul 2>&1
if %errorlevel% == 0 (
    echo  [OK] Ambiente virtuale esistente e funzionante.
    if not exist "%~dp0venv\.setup_done" echo 1 > "%~dp0venv\.setup_done"
    goto :START_SERVER
)

echo  [WARN] Ambiente virtuale rilevato ma incompleto (moduli mancanti).
echo  Installazione o ripristino delle dipendenze da requirements.txt...
echo(

:DO_SETUP
call :SETUP_VENV
if %errorlevel% neq 0 goto :FATAL_EXIT

:START_SERVER
:: -------------------------------------------------------
::  FASE 3 - Avvio in Primo Piano e Monitoraggio Asincrono
:: -------------------------------------------------------
echo  Avvio del server e monitoraggio in corso...
echo  (I log dell'applicazione verranno mostrati qui sotto in tempo reale)
echo(

:: Monitoraggio TCP asincrono puro
start /B "" powershell -NoProfile -Command "$r=0; while($r -lt 20){ try{ $c = New-Object System.Net.Sockets.TcpClient; $c.Connect('127.0.0.1', 8000); $c.Close(); Start-Process 'http://127.0.0.1:8000/frontend/ideogram-studio.html'; break; }catch{ Start-Sleep -Seconds 1; $r++ } }"

:: Esecuzione diretta di Uvicorn
if exist "%~dp0venv\Scripts\uvicorn.exe" (
    "%~dp0venv\Scripts\uvicorn.exe" backend.app:app --host 127.0.0.1 --port 8000
) else (
    echo  [ERRORE FATALE] Uvicorn non trovato dopo il setup.
    echo  Verifica il tuo file requirements.txt.
    goto :FATAL_EXIT
)

echo(
echo  ============================================
echo   Server arrestato con successo.
echo  ============================================
echo(
pause
exit /b 0


:: -------------------------------------------------------
::  USCITA IN CASO DI ERRORE FATALE
:: -------------------------------------------------------
:FATAL_EXIT
echo(
echo  Premi un tasto qualsiasi per chiudere questa finestra.
pause >nul
exit /b 1


:: ======================================================
::  SUBROUTINE: Installa Python automaticamente
:: ======================================================
:INSTALL_PYTHON
echo  [SETUP] Python non trovato o non valido - tentativo di installazione...
echo(

where winget >nul 2>&1
if %errorlevel% == 0 (
    echo  [INFO] Installazione tramite winget...
    winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% == 0 goto PY_REFRESH
)

echo  [INFO] Download Python 3.12.10 da python.org...
set "PY_INSTALLER=%TEMP%\python-3.12-installer.exe"
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '%PY_INSTALLER%' -UseBasicParsing"
if %errorlevel% neq 0 goto PY_MANUAL_MSG

echo  [INFO] Installazione silenziosa in corso...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
set "PY_INSTALL_ERR=%errorlevel%"
del /f /q "%PY_INSTALLER%" >nul 2>&1

if %PY_INSTALL_ERR% neq 0 goto PY_MANUAL_MSG

:PY_REFRESH
echo  [INFO] Configurazione variabili di ambiente...
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312\;%LOCALAPPDATA%\Programs\Python\Python312\Scripts\;%PATH%"
)

python -c "import sys; sys.exit(0)" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRORE] Python installato ma non risponde. Riavvia il PC.
    exit /b 1
)
exit /b 0

:PY_MANUAL_MSG
echo(
echo  ============================================
echo   ERRORE: Installa Python manualmente da:
echo   https://www.python.org/downloads/
echo  ============================================
echo(
exit /b 1


:: ======================================================
::  SUBROUTINE: Crea venv e installa dipendenze
:: ======================================================
:SETUP_VENV
echo  [SETUP] Configurazione ambiente virtuale...
if not exist "%~dp0venv\Scripts\python.exe" (
    python -m venv "%~dp0venv"
)

"%~dp0venv\Scripts\pip.exe" install --upgrade pip >nul 2>&1

echo  [SETUP] Installazione PyTorch...
"%~dp0venv\Scripts\pip.exe" install torch torchvision --index-url https://download.pytorch.org/whl/cu128
if %errorlevel% neq 0 (
    echo  [WARN] Fallback su PyTorch CPU...
    "%~dp0venv\Scripts\pip.exe" install torch torchvision --index-url https://download.pytorch.org/whl/cpu
)

echo  [SETUP] Installazione dipendenze rimanenti...
"%~dp0venv\Scripts\pip.exe" install --disable-pip-version-check -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo  [ERRORE] Installazione da requirements.txt fallita.
    exit /b 1
)

if exist "%~dp0comfy_core\requirements.txt" (
    echo  [SETUP] Installazione dipendenze ComfyUI...
    "%~dp0venv\Scripts\pip.exe" install --disable-pip-version-check -r "%~dp0comfy_core\requirements.txt"
)

echo 1 > "%~dp0venv\.setup_done"
exit /b 0
