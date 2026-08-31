@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
if defined PYTHON_EXE set "PYTHON=%PYTHON_EXE:"=%"
if defined PYTHON if not exist "%PYTHON%" set "PYTHON="
if not defined PYTHON if exist "%ROOT%.venv\pyvenv.cfg" set "PYTHON=%ROOT%.venv\Scripts\python.exe"
if not defined PYTHON if exist "C:\SUPER_NOVA_ENV\.venv\pyvenv.cfg" set "PYTHON=C:\SUPER_NOVA_ENV\.venv\Scripts\python.exe"
if not defined PYTHON set "PYTHON=python"

if /I not "%PYTHON%"=="python" if not exist "%PYTHON%" (
    echo [ERROR] Python executable not found: "%PYTHON%"
    exit /b 1
)
if not exist "%ROOT%SUPER_NOVA.spec" (
    echo [ERROR] SUPER_NOVA.spec not found.
    exit /b 1
)

tasklist /FI "IMAGENAME eq SUPER_NOVA.exe" /NH 2>nul | find /I "SUPER_NOVA.exe" >nul
if not errorlevel 1 (
    echo [ERROR] SUPER_NOVA.exe is still running. Close it before rebuilding.
    exit /b 1
)

powershell.exe -NoProfile -NonInteractive -Command "$busy = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw)\.exe$' -and $_.CommandLine -match 'SUPER_NOVA|tray\.py' }; if ($busy) { $busy | Select-Object Name,ProcessId,CommandLine | Format-Table -AutoSize; exit 1 }"
if errorlevel 1 (
    echo [ERROR] A development Python process is still using the project files.
    echo Close tray.py before rebuilding.
    exit /b 1
)

"%PYTHON%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed for "%PYTHON%".
    echo Install it with: "%PYTHON%" -m pip install pyinstaller
    exit /b 1
)
"%PYTHON%" -c "import flask, pystray, PIL, webview, win32security, win32net" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] A SUPER NOVA dependency is missing for "%PYTHON%".
    echo Install them with: "%PYTHON%" -m pip install flask pywin32 pystray pillow pywebview
    exit /b 1
)

echo Building SUPER NOVA...
pushd "%ROOT%"
"%PYTHON%" -m PyInstaller SUPER_NOVA.spec --noconfirm --clean
set "BUILD_ERROR=%ERRORLEVEL%"
popd
if not "%BUILD_ERROR%"=="0" exit /b %BUILD_ERROR%

if exist "%ROOT%dist\SUPER_NOVA\recovery" (
    echo [ERROR] Recovery files were found in the package.
    echo Remove the recovery folder before creating the installer.
    exit /b 1
)

echo Release ready: "%ROOT%dist\SUPER_NOVA"
exit /b 0
