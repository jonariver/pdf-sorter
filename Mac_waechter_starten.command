#!/bin/bash
# ---------------------------------------------------------------------------
# PDF-Sortierer - Waechter starten (Mac)
# Startet den automatischen Ordner-Waechter mit Fenster. Richtet beim ersten
# Start bei Bedarf die Umgebung ein.
# ---------------------------------------------------------------------------
cd "$(dirname "$0")" || exit 1

if [ ! -d ".venv" ]; then
  echo "==> Erste Einrichtung ..."
  if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "FEHLER: tkinter fehlt (siehe MAC.md: 'brew install python-tk')."
    read -n1 -s -r -p "Taste ..."; echo; exit 1
  fi
  python3 -m venv .venv || { echo "FEHLER: venv."; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip >/dev/null
  python -m pip install pdfplumber requests pymupdf || { \
    echo "FEHLER: Paketinstallation."; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "==> Starte PDF-Waechter ..."
python pdf_watcher_ui.py
