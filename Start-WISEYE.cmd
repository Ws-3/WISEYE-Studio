@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start-WISEYE.ps1" %*
if errorlevel 1 pause
