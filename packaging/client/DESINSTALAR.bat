@echo off
setlocal
cd /d "%~dp0"
echo.
echo  ============================================
echo   NFS ONLINE - DESINSTALADOR
echo  ============================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
if errorlevel 1 (
  echo.
  echo Hubo un error. Lee el mensaje de arriba.
  pause
)
endlocal
