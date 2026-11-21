@echo off
setlocal
cd /d "%~dp0"
echo.
echo  ============================================
echo   NFS ONLINE - INSTALADOR DE CLIENTE
echo  ============================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo Hubo un error. Lee el mensaje de arriba.
  pause
)
endlocal
