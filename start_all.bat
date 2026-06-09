@echo off
title Ideogram 4 Local Studio
color 0A
cls

:: Garantisce CWD corretto anche con doppio clic da Explorer
cd /d "%~dp0"

echo.
echo  ============================================
echo   Ideogram 4 Local Studio
echo  ============================================
echo.

:: -------------------------------------------------------
::  SINGOLA ISTANZA - controlla se porta 8000 e' gia' attiva
:: -------------------------------------------------------
netstat -an | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    echo  [INFO] Il server e' gia' in esecuzione sulla porta 8000.
    echo  [INFO] Apertura del browser sull'istanza esistente...
    start http://127.0.0.1:8000/frontend/ideogram-studio.html
    echo.
    pause
    exit /b 0
)

:: -------------------------------------------------------
::  FASE 1 - Assicura Python disponibile nel sistema
:: -------------------------------------------------------
where python >nul 2>&1
if %errorlevel% neq 0 (
    call :INSTALL_PYTHON
    if %errorlevel% neq 0 exit /b 1
)

:: -------------------------------------------------------
::  FASE 2 - Crea venv e installa dipendenze se necessario
:: -------------------------------------------------------
if not exist "%~dp0venv\Scripts\python.exe" (
    call :SETUP_VENV
    if %errorlevel% neq 0 exit /b 1
) else (
    echo  [OK] Ambiente virtuale pronto.
)

:: -------------------------------------------------------
::  FASE 3 - Avvia backend
:: -------------------------------------------------------
echo  Avvio backend API (porta 8000)...
start /B "" "%~dp0venv\Scripts\python.exe" -m uvicorn backend.app:app --host 127.0.0.1 --port 8000

:: -------------------------------------------------------
::  FASE 4 - Attendi che il backend risponda
:: -------------------------------------------------------
echo  In attesa che il backend sia pronto...
:WAIT_LOOP
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command "try{Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2 -EA Stop|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if %errorlevel% neq 0 goto WAIT_LOOP

:: -------------------------------------------------------
::  FASE 5 - Apri browser
:: -------------------------------------------------------
echo  Backend pronto!
start http://127.0.0.1:8000/frontend/ideogram-studio.html

echo.
echo  ============================================
echo   Studio in esecuzione: http://127.0.0.1:8000
echo   Chiudi questa finestra per spegnere il server.
echo  ============================================
echo.
pause
exit /b 0


:: ======================================================
::  SUBROUTINE: Installa Python automaticamente
:: ======================================================
:INSTALL_PYTHON
echo  [SETUP] Python non trovato - installazione automatica...
echo.

where winget >nul 2>&1
if %errorlevel% == 0 (
    echo  [INFO] Installazione tramite winget ^(Windows built-in^)...
    winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% == 0 goto :PY_REFRESH
    echo  [WARN] winget fallito, provo download diretto...
)

echo  [INFO] Download Python 3.12.10 da python.org...
set "PY_INSTALLER=%TEMP%\python-3.12-installer.exe"
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '%PY_INSTALLER%' -UseBasicParsing"
if %errorlevel% neq 0 (
    echo.
    echo  [ERRORE] Download Python fallito. Controlla la connessione internet.
    echo  Scarica e installa Python manualmente: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo  [INFO] Installazione silenziosa in corso...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
del /f /q "%PY_INSTALLER%" >nul 2>&1

:PY_REFRESH
echo  [INFO] Aggiornamento PATH di sessione...
for /f "skip=2 tokens=3*" %%A in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USR_PATH=%%A %%B"
for /f "skip=2 tokens=3*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYS_PATH=%%A %%B"
set "PATH=%USR_PATH%;%SYS_PATH%"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERRORE] Python ancora non trovato dopo l'installazione.
    echo  Riavvia il computer e riprova.
    echo.
    pause
    exit /b 1
)
echo  [OK] Python installato con successo.
exit /b 0

:: ======================================================
::  SUBROUTINE: Crea venv e installa dipendenze
:: ======================================================
:SETUP_VENV
echo  [SETUP] Creazione ambiente virtuale isolato ^(prima volta^)...
python -m venv "%~dp0venv"
if %errorlevel% neq 0 (
    echo.
    echo  [ERRORE] Creazione venv fallita.
    pause
    exit /b 1
)
echo  [OK] Venv creato.
echo.
echo  [SETUP] Aggiornamento pip...
"%~dp0venv\Scripts\pip.exe" install --upgrade pip >nul 2>&1

echo  [SETUP] Installazione PyTorch con supporto GPU ^(CUDA 12.8^)...
echo  ^(download pesante ~2GB - attendere^)...
"%~dp0venv\Scripts\pip.exe" install torch torchvision --index-url https://download.pytorch.org/whl/cu128
if %errorlevel% neq 0 (
    echo.
    echo  [WARN] Installazione PyTorch CUDA fallita, provo versione CPU...
    "%~dp0venv\Scripts\pip.exe\" install torch torchvision
)

echo.
echo  [SETUP] Installazione dipendenze rimanenti...
"%~dp0venv\Scripts\pip.exe" install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo  [ERRORE] Installazione dipendenze fallita. Controlla requirements.txt.
    pause
    exit /b 1
)
echo  [OK] Dipendenze installate con successo.
exit /b 0
