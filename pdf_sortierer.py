#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF-Sortierer - Schritt 1: Analyse & Vorschau (Dry Run)
========================================================

Dieses Programm durchsucht einen Ordner nach PDF-Dateien, liest ihren Text,
fragt ein LOKALES Sprachmodell (via Ollama) nach Kategorie + Metadaten und
schlaegt dir vor:
    - in welchen Unterordner das Dokument gehoert,
    - wie es sinnvoll umbenannt werden sollte,
    - mit welcher Sicherheit, und mit Begruendung.

WICHTIG: Dieser Lauf VERSCHIEBT und BENENNT NICHTS UM. Er zeigt dir nur eine
Uebersicht und schreibt einen Plan als Datei (plan.json / plan.csv), den du in
Ruhe pruefen kannst.

Kategorien und bekannte Absender stehen in einer separaten Datei config.json
neben dem Skript. Sie wird beim ersten Start automatisch angelegt und
ueberlebt jedes Skript-Update - dort passt du deine Ordner und Absender an.

------------------------------------------------------------
Voraussetzungen auf deinem Windows-11-Rechner
------------------------------------------------------------
1) Python 3.10+
2) Pflicht-Pakete:
       pip install pdfplumber requests
3) OPTIONAL fuer einen huebschen Fortschrittsbalken:
       pip install tqdm
   (ohne tqdm laeuft das Programm trotzdem - dann gibt es eine einfache
    Text-Fortschrittsanzeige)
4) Ollama installiert und ein Modell geladen:
       ollama pull qwen3:8b
5) OPTIONAL fuer reine Bild-Scans (OCR): PyMuPDF und ein Vision-Modell:
       pip install pymupdf
       ollama pull llama3.2-vision
   (kein Tesseract/Poppler noetig - die Texterkennung laeuft ueber Ollama).

------------------------------------------------------------
Aufruf (PowerShell)
------------------------------------------------------------
    python .\\pdf_sortierer.py "C:\\Pfad\\zu\\deinen\\Scans"

Optional:
    python .\\pdf_sortierer.py "C:\\Scans" --model gemma3:4b --schwelle 75
"""

import argparse
import base64
import csv
import json
import os
import re
import sys
import time
from datetime import datetime

# ----------------------------------------------------------------------------
# KONFIGURATION
# ----------------------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
STANDARD_MODELL = "qwen3:8b"
# Vision-Modell fuer OCR von reinen Bild-Scans (ohne Textebene). Ueber Ollama.
# Alternativen mit besserer Dokument-/Deutsch-OCR: "qwen3-vl:8b", "minicpm-v".
STANDARD_VISION_MODELL = "llama3.2-vision"

# Kategorien = spaetere Unterordner. Key = Ordnername, Wert = kurze Definition.
# Das hier sind nur die VORGABEN; im Betrieb wird aus config.json geladen.
STANDARD_KATEGORIEN = {
    "Arbeit":         "Gehalts-/Entgeltabrechnungen, Lohn, Arbeitsvertrag, "
                      "Zeugnisse, Schreiben vom Arbeitgeber",
    "Rechnungen":     "Rechnungen und Belege fuer gekaufte Waren oder "
                      "Dienstleistungen (NICHT Gehalt)",
    "Versicherungen": "Versicherungspolicen, Beitraege, Schreiben von "
                      "Versicherungen (Auto, Haftpflicht, Leben, Kranken, ...)",
    "Rente":          "Altersvorsorge: Renteninformationen, Pensionsvertraege, "
                      "Schreiben der Deutschen Rentenversicherung, Pensionsfonds",
    "Steuer":         "Finanzamt, Steuerbescheide, Steuererklaerung",
    "Vertraege":      "Vertraege (Miete, Handy, Strom-/Gasvertrag, Abos) - "
                      "ausser Versicherungsvertraegen",
    "Behoerden":      "Aemter und amtliche Bescheide (ausser Finanzamt)",
    "Gesundheit":     "Arztbriefe, Befunde, Rezepte, Behandlungen, Schreiben "
                      "der Krankenkasse zu Behandlungen",
    "Bank":           "Kontoauszuege, Bankmitteilungen, Kredite",
    "Sonstiges":      "Alles, was in keine andere Kategorie passt",
}

STANDARD_SCHWELLE = 80
DATEINAME_VORLAGE = "{datum}_{kategorie}_{absender}_{betreff}"
MIN_TEXTLAENGE_OHNE_OCR = 40

STANDARD_BEKANNTE_ABSENDER = {
    "bayerische motoren werke": "BMW",
    "stadtwerke muenchen": "Stadtwerke-Muenchen",
    "swm": "Stadtwerke-Muenchen",
    "telekom": "Telekom",
    "finanzamt": "Finanzamt",
    "aok": "AOK",
    "techniker krankenkasse": "TK",
}

# Diese beiden werden beim Start aus config.json geladen (siehe config_laden()).
# Bis dahin gelten die STANDARD_-Vorgaben von oben.
KATEGORIEN = dict(STANDARD_KATEGORIEN)
BEKANNTE_ABSENDER = dict(STANDARD_BEKANNTE_ABSENDER)
VISION_MODELL = STANDARD_VISION_MODELL


def app_verzeichnis():
    """Verzeichnis, in dem config.json & Co. liegen sollen.
    Bei einer mit PyInstaller gebauten .exe: neben der EXE. Sonst: neben dem Skript."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def config_pfad_ermitteln():
    return os.path.join(app_verzeichnis(), "config.json")


def _config_speichern(pfad, config):
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def config_laden():
    """Laedt config.json neben dem Skript. Legt sie mit den Vorgaben an, falls
    sie noch fehlt. Gibt (config, pfad) zurueck."""
    pfad = config_pfad_ermitteln()
    if not os.path.exists(pfad):
        config = {
            "kategorien": STANDARD_KATEGORIEN,
            "bekannte_absender": STANDARD_BEKANNTE_ABSENDER,
            "vision_modell": STANDARD_VISION_MODELL,
            "neue_absender": [],
        }
        _config_speichern(pfad, config)
        print(f"Konfigurationsdatei neu angelegt: {pfad}")
        return config, pfad
    with open(pfad, "r", encoding="utf-8") as f:
        config = json.load(f)
    # fehlende Schluessel robust ergaenzen (z.B. bei aelteren/handischen Dateien)
    config.setdefault("kategorien", STANDARD_KATEGORIEN)
    config.setdefault("bekannte_absender", STANDARD_BEKANNTE_ABSENDER)
    config.setdefault("vision_modell", STANDARD_VISION_MODELL)
    config.setdefault("neue_absender", [])
    return config, pfad


def _absender_bekannt(roh):
    klein = (roh or "").lower()
    return any(muster in klein for muster in BEKANNTE_ABSENDER)


# ----------------------------------------------------------------------------
# OLLAMA-STATUS (laeuft die KI im Hintergrund? / starten)
# ----------------------------------------------------------------------------

OLLAMA_BASIS = "http://localhost:11434"


def ollama_erreichbar(timeout=2):
    try:
        import requests
        r = requests.get(OLLAMA_BASIS + "/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def ollama_modelle(timeout=2):
    try:
        import requests
        r = requests.get(OLLAMA_BASIS + "/api/tags", timeout=timeout)
        r.raise_for_status()
        return [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        return []


def ollama_starten():
    """Versucht, den Ollama-Server zu starten. True, wenn der Startbefehl
    abgesetzt werden konnte (nicht, ob er schon laeuft)."""
    try:
        import subprocess
        if sys.platform.startswith("win"):
            subprocess.Popen(["ollama", "serve"],
                             creationflags=0x08000000)   # CREATE_NO_WINDOW
        else:
            subprocess.Popen(["ollama", "serve"],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def ollama_warten(sekunden=20):
    for _ in range(sekunden):
        if ollama_erreichbar(timeout=1):
            return True
        time.sleep(1)
    return False


def modell_vorhanden(name, timeout=3):
    return name in ollama_modelle(timeout=timeout)


def modell_laden(name, fortschritt=None):
    """Laedt ein Modell via Ollama (/api/pull) herunter und streamt den
    Fortschritt. fortschritt(text, prozent_oder_None) wird laufend aufgerufen.
    Gibt True bei Erfolg zurueck."""
    try:
        import requests
        with requests.post(OLLAMA_BASIS + "/api/pull",
                           json={"name": name, "stream": True},
                           stream=True, timeout=None) as r:
            r.raise_for_status()
            for zeile in r.iter_lines():
                if not zeile:
                    continue
                try:
                    d = json.loads(zeile.decode("utf-8"))
                except Exception:
                    continue
                if d.get("error"):
                    if fortschritt:
                        fortschritt(f"Fehler: {d['error']}", None)
                    return False
                status = d.get("status", "")
                total = d.get("total")
                completed = d.get("completed")
                prozent = None
                if total and completed is not None and total > 0:
                    prozent = int(completed * 100 / total)
                if fortschritt:
                    fortschritt(status, prozent)
                if status == "success":
                    return True
        return True
    except Exception as e:
        if fortschritt:
            fortschritt(f"Fehler: {e}", None)
        return False


def modell_entladen(modell):
    """Bittet Ollama, das Modell aus dem Speicher zu entladen (keep_alive=0),
    um VRAM/RAM freizugeben. Gibt True zurueck, wenn der Aufruf gelang."""
    try:
        import requests
        requests.post(OLLAMA_BASIS + "/api/generate",
                      json={"model": modell, "keep_alive": 0}, timeout=10)
        return True
    except Exception:
        return False

# ----------------------------------------------------------------------------
# TEXT-EXTRAKTION
# ----------------------------------------------------------------------------

def text_aus_pdf(pfad):
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(pfad) as pdf:
            teile = []
            for seite in pdf.pages[:3]:
                teile.append(seite.extract_text() or "")
            text = "\n".join(teile).strip()
    except Exception as e:
        print(f"    [Hinweis] Textebene nicht lesbar ({e}).")

    if len(text) >= MIN_TEXTLAENGE_OHNE_OCR:
        return text, "textebene"

    ocr_text = _ocr_versuchen(pfad)
    if ocr_text and len(ocr_text.strip()) >= MIN_TEXTLAENGE_OHNE_OCR:
        return ocr_text.strip(), "ocr"

    return text, ("leer" if not text else "textebene")


def _pdf_seiten_bilder(pfad, max_seiten=2, zoom=2.0):
    """Rendert die ersten Seiten eines PDFs zu PNG-Bildern (als base64-Strings).
    Nutzt PyMuPDF (reines Python-Paket, kein Fremdprogramm noetig). Gibt eine
    leere Liste zurueck, wenn PyMuPDF fehlt oder das Rendern scheitert."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
    except ImportError:
        return []
    bilder = []
    try:
        doc = fitz.open(pfad)
        seiten = min(max_seiten, doc.page_count)
        matrix = fitz.Matrix(zoom, zoom)   # hoehere Aufloesung = bessere OCR
        for i in range(seiten):
            pix = doc[i].get_pixmap(matrix=matrix)
            bilder.append(base64.b64encode(pix.tobytes("png")).decode("ascii"))
        doc.close()
    except Exception as e:
        print(f"    [Hinweis] Konnte Seiten nicht rendern ({e}).")
        return []
    return bilder


def _ocr_versuchen(pfad):
    """Liest reine Bild-Scans (ohne Textebene) per lokalem Vision-Modell ueber
    Ollama: die Seite wird zu einem Bild gerendert und das Modell gibt den Text
    zurueck. Braucht ein installiertes Vision-Modell (z.B. 'ollama pull
    llama3.2-vision'). Gibt den erkannten Text oder None zurueck."""
    bilder = _pdf_seiten_bilder(pfad)
    if not bilder:
        return None
    modell = VISION_MODELL or STANDARD_VISION_MODELL
    try:
        import requests
    except ImportError:
        return None
    system = ("Du bist ein praezises OCR-Werkzeug fuer deutsche Dokumente. Gib "
              "den GESAMTEN sichtbaren Text so genau wie moeglich wieder - nur "
              "den Text, ohne Kommentare und ohne Markdown.")
    payload = {
        "model": modell,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",
             "content": "Bitte gib den vollstaendigen Text dieses Dokuments wieder.",
             "images": bilder},
        ],
        "stream": False,
        "options": {"temperature": 0},
    }
    try:
        antwort = requests.post(OLLAMA_URL, json=payload, timeout=600)
        antwort.raise_for_status()
        return (antwort.json()["message"]["content"] or "").strip()
    except Exception as e:
        print(f"    [Hinweis] Bild-Texterkennung nicht moeglich ({e}). "
              f"Ist das Vision-Modell '{modell}' installiert?")
        return None


# ----------------------------------------------------------------------------
# LOKALES MODELL (OLLAMA)
# ----------------------------------------------------------------------------

def modell_fragen(text, modell):
    import requests

    kategorien_liste = "\n".join(
        f"- {name}: {beschreibung}" for name, beschreibung in KATEGORIEN.items()
    )
    system = (
        "Du bist ein sorgfaeltiger Assistent, der eingescannte deutsche "
        "Dokumente einsortiert. Du antwortest AUSSCHLIESSLICH mit einem "
        "JSON-Objekt, ohne einleitenden Text und ohne Markdown."
    )
    user = f"""Ordne das folgende Dokument GENAU EINER Kategorie zu.

Verfuegbare Kategorien:
{kategorien_liste}

Gib dieses JSON zurueck (keine weiteren Felder, kein weiterer Text):
{{
  "kategorie": "<eine der Kategorien oben>",
  "absender": "<Wer hat es geschickt? Firma/Behoerde/Person, sonst 'Unbekannt'>",
  "betreff": "<worum geht es, sehr kurz>",
  "dokumentdatum": "<Datum AUF dem Dokument als JJJJ-MM-TT, sonst ''>",
  "referenz": "<Rechnungs-/Aktenzeichen falls vorhanden, sonst ''>",
  "sicherheit": <ganze Zahl 0-100>,
  "begruendung": "<ein kurzer Satz, warum diese Kategorie>"
}}

Dokumententext:
\"\"\"
{text[:6000]}
\"\"\""""

    payload = {
        "model": modell,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": "json",
        "think": False,   # Qwen3 "Thinking"-Modus aus -> deutlich schneller
        "options": {"temperature": 0},
    }

    antwort = requests.post(OLLAMA_URL, json=payload, timeout=300)
    antwort.raise_for_status()
    inhalt = antwort.json()["message"]["content"]
    return _json_robust_parsen(inhalt)


def _json_robust_parsen(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


# ----------------------------------------------------------------------------
# NAMEN & PLAN AUFBEREITEN
# ----------------------------------------------------------------------------

UNGUELTIGE_ZEICHEN = r'[\\/:*?"<>|]'

def dateiname_saeubern(text):
    text = re.sub(UNGUELTIGE_ZEICHEN, "", text)
    text = text.strip().replace(" ", "-")
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("-.")
    return text or "Unbekannt"


def absender_vereinheitlichen(roh):
    klein = (roh or "").lower()
    for muster, einheitlich in BEKANNTE_ABSENDER.items():
        if muster in klein:
            return einheitlich
    return dateiname_saeubern(roh or "Unbekannt")


def scan_datum_aus_praefix(dateiname):
    """Zieht ein Datum aus dem Anfang des Dateinamens (ScanSnap-Praefix).
    Unterstuetzt JJJJMMTT und TTMMJJJJ, auch mit Trennern (-, _, .)."""
    kopf = re.match(r"[\d\-_.]{6,}", dateiname)
    if not kopf:
        return ""
    ziffern = re.sub(r"\D", "", kopf.group(0))[:8]
    if len(ziffern) < 8:
        return ""
    # Zuerst JJJJMMTT probieren, dann TTMMJJJJ
    d = datum_pruefen(f"{ziffern[:4]}-{ziffern[4:6]}-{ziffern[6:8]}")
    if d:
        return d
    return datum_pruefen(f"{ziffern[4:8]}-{ziffern[2:4]}-{ziffern[:2]}")


def datum_pruefen(roh):
    if not roh:
        return ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(roh))
    if not m:
        return ""
    try:
        datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    except ValueError:
        return ""


def neuen_namen_bauen(daten, original_dateiname):
    dok_datum = datum_pruefen(daten.get("dokumentdatum"))
    scan_datum = scan_datum_aus_praefix(original_dateiname)
    datum = dok_datum or scan_datum or "ohne-Datum"

    kategorie = dateiname_saeubern(daten.get("kategorie", "Sonstiges"))
    absender = absender_vereinheitlichen(daten.get("absender", "Unbekannt"))
    betreff = dateiname_saeubern(daten.get("betreff", ""))

    name = DATEINAME_VORLAGE.format(
        datum=datum, kategorie=kategorie, absender=absender, betreff=betreff
    )
    name = name[:120].strip("-_") + ".pdf"
    return name


# ----------------------------------------------------------------------------
# FORTSCHRITTSANZEIGE (tqdm optional, mit Fallback)
# ----------------------------------------------------------------------------

def _fortschritt_vorbereiten(gesamt):
    """Liefert vier Funktionen: schreibe(text), status(text),
    weiter(), schliessen(). Nutzt tqdm falls vorhanden, sonst einfache Prints."""
    try:
        from tqdm import tqdm
        balken = tqdm(total=gesamt, unit="PDF", ncols=78, desc="Analyse")

        def schreibe(msg):
            tqdm.write(msg)

        def status(msg):
            balken.set_postfix_str(msg)

        def weiter():
            balken.update(1)

        def schliessen():
            balken.close()

        return schreibe, status, weiter, schliessen
    except ImportError:
        def schreibe(msg):
            print(msg, flush=True)

        def status(msg):
            print(f"       ... {msg}", flush=True)

        def weiter():
            pass

        def schliessen():
            pass

        return schreibe, status, weiter, schliessen


# ----------------------------------------------------------------------------
# HAUPTABLAUF
# ----------------------------------------------------------------------------

def analysiere_ordner(ordner, modell, schwelle, limit=None):
    pdfs = [f for f in sorted(os.listdir(ordner)) if f.lower().endswith(".pdf")]
    if not pdfs:
        print(f"Keine PDF-Dateien in {ordner} gefunden.")
        return []

    gesamt_vorhanden = len(pdfs)
    if limit:
        pdfs = pdfs[:limit]
        print(f"\n(Testmodus: nur die ersten {len(pdfs)} von "
              f"{gesamt_vorhanden} PDFs)")

    print(f"\n{len(pdfs)} PDF(s) gefunden. Modell: {modell}. "
          f"Sicherheits-Schwelle: {schwelle}")
    print("Hinweis: Das erste Dokument dauert laenger, weil Ollama das Modell "
          "erst laden muss.\n" + "-" * 70)

    schreibe, status, weiter, schliessen = _fortschritt_vorbereiten(len(pdfs))
    plan = []

    for i, dateiname in enumerate(pdfs, 1):
        pfad = os.path.join(ordner, dateiname)
        schreibe(f"[{i}/{len(pdfs)}] {dateiname}")
        t_doc = time.time()

        status(f"Text lesen: {dateiname[:24]}")
        text, methode = text_aus_pdf(pfad)
        if methode == "leer":
            schreibe("    -> kein Text lesbar (Bild-Scan ohne OCR?) "
                     "-> manuelle Pruefung")
            plan.append({
                "datei": dateiname, "kategorie": "?", "zielordner": "?",
                "neuer_name": dateiname, "sicherheit": 0,
                "rueckfrage": True, "begruendung": "Kein Text extrahierbar",
                "textmethode": methode,
                "modell": modell, "dauer_s": round(time.time() - t_doc, 1),
            })
            weiter()
            continue

        status("Modell denkt nach (1. Mal dauert laenger)")
        try:
            daten = modell_fragen(text, modell)
        except Exception as e:
            schreibe(f"    -> Fehler beim Modell-Aufruf: {e}")
            plan.append({
                "datei": dateiname, "kategorie": "?", "zielordner": "?",
                "neuer_name": dateiname, "sicherheit": 0,
                "rueckfrage": True, "begruendung": f"Modellfehler: {e}",
                "textmethode": methode,
                "modell": modell, "dauer_s": round(time.time() - t_doc, 1),
            })
            weiter()
            continue

        kategorie = daten.get("kategorie", "Sonstiges")
        if kategorie not in KATEGORIEN:
            kategorie = "Sonstiges"
        sicherheit = int(daten.get("sicherheit", 0) or 0)
        neuer_name = neuen_namen_bauen(daten, dateiname)
        rueckfrage = sicherheit < schwelle
        dauer_s = round(time.time() - t_doc, 1)

        plan.append({
            "datei": dateiname,
            "kategorie": kategorie,
            "zielordner": kategorie,
            "neuer_name": neuer_name,
            "absender_roh": daten.get("absender", ""),
            "sicherheit": sicherheit,
            "rueckfrage": rueckfrage,
            "begruendung": daten.get("begruendung", ""),
            "textmethode": methode,
            "modell": modell,
            "dauer_s": dauer_s,
        })

        markierung = "  << RUECKFRAGE NOETIG" if rueckfrage else ""
        schreibe(f"    -> {kategorie} ({sicherheit}%)  "
                 f"[{dauer_s}s, {methode}, {modell}]{markierung}")
        schreibe(f"       neu: {neuer_name}")
        weiter()

    schliessen()
    return plan


def uebersicht_ausgeben(plan):
    if not plan:
        return
    print("\n" + "=" * 70)
    print("UEBERSICHT")
    print("=" * 70)

    sicher = [p for p in plan if not p["rueckfrage"]]
    unsicher = [p for p in plan if p["rueckfrage"]]

    ordner = sorted({p["zielordner"] for p in sicher if p["zielordner"] != "?"})
    print("\nAnzulegende Unterordner:")
    for o in ordner:
        anzahl = sum(1 for p in sicher if p["zielordner"] == o)
        print(f"  [+] {o}  ({anzahl} Dokument(e))")

    print(f"\nSicher zugeordnet: {len(sicher)}   |   "
          f"Rueckfrage noetig: {len(unsicher)}")

    if unsicher:
        print("\nDiese brauchen deine Entscheidung:")
        for p in unsicher:
            print(f"  [?] {p['datei']}  (Vorschlag: {p['kategorie']}, "
                  f"{p['sicherheit']}%)")

    print("\nHinweis: Es wurde NICHTS verschoben oder umbenannt. "
          "Das ist ein reiner Vorschau-Lauf.")


def plan_speichern(plan, ordner):
    json_pfad = os.path.join(ordner, "plan.json")
    csv_pfad = os.path.join(ordner, "plan.csv")

    with open(json_pfad, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    felder = ["datei", "kategorie", "zielordner", "neuer_name",
              "sicherheit", "rueckfrage", "begruendung", "textmethode",
              "dauer_s", "modell"]
    with open(csv_pfad, "w", encoding="utf-8-sig", newline="") as f:
        # Semikolon = Standard-Trennzeichen fuer deutsches Excel: die Datei
        # oeffnet sich per Doppelklick direkt in sauberen Spalten, und die
        # Kommas in den Dateinamen zerreissen nichts mehr.
        w = csv.DictWriter(f, fieldnames=felder, delimiter=";")
        w.writeheader()
        for p in plan:
            zeile = {}
            for k in felder:
                wert = str(p.get(k, ""))
                # Trennzeichen und Zeilenumbrueche aus den Werten entfernen
                wert = wert.replace(";", ",").replace("\n", " ").replace("\r", " ")
                # Einheit anhaengen, sonst deutet Excel z.B. "4.1" als Datum
                if k == "dauer_s" and wert.strip():
                    wert = f"{wert} s"
                zeile[k] = wert
            w.writerow(zeile)

    print(f"\nPlan gespeichert:\n  {json_pfad}\n  {csv_pfad}")


def neue_absender_pflegen(plan, config, config_pfad):
    """Halbautomatisches Lernen: sammelt neu gesehene, noch nicht
    vereinheitlichte Absender in config.json und zeigt sie am Ende an.
    Bereits gepflegte (jetzt bekannte) verschwinden von selbst aus der Liste."""
    gesehen = set()
    bereinigt = []
    # 1) bisher gemerkte behalten - aber solche, die inzwischen bekannt sind, raus
    for a in config.get("neue_absender", []):
        if a and not _absender_bekannt(a) and a.lower() not in gesehen:
            bereinigt.append(a)
            gesehen.add(a.lower())
    # 2) neue aus diesem Lauf ergaenzen
    for eintrag in plan:
        roh = (eintrag.get("absender_roh") or "").strip()
        if roh and not _absender_bekannt(roh) and roh.lower() not in gesehen:
            bereinigt.append(roh)
            gesehen.add(roh.lower())

    config["neue_absender"] = bereinigt
    _config_speichern(config_pfad, config)

    if bereinigt:
        print("\n" + "-" * 70)
        print("Neu gesehene Absender (noch nicht vereinheitlicht):")
        for a in bereinigt:
            print(f"  - {a}")
        print("\nTipp: Wer davon gekuerzt werden soll, in config.json unter")
        print('  "bekannte_absender" eintragen, z.B.  "bayerische motoren werke": "BMW"')
        print("  (kleiner Textausschnitt links, gewuenschte Kurzform rechts).")
        print("Die Liste 'neue_absender' raeumt sich danach von selbst auf.")


VERSCHIEBUNGSLOG_NAME = "verschiebungen.csv"


def verschiebung_loggen(ordner, von_pfad, nach_pfad):
    """Haengt eine Zeile an ein dauerhaftes, menschenlesbares Verschiebe-Log
    (verschiebungen.csv im jeweiligen Ordner) an: Zeitpunkt, Name vorher, Name
    nachher, Zielordner. Dieses Log wird - anders als das Rueckgaengig-Protokoll -
    nie automatisch geleert und haelt dauerhaft fest, was wann passiert ist."""
    pfad = os.path.join(ordner, VERSCHIEBUNGSLOG_NAME)
    neu = not os.path.exists(pfad)
    try:
        with open(pfad, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            if neu:
                w.writerow(["Zeitpunkt", "Vorher", "Nachher", "Zielordner", "Pfad"])
            w.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                os.path.basename(von_pfad),
                os.path.basename(nach_pfad),
                os.path.basename(os.path.dirname(nach_pfad)),
                os.path.abspath(nach_pfad),
            ])
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="PDF-Sortierer - Analyse & Vorschau (verschiebt nichts).")
    parser.add_argument("ordner", help="Ordner mit den PDF-Dateien")
    parser.add_argument("--model", default=STANDARD_MODELL,
                        help=f"Ollama-Modell (Standard: {STANDARD_MODELL})")
    parser.add_argument("--schwelle", type=int, default=STANDARD_SCHWELLE,
                        help="Sicherheits-Schwelle 0-100 "
                             f"(Standard: {STANDARD_SCHWELLE})")
    parser.add_argument("--limit", type=int, default=None,
                        help="Nur die ersten N PDFs verarbeiten (zum Testen)")
    args = parser.parse_args()

    if not os.path.isdir(args.ordner):
        print(f"Ordner nicht gefunden: {args.ordner}")
        sys.exit(1)

    # Kategorien + Absender aus config.json neben dem Skript laden
    global KATEGORIEN, BEKANNTE_ABSENDER, VISION_MODELL
    config, config_pfad = config_laden()
    KATEGORIEN = config["kategorien"]
    BEKANNTE_ABSENDER = config["bekannte_absender"]
    VISION_MODELL = config["vision_modell"]

    plan = analysiere_ordner(args.ordner, args.model, args.schwelle, args.limit)
    uebersicht_ausgeben(plan)
    if plan:
        plan_speichern(plan, args.ordner)
        neue_absender_pflegen(plan, config, config_pfad)


if __name__ == "__main__":
    main()
