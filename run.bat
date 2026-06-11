@echo off
echo %USERNAME% > user.txt
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    powershell -Command "Start-Process -FilePath \"wscript.exe\" -ArgumentList \"%~dp0Lunch.vbs\" -Verb RunAs" 
    exit /b
)
cd /d %~dp0
pythonw tray.py
exit /b