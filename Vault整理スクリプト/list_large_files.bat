@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0list_large_files.ps1" -Path "%~dp0..\.."
pause
