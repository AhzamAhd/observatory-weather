@echo off
REM ============================================================
REM  GOWC dev launcher — starts the backend API and the web
REM  frontend in two separate windows, then opens the browser.
REM  Just double-click this file.
REM ============================================================

echo Starting GOWC development servers...
echo.

REM %~dp0 is this file's folder (with trailing backslash). pushd handles
REM paths that contain spaces and switches drive if needed.

REM --- Backend API (FastAPI) in its own window ---
REM Activate the project venv first so uvicorn + all Python deps are found
REM (a fresh cmd window does not inherit the venv).
start "GOWC API (backend)" cmd /k "call "%~dp0venv\Scripts\activate.bat" && pushd "%~dp0api" && uvicorn main:app --port 8000"

REM --- Frontend (Next.js) in its own window ---
start "GOWC Web (frontend)" cmd /k "pushd "%~dp0web" && npm run dev"

REM --- Give them a few seconds to boot, then open the browser ---
echo Waiting for servers to start...
timeout /t 8 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo ============================================================
echo  Two windows opened:
echo    - "GOWC API (backend)"  -^> http://localhost:8000
echo    - "GOWC Web (frontend)" -^> http://localhost:3000
echo  Your browser should open to the dashboard automatically.
echo.
echo  To STOP the servers: close both of those windows.
echo ============================================================
echo.
pause
