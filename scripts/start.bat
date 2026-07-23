@echo off
setlocal

set ROOT_DIR=%~dp0..
set ROOT_DIR=%ROOT_DIR:\=\%

echo Starting Redis...
docker ps -a --format "{{.Names}}" | findstr /x "itspeak-redis" >nul
if %errorlevel%==0 (
  docker start itspeak-redis >nul
) else (
  docker run -d --name itspeak-redis -p 6379:6379 redis:7 >nul
)
if errorlevel 1 echo Warning: docker not found or failed; ensure Redis is reachable at localhost:6379.

echo Starting backend (API, worker, beat)...
start "ItSpeak Backend" /D "%ROOT_DIR%\backend" cmd /k node "%ROOT_DIR%\scripts\run-backend.mjs"

echo Starting frontend...
start "ItSpeak Frontend" /D "%ROOT_DIR%\frontend" cmd /k node "%ROOT_DIR%\frontend\node_modules\next\dist\bin\next" dev

echo.
echo Backend and frontend are starting in their own windows.
echo API:      http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo.
echo Run scripts\stop.bat to stop everything.

endlocal
