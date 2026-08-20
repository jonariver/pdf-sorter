@echo off
REM ============================================================
REM  PDF-Sortierer: EXE bauen
REM  Diese Datei muss im SKRIPT-Ordner liegen (neben pdf_ui.py).
REM  Einfach doppelklicken.
REM ============================================================
cd /d "%~dp0"

echo.
echo [1/2] PyInstaller installieren (falls noch nicht vorhanden)...
python -m pip install --upgrade pyinstaller pymupdf
if errorlevel 1 (
    echo.
    echo Fehler bei der Installation von PyInstaller.
    echo Laeuft Python? Pruefe mit:  python --version
    pause
    exit /b 1
)

echo.
echo [2/2] EXE wird gebaut - das dauert ein bis zwei Minuten...
python -m PyInstaller --onefile --windowed --name "PDF-Sortierer" --collect-all pdfplumber --collect-all pymupdf --hidden-import requests pdf_ui.py
if errorlevel 1 (
    echo.
    echo Beim Bauen ist ein Fehler aufgetreten - siehe Meldungen oben.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  FERTIG!
echo  Die Datei  PDF-Sortierer.exe  liegt jetzt im Ordner  dist\
echo.
echo  Zum Verteilen: PDF-Sortierer.exe an ihren Zielort kopieren
echo  (z.B. auf den Desktop). Wenn du bereits eine config.json mit
echo  deinen Kategorien/Absendern hast, kopiere sie dorthin daneben,
echo  damit deine Einstellungen erhalten bleiben.
echo ============================================================
pause
