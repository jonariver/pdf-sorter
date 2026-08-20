@echo off
REM ============================================================
REM  PDF-Sortierer: Setup.exe bauen (mit Inno Setup)
REM  ----------------------------------------------------------
REM  Voraussetzung: Inno Setup 6 ist installiert
REM     (kostenlos: https://jrsoftware.org/isdl.php)
REM  Ausserdem muessen vorher gebaut sein:
REM     dist\PDF-Sortierer.exe   und   dist\PDF-Waechter.exe
REM  (mit Exe_bauen.bat und Waechter_Exe_bauen.bat)
REM  Ollama muss NICHT vorab besorgt werden - die fertige Setup.exe
REM  laedt es bei Bedarf selbst von ollama.com herunter.
REM ============================================================
cd /d "%~dp0"

set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo.
    echo Inno Setup wurde nicht gefunden.
    echo Bitte installieren von:  https://jrsoftware.org/isdl.php
    echo und danach diese Datei erneut ausfuehren.
    echo.
    pause
    exit /b 1
)

if not exist "dist\PDF-Sortierer.exe" (
    echo.
    echo dist\PDF-Sortierer.exe fehlt - bitte zuerst Exe_bauen.bat ausfuehren.
    pause
    exit /b 1
)
if not exist "dist\PDF-Waechter.exe" (
    echo.
    echo dist\PDF-Waechter.exe fehlt - bitte zuerst Waechter_Exe_bauen.bat ausfuehren.
    pause
    exit /b 1
)

echo Baue Setup.exe ...
"%ISCC%" "PDF-Sortierer.iss"
if errorlevel 1 (
    echo.
    echo Beim Bauen ist ein Fehler aufgetreten - siehe Meldungen oben.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  FERTIG!
echo  Die Datei  PDF-Sortierer-Setup.exe  liegt im Ordner  Output\
echo ============================================================
pause
