@echo off
setlocal
cd /d "%~dp0"
REM Usage:  run.bat          development mode (API on :8000, UI on :5173 with hot reload)
REM         run.bat prod     production-style mode (builds the UI, everything served on :8000)
REM         run.bat seed     start and also load the synthetic demonstration data

if not exist .venv\Scripts\python.exe call setup.bat
if errorlevel 1 exit /b 1
if not exist frontend\node_modules call setup.bat
if errorlevel 1 exit /b 1

if /i "%1"=="seed" ".venv\Scripts\python.exe" scripts\seed_demo.py

if /i "%1"=="prod" (
  pushd frontend
  call npm run build
  if errorlevel 1 ( popd & echo [ERROR] Frontend build failed. & exit /b 1 )
  popd
  set SERVE_FRONTEND=true
  echo Starting FraudShield AI on http://127.0.0.1:8000
  start "" http://127.0.0.1:8000
  ".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
  exit /b 0
)

echo Starting API on http://127.0.0.1:8000  (API docs: http://127.0.0.1:8000/docs)
start "FraudShield AI - API" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --reload-dir backend"
echo Starting UI on http://localhost:5173
start "FraudShield AI - UI" cmd /k "cd /d frontend && npm run dev"
timeout /t 6 /nobreak >nul
start "" http://localhost:5173
echo Both servers run in their own windows. Close those windows to stop FraudShield AI.
exit /b 0
