@echo off
cd /d "%~dp0\.."
where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.11+ from python.org.
  pause
  exit /b 1
)
py -m pip install -r local_studio\requirements.txt
if errorlevel 1 (pause & exit /b 1)
py -m streamlit run local_studio\app.py
pause
