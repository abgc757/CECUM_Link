@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%first_deploy_clean.ps1"

if not exist "%PS_SCRIPT%" (
  echo No se encontro el script PowerShell: "%PS_SCRIPT%"
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo El despliegue limpio fallo con codigo %EXIT_CODE%.
  exit /b %EXIT_CODE%
)

echo.
echo Proceso finalizado correctamente.
exit /b 0
