$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Project virtual environment not found. Run run-cjchatbot.bat once, or create .venv and install server\requirements.txt."
}

Push-Location $projectRoot
try {
    & $python -m pip install --disable-pip-version-check -r server\requirements.txt "pyinstaller>=6.18,<7"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install the application and packaging requirements."
    }

    $webDir = Join-Path $projectRoot "web"
    $iconPath = Join-Path $projectRoot "web\assets\favicon.ico"
    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --onedir `
        --name CjChatBot `
        --icon $iconPath `
        --add-data "$webDir;web" `
        --distpath dist `
        --specpath build\pyinstaller `
        --workpath build\pyinstaller `
        packaging\launcher.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed to build CjChatBot."
    }

    Copy-Item LICENSE dist\CjChatBot\LICENSE -Force
    Copy-Item README.md dist\CjChatBot\README.md -Force
    Copy-Item packaging\Start-CjChatBot.bat dist\CjChatBot\Start-CjChatBot.bat -Force
    Compress-Archive -Path dist\CjChatBot -DestinationPath dist\CjChatBot-Windows.zip -Force
    Write-Host ""
    Write-Host "Build complete: $projectRoot\dist\CjChatBot\CjChatBot.exe"
    Write-Host "Client package: $projectRoot\dist\CjChatBot-Windows.zip"
    Write-Host "Share the ZIP with your client; do not send only the EXE."
}
finally {
    Pop-Location
}
