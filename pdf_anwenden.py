#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF-Sortierer - Schritt 2: Plan ANWENDEN
========================================

Nimmt den geprueften Plan (plan.json), den Schritt 1 (pdf_sortierer.py) erzeugt
hat, und setzt ihn tatsaechlich um: legt die Unterordner an, benennt die PDFs um
und verschiebt sie hinein.

Eingebaute Sicherheiten:
  - Zeigt zuerst eine Zusammenfassung mit Beispielen und fragt, ob es losgehen
    soll. Ohne dein "j" passiert nichts.
  - Es wird NUR innerhalb des angegebenen Ordners in Unterordner verschoben.
  - Bei "Rueckfrage noetig"-Dokumenten wirst du gefragt, wohin sie sollen.
  - Namenskollisionen (zwei Dokumente wollen denselben Namen) bekommen _2, _3 ...
  - Jede Verschiebung wird protokolliert -> laesst sich komplett rueckgaengig
    machen.

------------------------------------------------------------
Ablauf (PowerShell)
------------------------------------------------------------
1) Erst Schritt 1 (Analyse) OHNE --limit laufen lassen und die plan.csv pruefen:
       python .\\pdf_sortierer.py "C:\\...\\ScanSnap TEST"

2) Dann anwenden:
       python .\\pdf_anwenden.py "C:\\...\\ScanSnap TEST"

3) Falls doch etwas nicht passt - alles wieder zurueck:
       python .\\pdf_anwenden.py "C:\\...\\ScanSnap TEST" --rueckgaengig
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime

PROTOKOLL_NAME = "verschiebe_protokoll.jsonl"
UNGUELTIGE_ZEICHEN = r'[\\/:*?"<>|]'


def config_kategorien(skript_dir):
    """Liest die Kategorienliste aus config.json neben dem Skript (falls da)."""
    pfad = os.path.join(skript_dir, "config.json")
    if os.path.exists(pfad):
        try:
            with open(pfad, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            kats = list(cfg.get("kategorien", {}).keys())
            if kats:
                return kats
        except Exception:
            pass
    return []


def ordnername_saeubern(name):
    """Macht aus einem Kategorienamen einen sicheren, einzelnen Ordnernamen
    (keine Pfadtrenner, kein '..' -> bleibt garantiert im Zielordner)."""
    name = re.sub(UNGUELTIGE_ZEICHEN, "", str(name)).strip().strip(".")
    return name or "Sonstiges"


def freier_zielpfad(zielordner_pfad, dateiname, belegt):
    """Gibt einen noch freien Zielpfad zurueck. Existiert der Name schon (auf
    der Platte oder bereits in diesem Lauf vergeben), wird _2, _3, ... angehaengt."""
    basis, endung = os.path.splitext(dateiname)
    kandidat = os.path.join(zielordner_pfad, dateiname)
    n = 2
    while kandidat.lower() in belegt or os.path.exists(kandidat):
        kandidat = os.path.join(zielordner_pfad, f"{basis}_{n}{endung}")
        n += 1
    belegt.add(kandidat.lower())
    return kandidat


def frage_kategorie(eintrag, kategorien):
    """Interaktive Rueckfrage bei unsicheren Dokumenten: In welche Kategorie?"""
    print("\n  Unsicheres Dokument:")
    print(f"    Datei:     {eintrag['datei']}")
    vorschlag = eintrag.get("kategorie", "?")
    if vorschlag and vorschlag != "?":
        print(f"    Vorschlag: {vorschlag} ({eintrag.get('sicherheit', 0)}%)")
    if eintrag.get("begruendung"):
        print(f"    Grund:     {eintrag['begruendung']}")
    print("    Kategorien:")
    for i, k in enumerate(kategorien, 1):
        print(f"      {i}) {k}")
    print("      s) ueberspringen (Dokument bleibt liegen)")
    while True:
        wahl = input("    Wahl (Nummer / Enter=Vorschlag / s): ").strip()
        if wahl == "" and vorschlag and vorschlag != "?":
            return vorschlag
        if wahl.lower() == "s":
            return None
        if wahl.isdigit() and 1 <= int(wahl) <= len(kategorien):
            return kategorien[int(wahl) - 1]
        print("    Bitte eine gueltige Nummer, Enter oder s eingeben.")


def anwenden(ordner, kategorien):
    plan_pfad = os.path.join(ordner, "plan.json")
    if not os.path.exists(plan_pfad):
        print(f"Keine plan.json in {ordner} gefunden.")
        print("Bitte zuerst Schritt 1 (pdf_sortierer.py) laufen lassen.")
        return
    with open(plan_pfad, "r", encoding="utf-8") as f:
        plan = json.load(f)

    # Kategorienliste: aus config.json, sonst aus dem Plan ableiten
    if not kategorien:
        kategorien = sorted({e["zielordner"] for e in plan
                             if e.get("zielordner") and e["zielordner"] != "?"})
        if "Sonstiges" not in kategorien:
            kategorien.append("Sonstiges")

    sicher = [e for e in plan if not e.get("rueckfrage")]
    unsicher = [e for e in plan if e.get("rueckfrage")]

    # ---- Zusammenfassung + Sicherheitsabfrage -----------------------------
    print("=" * 70)
    print("ANWENDEN - Zusammenfassung")
    print("=" * 70)
    ordnerliste = sorted({ordnername_saeubern(e["zielordner"]) for e in sicher
                          if e.get("zielordner") and e["zielordner"] != "?"})
    print(f"Ordner, die angelegt/genutzt werden: {', '.join(ordnerliste) or '-'}")
    print(f"Sicher zu verschieben: {len(sicher)}")
    print(f"Mit Rueckfrage:        {len(unsicher)}")
    if sicher:
        print("\nBeispiele:")
        for e in sicher[:5]:
            print(f"  {e['datei']}")
            print(f"    -> {ordnername_saeubern(e['zielordner'])}\\{e['neuer_name']}")
    print("\nEs wird NUR innerhalb dieses Ordners in Unterordner verschoben.")
    if input("\nJetzt wirklich umbenennen und verschieben? (j/n): ").strip().lower() != "j":
        print("Abgebrochen. Es wurde nichts veraendert.")
        return

    # ---- Umsetzen ---------------------------------------------------------
    belegt = set()
    protokoll = []
    zaehler = {"verschoben": 0, "uebersprungen": 0}

    def verarbeiten(eintrag, zielkategorie, zielname):
        quelle = os.path.join(ordner, eintrag["datei"])
        if not os.path.exists(quelle):
            print(f"  [!] Quelle fehlt, uebersprungen: {eintrag['datei']}")
            zaehler["uebersprungen"] += 1
            return
        zielkategorie = ordnername_saeubern(zielkategorie)
        zielordner_pfad = os.path.join(ordner, zielkategorie)
        os.makedirs(zielordner_pfad, exist_ok=True)
        ziel = freier_zielpfad(zielordner_pfad, zielname, belegt)
        shutil.move(quelle, ziel)
        protokoll.append({"von": quelle, "nach": ziel,
                          "zeit": datetime.now().isoformat(timespec="seconds")})
        zaehler["verschoben"] += 1
        print(f"  [ok] {eintrag['datei']}")
        print(f"       -> {zielkategorie}\\{os.path.basename(ziel)}")

    # zuerst die sicheren
    for e in sicher:
        verarbeiten(e, e["zielordner"], e["neuer_name"])

    # dann die unsicheren interaktiv
    for e in unsicher:
        kat = frage_kategorie(e, kategorien)
        if kat is None:
            print(f"  [--] uebersprungen: {e['datei']}")
            zaehler["uebersprungen"] += 1
            continue
        # Bei unsicheren behalten wir den ORIGINALNAMEN: der vorgeschlagene Name
        # koennte die falsche Kategorie enthalten. Wir ordnen nur ein.
        verarbeiten(e, kat, e["datei"])

    # ---- Protokoll schreiben ---------------------------------------------
    if protokoll:
        prot_pfad = os.path.join(ordner, PROTOKOLL_NAME)
        with open(prot_pfad, "a", encoding="utf-8") as f:
            for zeile in protokoll:
                f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
        print(f"\nProtokoll ergaenzt: {prot_pfad}")

    print("\n" + "-" * 70)
    print(f"Fertig. Verschoben: {zaehler['verschoben']}   "
          f"Uebersprungen: {zaehler['uebersprungen']}")
    print("Alles wieder rueckgaengig machen mit:  --rueckgaengig")


def rueckgaengig(ordner):
    prot_pfad = os.path.join(ordner, PROTOKOLL_NAME)
    if not os.path.exists(prot_pfad):
        print("Kein Protokoll gefunden - es gibt nichts rueckgaengig zu machen.")
        return
    with open(prot_pfad, "r", encoding="utf-8") as f:
        zeilen = [json.loads(z) for z in f if z.strip()]
    if not zeilen:
        print("Protokoll ist leer.")
        return

    print(f"{len(zeilen)} Verschiebung(en) werden zurueckgenommen "
          f"(Dateien wandern an ihren Ursprungsort zurueck).")
    if input("Fortfahren? (j/n): ").strip().lower() != "j":
        print("Abgebrochen.")
        return

    zurueck = 0
    for e in reversed(zeilen):          # in umgekehrter Reihenfolge
        von, nach = e["von"], e["nach"]
        if not os.path.exists(nach):
            print(f"  [!] Datei nicht mehr am Zielort: {nach}")
            continue
        if os.path.exists(von):
            print(f"  [!] Original existiert bereits, uebersprungen: {von}")
            continue
        os.makedirs(os.path.dirname(von), exist_ok=True)
        shutil.move(nach, von)
        zurueck += 1

    # Protokoll nach dem Zuruecknehmen archivieren, damit es nicht doppelt wirkt
    archiv = prot_pfad + ".erledigt"
    try:
        if os.path.exists(archiv):
            os.remove(archiv)
        os.replace(prot_pfad, archiv)
    except OSError:
        pass
    print(f"\nZurueckgenommen: {zurueck}. "
          f"Protokoll archiviert als {os.path.basename(archiv)}.")


def main():
    parser = argparse.ArgumentParser(
        description="PDF-Sortierer - geprueften Plan anwenden (verschieben & umbenennen).")
    parser.add_argument("ordner", help="Ordner mit plan.json und den PDFs")
    parser.add_argument("--rueckgaengig", action="store_true",
                        help="Letzten Anwenden-Lauf komplett zuruecknehmen")
    args = parser.parse_args()

    if not os.path.isdir(args.ordner):
        print(f"Ordner nicht gefunden: {args.ordner}")
        sys.exit(1)

    skript_dir = os.path.dirname(os.path.abspath(__file__))

    if args.rueckgaengig:
        rueckgaengig(args.ordner)
    else:
        anwenden(args.ordner, config_kategorien(skript_dir))


if __name__ == "__main__":
    main()
