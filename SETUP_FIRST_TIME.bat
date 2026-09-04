@echo off
chcp 65001 >nul
echo ==========================================
echo   Plantopia Final - First Time Setup
echo ==========================================
cd /d "%~dp0backend"
py -3.12 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
cd /d "%~dp0frontend"
call npm.cmd install
if errorlevel 1 goto :error
echo.
echo Setup completed.
echo Run START_PLANTOPIA.bat next time.
pause
exit /b 0
:error
echo.
echo Setup failed. Please copy the error message and send it to ChatGPT.
pause
exit /b 1
