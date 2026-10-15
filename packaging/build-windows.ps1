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

    Copy-Item LICENSE, README.md, packaging\Start-CjChatBot.bat -Destination dist\CjChatBot -Force
    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if (-not $compiler) {
        throw "Inno Setup is required to create the Windows installer. Install it from https://jrsoftware.org/isdl.php and ensure ISCC.exe is on PATH."
    }

    & $compiler.Source packaging\CjChatBot.iss
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed to build the Windows installer."
    }

    Write-Host ""
    Write-Host "Windows installer: $projectRoot\dist\CjChatBot-Setup.exe"
    Write-Host "Share the installer EXE with your client."
}
finally {
    Pop-Location
}
