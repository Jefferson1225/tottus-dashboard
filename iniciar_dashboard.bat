@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Primero sigue los pasos de instalacion del README.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless false
pause
