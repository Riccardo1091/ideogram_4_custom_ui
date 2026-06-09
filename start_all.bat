@echo off
title Ideogram 4 Local Studio
color 0A
cls

echo.
echo  ============================================
echo   Ideogram 4 Local Studio - Avvio in corso
echo  ============================================
echo.

set "VENV_PYTHON=%~dp0venv\Scripts\python.exe"
set "VENV_PIP=%~dp0venv\Scripts\pip.exe"
set "REQ_FILE=%~dp0requirements.txt"

:: -------------------------------------------------------
::  FASE 1 - Assicura Python disponibile nel sistema
:: -------------------------------------------------------
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [SETUP] Python non trovato - installazione automatica in corso...
    echo.

    :: Prova prima winget (Windows 10/11 built-in)
    where winget >nul 2>&1
    if %errorlevel% == 0 (
        echo  [INFO] Utilizzo winget per installare Python 3.12...
        winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        if %errorlevel% neq 0 (
            echo  [WARN] winget ha fallito, provo download diretto...
            goto :DOWNLOAD_PYTHON
        )
        echo  [OK] Python installato tramite winget.
        goto :REFRESH_PATH
    )

    :DOWNLOAD_PYTHON
    echo  [INFO] Download installer Python 3.12 da python.org...
    set "PY_INSTALLER=%TEMP%\python-installer.exe"
    powershell -NoProfile -Command ^
        "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile '%PY_INSTALLER%' -UseBasicParsing"
    if %errorlevel% neq 0 (
        echo.
        echo  [ERRORE] Download Python fallito. Controlla la connessione internet.
        echo  In alternativa installa Python manualmente da https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )

    echo  [INFO] Installazione Python in corso (modalita' silenziosa)...
    "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
    if %errorlevel% neq 0 (
        echo.
        echo  [ERRORE] Installazione Python fallita.
        echo  Prova a installare Python manualmente da https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    del /f /q "%PY_INSTALLER%" >nul 2>&1
    echo  [OK] Python 3.12 installato con successo.

    :REFRESH_PATH
    :: Aggiorna le variabili di ambiente nella sessione corrente
    echo  [INFO] Aggiornamento PATH di sessione...
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%B"
    for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYS_PATH=%%B"
    set "PATH=%USER_PATH%;%SYS_PATH%;%PATH%"

    :: Verifica finale
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  [ERRORE] Python ancora non trovato dopo l'installazione.
        echo  Riavvia il computer e prova di nuovo.
        echo.
        pause
        exit /b 1
    )
    echo  [OK] Python disponibile nel PATH.
    echo.
)

:: -------------------------------------------------------
::  FASE 2 - Crea venv se non esiste e installa dipendenze
:: -------------------------------------------------------
if not exist "%VENV_PYTHON%" (
    echo  [SETUP] Creazione ambiente virtuale isolato...
    python -m venv "%~dp0venv"
    if %errorlevel% neq 0 (
        echo.
        echo  [ERRORE] Creazione venv fallita.
        pause
        exit /b 1
    )
    echo  [OK] Venv creato.
    echo.

    echo  [SETUP] Installazione dipendenze (prima volta - potrebbe richiedere qualche minuto)...
    echo  (nulla viene installato sul sistema, solo nel venv locale)
    echo.
    "%VENV_PIP%" install --upgrade pip >nul 2>&1
    "%VENV_PIP%" install -r "%REQ_FILE%"
    if %errorlevel% neq 0 (
        echo.
        echo  [ERRORE] Installazione dipendenze fallita. Controlla requirements.txt.
        pause
        exit /b 1
    )
    echo.
    echo  [OK] Dipendenze installate con successo.
    echo.
) else (
    echo  [OK] Ambiente pronto.
)

:: -------------------------------------------------------
::  FASE 3 - Avvia il backend
:: -------------------------------------------------------
echo  Avvio backend API (porta 8000)...
pushd "%~dp0"
start /B "" "%VENV_PYTHON%" -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
popd

:: -------------------------------------------------------
::  FASE 4 - Attendi che il backend risponda
:: -------------------------------------------------------
echo  In attesa che il backend sia pronto...
:WAIT_LOOP
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command ^
    "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2 -EA Stop | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 goto WAIT_LOOP

:: -------------------------------------------------------
::  FASE 5 - Apri browser
:: -------------------------------------------------------
echo  Backend pronto!
start http://127.0.0.1:8000/frontend/ideogram-studio.html

echo.
echo  ============================================
echo   Studio in esecuzione su http://127.0.0.1:8000
echo   Chiudi questa finestra per spegnere il server.
echo  ============================================
echo.
pause
