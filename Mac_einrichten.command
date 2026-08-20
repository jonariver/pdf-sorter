#!/bin/bash
# ---------------------------------------------------------------------------
# PDF-Sortierer - Einrichtung auf dem Mac (einmalig ausfuehren)
# Legt eine lokale Python-Umgebung (.venv) an und installiert die noetigen
# Pakete. Aendert nichts an deinem System ausserhalb dieses Ordners.
# ---------------------------------------------------------------------------
cd "$(dirname "$0")" || exit 1

echo "==> Pruefe Python 3 ..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "FEHLER: 'python3' wurde nicht gefunden."
  echo "Bitte Python 3 installieren: https://www.python.org/downloads/"
  echo "oder mit Homebrew:  brew install python"
  read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo; exit 1
fi
python3 --version

echo "==> Pruefe tkinter (fuer die grafische Oberflaeche) ..."
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
  echo "FEHLER: In dieser Python-Installation fehlt tkinter."
  echo "  - Homebrew-Python: 'brew install python-tk' ausfuehren, dann dieses"
  echo "    Script erneut starten."
  echo "  - Alternativ Python vom python.org-Installer verwenden (enthaelt tkinter)."
  read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo; exit 1
fi

echo "==> Erstelle virtuelle Umgebung (.venv) ..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv || { echo "FEHLER beim Anlegen der Umgebung."; \
    read -n1 -s -r -p "Taste ..."; echo; exit 1; }
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installiere Pakete (pdfplumber, requests, pymupdf) ..."
python -m pip install --upgrade pip >/dev/null
if ! python -m pip install pdfplumber requests pymupdf; then
  echo "FEHLER bei der Paketinstallation."
  read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo; exit 1
fi

echo ""
echo "============================================================"
echo " Einrichtung abgeschlossen."
echo ""
echo " Noch noetig (einmalig):"
echo "   1) Ollama installieren:  https://ollama.com"
echo "   2) Ein Modell laden, im Terminal z. B.:  ollama pull qwen3:4b"
echo ""
echo " Starten dann per Doppelklick auf:  Mac_starten.command"
echo "============================================================"
read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo
