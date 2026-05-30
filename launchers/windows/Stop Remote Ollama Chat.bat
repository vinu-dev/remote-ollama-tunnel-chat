@echo off
setlocal
cd /d "%~dp0..\.."
where python >nul 2>nul
if %errorlevel%==0 (
  python scripts\remote_ollama_chat.py stop
) else (
  py -3 scripts\remote_ollama_chat.py stop
)
echo.
echo Done. Press any key to close.
pause >nul
