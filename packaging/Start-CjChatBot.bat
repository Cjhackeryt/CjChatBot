@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0CjChatBot.exe" (
    echo CjChatBot.exe is missing. Extract the complete CjChatBot folder from the ZIP first.
    pause
    exit /b 1
)
"%~dp0CjChatBot.exe"
if errorlevel 1 (
    echo CjChatBot exited with an error. See %%LOCALAPPDATA%%\CjChatBot\startup-error.log if present.
    pause
)
