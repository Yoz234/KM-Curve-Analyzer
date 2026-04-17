@echo off
echo Stopping old processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " 2^>nul') do taskkill /F /T /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " 2^>nul') do taskkill /F /T /PID %%a >nul 2>&1
timeout /t 1 >nul

echo ==========================================
echo   KM Curve Analyzer
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo ==========================================
echo.
echo [1/2] Starting backend...
start "KM Backend" cmd /k "call D:\ProgramData\anaconda3\Scripts\activate.bat && conda activate km-analyzer && cd /d D:\AAAraprojects\bio2final\backend && uvicorn main:app --host 0.0.0.0 --port 8000 || (echo. & echo Backend stopped. & pause)"
timeout /t 2 >nul
echo [2/2] Starting frontend...
start "KM Frontend" cmd /k "cd /d D:\AAAraprojects\bio2final\frontend && npm run dev || (echo. & echo Frontend stopped. & pause)"
echo.
echo Servers starting. Opening browser in 10 seconds...
echo You can close this window.
timeout /t 10 >nul
start http://localhost:3000
