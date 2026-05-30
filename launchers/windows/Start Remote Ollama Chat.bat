@echo off
setlocal
cd /d "%~dp0..\.."
where python >nul 2>nul
if %errorlevel%==0 (
  python scripts\remote_ollama_chat.py start
) else (
  py -3 scripts\remote_ollama_chat.py start
)
if errorlevel 1 (
  echo.
  echo Start failed. Press any key to close.
  pause >nul
)
