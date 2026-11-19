@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Python environment is missing. Run Install.cmd first.
  exit /b 2
)
"%~dp0.venv\Scripts\python.exe" -B "%~dp0cli.py" doctor
exit /b %errorlevel%
