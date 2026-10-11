@echo off
setlocal
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0oshi_windows.py" %*
exit /b %errorlevel%
