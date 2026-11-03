@echo off
setlocal
cd /d "%~dp0"
python -B -m src %*
exit /b %errorlevel%
