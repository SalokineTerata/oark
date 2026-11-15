@echo off
setlocal
set "PYTHONUTF8=1"
set "HF_HUB_OFFLINE=1"
set "OPENBLAS_NUM_THREADS=1"
set "PIP_CACHE_DIR=%~dp0..\pip-cache"
set "AUTO="
for %%A in (%*) do if /i "%%~A"=="--auto" set "AUTO=1"
if not exist "%~dp0temp_audio" mkdir "%~dp0temp_audio"
if not exist "%~dp0temp_audio" (
  echo Impossible de creer le dossier temporaire sur D:.
  set "RESULT=1"
  goto finish
)
set "TEMP=%~dp0temp_audio"
set "TMP=%~dp0temp_audio"
if not exist "%~dp0..\.venv\Scripts\activate.bat" (
  echo Environnement virtuel introuvable : %~dp0..\.venv
  set "RESULT=1"
  goto finish
)
call "%~dp0..\.venv\Scripts\activate.bat"
python "%~dp0..\main_audiobook.py" analyse %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto finish
if "%AUTO%"=="1" goto automatic
echo.
echo Verifiez les fichiers dans "%~dp0orientations" puis corrigez les locuteurs et intentions.
set "APPROVAL="
set /p "APPROVAL=Tapez OUI pour valider et lancer la generation : "
if /i not "%APPROVAL%"=="OUI" (
  echo Generation annulee. Les orientations sont conservees.
  set "RESULT=1"
  goto finish
)
python "%~dp0..\main_audiobook.py" generer --approuve %*
set "RESULT=%ERRORLEVEL%"
goto finish
:automatic
echo Generation automatique sans validation humaine.
python "%~dp0..\main_audiobook.py" generer %*
set "RESULT=%ERRORLEVEL%"
:finish
if "%AUTO%"=="1" exit /b %RESULT%
pause
exit /b %RESULT%
