@echo off
set ROOT_DIR=%~dp0

if not exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
  echo .venv が見つかりません。先に python -m venv .venv を実行してください。
  exit /b 1
)

"%ROOT_DIR%\.venv\Scripts\python.exe" "%ROOT_DIR%\main.py" %*
