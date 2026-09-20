@echo off
cd /d "%~dp0"
py -3 patch_stq.py %*
if errorlevel 1 pause
