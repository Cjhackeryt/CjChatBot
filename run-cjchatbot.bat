@echo off
setlocal
cd /d "%~dp0"

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    where py >nul 2>nul
    if not errorlevel 1 (
        echo Creating a local Python environment...
        py -3 -m venv "%~dp0.venv"
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (
            echo Python 3.12 or newer is required. Install Python, then run this file again.
            pause
            exit /b 1
        )
        echo Creating a local Python environment...
        python -m venv "%~dp0.venv"
    )

    if errorlevel 1 (
        echo Could not create the Python environment.
        pause
        exit /b 1
    )
)

"%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 (
    echo Python 3.12 or newer is required.
    echo Install a newer Python version and remove the old .venv folder before retrying.
    pause
    exit /b 1
)

echo Installing or checking CjChatBot requirements...
"%VENV_PYTHON%" -m pip install --disable-pip-version-check -r server\requirements.txt
if errorlevel 1 (
    echo Could not install requirements. Check your internet connection and try again.
    pause
    exit /b 1
)

start "" /min powershell.exe -NoProfile -WindowStyle Hidden -Command "$deadline = (Get-Date).AddSeconds(90); while ((Get-Date) -lt $deadline) { try { $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2; if ($response.StatusCode -eq 200) { Start-Process 'http://127.0.0.1:8000'; exit 0 } } catch { }; Start-Sleep -Seconds 1 }; exit 1"

echo Starting CjChatBot at http://127.0.0.1:8000
echo Leave this window open while you use CjChatBot. Press Ctrl+C to stop.
"%VENV_PYTHON%" -m uvicorn server.main:app --host 127.0.0.1 --port 8000

if errorlevel 1 (
    echo CjChatBot stopped with an error. Check the messages above.
    pause
)
