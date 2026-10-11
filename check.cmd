@echo off
setlocal
set "taskRuntime=%~dp0runtime\python\python.exe"
if exist "%~dp0runtime-path.cmd" call "%~dp0runtime-path.cmd"
if not exist "%taskRuntime%" set "taskRuntime=python"
"%taskRuntime%" -I "%~dp0scripts\setup.py" --check
exit /b %errorlevel%
