@echo off
REM Build single-file Windows EXE for draw_plot.py

setlocal

echo Installing/Updating dependencies...
"C:\Users\NgocToan\AppData\Local\Programs\Python\Python313\python.exe" -m pip install --upgrade pip
"C:\Users\NgocToan\AppData\Local\Programs\Python\Python313\python.exe" -m pip install pyinstaller
if exist requirements.txt (
    "C:\Users\NgocToan\AppData\Local\Programs\Python\Python313\python.exe" -m pip install -r requirements.txt
) else (
    echo requirements.txt not found. Installing default packages...
    "C:\Users\NgocToan\AppData\Local\Programs\Python\Python313\python.exe" -m pip install matplotlib PyQt5 openpyxl pillow
)

echo.
echo Building EXE with PyInstaller...
REM --noconfirm: Do not ask to overwrite existing dist/build folders
REM --onefile: Create a single executable file
REM --windowed: No console window
REM --add-data: Include the png file for the internal icon usage
REM --icon: Set the .exe icon
"C:\Users\NgocToan\AppData\Local\Programs\Python\Python313\python.exe" -m PyInstaller --noconfirm --onefile --windowed --name "CSV Torque Plot Viewer" --icon "assets\icons\data-analysis.ico" --add-data "assets\icons\data-analysis.png;." draw_plot\draw_plot.py

if errorlevel 1 (
    echo.
    echo ****************************
    echo *      BUILD FAILED        *
    echo ****************************
    goto :end
)

echo.
echo ****************************
echo *      BUILD SUCCESS       *
echo ****************************
echo The executable is located in the "dist" folder:
echo dist\"CSV Torque Plot Viewer.exe"

:end
pause
endlocal