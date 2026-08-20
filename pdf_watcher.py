#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF-Sortierer - Ordnerueberwachung (Dauerbetrieb)
=================================================

Beobachtet einen Ordner (z.B. den ScanSnap-Ausgabeordner). Sobald ein neues,
fertig geschriebenes PDF auftaucht:
  - wird es analysiert,
  - bei HOHER Sicherheit automatisch umbenannt und in den passenden Unterordner
    verschoben,
  - bei Unsicherheit bleibt es liegen  -> du sortierst es spaeter in der
    Oberflaeche (pdf_ui.py) per Hand.

Jede automatische Verschiebung landet im selben Protokoll wie das Anwenden-
Skript, ist also per  pdf_anwenden.py --rueckgaengig  (oder dem Rueckgaengig-
Knopf in der Oberflaeche) umkehrbar.

Diese Datei gehoert in denselben Ordner wie pdf_sortierer.py / pdf_anwenden.py.

------------------------------------------------------------
Aufruf (PowerShell)
------------------------------------------------------------
    python .\\pdf_watcher.py "C:\\Users\\DeinName\\...\\ScanSnap Ausgabe"

Optionen:
    --modell qwen3:8b     genaueres Modell fuers unbeaufsichtigte Sortieren
    --schwelle 90         erst ab dieser Sicherheit automatisch verschieben
    --intervall 20        alle 20 Sekunden nachschauen (Standard: 15)
    --nur-melden          NICHTS verschieben, nur anzeigen was passieren wuerde
                          (zum gefahrlosen Beobachten)

Beenden: Strg + C
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime

import pdf_sortierer as kern
import pdf_anwenden as anwenden


def verarbeite_pdf(ordner, dateiname, modell, schwelle, nur_melden):
    """Analysiert eine Datei und (falls sicher genug) verschiebt sie.
    Gibt (status, info, absender_roh) zurueck.
    status: 'verschoben' | 'wuerde' | 'unsicher' | 'fehler'"""
    pfad = os.path.join(ordner, dateiname)
    text, methode = kern.text_aus_pdf(pfad)
    if methode == "leer":
        return "unsicher", "kein Text lesbar (Bild-Scan ohne OCR?)", ""
    try:
        daten = kern.modell_fragen(text, modell)
    except Exception as e:
        return "fehler", str(e), ""

    absender = daten.get("absender", "")
    kat = daten.get("kategorie", "Sonstiges")
    if kat not in kern.KATEGORIEN:
        kat = "Sonstiges"
    sich = int(daten.get("sicherheit", 0) or 0)

    if sich < schwelle:
        return "unsicher", f"{kat} nur {sich}% (< {schwelle}%)", absender

    neuer_name = kern.neuen_namen_bauen(daten, dateiname)
    zielkat = anwenden.ordnername_saeubern(kat)

    if nur_melden:
        return "wuerde", f"{zielkat}\\{neuer_name}  ({sich}%)", absender

    zielordner = os.path.join(ordner, zielkat)
    os.makedirs(zielordner, exist_ok=True)
    ziel = anwenden.freier_zielpfad(zielordner, neuer_name, set())
    shutil.move(pfad, ziel)
    with open(os.path.join(ordner, anwenden.PROTOKOLL_NAME),
              "a", encoding="utf-8") as f:
        f.write(json.dumps(
            {"von": pfad, "nach": ziel,
             "zeit": datetime.now().isoformat(timespec="seconds")},
            ensure_ascii=False) + "\n")
    kern.verschiebung_loggen(ordner, pfad, ziel)
    return "verschoben", f"{zielkat}\\{os.path.basename(ziel)}  ({sich}%)", absender


def _absender_merken(config, config_pfad, absender):
    """Neu gesehene, unbekannte Absender fuer die Oberflaeche sammeln."""
    if not absender or kern._absender_bekannt(absender):
        return
    bekannt = {a.lower() for a in config.get("neue_absender", [])}
    if absender.lower() not in bekannt:
        config.setdefault("neue_absender", []).append(absender)
        kern._config_speichern(config_pfad, config)


def main():
    parser = argparse.ArgumentParser(
        description="PDF-Sortierer - Ordnerueberwachung (Dauerbetrieb).")
    parser.add_argument("ordner", help="zu ueberwachender Ordner")
    parser.add_argument("--modell", default=kern.STANDARD_MODELL,
                        help=f"Ollama-Modell (Standard: {kern.STANDARD_MODELL})")
    parser.add_argument("--schwelle", type=int, default=85,
                        help="ab dieser Sicherheit automatisch verschieben "
                             "(Standard: 85)")
    parser.add_argument("--intervall", type=int, default=15,
                        help="Sekunden zwischen zwei Kontrollen (Standard: 15)")
    parser.add_argument("--nur-melden", dest="nur_melden", action="store_true",
                        help="nichts verschieben, nur anzeigen")
    args = parser.parse_args()

    if not os.path.isdir(args.ordner):
        print(f"Ordner nicht gefunden: {args.ordner}")
        sys.exit(1)

    config, config_pfad = kern.config_laden()
    kern.KATEGORIEN = config["kategorien"]
    kern.BEKANNTE_ABSENDER = config["bekannte_absender"]
    kern.VISION_MODELL = config.get("vision_modell", kern.STANDARD_VISION_MODELL)

    print(f"Ueberwache: {args.ordner}")
    print(f"Modell: {args.modell} | Auto-Schwelle: {args.schwelle}% | "
          f"Intervall: {args.intervall}s"
          + ("  | NUR-MELDEN (nichts wird verschoben)" if args.nur_melden else ""))
    print("Sichere neue Scans werden automatisch einsortiert, unsichere bleiben "
          "liegen.\nBeenden mit Strg + C.\n" + "-" * 70)

    groessen = {}      # dateiname -> zuletzt gesehene Groesse (Stabilitaetscheck)
    erledigt = set()   # schon behandelte (unsichere/fehlerhafte) Dateien

    try:
        while True:
            try:
                aktuelle = {f for f in os.listdir(args.ordner)
                            if f.lower().endswith(".pdf")}
            except OSError:
                aktuelle = set()

            for f in sorted(aktuelle):
                pfad = os.path.join(args.ordner, f)
                try:
                    groesse = os.path.getsize(pfad)
                except OSError:
                    continue
                vorher = groessen.get(f)
                groessen[f] = groesse
                if f in erledigt:
                    continue
                # Erst verarbeiten, wenn die Datei "stabil" ist (Groesse
                # zwischen zwei Runden unveraendert -> Scan fertig geschrieben)
                if vorher is None or vorher != groesse or groesse == 0:
                    continue

                status, info, absender = verarbeite_pdf(
                    args.ordner, f, args.modell, args.schwelle, args.nur_melden)
                stempel = datetime.now().strftime("%H:%M:%S")
                if status == "verschoben":
                    print(f"[{stempel}] OK    {f}\n              -> {info}")
                    _absender_merken(config, config_pfad, absender)
                elif status == "wuerde":
                    print(f"[{stempel}] WUERDE {f}\n              -> {info}")
                    _absender_merken(config, config_pfad, absender)
                    erledigt.add(f)      # im Nur-Melden-Modus nicht wiederholen
                elif status == "unsicher":
                    print(f"[{stempel}] ??    {f}  (bleibt liegen: {info})")
                    _absender_merken(config, config_pfad, absender)
                    erledigt.add(f)
                else:
                    print(f"[{stempel}] FEHLER {f}: {info}")
                    erledigt.add(f)

            # verschwundene Dateien vergessen (verschoben/geloescht)
            for f in list(groessen):
                if f not in aktuelle:
                    groessen.pop(f, None)
                    erledigt.discard(f)

            time.sleep(args.intervall)
    except KeyboardInterrupt:
        print("\nUeberwachung beendet.")


if __name__ == "__main__":
    main()
