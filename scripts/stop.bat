@echo off
setlocal

echo Stopping backend...
taskkill /FI "WINDOWTITLE eq ItSpeak Backend*" /T /F >nul 2>&1

echo Stopping frontend...
taskkill /FI "WINDOWTITLE eq ItSpeak Frontend*" /T /F >nul 2>&1

docker ps --format "{{.Names}}" | findstr /x "itspeak-redis" >nul
if %errorlevel%==0 (
  echo Stopping Redis container...
  docker stop itspeak-redis >nul
)

echo Done.
endlocal
