@echo off
REM ============================================================
REM  PDF-Waechter: EXE bauen
REM  Diese Datei muss im SKRIPT-Ordner liegen (neben pdf_watcher_ui.py).
REM  Einfach doppelklicken.
REM ============================================================
cd /d "%~dp0"

echo.
echo [1/2] PyInstaller installieren (falls noch nicht vorhanden)...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo.
    echo Fehler bei der Installation von PyInstaller.
    pause
    exit /b 1
)

echo.
echo [2/2] Waechter-EXE wird gebaut - das dauert ein bis zwei Minuten...
python -m PyInstaller --onefile --windowed --name "PDF-Waechter" --collect-all pdfplumber --hidden-import requests pdf_watcher_ui.py
if errorlevel 1 (
    echo.
    echo Beim Bauen ist ein Fehler aufgetreten - siehe Meldungen oben.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  FERTIG!
echo  Die Datei  PDF-Waechter.exe  liegt jetzt im Ordner  dist\
echo  Lege sie dorthin, wo auch deine config.json liegen soll,
echo  und starte sie per Doppelklick.
echo ============================================================
pause
