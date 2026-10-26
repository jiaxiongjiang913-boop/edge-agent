@echo off
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Run Install.cmd first.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -B "%~dp0cli.py" stop
pause
