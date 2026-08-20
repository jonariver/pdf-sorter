#!/bin/bash
# ---------------------------------------------------------------------------
# PDF-Sortierer - eigenstaendige Mac-App (.app) bauen  [optional/fortgeschritten]
# Erzeugt mit PyInstaller PDF-Sortierer.app und PDF-Waechter.app im Ordner dist/.
# Ollama wird dabei NICHT eingebettet und muss auf dem Zielrechner vorhanden sein.
# ---------------------------------------------------------------------------
cd "$(dirname "$0")" || exit 1

if [ ! -d ".venv" ]; then
  echo "FEHLER: Umgebung fehlt. Bitte zuerst 'Mac_einrichten.command' ausfuehren."
  read -n1 -s -r -p "Taste ..."; echo; exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installiere PyInstaller ..."
python -m pip install --upgrade pyinstaller >/dev/null || { \
  echo "FEHLER: PyInstaller-Installation."; read -n1 -s -r -p "Taste ..."; echo; exit 1; }

echo "==> Baue PDF-Sortierer.app ..."
pyinstaller --noconfirm --windowed --name "PDF-Sortierer" \
  --collect-all pymupdf --collect-all pdfplumber \
  pdf_ui.py

echo "==> Baue PDF-Waechter.app ..."
pyinstaller --noconfirm --windowed --name "PDF-Waechter" \
  --collect-all pymupdf --collect-all pdfplumber \
  pdf_watcher_ui.py

echo ""
echo "Fertig. Die Apps liegen unter:"
echo "   dist/PDF-Sortierer.app"
echo "   dist/PDF-Waechter.app"
echo ""
echo "Hinweis: Unsignierte Apps blockt Gatekeeper beim ersten Start."
echo "Dann Rechtsklick auf die App -> 'Oeffnen' -> 'Oeffnen' bestaetigen."
read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo
