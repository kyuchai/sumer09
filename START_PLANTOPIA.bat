@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Virtual environment not found. Please run SETUP_FIRST_TIME.bat first.
  pause
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo Frontend packages not found. Please run SETUP_FIRST_TIME.bat first.
  pause
  exit /b 1
)
start "Plantopia Backend" cmd /k "cd /d ""%~dp0backend"" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload"
start "Plantopia Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm.cmd run dev"
echo Plantopia started.
echo Frontend: http://localhost:5173
echo API docs: http://127.0.0.1:8000/docs
pause
