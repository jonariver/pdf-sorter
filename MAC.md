# PDF-Sortierer auf dem Mac

Der PDF-Sortierer läuft auch auf macOS. Der Programmkern ist plattform­unabhängig
(Python, tkinter, Ollama, PyMuPDF); nur die Verpackung als Programm und der
Autostart sind unter Windows und Mac unterschiedlich gelöst. Diese Anleitung
zeigt den einfachsten Weg – **aus dem Quellcode starten** – und enthält fertige
Scripts, die du nur noch ausführen musst.

> Die allgemeine Bedienung (Analysieren, Anwenden, Wächter, Einstellungen, OCR)
> steht in [ANLEITUNG.md](ANLEITUNG.md). Hier geht es nur um die Mac-Einrichtung.

---

## Inhalt

1. [Voraussetzungen](#1-voraussetzungen)
2. [Projekt auf den Mac holen](#2-projekt-auf-den-mac-holen)
3. [Schnellstart in 4 Schritten](#3-schnellstart-in-4-schritten)
4. [Die Scripts im Überblick](#4-die-scripts-im-überblick)
5. [Wächter automatisch starten (Autostart)](#5-wächter-automatisch-starten-autostart)
6. [Optional: eigenständige .app bauen](#6-optional-eigenständige-app-bauen)
7. [Unterschiede zu Windows](#7-unterschiede-zu-windows)
8. [Problembehebung](#8-problembehebung)
9. [Anhang: die Scripts zum Selbst-Anlegen](#9-anhang-die-scripts-zum-selbst-anlegen)

---

## 1. Voraussetzungen

- **macOS** – Apple Silicon (M1/M2/M3/M4) läuft besonders schnell, Intel geht auch.
- **Ollama für macOS** – die lokale KI. Von [ollama.com](https://ollama.com)
  herunterladen und installieren.
- **Python 3.10+ mit tkinter** – tkinter ist die grafische Oberfläche.
  - Beim Installer von [python.org](https://www.python.org/downloads/) ist tkinter
    **enthalten** (empfohlen, am wenigsten Ärger).
  - Bei Homebrew-Python zusätzlich einmalig: `brew install python-tk`

Die Python-Pakete (pdfplumber, requests, pymupdf) installieren die Scripts
selbst in eine lokale Umgebung – da musst du nichts von Hand machen.

---

## 2. Projekt auf den Mac holen

Entweder per Git klonen …

```bash
git clone https://github.com/jonariver/pdf-sorter.git
cd pdf-sorter
```

… oder auf GitHub über **Code → Download ZIP** herunterladen und entpacken.
(Solange das Repo privat ist, musst du dabei angemeldet sein.)

---

## 3. Schnellstart in 4 Schritten

Alles im Terminal im Projektordner (`pdf-sorter`).

**Schritt 1 – Scripts ausführbar machen** (einmalig):
```bash
chmod +x *.command
```

**Schritt 2 – Ollama-Modell laden** (einmalig, mehrere GB):
```bash
ollama pull qwen3:4b
```
Für die Texterkennung bei reinen Bild-Scans zusätzlich (optional):
```bash
ollama pull llama3.2-vision
```

**Schritt 3 – Einrichten** (einmalig): Doppelklick auf **`Mac_einrichten.command`**
im Finder – oder im Terminal:
```bash
./Mac_einrichten.command
```
Das legt eine lokale Python-Umgebung `.venv` an und installiert die Pakete.

**Schritt 4 – Starten:** Doppelklick auf **`Mac_starten.command`** – oder:
```bash
./Mac_starten.command
```

Das war's. Beim ersten Start fragt das Programm, ob es Ollama starten soll → **Ja**.

> **Tipp:** Schritt 3 ist optional – `Mac_starten.command` richtet die Umgebung
> beim allerersten Start notfalls selbst ein. Wer lieber erst einrichtet und dann
> startet, nimmt den expliziten Schritt 3.

---

## 4. Die Scripts im Überblick

| Script | Was es tut |
|--------|------------|
| `Mac_einrichten.command` | Legt `.venv` an und installiert die Pakete (einmalig). |
| `Mac_starten.command` | Startet die Sortierer-Oberfläche (richtet notfalls selbst ein). |
| `Mac_waechter_starten.command` | Startet den automatischen Ordner-Wächter. |
| `Mac_autostart_einrichten.command` | Lässt den Wächter bei jeder Anmeldung starten. |
| `Mac_autostart_entfernen.command` | Entfernt diesen Autostart wieder. |
| `Mac_app_bauen.command` | Baut eigenständige `.app`-Dateien (optional). |

Ausführen entweder per **Doppelklick im Finder** oder im Terminal mit
`./Scriptname.command`.

---

## 5. Wächter automatisch starten (Autostart)

Das Autostart-Häkchen **in** der Wächter-Oberfläche ist Windows-spezifisch (es
nutzt die Windows-Registry) und tut auf dem Mac nichts. Für echten Autostart gibt
es unter macOS **LaunchAgents** – das übernimmt ein Script:

- Einrichten: **`Mac_autostart_einrichten.command`** ausführen.
  Danach startet der Wächter bei jeder Anmeldung automatisch.
- Entfernen: **`Mac_autostart_entfernen.command`** ausführen.

Technisch legt das Script die Datei
`~/Library/LaunchAgents/com.pdfsortierer.waechter.plist` an und lädt sie mit
`launchctl`. Verschiebst du den Projektordner später, richte den Autostart einmal
neu ein (die Pfade sind fest eingetragen).

---

## 6. Optional: eigenständige .app bauen

Wenn du das Programm ohne Terminal per Doppelklick starten (oder weitergeben)
willst, baust du mit **`Mac_app_bauen.command`** zwei Apps:
`dist/PDF-Sortierer.app` und `dist/PDF-Waechter.app`.

Hinweise:
- Der Bau muss **auf einem Mac** passieren – eine Windows-`.exe` lässt sich nicht
  umwandeln.
- Ollama wird **nicht** eingebettet und muss auf dem Zielrechner vorhanden sein.
- Unsignierte Apps blockt **Gatekeeper** beim ersten Start. Dann Rechtsklick auf
  die App → **Öffnen** → im Dialog nochmal **Öffnen**. Danach startet sie normal.
- Für den Alltag reicht der Start aus dem Quellcode (Abschnitt 3) völlig – die
  `.app` ist nur Komfort.

---

## 7. Unterschiede zu Windows

- **Kein Installer/keine .exe:** Die `.bat`-Dateien und `PDF-Sortierer.iss`
  (Inno Setup) sind Windows-only. Auf dem Mac läuft es aus dem Quellcode oder als
  selbstgebaute `.app`.
- **Autostart** über LaunchAgent statt Registry (siehe Abschnitt 5).
- **Speicherorte:** `config.json`, `plan.json`/`plan.csv`, `verschiebungen.csv`
  liegen genau wie unter Windows neben den Programmdateien bzw. im jeweiligen
  Scan-Ordner.
- Ollama automatisch starten und „Datei/Ordner öffnen" (z. B. „Als CSV öffnen")
  funktionieren auf dem Mac bereits ohne Anpassung.
- Optisch sieht tkinter unter macOS etwas anders aus – funktional identisch.

---

## 8. Problembehebung

**`python3: command not found`** – Python ist nicht installiert. Über python.org
oder `brew install python` nachinstallieren.

**Fehler „No module named `_tkinter`" / Fenster geht nicht auf** – tkinter fehlt.
Bei Homebrew-Python: `brew install python-tk`. Oder Python vom python.org-Installer
verwenden (enthält tkinter) und die Umgebung neu anlegen: den Ordner `.venv`
löschen und `Mac_einrichten.command` erneut ausführen.

**„… kann nicht geöffnet werden, da es von einem nicht verifizierten Entwickler
stammt"** (bei `.command` oder `.app`) – Rechtsklick auf die Datei → **Öffnen** →
im Dialog **Öffnen** bestätigen. Beim `.command` reicht alternativ der Start im
Terminal mit `./Scriptname.command`.

**`pip`-Fehler „externally-managed-environment"** – tritt nur auf, wenn man am
System-Python vorbei installiert. Passiert hier nicht, weil alles in `.venv`
läuft. Falls doch: sicherstellen, dass die Umgebung aktiv ist (die Scripts machen
das automatisch).

**Ollama nicht erreichbar** – prüfen, ob Ollama läuft (Menüleisten-Symbol) bzw.
im Terminal `ollama serve` starten. Das Programm bietet den Start beim Öffnen auch
selbst an.

**Sehr langsam** – ohne dedizierte GPU rechnet Ollama auf dem Prozessor. Auf
Apple Silicon ist das dank der eingebauten Beschleunigung meist flott; auf
älteren Intel-Macs hilft das kleinere Modell `qwen3:4b`.

---

## 9. Anhang: die Scripts zum Selbst-Anlegen

Falls du das Projekt nicht klonst, sondern die Scripts von Hand anlegen willst:
Textdatei mit dem jeweiligen Namen erstellen, Inhalt hineinkopieren, dann einmal
`chmod +x *.command` ausführen.

### `Mac_einrichten.command`
```bash
#!/bin/bash
cd "$(dirname "$0")" || exit 1
echo "==> Pruefe Python 3 ..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "FEHLER: 'python3' nicht gefunden. Installiere Python 3 (python.org oder 'brew install python')."
  read -n1 -s -r -p "Taste ..."; echo; exit 1
fi
python3 --version
echo "==> Pruefe tkinter ..."
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
  echo "FEHLER: tkinter fehlt. Homebrew: 'brew install python-tk', sonst python.org-Installer nutzen."
  read -n1 -s -r -p "Taste ..."; echo; exit 1
fi
echo "==> Erstelle .venv ..."
[ -d ".venv" ] || python3 -m venv .venv || { echo "FEHLER: venv"; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
source .venv/bin/activate
echo "==> Installiere Pakete ..."
python -m pip install --upgrade pip >/dev/null
python -m pip install pdfplumber requests pymupdf || { echo "FEHLER: Pakete"; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
echo ""
echo "Fertig. Noch: Ollama installieren (ollama.com) und 'ollama pull qwen3:4b'."
echo "Danach 'Mac_starten.command' ausfuehren."
read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo
```

### `Mac_starten.command`
```bash
#!/bin/bash
cd "$(dirname "$0")" || exit 1
if [ ! -d ".venv" ]; then
  python3 -c "import tkinter" >/dev/null 2>&1 || { echo "tkinter fehlt (brew install python-tk)"; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
  python3 -m venv .venv || { echo "FEHLER: venv"; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
  source .venv/bin/activate
  python -m pip install --upgrade pip >/dev/null
  python -m pip install pdfplumber requests pymupdf || { echo "FEHLER: Pakete"; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
else
  source .venv/bin/activate
fi
python pdf_ui.py
```

### `Mac_waechter_starten.command`
```bash
#!/bin/bash
cd "$(dirname "$0")" || exit 1
if [ ! -d ".venv" ]; then
  python3 -c "import tkinter" >/dev/null 2>&1 || { echo "tkinter fehlt (brew install python-tk)"; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
  python3 -m venv .venv || { echo "FEHLER: venv"; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
  source .venv/bin/activate
  python -m pip install --upgrade pip >/dev/null
  python -m pip install pdfplumber requests pymupdf || { echo "FEHLER: Pakete"; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
else
  source .venv/bin/activate
fi
python pdf_watcher_ui.py
```

### `Mac_autostart_einrichten.command`
```bash
#!/bin/bash
cd "$(dirname "$0")" || exit 1
REPO="$(pwd)"; PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || { echo "Bitte zuerst 'Mac_einrichten.command' ausfuehren."; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
AGENTS="$HOME/Library/LaunchAgents"; PLIST="$AGENTS/com.pdfsortierer.waechter.plist"
mkdir -p "$AGENTS"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.pdfsortierer.waechter</string>
  <key>ProgramArguments</key>
  <array><string>$PY</string><string>$REPO/pdf_watcher_ui.py</string></array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
</dict>
</plist>
PLISTEOF
launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" && echo "Autostart eingerichtet." || echo "FEHLER beim Laden."
read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo
```

### `Mac_autostart_entfernen.command`
```bash
#!/bin/bash
PLIST="$HOME/Library/LaunchAgents/com.pdfsortierer.waechter.plist"
[ -f "$PLIST" ] || { echo "Kein Autostart eingerichtet."; read -n1 -s -r -p "Taste ..."; echo; exit 0; }
launchctl unload "$PLIST" 2>/dev/null
rm -f "$PLIST"
echo "Autostart entfernt."
read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo
```

### `Mac_app_bauen.command`
```bash
#!/bin/bash
cd "$(dirname "$0")" || exit 1
[ -d ".venv" ] || { echo "Bitte zuerst 'Mac_einrichten.command' ausfuehren."; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
source .venv/bin/activate
python -m pip install --upgrade pyinstaller >/dev/null || { echo "FEHLER: PyInstaller"; read -n1 -s -r -p "Taste ..."; echo; exit 1; }
pyinstaller --noconfirm --windowed --name "PDF-Sortierer" --collect-all pymupdf --collect-all pdfplumber pdf_ui.py
pyinstaller --noconfirm --windowed --name "PDF-Waechter"  --collect-all pymupdf --collect-all pdfplumber pdf_watcher_ui.py
echo "Fertig: dist/PDF-Sortierer.app und dist/PDF-Waechter.app"
echo "Gatekeeper: Rechtsklick auf die App -> Oeffnen -> Oeffnen."
read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo
```
