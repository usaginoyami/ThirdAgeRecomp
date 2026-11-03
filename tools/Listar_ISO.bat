@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "The Third Age.iso" (
  python listar_iso.py "The Third Age.iso"
) else (
  echo Coloque este arquivo e o listar_iso.py na mesma pasta do "The Third Age.iso".
)
pause
