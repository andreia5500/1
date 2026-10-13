@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto fallback
py -3 app.py
goto done
:fallback
python app.py
:done
if errorlevel 1 pause
