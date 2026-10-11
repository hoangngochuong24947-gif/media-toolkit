@echo off
setlocal
if "%~1"=="" (
  echo Usage: install-skill.cmd "SKILL_DIRECTORY" "BACKUP_DIRECTORY"
  exit /b 2
)
if "%~2"=="" (
  echo A backup directory is required.
  exit /b 2
)
set "taskRuntime=%~dp0runtime\python\python.exe"
if exist "%~dp0runtime-path.cmd" call "%~dp0runtime-path.cmd"
if not exist "%taskRuntime%" set "taskRuntime=python"
"%taskRuntime%" -I "%~dp0scripts\setup.py" --install-to "%~1" --backup-dir "%~2"
exit /b %errorlevel%
