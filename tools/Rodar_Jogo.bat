@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
set EXE=build\runtime\ps2xRuntime\ps2EntryRunner.exe
if not exist "%EXE%" (
  echo Nao achei %EXE% - rode antes o Montar_Runtime.bat
  pause
  exit /b 1
)
rem O runtime usa a pasta do ELF como raiz do CD: ela precisa ter MODULES\ e os outros arquivos do disco.
if not exist "extract\MODULES" (
  echo Nao achei extract\MODULES - rode o Extrair_ISO.bat antes.
  pause
  exit /b 1
)
if not exist "extract\SLUS_210.27" copy /y "dados\SLUS_210.27" "extract\SLUS_210.27" >nul
echo Rodando. Deixe uns 30-60 segundos e feche a janela do jogo. Log em tools\boot.log
"%EXE%" "extract\SLUS_210.27" > tools\boot.log 2>&1
echo.
echo Terminou (codigo %errorlevel%). Me mande as primeiras e as ultimas ~60 linhas de tools\boot.log
echo (no PowerShell:  Get-Content tools\boot.log -TotalCount 60  e  Get-Content tools\boot.log -Tail 60)
pause
