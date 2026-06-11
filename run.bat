@echo off
echo %USERNAME% > user.txt
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %~dp0 && pythonw tray.py' -Verb RunAs"
    exit /b
)
cd /d %~dp0
pythonw tray.py