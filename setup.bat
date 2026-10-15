@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo  FraudShield AI - setup
echo ============================================================

set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" where python >nul 2>nul && set PY=python
if "%PY%"=="" (
  echo [ERROR] Python 3.10+ was not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  exit /b 1
)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo [ERROR] Python 3.10 or newer is required.
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js 18+ was not found. Install the LTS version from https://nodejs.org/ and re-run setup.bat.
  exit /b 1
)

if not exist .venv (
  echo Creating Python virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 ( echo [ERROR] Could not create the virtual environment. & exit /b 1 )
)
echo Installing backend dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 ( echo [ERROR] Backend dependency installation failed. & exit /b 1 )

if not exist .env copy .env.example .env >nul

echo Installing frontend dependencies (this can take a few minutes)...
pushd frontend
call npm install --no-audit --no-fund
if errorlevel 1 ( popd & echo [ERROR] npm install failed. & exit /b 1 )
popd

echo Initialising the database...
".venv\Scripts\python.exe" scripts\init_db.py
if errorlevel 1 ( echo [ERROR] Database initialisation failed. & exit /b 1 )

echo.
echo Setup complete. Start the application with:  run.bat
exit /b 0
