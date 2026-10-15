@echo off
cd /d "%~dp0"
python scripts\build_exe.py %*
if errorlevel 1 pause
