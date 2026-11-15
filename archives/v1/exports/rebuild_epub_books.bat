@echo off
setlocal
set "PYTHONUTF8=1"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 est requis pour reconstruire les livres.
  exit /b 1
)
python "%~dp0..\scripts\build_books.py" --format epub %*
exit /b %errorlevel%
