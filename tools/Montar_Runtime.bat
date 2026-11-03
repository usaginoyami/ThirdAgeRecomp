@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo Requer: Python, CMake, Git, e um compilador C++20 (Visual Studio Build Tools ou MinGW). Ninja ajuda muito.
echo O ELF deve estar em dados\SLUS_210.27
python tools\montar_runtime.py --gerar 2> tools\montar_runtime.log
echo.
echo Fim. Se deu erro, me mande o arquivo tools\montar_runtime.log (as ultimas linhas).
pause
