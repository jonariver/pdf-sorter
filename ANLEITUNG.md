# PDF-Sortierer – Anleitung

Diese Anleitung erklärt Schritt für Schritt, wie du den PDF-Sortierer benutzt –
von der Installation bis zum täglichen Sortieren. Du brauchst dafür keine
Programmierkenntnisse.

---

## Inhalt

1. [Was macht das Programm?](#1-was-macht-das-programm)
2. [Was du einmalig brauchst](#2-was-du-einmalig-brauchst)
3. [Installation](#3-installation)
4. [Der erste Start](#4-der-erste-start)
5. [Die zwei Programme im Überblick](#5-die-zwei-programme-im-überblick)
6. [Sortieren Schritt für Schritt](#6-sortieren-schritt-für-schritt)
7. [Einstellungen: Kategorien, Absender, OCR](#7-einstellungen-kategorien-absender-ocr)
8. [Der Wächter (automatischer Dauerbetrieb)](#8-der-wächter-automatischer-dauerbetrieb)
9. [Bild-Scans und Texterkennung (OCR)](#9-bild-scans-und-texterkennung-ocr)
10. [Wo liegen meine Dateien?](#10-wo-liegen-meine-dateien)
11. [Tipps für gute Ergebnisse](#11-tipps-für-gute-ergebnisse)
12. [Wenn etwas nicht klappt](#12-wenn-etwas-nicht-klappt)
13. [Deinstallieren](#13-deinstallieren)
14. [Datenschutz](#14-datenschutz)
15. [Spickzettel](#15-spickzettel)

---

## 1. Was macht das Programm?

Der PDF-Sortierer nimmt gescannte PDF-Dokumente mit kryptischen Namen (wie sie
ein Dokumentenscanner auswirft) und ordnet sie automatisch ein. Für jedes
Dokument:

- **liest** es den Text,
- **bestimmt** eine Kategorie (z. B. „Versicherungen", „Rechnungen"),
- **schlägt einen sauberen Dateinamen vor** (Datum, Kategorie, Absender, Betreff),
- und **verschiebt** die Datei in den passenden Unterordner.

Die eigentliche „Intelligenz" kommt von einem KI-Modell, das **komplett auf
deinem eigenen Rechner** läuft. Deine Dokumente verlassen den Computer nie.

**Wichtig:** Das Programm verschiebt nichts heimlich. Es zeigt dir immer erst
eine Übersicht, und du entscheidest, ob es losgeht. Jede Aktion lässt sich
rückgängig machen.

---

## 2. Was du einmalig brauchst

Das Programm selbst bringt alles mit. Zusätzlich brauchst du nur die KI im
Hintergrund – das ist ein separates, kostenloses Programm namens **Ollama**:

- **Ollama** – das Programm, das die KI-Modelle ausführt. Kann bei der
  Installation automatisch mitinstalliert werden (siehe unten) oder von
  [ollama.com](https://ollama.com).
- **Ein Sprachmodell** – das eigentliche „Gehirn". Es wird beim ersten Start
  heruntergeladen (mehrere GB, einmalig, dafür brauchst du kurz Internet).
  Zur Auswahl:
  - `qwen3:4b` – kleiner und schneller, läuft auch auf schwächeren Rechnern.
  - `qwen3:8b` – etwas genauer, braucht mehr Speicher.

Danach arbeitet alles offline auf deinem Rechner.

**Grober Rechnerbedarf:** Windows 10/11 (64-Bit), mindestens 8 GB RAM. Eine
Grafikkarte ist nicht nötig, macht die Zuordnung aber deutlich schneller.

---

## 3. Installation

Es gibt zwei Wege. Wähle den, der zu dir passt.

### Weg A: Mit der Setup.exe (empfohlen)

1. `PDF-Sortierer-Setup.exe` doppelklicken.
2. Windows zeigt eventuell eine blaue SmartScreen-Warnung, weil das Programm
   nicht signiert ist. Das ist bei selbstgebauten Programmen normal:
   **„Weitere Informationen" → „Trotzdem ausführen"**.
3. Im Assistenten kannst du ankreuzen:
   - **Desktop-Verknüpfung** anlegen,
   - **Wächter automatisch beim Windows-Start** mitlaufen lassen (standardmäßig aus),
   - **Ollama herunterladen und installieren**, falls noch nicht vorhanden
     (standardmäßig an – braucht einmalig Internet).
4. Fertigstellen. Du findest den PDF-Sortierer danach im Startmenü (und auf dem
   Desktop, falls angehakt).

### Weg B: Ohne Installation (Ordner mit den Programmen)

Wenn du nur die fertigen Programmdateien hast (`PDF-Sortierer.exe` und
`PDF-Waechter.exe`) oder das Programm aus dem Quellcode startest:

- Leg die Dateien in einen Ordner deiner Wahl und starte sie per Doppelklick.
- Ollama musst du in diesem Fall selbst installieren (von ollama.com), falls
  noch nicht vorhanden.
- Es wird nichts „installiert" – zum Entfernen später einfach den Ordner löschen.

---

## 4. Der erste Start

1. **PDF-Sortierer** öffnen.
2. Läuft Ollama noch nicht, fragt das Programm, ob es Ollama automatisch starten
   soll → mit **Ja** bestätigen.
3. Beim allerersten Sortieren wird das gewählte Modell heruntergeladen. Das dauert
   ein paar Minuten (mehrere GB) und passiert nur einmal. Der Fortschritt wird
   unten angezeigt.
4. Auch das **erste Dokument** dauert etwas länger, weil das Modell erst in den
   Speicher geladen wird. Danach geht es zügig.

Wenn unten „Bereit. (Ollama läuft)" steht, kann es losgehen.

---

## 5. Die zwei Programme im Überblick

Es gibt zwei Programme, die zusammengehören:

- **PDF-Sortierer** – die Oberfläche zum **manuellen** Sortieren: Ordner wählen,
  analysieren, prüfen, anwenden. Hier hast du volle Kontrolle und siehst alles.
- **PDF-Wächter** – der **automatische** Dauerbetrieb: Er überwacht einen Ordner
  (z. B. den Ausgabeordner deines Scanners) und sortiert neue, sichere Scans von
  selbst ein. Unsichere lässt er liegen, damit du sie später von Hand einordnest.

Du kannst mit dem Sortierer anfangen und den Wächter später dazunehmen – oder nur
eines von beiden nutzen.

---

## 6. Sortieren Schritt für Schritt

So läuft ein typischer Durchgang in der Oberfläche **PDF-Sortierer**:

### Schritt 1 – Ordner wählen
Oben bei „Ordner" auf **Durchsuchen…** klicken und den Ordner mit deinen
gescannten PDFs auswählen. Der zuletzt benutzte Ordner wird gemerkt.

### Schritt 2 – (optional) Einstellungen prüfen
- **Modell**: `qwen3:4b` oder `qwen3:8b`.
- **Sicherheits-Schwelle**: Ab wie viel Prozent Sicherheit eine Zuordnung als
  „sicher" gilt (Standard 80). Alles darunter wird zur Rückfrage markiert.
- **Test: nur erste N**: Zum Ausprobieren nur die ersten paar PDFs verarbeiten
  (0 = alle).

### Schritt 3 – Analysieren
Auf **Analysieren** klicken. Das Programm liest jedes PDF und füllt die Tabelle:

| Spalte | Bedeutung |
|--------|-----------|
| Datei | der aktuelle (kryptische) Dateiname |
| Kategorie | vorgeschlagener Unterordner |
| % | wie sicher sich die KI ist |
| Neuer Name | so würde die Datei umbenannt |
| Begründung | warum diese Kategorie |

**Es wird dabei noch nichts verschoben!** Das ist nur eine Vorschau.

Die Zeilenfarben helfen beim Prüfen:
- **rötlich hinterlegt** = unsicher, bitte anschauen.
- **bläulich hinterlegt** = von dir von Hand geändert.

### Schritt 4 – Prüfen und korrigieren
- **Doppelklick auf eine Zeile** öffnet ein kleines Fenster, in dem du die
  **Kategorie ändern** kannst.
- Über die **Spaltenköpfe** kannst du die Tabelle sortieren (z. B. nach „%", um
  die unsichersten oben zu sehen).

### Schritt 5 – Anwenden
Wenn alles passt, auf **Anwenden** klicken und die Sicherheitsabfrage bestätigen.
Jetzt werden die Unterordner angelegt, die Dateien umbenannt und verschoben – nur
**innerhalb** des gewählten Ordners.

### Schritt 6 – Falls doch etwas nicht passt: Rückgängig
**Rückgängig** nimmt den letzten Anwenden-Lauf komplett zurück und legt die
Dateien wieder an ihren Ursprungsort.

### Extra: Plan laden
Hast du gestern analysiert und willst heute erst verschieben? Mit **Plan laden**
holst du die gespeicherte Vorschau (`plan.json`) aus dem Ordner zurück in die
Tabelle, ohne neu zu analysieren. Liegen Dateien aus dem Plan nicht mehr im
Ordner, warnt das Programm – dann lieber neu analysieren.

---

## 7. Einstellungen: Kategorien, Absender, OCR

Über **Einstellungen…** öffnet sich ein Fenster mit drei Bereichen.

### Kategorien
Das sind deine späteren Unterordner. Jede Kategorie hat einen **Ordnernamen** und
eine kurze **Beschreibung**. Die Beschreibung ist wichtig: Sie hilft der KI zu
verstehen, was in die Kategorie gehört. Du kannst Kategorien hinzufügen, ändern
(Doppelklick auf eine Zelle) oder entfernen.

Standardmäßig gibt es u. a.: Arbeit, Rechnungen, Versicherungen, Rente, Steuer,
Verträge, Behörden, Gesundheit, Bank, Sonstiges.

### Bekannte Absender (Kürzungen)
Hier legst du fest, wie lange Firmennamen abgekürzt werden. Links steht ein
kleiner Ausschnitt des erkannten Namens (klein geschrieben), rechts die
gewünschte Kurzform. Beispiel:

- `bayerische motoren werke` → `BMW`
- `techniker krankenkasse` → `TK`

Sobald ein Absender dort steht, wird er in allen künftigen Dateinamen einheitlich
gekürzt.

### Neu gesehen
Trifft das Programm auf einen Absender, den es noch nicht kennt, sammelt es ihn
hier und macht einen **Kürzungs-Vorschlag**. Du kannst die Vorschläge bearbeiten
und mit einem Klick alle in die Absender-Liste übernehmen. So „lernt" das
Programm nach und nach deine typischen Absender.

### Vision-Modell (OCR)
Modellname für die Texterkennung bei reinen Bild-Scans (siehe nächster
Abschnitt). Standard ist `llama3.2-vision`. Mit **Vision-Modell laden** kannst du
es direkt herunterladen, ohne die Kommandozeile zu benutzen.

Zum Schluss **Speichern** nicht vergessen.

---

## 8. Der Wächter (automatischer Dauerbetrieb)

Der **PDF-Wächter** überwacht einen Ordner und sortiert neue Scans automatisch
ein. Ideal für den Ausgabeordner deines Scanners.

### So richtest du ihn ein
1. **PDF-Wächter** öffnen.
2. Den zu überwachenden Ordner wählen.
3. Einstellungen nach Bedarf:
   - **Modell** (Standard `qwen3:4b` – gut für nebenbei),
   - **Auto-Schwelle** (Standard 85): Erst ab dieser Sicherheit wird
     automatisch verschoben. Alles darunter bleibt liegen.
   - **Intervall**: Wie oft nachgeschaut wird (Standard 15 Sekunden).
   - **Nur melden**: Testmodus – zeigt nur an, was passieren *würde*, verschiebt
     aber nichts. Gut zum gefahrlosen Beobachten am Anfang.
4. Auf **Start** klicken. Die Statuslampe wird grün („läuft").

### Praktische Schalter
- **Beim Windows-Start automatisch mitlaufen**: Der Wächter startet dann bei
  jeder Anmeldung und überwacht sofort.
- **Beim Programmstart sofort überwachen**: Beim Öffnen gleich loslegen, ohne
  „Start" zu drücken.
- **Speicher nach der Arbeit freigeben**: Gibt nach jedem Dokument RAM/Grafik-
  speicher frei. Spart Speicher, lädt aber das Modell bei jedem neuen Dokument
  neu – auf schwachen Rechnern lieber ausgeschaltet lassen.

### Was der Wächter noch kann
- **Verlauf anzeigen**: zeigt eine Liste aller automatisch verschobenen Dateien
  (Zeitpunkt, Name vorher/nachher, Zielordner, voller Pfad). Die kann auch als
  CSV geöffnet werden.
- **Einstellungen…**: derselbe Dialog wie in der Hauptoberfläche (Kategorien,
  Absender, Vision-Modell). Änderungen greifen ab dem nächsten Dokument, ohne
  Neustart.

Auch die automatischen Verschiebungen des Wächters lassen sich über die
Oberfläche mit **Rückgängig** wieder zurücknehmen.

---

## 9. Bild-Scans und Texterkennung (OCR)

Die meisten Scans enthalten eine unsichtbare Textebene – daraus liest das
Programm direkt. Manche Scans sind aber **reine Bilder ohne Text** (z. B. Fotos
oder sehr alte Scans). Dafür gibt es die **Texterkennung (OCR)**:

- Das Programm rendert die Seite zu einem Bild und lässt sie von einem lokalen
  **Vision-Modell** vorlesen. Auch das läuft komplett auf deinem Rechner – kein
  Tesseract, kein Poppler, keine Cloud.
- Dafür muss das Vision-Modell installiert sein. Am einfachsten über
  **Einstellungen → Vision-Modell laden** (Standard: `llama3.2-vision`,
  mehrere GB).
- Ist kein Vision-Modell vorhanden, stürzt nichts ab: Der Bild-Scan bleibt
  einfach unsortiert liegen, damit du ihn von Hand einordnen kannst.

Wenn du nur normale Scans mit Textebene hast, brauchst du OCR gar nicht.

---

## 10. Wo liegen meine Dateien?

- **`config.json`** – deine Einstellungen (Kategorien, Absender, Vision-Modell).
  Liegt **neben dem Programm** (neben `PDF-Sortierer.exe` bzw. `pdf_ui.py`). Wird
  beim ersten Start automatisch angelegt. Nicht löschen, wenn du deine
  Einstellungen behalten willst.
- **`plan.json` / `plan.csv`** – die Vorschau aus dem letzten Analyse-Lauf. Liegt
  **im jeweiligen Scan-Ordner**. `plan.csv` kannst du in Excel öffnen. Wird bei
  jeder neuen Analyse überschrieben.
- **`verschiebungen.csv`** – dauerhaftes Protokoll aller Verschiebungen (wird nie
  automatisch geleert). Liegt im Scan-Ordner.
- **`verschiebe_protokoll.jsonl`** – interne Datei für die Rückgängig-Funktion.

Bei der installierten Version liegt die `config.json` im Installationsordner.
Willst du deine bisherigen Kategorien/Absender übernehmen, kopiere deine alte
`config.json` einfach dorthin.

---

## 11. Tipps für gute Ergebnisse

- **Erst im Testmodus ausprobieren:** In der Oberfläche „Test: nur erste 5"
  setzen oder im Wächter „Nur melden" aktivieren, bis du dem Ergebnis vertraust.
- **Kategorien-Beschreibungen pflegen:** Je klarer die Beschreibung, desto besser
  ordnet die KI ein. Ein Satz reicht meist.
- **Absender-Kürzungen nutzen:** Über „Neu gesehen" nach und nach deine typischen
  Absender kürzen – die Dateinamen werden dadurch viel einheitlicher.
- **Genaueres Modell bei Zweifeln:** Wenn `qwen3:4b` zu oft danebenliegt, in den
  Einstellungen auf `qwen3:8b` wechseln (etwas langsamer, dafür treffsicherer).
- **Schwelle anpassen:** Landen zu viele Dokumente in „Sonstiges" oder werden zu
  viele als unsicher markiert, kannst du mit der Sicherheits-Schwelle spielen.

---

## 12. Wenn etwas nicht klappt

**„Ollama läuft nicht":** Das Programm bietet an, Ollama zu starten – mit Ja
bestätigen. Klappt das nicht, Ollama einmal manuell starten (bzw. von ollama.com
installieren) und es erneut versuchen.

**Modell fehlt / wird nicht gefunden:** Beim Analysieren bietet das Programm an,
das Modell herunterzuladen. Zustimmen und einige Minuten warten (einmalig).

**Windows SmartScreen warnt beim Start:** Normal bei selbstgebauten, nicht
signierten Programmen. „Weitere Informationen" → „Trotzdem ausführen".

**Alles ist sehr langsam:** Ohne Grafikkarte rechnet die KI auf dem Prozessor –
das dauert pro Dokument einige Sekunden. Das kleinere Modell `qwen3:4b` hilft.
Das allererste Dokument ist immer am langsamsten (Modell wird geladen).

**Ein Bild-Scan bleibt liegen / „kein Text lesbar":** Das PDF hat keine
Textebene. Für automatische Verarbeitung brauchst du das Vision-Modell (OCR,
siehe Abschnitt 9). Sonst das Dokument von Hand einordnen.

**Eine Kategorie ist falsch:** Vor dem Anwenden per Doppelklick auf die Zeile
korrigieren. Häuft sich ein Fehler, die Kategorien-Beschreibung in den
Einstellungen schärfen.

**Aus Versehen falsch verschoben:** **Rückgängig** drücken – der letzte Lauf wird
komplett zurückgenommen.

---

## 13. Deinstallieren

**Installierte Version (über Setup.exe):**
Windows-Einstellungen → **Apps** → **Installierte Apps** → **PDF-Sortierer** →
**Deinstallieren**. Das entfernt beide Programme, die Verknüpfungen und – falls
gesetzt – den Wächter-Autostart.

**Ordner-Variante (ohne Installation):**
Einfach den Programm-Ordner löschen. Falls du den Wächter-Autostart aktiviert
hattest, vorher im Wächter das Häkchen „Beim Windows-Start automatisch mitlaufen"
entfernen.

**In beiden Fällen bleiben absichtlich erhalten:**
- deine `config.json` und die Protokolldateien (kannst du bei Bedarf mitlöschen),
- **Ollama und die KI-Modelle** – die sind ein eigenes Programm. Willst du sie
  auch loswerden: Modelle mit `ollama rm qwen3:4b` (usw.) löschen und Ollama
  separat über „Installierte Apps" deinstallieren.

---

## 14. Datenschutz

Alle Dokumente werden **ausschließlich lokal** auf deinem Rechner verarbeitet. Es
werden keine Inhalte an Dritte oder in eine Cloud gesendet. Die KI (Ollama) läuft
offline; Internet brauchst du nur einmalig zum Herunterladen von Ollama und den
Modellen.

---

## 15. Spickzettel

| Ich will… | Das mache ich |
|-----------|---------------|
| Einen Ordner einmalig sortieren | Sortierer → Ordner wählen → Analysieren → prüfen → Anwenden |
| Eine Zuordnung ändern | Doppelklick auf die Zeile |
| Einen Fehler zurücknehmen | Rückgängig |
| Gestrige Analyse weiterverwenden | Plan laden |
| Neue Scans automatisch einsortieren | Wächter → Ordner wählen → Start |
| Erst gefahrlos testen | „Test: nur erste N" bzw. Wächter „Nur melden" |
| Kategorien/Absender anpassen | Einstellungen… |
| Bild-Scans lesbar machen | Einstellungen → Vision-Modell laden |
| Sehen, was verschoben wurde | Wächter → Verlauf anzeigen (oder `verschiebungen.csv`) |

---

*Dies ist ein privates Werkzeug, mit Sorgfalt gebaut, aber nicht über alle
Geräte und Dokumenttypen hinweg getestet. Nutzung auf eigene Verantwortung – die
Vorschau und die Rückgängig-Funktion sind dafür da, auf der sicheren Seite zu
bleiben.*
