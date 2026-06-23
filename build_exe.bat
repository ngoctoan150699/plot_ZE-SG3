@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PY=.\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=G:\python\python.exe"
"%PY%" --version >nul 2>&1
if errorlevel 1 set "PY=G:\python\python.exe"
set "APP_NAME=ZE-SG3 Torque Acquisition v1.1.1"
set "ICON=python\app_icon.ico"

echo [1/5] Cleaning build cache...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "*.spec" del /q "*.spec"
for /d /r %%D in (__pycache__) do @if exist "%%D" rmdir /s /q "%%D"

echo [2/5] Checking PyInstaller...
"%PY%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller is missing. Installing into venv...
    "%PY%" -m pip install pyinstaller
    if errorlevel 1 goto :fail
)

echo [3/5] Syntax check...
"%PY%" -m py_compile python\main.py python\ui\main_window.py python\domain\plc_protocol.py python\exporters\csv_ctr_exporter.py python\torque_simulator.py
if errorlevel 1 goto :fail

echo [4/5] Building EXE...
"%PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "%APP_NAME%" ^
  --icon "%ICON%" ^
  --paths "python" ^
  --paths "draw_plot" ^
  --add-data "python\app_icon.ico;." ^
  --add-data "draw_plot;draw_plot" ^
  --add-data "python\settings.json;." ^
  python\main.py
if errorlevel 1 goto :fail

echo [5/5] Cleaning residual build cache...
if exist build rmdir /s /q build
for /d /r %%D in (__pycache__) do @if exist "%%D" rmdir /s /q "%%D"

echo.
echo BUILD SUCCESS
echo Output: dist\%APP_NAME%.exe
goto :end

:fail
echo.
echo BUILD FAILED
exit /b 1

:end
endlocal