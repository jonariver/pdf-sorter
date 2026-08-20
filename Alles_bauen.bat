@echo off
REM ============================================================
REM  PDF-Sortierer: ALLES bauen (ein Klick)
REM  ----------------------------------------------------------
REM  Baut nacheinander:
REM     1) PDF-Sortierer.exe   (aus pdf_ui.py)
REM     2) PDF-Waechter.exe    (aus pdf_watcher_ui.py)
REM     3) Setup.exe           (aus PDF-Sortierer.iss)
REM
REM  Voraussetzungen:
REM     - Python ist installiert  (pruefe: python --version)
REM     - Inno Setup 6 ist installiert (fuer Schritt 3)
REM       kostenlos: https://jrsoftware.org/isdl.php
REM  Ollama muss NICHT vorab besorgt werden - die fertige Setup.exe
REM  laedt es bei Bedarf selbst von ollama.com herunter.
REM
REM  Diese Datei muss im SKRIPT-Ordner liegen (neben pdf_ui.py).
REM  Einfach doppelklicken.
REM ============================================================
cd /d "%~dp0"

echo.
echo [1/4] PyInstaller bereitstellen...
python -m pip install --upgrade pyinstaller pymupdf
if errorlevel 1 (
    echo.
    echo Fehler: PyInstaller liess sich nicht installieren.
    echo Laeuft Python? Pruefe mit:  python --version
    pause
    exit /b 1
)

echo.
echo [2/4] PDF-Sortierer.exe wird gebaut (ein bis zwei Minuten)...
python -m PyInstaller --onefile --windowed --name "PDF-Sortierer" --collect-all pdfplumber --collect-all pymupdf --hidden-import requests pdf_ui.py
if errorlevel 1 (
    echo.
    echo Fehler beim Bauen der Oberflaeche - siehe Meldungen oben.
    pause
    exit /b 1
)

echo.
echo [3/4] PDF-Waechter.exe wird gebaut (ein bis zwei Minuten)...
python -m PyInstaller --onefile --windowed --name "PDF-Waechter" --collect-all pdfplumber --collect-all pymupdf --hidden-import requests pdf_watcher_ui.py
if errorlevel 1 (
    echo.
    echo Fehler beim Bauen des Waechters - siehe Meldungen oben.
    pause
    exit /b 1
)

echo.
echo [4/4] Setup.exe wird gebaut...
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo.
    echo Die beiden Programme liegen jetzt im Ordner  dist\  - fertig.
    echo.
    echo NUR die Setup.exe fehlt noch: dafuer wird Inno Setup benoetigt.
    echo Bitte installieren von  https://jrsoftware.org/isdl.php
    echo und danach diese Datei erneut ausfuehren.
    pause
    exit /b 0
)

"%ISCC%" "PDF-Sortierer.iss"
if errorlevel 1 (
    echo.
    echo Fehler beim Bauen der Setup.exe - siehe Meldungen oben.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  FERTIG!
echo  - Einzelprogramme:  dist\PDF-Sortierer.exe , dist\PDF-Waechter.exe
echo  - Installer:        Output\PDF-Sortierer-Setup.exe
echo ============================================================
pause
