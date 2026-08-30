@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
set "RECOVERY=%ROOT%..\SUPER_NOVA_RECOVERY"
if defined PYTHON_EXE set "PYTHON=%PYTHON_EXE:"=%"
if defined PYTHON if not exist "%PYTHON%" set "PYTHON="
if not defined PYTHON if exist "%ROOT%.venv\pyvenv.cfg" set "PYTHON=%ROOT%.venv\Scripts\python.exe"
if not defined PYTHON if exist "C:\SUPER_NOVA_ENV\.venv\pyvenv.cfg" set "PYTHON=C:\SUPER_NOVA_ENV\.venv\Scripts\python.exe"
if not defined PYTHON set "PYTHON=python"

if /I not "%PYTHON%"=="python" if not exist "%PYTHON%" (
    echo [ERROR] Python executable not found: "%PYTHON%"
    exit /b 1
)
if not exist "%RECOVERY%\recovery_manager.spec" (
    echo [ERROR] Recovery spec not found: "%RECOVERY%\recovery_manager.spec"
    exit /b 1
)

for %%P in (SUPER_NOVA.exe recovery_manager.exe) do (
    tasklist /FI "IMAGENAME eq %%P" /NH 2>nul | find /I "%%P" >nul
    if not errorlevel 1 (
        echo [ERROR] %%P is still running. Close it before rebuilding.
        exit /b 1
    )
)

powershell.exe -NoProfile -NonInteractive -Command "$busy = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw)\.exe$' -and $_.CommandLine -match 'SUPER_NOVA|recovery_manager|tray\.py' }; if ($busy) { $busy | Select-Object Name,ProcessId,CommandLine | Format-Table -AutoSize; exit 1 }"
if errorlevel 1 (
    echo [ERROR] A development Python process is still using the project files.
    echo Close tray.py or recovery_manager.py before rebuilding.
    exit /b 1
)

"%PYTHON%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed for "%PYTHON%".
    echo Install it with: "%PYTHON%" -m pip install pyinstaller
    exit /b 1
)
"%PYTHON%" -c "import flask, waitress, pystray, PIL, webview, win32security, win32gui, win32process" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] A SUPER NOVA dependency is missing for "%PYTHON%".
    echo Install them with: "%PYTHON%" -m pip install flask waitress pywin32 pystray pillow pywebview
    exit /b 1
)

echo [1/3] Building SUPER_NOVA_RECOVERY...
pushd "%RECOVERY%"
"%PYTHON%" -m PyInstaller recovery_manager.spec --noconfirm --clean
if errorlevel 1 (
    popd
    exit /b 1
)
popd

echo [2/3] Building SUPER_NOVA...
pushd "%ROOT%"
"%PYTHON%" -m PyInstaller SUPER_NOVA.spec --noconfirm --clean
if errorlevel 1 (
    popd
    exit /b 1
)
popd

echo [3/3] Bundling the Recovery manager...
robocopy "%RECOVERY%\dist\recovery_manager" "%ROOT%dist\SUPER_NOVA\recovery" /E /R:1 /W:1 /NFL /NDL /NJH /NJS
if errorlevel 8 (
    exit /b 1
)

echo.
echo Release ready: "%ROOT%dist\SUPER_NOVA"
exit /b 0
