# PDF-Sortierer

Ein Werkzeug für Windows, das gescannte PDF-Dokumente mit Hilfe eines **lokalen
Sprachmodells** automatisch einordnet: Es liest den Text, bestimmt eine
Kategorie, schlägt einen sinnvollen Dateinamen vor und verschiebt die Datei in
den passenden Unterordner.

Gedacht für den typischen Fall: Ein Dokumentenscanner (z. B. ScanSnap) wirft
kryptisch benannte PDFs aus, und das Sortieren von Hand ist zu mühsam.

**Alles läuft lokal auf dem eigenen Rechner** – die Dokumente verlassen den
Computer nicht. Für die KI wird [Ollama](https://ollama.com) verwendet.

## Was es kann

- **Analysieren & Vorschlagen:** liest jeden Scan, bestimmt Kategorie, Absender,
  Betreff und Datum und schlägt einen ordentlichen Dateinamen vor
  (`Datum_Kategorie_Absender_Betreff`).
- **Sicherheit zuerst:** zeigt erst eine Übersicht, bevor irgendetwas verschoben
  wird. Unsichere Zuordnungen werden zur Rückfrage markiert. Jede Aktion lässt
  sich rückgängig machen.
- **Grafische Oberfläche:** Ordner wählen, analysieren, in einer Tabelle prüfen
  (unsichere Fälle per Doppelklick korrigieren), anwenden, rückgängig.
- **Wächter (Dauerbetrieb):** überwacht einen Ordner und sortiert neue, sichere
  Scans automatisch ein; unsichere bleiben zur manuellen Prüfung liegen.
- **Lernfähige Kürzungen:** neu gesehene Absender werden gesammelt und lassen
  sich per Klick auf einheitliche Kurznamen bringen.
- **Kategorien & Absender** sind frei konfigurierbar (im Programm oder in
  `config.json`).

## Mindestanforderungen

Das Programm selbst ist sehr genuegsam - der Bedarf kommt fast ausschliesslich
vom lokalen KI-Modell (ueber Ollama). Richtwerte:

**Minimum (mit dem kleinen Modell `qwen3:4b`):**
- Windows 10 oder 11 (64-Bit)
- 64-Bit-Prozessor mit AVX2-Unterstuetzung (praktisch jeder Rechner ab ca. 2015)
- 8 GB Arbeitsspeicher (RAM)
- ca. 10 GB freier Speicherplatz (Ollama + ein Modell)
- Keine Grafikkarte noetig - Ollama rechnet dann auf dem Prozessor (langsamer,
  fuer den Hintergrund-Betrieb aber ausreichend)
- Internet einmalig fuer die Installation von Ollama und den Modell-Download

**Empfohlen (fluessiger, auch fuer das genauere `qwen3:8b`):**
- 16 GB Arbeitsspeicher
- SSD statt Festplatte (das Modell laedt dann in Sekunden statt Minuten)
- Optional eine Grafikkarte mit mindestens 6 GB Videospeicher (NVIDIA ab
  GTX-900-Serie / CUDA 5.0, AMD via ROCm, oder Apple Silicon) - damit laeuft
  die Zuordnung um ein Vielfaches schneller

**Faustregel zum Speicher:** Ein Modell braucht grob so viel freien Speicher wie
seine Dateigroesse plus etwas Reserve - `qwen3:4b` etwa 3-4 GB, `qwen3:8b` etwa
6 GB. Ist zu wenig frei, laedt Ollama das Modell nicht; dann hilft das kleinere
Modell.

Nicht unterstuetzt: sehr alte Prozessoren ohne AVX2 - dort startet Ollama nicht.

## Voraussetzungen

- Windows 10/11
- [Ollama](https://ollama.com) installiert und ein Modell geladen, z. B.:
  ```
  ollama pull qwen3:4b
  ```
  (`qwen3:4b` ist schneller, `qwen3:8b` etwas genauer.) Fehlt das Modell, bietet
  das Programm an, es herunterzuladen.
- Zum Ausführen aus dem Quellcode: Python 3.10+ und die Pakete
  ```
  pip install pdfplumber requests
  ```
  (Optional für reine Bild-Scans ohne Textebene: `pip install pytesseract
  pdf2image` plus Tesseract-OCR mit deutschem Sprachpaket und Poppler.)
- Eine dedizierte Grafikkarte beschleunigt die Zuordnung deutlich, ist aber kein
  Muss. Ohne GPU dauert ein Dokument je nach Rechner einige Sekunden.

## Start

**Oberfläche:**
```
python pdf_ui.py
```
Ordner wählen → *Analysieren* → in der Tabelle prüfen → *Anwenden*.
*Rückgängig* nimmt den letzten Lauf zurück.

**Wächter (Dauerbetrieb):**
```
python pdf_watcher_ui.py
```
Ordner wählen, *Start* – oder als Fenster, das beim Windows-Start automatisch
mitläuft und sofort überwacht (Häkchen in der Oberfläche).

## Als .exe verpacken (ohne Python-Start)

Die beigelegten Batch-Dateien bauen mit
[PyInstaller](https://pyinstaller.org) je eine `.exe`:

- `Exe_bauen.bat` → `PDF-Sortierer.exe` (Oberfläche)
- `Waechter_Exe_bauen.bat` → `PDF-Waechter.exe` (Wächter)

Die `.exe` ersetzt nur den Python-Start – **Ollama muss weiterhin installiert
sein und laufen.**

## Dateien

| Datei | Zweck |
|-------|-------|
| `pdf_sortierer.py` | Analyse-Logik (Text lesen, Kategorie/Name, Ollama, Kern) |
| `pdf_anwenden.py` | Ordner anlegen, umbenennen, verschieben, rückgängig (Konsole) |
| `pdf_ui.py` | grafische Oberfläche |
| `pdf_watcher.py` | Wächter-Logik (Konsole) |
| `pdf_watcher_ui.py` | Wächter mit Fenster (Status, Start/Stopp, Autostart) |
| `Exe_bauen.bat` / `Waechter_Exe_bauen.bat` | `.exe` bauen |

`config.json` (Kategorien & Absender) sowie die Zustandsdateien werden beim
ersten Start automatisch angelegt und sind bewusst nicht Teil des Repositories.

## Datenschutz

Die Dokumente werden ausschließlich lokal verarbeitet. Es werden keine Daten an
Dritte oder in eine Cloud gesendet.

## Hinweis

Dies ist ein privates Werkzeug, das mit Sorgfalt gebaut, aber nicht umfassend
über viele Geräte und Dokumenttypen getestet wurde. Nutzung auf eigene
Verantwortung – die eingebaute Vorschau und die Rückgängig-Funktion sind dafür
da, auf der sicheren Seite zu bleiben.

## Lizenz

Siehe [LICENSE](LICENSE).
