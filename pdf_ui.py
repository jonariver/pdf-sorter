#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF-Sortierer - Grafische Oberflaeche
=====================================

Ein Fenster statt Kommandozeile. Die eigentliche Arbeit erledigen im Hintergrund
die beiden vorhandenen Skripte:
    - pdf_sortierer.py  (Analyse: Text lesen, Kategorie + Name bestimmen)
    - pdf_anwenden.py   (Ordner anlegen, umbenennen, verschieben, rueckgaengig)

Diese drei Dateien muessen im SELBEN Ordner liegen, ebenso die config.json.

Start (einmalig zum Testen, zeigt auch Fehlermeldungen):
    python .\\pdf_ui.py

Fuer den Alltag ohne schwarzes Konsolenfenster: eine Verknuepfung/Batch mit
    pythonw .\\pdf_ui.py

Voraussetzungen wie gehabt: Ollama laeuft, Modell geladen (qwen3:8b / qwen3:4b),
pip install pdfplumber requests  (tkinter ist in Python bereits enthalten).
"""

import os
import sys
import json
import time
import queue
import shutil
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pdf_sortierer as kern
import pdf_anwenden as anwenden

MODELLE = ["qwen3:4b", "qwen3:8b"]   # erstes = Standard in der Oberflaeche


# ---------------------------------------------------------------------------
# UI-ZUSTAND (merkt sich z.B. den zuletzt gewaehlten Ordner)
# ---------------------------------------------------------------------------

def _ui_state_pfad():
    return os.path.join(kern.app_verzeichnis(), "ui_einstellungen.json")


def _ui_state_laden():
    try:
        with open(_ui_state_pfad(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _ui_state_speichern(state):
    try:
        with open(_ui_state_pfad(), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# OLLAMA-STATUS  (liegt jetzt im gemeinsamen Kern; hier nur unter denselben
# Namen verfuegbar gemacht, damit der restliche Code unveraendert bleibt)
# ---------------------------------------------------------------------------

ollama_erreichbar = kern.ollama_erreichbar
ollama_modelle = kern.ollama_modelle
ollama_starten = kern.ollama_starten
ollama_warten = kern.ollama_warten


# ---------------------------------------------------------------------------
# HINTERGRUND-LOGIK (ohne UI, damit sie sich testen laesst)
# ---------------------------------------------------------------------------

def _eintrag_leer(dateiname, methode, modell, dauer, grund):
    return {"datei": dateiname, "kategorie": "?", "zielordner": "?",
            "neuer_name": dateiname, "absender_roh": "", "sicherheit": 0,
            "rueckfrage": True, "begruendung": grund, "textmethode": methode,
            "modell": modell, "dauer_s": dauer, "editiert": False}


def analyse_lauf(ordner, modell, schwelle, limit, on_datei, on_status):
    """Laeuft im Hintergrund-Thread. Nutzt die Kern-Funktionen und meldet jeden
    fertigen Eintrag ueber on_datei(i, gesamt, eintrag). Gibt den Plan zurueck."""
    config, config_pfad = kern.config_laden()
    kern.KATEGORIEN = config["kategorien"]
    kern.BEKANNTE_ABSENDER = config["bekannte_absender"]
    kern.VISION_MODELL = config.get("vision_modell", kern.STANDARD_VISION_MODELL)

    pdfs = [f for f in sorted(os.listdir(ordner)) if f.lower().endswith(".pdf")]
    if limit:
        pdfs = pdfs[:limit]
    gesamt = len(pdfs)
    plan = []

    for i, dateiname in enumerate(pdfs, 1):
        on_status(f"({i}/{gesamt}) {dateiname}")
        pfad = os.path.join(ordner, dateiname)
        t0 = time.time()
        text, methode = kern.text_aus_pdf(pfad)

        if methode == "leer":
            eintrag = _eintrag_leer(dateiname, methode, modell,
                                    round(time.time() - t0, 1),
                                    "Kein Text extrahierbar")
        else:
            try:
                daten = kern.modell_fragen(text, modell)
                kat = daten.get("kategorie", "Sonstiges")
                if kat not in kern.KATEGORIEN:
                    kat = "Sonstiges"
                sich = int(daten.get("sicherheit", 0) or 0)
                eintrag = {
                    "datei": dateiname, "kategorie": kat, "zielordner": kat,
                    "neuer_name": kern.neuen_namen_bauen(daten, dateiname),
                    "absender_roh": daten.get("absender", ""),
                    "sicherheit": sich, "rueckfrage": sich < schwelle,
                    "begruendung": daten.get("begruendung", ""),
                    "textmethode": methode, "modell": modell,
                    "dauer_s": round(time.time() - t0, 1), "editiert": False,
                }
            except Exception as e:
                eintrag = _eintrag_leer(dateiname, methode, modell,
                                        round(time.time() - t0, 1),
                                        f"Modellfehler: {e}")
        plan.append(eintrag)
        on_datei(i, gesamt, eintrag)

    kern.plan_speichern(plan, ordner)
    kern.neue_absender_pflegen(plan, config, config_pfad)
    return plan


def anwenden_lauf(ordner, plan, on_zeile):
    """Setzt den (ggf. in der UI korrigierten) Plan um. Gibt (verschoben,
    uebersprungen) zurueck. Schreibt dasselbe Protokoll wie pdf_anwenden.py."""
    belegt = set()
    protokoll = []
    verschoben = uebersprungen = 0

    for e in plan:
        kat_roh = e.get("zielordner") or e.get("kategorie") or ""
        if not kat_roh or kat_roh == "?":
            uebersprungen += 1
            on_zeile(f"uebersprungen (keine Kategorie): {e['datei']}")
            continue
        quelle = os.path.join(ordner, e["datei"])
        if not os.path.exists(quelle):
            uebersprungen += 1
            on_zeile(f"Quelle fehlt: {e['datei']}")
            continue
        # Unsichere oder von Hand geaenderte Zuordnungen behalten den
        # Originalnamen (der vorgeschlagene Name koennte die alte Kategorie tragen)
        origname_behalten = e.get("rueckfrage") or e.get("editiert")
        zielname = e["datei"] if origname_behalten else e["neuer_name"]

        kat = anwenden.ordnername_saeubern(kat_roh)
        zielordner_pfad = os.path.join(ordner, kat)
        os.makedirs(zielordner_pfad, exist_ok=True)
        ziel = anwenden.freier_zielpfad(zielordner_pfad, zielname, belegt)
        shutil.move(quelle, ziel)
        protokoll.append({"von": quelle, "nach": ziel,
                          "zeit": datetime.now().isoformat(timespec="seconds")})
        kern.verschiebung_loggen(ordner, quelle, ziel)
        verschoben += 1
        on_zeile(f"{e['datei']}  ->  {kat}\\{os.path.basename(ziel)}")

    if protokoll:
        with open(os.path.join(ordner, anwenden.PROTOKOLL_NAME),
                  "a", encoding="utf-8") as f:
            for z in protokoll:
                f.write(json.dumps(z, ensure_ascii=False) + "\n")
    return verschoben, uebersprungen


def rueckgaengig_lauf(ordner, on_zeile):
    """Nimmt den letzten Anwenden-Lauf zurueck. Gibt Anzahl zurueck."""
    prot = os.path.join(ordner, anwenden.PROTOKOLL_NAME)
    if not os.path.exists(prot):
        return 0
    with open(prot, "r", encoding="utf-8") as f:
        zeilen = [json.loads(z) for z in f if z.strip()]
    zurueck = 0
    for e in reversed(zeilen):
        von, nach = e["von"], e["nach"]
        if not os.path.exists(nach) or os.path.exists(von):
            on_zeile(f"uebersprungen: {os.path.basename(nach)}")
            continue
        os.makedirs(os.path.dirname(von), exist_ok=True)
        shutil.move(nach, von)
        zurueck += 1
    archiv = prot + ".erledigt"
    try:
        if os.path.exists(archiv):
            os.remove(archiv)
        os.replace(prot, archiv)
    except OSError:
        pass
    return zurueck


# ---------------------------------------------------------------------------
# EINSTELLUNGEN (config.json bearbeiten)
# ---------------------------------------------------------------------------

# Tokens, die fuer eine Kurzform unwichtig sind (Rechtsformen, Fuellwoerter)
_RECHTSFORMEN = {"gmbh", "ag", "mbh", "kg", "kgaa", "se", "ohg", "gbr", "ug",
                 "e.v.", "e.v", "ev", "co", "co.", "&", "a.", "g.", "a.g.",
                 "ag.", "aktiengesellschaft"}
_FUELLWOERTER = {"der", "die", "das", "und", "fuer", "für", "von", "vom",
                 "zur", "zum", "des", "den", "am"}


def kuerzel_vorschlag(name):
    """Schlaegt (muster, kurzform) fuer einen erkannten Absender vor.
    muster = kleiner Match-Ausschnitt, kurzform = Windows-tauglicher Kurzname."""
    tokens = name.split()
    behalten = []
    for t in tokens:
        low = t.lower()
        stripped = low.strip(".,")
        if low in _RECHTSFORMEN or stripped in _RECHTSFORMEN:
            continue
        if stripped in _FUELLWOERTER:
            continue
        behalten.append(t)
    if not behalten:
        behalten = tokens or [name]
    wichtig = behalten[:2]
    muster = " ".join(w.lower() for w in wichtig)
    kurzform = kern.dateiname_saeubern(" ".join(wichtig))
    return muster, kurzform


# ---------------------------------------------------------------------------
# TABELLEN-SORTIERUNG (Klick auf Spaltenkopf: auf-/absteigend)
# ---------------------------------------------------------------------------

def _tv_sort(tree, col, umgekehrt):
    def schluessel(iid):
        v = tree.item(iid, "text") if col == "#0" else tree.set(iid, col)
        try:                                   # Zahlen numerisch sortieren
            return (0, float(str(v).replace(",", ".")))
        except (ValueError, TypeError):
            return (1, str(v).lower())
    items = list(tree.get_children(""))
    items.sort(key=schluessel, reverse=umgekehrt)
    for i, iid in enumerate(items):
        tree.move(iid, "", i)
    # Beim naechsten Klick in die andere Richtung sortieren
    tree.heading(col, command=lambda: _tv_sort(tree, col, not umgekehrt))


def _sortierbar_machen(tree, spalten):
    for col in spalten:
        tree.heading(col, command=lambda c=col: _tv_sort(tree, c, False))


def _zelle_editieren(tree, event, erlaubt):
    """Macht eine Tabellenzelle per Doppelklick direkt bearbeitbar.
    'erlaubt' = Menge der editierbaren Spalten (z.B. {'#0', 'v'})."""
    if tree.identify_region(event.x, event.y) != "cell":
        return
    row = tree.identify_row(event.y)
    colid = tree.identify_column(event.x)   # '#0', '#1', ...
    if not row:
        return
    if colid == "#0":
        colname = "#0"
    else:
        idx = int(colid[1:]) - 1
        cols = tree["columns"]
        if not (0 <= idx < len(cols)):
            return
        colname = cols[idx]
    if colname not in erlaubt:
        return
    bbox = tree.bbox(row, colid)
    if not bbox:
        return
    x, y, w, h = bbox
    aktuell = tree.item(row, "text") if colname == "#0" else tree.set(row, colname)

    entry = ttk.Entry(tree)
    entry.place(x=x, y=y, width=w, height=h)
    entry.insert(0, aktuell)
    entry.focus_set()
    entry.select_range(0, "end")
    zustand = {"fertig": False}

    def commit(_=None):
        if zustand["fertig"]:
            return
        zustand["fertig"] = True
        neu = entry.get()
        if colname == "#0":
            tree.item(row, text=neu)
        else:
            tree.set(row, colname, neu)
        entry.destroy()

    def abbruch(_=None):
        if zustand["fertig"]:
            return
        zustand["fertig"] = True
        entry.destroy()

    entry.bind("<Return>", commit)
    entry.bind("<FocusOut>", commit)
    entry.bind("<Escape>", abbruch)


class DictEditor(ttk.Frame):
    """Kleine editierbare Schluessel/Wert-Tabelle."""

    def __init__(self, master, titel, key_label, val_label, daten, key_lower=False):
        super().__init__(master)
        self.key_lower = key_lower
        ttk.Label(self, text=titel, font=("", 10, "bold")).pack(anchor="w")

        rahmen = ttk.Frame(self)
        rahmen.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(rahmen, columns=("v",), show="tree headings",
                                 height=6)
        self.tree.heading("#0", text=key_label)
        self.tree.heading("v", text=val_label)
        self.tree.column("#0", width=230)
        self.tree.column("v", width=430)
        scroll = ttk.Scrollbar(rahmen, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._auswahl)
        for k, v in daten.items():
            self.tree.insert("", "end", text=k, values=(v,))
        _sortierbar_machen(self.tree, ("#0", "v"))
        self.tree.bind("<Double-1>",
                       lambda ev: _zelle_editieren(self.tree, ev, {"#0", "v"}))

        f = ttk.Frame(self)
        f.pack(fill="x", pady=4)
        ttk.Label(f, text=key_label + ":").grid(row=0, column=0, sticky="w")
        self.key_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.key_var, width=26).grid(row=0, column=1, padx=4)
        ttk.Label(f, text=val_label + ":").grid(row=0, column=2, sticky="w")
        self.val_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.val_var, width=38).grid(row=0, column=3, padx=4)
        ttk.Button(f, text="Hinzufuegen / Aendern", command=self._add).grid(
            row=0, column=4, padx=4)
        ttk.Button(f, text="Entfernen", command=self._del).grid(row=0, column=5)

    def _auswahl(self, _=None):
        sel = self.tree.selection()
        if sel:
            self.key_var.set(self.tree.item(sel[0], "text"))
            werte = self.tree.item(sel[0], "values")
            self.val_var.set(werte[0] if werte else "")

    def _add(self):
        k = self.key_var.get().strip()
        v = self.val_var.get().strip()
        if self.key_lower:
            k = k.lower()
        if not k:
            return
        self.setze(k, v)
        self.key_var.set("")
        self.val_var.set("")

    def setze(self, k, v):
        """Fuegt einen Eintrag hinzu oder aktualisiert ihn (nach Schluessel)."""
        for iid in self.tree.get_children():
            if self.tree.item(iid, "text") == k:
                self.tree.item(iid, values=(v,))
                return
        self.tree.insert("", "end", text=k, values=(v,))

    def _del(self):
        for iid in self.tree.selection():
            self.tree.delete(iid)

    def werte(self):
        return {self.tree.item(iid, "text"): self.tree.item(iid, "values")[0]
                for iid in self.tree.get_children()}


class KonfigFenster(tk.Toplevel):
    def __init__(self, master, on_save):
        super().__init__(master)
        self.title("Einstellungen - Kategorien & Absender")
        self.geometry("860x780")
        self.minsize(760, 560)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.on_save = on_save
        self.config, self.config_pfad = kern.config_laden()

        hinweis = ("Kategorien = deine Ordner (Name + kurze Beschreibung, die dem "
                   "Modell bei der Einordnung hilft).\n"
                   "Absender = Kuerzungsregeln: links ein kleiner Ausschnitt des "
                   "erkannten Namens (klein), rechts die gewuenschte Kurzform.")
        ttk.Label(self, text=hinweis, wraplength=760, padding=10).pack(anchor="w")

        self.kat_editor = DictEditor(self, "Kategorien", "Ordnername",
                                     "Beschreibung",
                                     self.config.get("kategorien", {}))
        self.kat_editor.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.abs_editor = DictEditor(self, "Bekannte Absender (Kuerzungen)",
                                     "Erkannt (klein)", "Kurzform",
                                     self.config.get("bekannte_absender", {}),
                                     key_lower=True)
        self.abs_editor.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        neu = self.config.get("neue_absender", [])
        if neu:
            box = ttk.LabelFrame(
                self, text="Neu gesehen  (Doppelklick auf 'Vorschlag': bearbeiten)",
                padding=6)
            box.pack(fill="both", expand=True, padx=10, pady=(0, 8))
            tabelle_rahmen = ttk.Frame(box)
            tabelle_rahmen.pack(fill="both", expand=True)
            self.neu_tree = ttk.Treeview(tabelle_rahmen, columns=("vorschlag",),
                                         show="tree headings", height=5)
            self.neu_tree.heading("#0", text="Erkannt")
            self.neu_tree.heading("vorschlag", text="Vorschlag (Kurzform)")
            self.neu_tree.column("#0", width=400)
            self.neu_tree.column("vorschlag", width=300)
            for a in neu:
                _, kurz = kuerzel_vorschlag(a)
                self.neu_tree.insert("", "end", text=a, values=(kurz,))
            nscroll = ttk.Scrollbar(tabelle_rahmen, orient="vertical",
                                    command=self.neu_tree.yview)
            self.neu_tree.configure(yscrollcommand=nscroll.set)
            self.neu_tree.pack(side="left", fill="both", expand=True)
            nscroll.pack(side="right", fill="y")
            _sortierbar_machen(self.neu_tree, ("#0", "vorschlag"))
            _tv_sort(self.neu_tree, "vorschlag", False)   # gleich nach Vorschlag sortiert
            self.neu_tree.bind(
                "<Double-1>",
                lambda ev: _zelle_editieren(self.neu_tree, ev, {"vorschlag"}))
            ttk.Button(box, text="Alle Vorschlaege uebernehmen",
                       command=self._vorschlaege).pack(anchor="e", pady=(4, 0))

        f = ttk.Frame(self, padding=10)
        f.pack(fill="x")
        ttk.Button(f, text="Speichern", command=self._speichern).pack(side="right")
        ttk.Button(f, text="Abbrechen", command=self.destroy).pack(side="right", padx=6)

    def _vorschlaege(self):
        eintraege = [(self.neu_tree.item(iid, "text"),
                      self.neu_tree.set(iid, "vorschlag"))
                     for iid in self.neu_tree.get_children()]
        if not eintraege:
            return
        for name, kurz in eintraege:
            muster = kuerzel_vorschlag(name)[0]   # Match-Muster bleibt automatisch
            self.abs_editor.setze(muster, kurz)
        for iid in self.neu_tree.get_children():
            self.neu_tree.delete(iid)
        messagebox.showinfo(
            "Vorschlaege uebernommen",
            f"Fuer {len(eintraege)} Absender wurden die (ggf. bearbeiteten) "
            f"Vorschlaege in die Tabelle 'Bekannte Absender' eingetragen.\n\n"
            f"Bitte pruefen, bei Bedarf anpassen und dann 'Speichern'.")

    def _speichern(self):
        kats = self.kat_editor.werte()
        if not kats:
            messagebox.showerror("Fehler",
                                 "Es muss mindestens eine Kategorie geben.")
            return
        self.config["kategorien"] = kats
        self.config["bekannte_absender"] = self.abs_editor.werte()
        kern._config_speichern(self.config_pfad, self.config)
        self.on_save(list(kats.keys()))
        messagebox.showinfo("Gespeichert", "Einstellungen wurden gespeichert.")
        self.destroy()


# ---------------------------------------------------------------------------
# OBERFLAECHE
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF-Sortierer")
        self.geometry("980x620")
        self.minsize(820, 520)

        self.plan = []                 # aktueller Plan (Liste von dicts)
        self.item_index = {}           # Treeview-Item-ID -> Index in self.plan
        self.meldungen = queue.Queue()  # Thread -> UI
        self.arbeitet = False

        try:
            self.kategorien = list(kern.config_laden()[0]["kategorien"].keys())
        except Exception:
            self.kategorien = list(kern.STANDARD_KATEGORIEN.keys())

        self._baue_oberflaeche()
        self._ordner_wiederherstellen()
        self.after(100, self._queue_abfragen)
        self.after(300, self._ollama_pruefen_beim_start)

    # ---- Aufbau ----------------------------------------------------------
    def _baue_oberflaeche(self):
        oben = ttk.Frame(self, padding=10)
        oben.pack(fill="x")

        ttk.Label(oben, text="Ordner:").grid(row=0, column=0, sticky="w")
        self.ordner_var = tk.StringVar()
        ttk.Entry(oben, textvariable=self.ordner_var, width=70).grid(
            row=0, column=1, padx=6, sticky="we")
        ttk.Button(oben, text="Durchsuchen...", command=self._ordner_waehlen).grid(
            row=0, column=2)

        ttk.Label(oben, text="Modell:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        modellzeile = ttk.Frame(oben)
        modellzeile.grid(row=1, column=1, sticky="w", padx=6, pady=(8, 0))
        self.modell_var = tk.StringVar(value=MODELLE[0])
        ttk.Combobox(modellzeile, textvariable=self.modell_var, values=MODELLE,
                     width=14, state="readonly").pack(side="left")
        self.btn_modell = ttk.Button(modellzeile, text="Modell laden",
                                     command=self._modell_laden_klick)
        self.btn_modell.pack(side="left", padx=6)

        rechts = ttk.Frame(oben)
        rechts.grid(row=1, column=1, sticky="e", pady=(8, 0))
        ttk.Label(rechts, text="Sicherheits-Schwelle:").pack(side="left")
        self.schwelle_var = tk.IntVar(value=kern.STANDARD_SCHWELLE)
        ttk.Spinbox(rechts, from_=0, to=100, width=5,
                    textvariable=self.schwelle_var).pack(side="left", padx=(4, 12))
        ttk.Label(rechts, text="Test: nur erste").pack(side="left")
        self.limit_var = tk.IntVar(value=0)
        ttk.Spinbox(rechts, from_=0, to=100000, width=6,
                    textvariable=self.limit_var).pack(side="left", padx=4)
        ttk.Label(rechts, text="(0 = alle)").pack(side="left")

        oben.columnconfigure(1, weight=1)

        knoepfe = ttk.Frame(self, padding=(10, 0))
        knoepfe.pack(fill="x")
        self.btn_analyse = ttk.Button(knoepfe, text="Analysieren",
                                      command=self._analysieren_starten)
        self.btn_analyse.pack(side="left")
        self.btn_plan_laden = ttk.Button(knoepfe, text="Plan laden",
                                         command=self._plan_laden)
        self.btn_plan_laden.pack(side="left", padx=6)
        self.btn_anwenden = ttk.Button(knoepfe, text="Anwenden",
                                       command=self._anwenden_starten, state="disabled")
        self.btn_anwenden.pack(side="left", padx=6)
        self.btn_undo = ttk.Button(knoepfe, text="Rueckgaengig",
                                   command=self._rueckgaengig_starten)
        self.btn_undo.pack(side="left")
        ttk.Button(knoepfe, text="Einstellungen...",
                   command=self._konfig_oeffnen).pack(side="left", padx=6)
        ttk.Label(knoepfe, text="  (Doppelklick auf eine Zeile: Kategorie aendern)"
                  ).pack(side="left", padx=10)

        self.fortschritt = ttk.Progressbar(self, mode="determinate")
        self.fortschritt.pack(fill="x", padx=10, pady=(8, 0))
        self.status_var = tk.StringVar(value="Bereit.")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(
            fill="x", padx=10)

        # Ergebnistabelle
        rahmen = ttk.Frame(self, padding=10)
        rahmen.pack(fill="both", expand=True)
        spalten = ("kategorie", "sicherheit", "neuer_name", "grund")
        self.tabelle = ttk.Treeview(rahmen, columns=spalten, show="tree headings")
        self.tabelle.heading("#0", text="Datei")
        self.tabelle.heading("kategorie", text="Kategorie")
        self.tabelle.heading("sicherheit", text="%")
        self.tabelle.heading("neuer_name", text="Neuer Name")
        self.tabelle.heading("grund", text="Begruendung")
        self.tabelle.column("#0", width=230)
        self.tabelle.column("kategorie", width=110)
        self.tabelle.column("sicherheit", width=40, anchor="center")
        self.tabelle.column("neuer_name", width=300)
        self.tabelle.column("grund", width=260)
        _sortierbar_machen(self.tabelle,
                           ("#0", "kategorie", "sicherheit", "neuer_name", "grund"))
        self.tabelle.tag_configure("unsicher", background="#ffe8e0")
        self.tabelle.tag_configure("editiert", background="#e3f0ff")
        self.tabelle.bind("<Double-1>", self._zeile_bearbeiten)

        scroll = ttk.Scrollbar(rahmen, orient="vertical",
                               command=self.tabelle.yview)
        self.tabelle.configure(yscrollcommand=scroll.set)
        self.tabelle.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.log = tk.Text(self, height=6, state="disabled", wrap="word")
        self.log.pack(fill="x", padx=10, pady=(0, 10))

    # ---- Hilfen ----------------------------------------------------------
    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _ordner_waehlen(self):
        pfad = filedialog.askdirectory(title="Ordner mit den PDFs waehlen")
        if pfad:
            self.ordner_var.set(pfad)
            self._ordner_merken(pfad)

    def _ordner_merken(self, pfad):
        state = _ui_state_laden()
        state["letzter_ordner"] = pfad
        _ui_state_speichern(state)

    def _ordner_wiederherstellen(self):
        pfad = _ui_state_laden().get("letzter_ordner", "")
        if pfad and os.path.isdir(pfad):
            self.ordner_var.set(pfad)

    def _ollama_pruefen_beim_start(self):
        if ollama_erreichbar():
            self.status_var.set("Bereit. (Ollama laeuft)")
        else:
            self._ollama_anbieten_start()

    def _ollama_anbieten_start(self):
        if not messagebox.askyesno(
                "Ollama laeuft nicht",
                "Ollama (die KI im Hintergrund) scheint nicht zu laufen.\n\n"
                "Soll ich versuchen, Ollama automatisch zu starten?\n"
                "Bei 'Nein' bitte Ollama selbst starten und es erneut versuchen."):
            self.status_var.set("Ollama laeuft nicht - bitte starten.")
            return
        self.status_var.set("Starte Ollama...")

        def arbeit():
            if not ollama_starten():
                self.meldungen.put(("ollama_status", "nicht_gefunden"))
                return
            ok = ollama_warten(20)
            self.meldungen.put(("ollama_status", "bereit" if ok else "timeout"))

        threading.Thread(target=arbeit, daemon=True).start()

    def _modell_laden_klick(self):
        self._modell_laden_starten(self.modell_var.get())

    def _modell_laden_starten(self, name):
        if self.arbeitet:
            return
        if not ollama_erreichbar():
            self._ollama_anbieten_start()
            return
        if kern.modell_vorhanden(name):
            messagebox.showinfo("Modell vorhanden",
                                f"'{name}' ist bereits installiert.")
            return
        self.arbeitet = True
        self.btn_analyse.configure(state="disabled")
        self.btn_modell.configure(state="disabled")
        self.fortschritt.configure(mode="determinate", value=0, maximum=100)
        self._log(f"Lade Modell '{name}' herunter (mehrere GB, das dauert)...")

        def cb(status, prozent):
            self.meldungen.put(("pull", status, prozent))

        def arbeit():
            ok = kern.modell_laden(name, fortschritt=cb)
            self.meldungen.put(("pull_fertig", name, ok))

        threading.Thread(target=arbeit, daemon=True).start()

    def _konfig_oeffnen(self):
        KonfigFenster(self, on_save=self._konfig_gespeichert)

    def _konfig_gespeichert(self, kategorien):
        self.kategorien = kategorien
        self._log("Einstellungen gespeichert (config.json aktualisiert).")

    def _plan_laden(self):
        if self.arbeitet:
            return
        ordner = self.ordner_var.get().strip()
        if not os.path.isdir(ordner):
            messagebox.showerror("Ordner fehlt",
                                 "Bitte zuerst einen gueltigen Ordner waehlen.")
            return
        plan_pfad = os.path.join(ordner, "plan.json")
        if not os.path.exists(plan_pfad):
            messagebox.showinfo(
                "Kein Plan",
                "In diesem Ordner gibt es keine plan.json.\n"
                "Bitte zuerst 'Analysieren'.")
            return
        try:
            with open(plan_pfad, "r", encoding="utf-8") as f:
                plan = json.load(f)
        except Exception as e:
            messagebox.showerror("Fehler",
                                 f"plan.json konnte nicht gelesen werden:\n{e}")
            return

        for e in plan:                       # Feld ergaenzen (aeltere Plaene)
            e.setdefault("editiert", False)

        self.plan = plan
        self._tabelle_leeren()
        for i, e in enumerate(plan):
            self._zeile_einfuegen(i, e)
        self.btn_anwenden.configure(state="normal" if plan else "disabled")

        stand = datetime.fromtimestamp(
            os.path.getmtime(plan_pfad)).strftime("%d.%m.%Y %H:%M")
        fehlen = sum(1 for e in plan
                     if not os.path.exists(os.path.join(ordner, e["datei"])))
        self.status_var.set(
            f"Plan geladen: {len(plan)} Eintrag/Eintraege (Stand {stand}).")
        self._log(f"Vorhandenen Plan geladen: {len(plan)} Eintraege "
                  f"(Stand {stand}).")
        if fehlen:
            self._log(f"ACHTUNG: {fehlen} im Plan gelistete Datei(en) liegen "
                      f"nicht mehr im Ordner - der Plan ist vermutlich veraltet.")
            messagebox.showwarning(
                "Plan evtl. veraltet",
                f"{fehlen} der {len(plan)} Dokumente aus dem Plan liegen nicht "
                f"mehr im Ordner\n(z.B. bereits verschoben oder geloescht).\n\n"
                f"Im Zweifel lieber neu analysieren.")

    def _tabelle_leeren(self):
        for iid in self.tabelle.get_children():
            self.tabelle.delete(iid)
        self.item_index.clear()

    def _zeile_einfuegen(self, index, e):
        tags = ()
        if e.get("editiert"):
            tags = ("editiert",)
        elif e.get("rueckfrage"):
            tags = ("unsicher",)
        iid = self.tabelle.insert(
            "", "end", text=e["datei"],
            values=(e["kategorie"], e["sicherheit"], e["neuer_name"],
                    e.get("begruendung", "")), tags=tags)
        self.item_index[iid] = index

    # ---- Analyse ---------------------------------------------------------
    def _analysieren_starten(self):
        ordner = self.ordner_var.get().strip()
        if not os.path.isdir(ordner):
            messagebox.showerror("Ordner fehlt",
                                 "Bitte zuerst einen gueltigen Ordner waehlen.")
            return
        if self.arbeitet:
            return
        if not ollama_erreichbar():
            self._ollama_anbieten_start()
            return
        modelle = ollama_modelle()
        if modelle and self.modell_var.get() not in modelle:
            if messagebox.askyesno(
                    "Modell nicht installiert",
                    f"Das Modell '{self.modell_var.get()}' ist noch nicht "
                    f"installiert.\n\nJetzt herunterladen? (mehrere GB, kann "
                    f"einige Minuten dauern)"):
                self._modell_laden_starten(self.modell_var.get())
            return
        self.arbeitet = True
        self._ordner_merken(ordner)
        self.plan = []
        self._tabelle_leeren()
        self.btn_analyse.configure(state="disabled")
        self.btn_anwenden.configure(state="disabled")
        self.fortschritt.configure(value=0, maximum=100)
        self._log(f"Analyse gestartet: {ordner}")

        modell = self.modell_var.get()
        schwelle = self.schwelle_var.get()
        limit = self.limit_var.get() or None

        def arbeit():
            try:
                plan = analyse_lauf(
                    ordner, modell, schwelle, limit,
                    on_datei=lambda i, g, e: self.meldungen.put(("datei", i, g, e)),
                    on_status=lambda s: self.meldungen.put(("status", s)))
                self.meldungen.put(("analyse_fertig", plan))
            except Exception as e:
                self.meldungen.put(("fehler", f"Analyse-Fehler: {e}"))

        threading.Thread(target=arbeit, daemon=True).start()

    # ---- Anwenden / Rueckgaengig ----------------------------------------
    def _anwenden_starten(self):
        ordner = self.ordner_var.get().strip()
        if not self.plan or not os.path.isdir(ordner):
            return
        sicher = sum(1 for e in self.plan
                     if e.get("zielordner") and e["zielordner"] != "?")
        if not messagebox.askyesno(
                "Anwenden",
                f"{sicher} Dokument(e) werden in Unterordner verschoben und "
                f"umbenannt.\n\nEs wird nur innerhalb des gewaehlten Ordners "
                f"verschoben. Fortfahren?"):
            return
        self.arbeitet = True
        self.btn_analyse.configure(state="disabled")
        self.btn_anwenden.configure(state="disabled")
        plan = list(self.plan)

        def arbeit():
            try:
                v, u = anwenden_lauf(
                    ordner, plan,
                    on_zeile=lambda t: self.meldungen.put(("log", t)))
                self.meldungen.put(("anwenden_fertig", v, u))
            except Exception as e:
                self.meldungen.put(("fehler", f"Anwenden-Fehler: {e}"))

        threading.Thread(target=arbeit, daemon=True).start()

    def _rueckgaengig_starten(self):
        ordner = self.ordner_var.get().strip()
        if not os.path.isdir(ordner):
            messagebox.showerror("Ordner fehlt", "Bitte zuerst einen Ordner waehlen.")
            return
        if not messagebox.askyesno(
                "Rueckgaengig",
                "Den letzten Anwenden-Lauf komplett zuruecknehmen?"):
            return
        self.arbeitet = True
        self.btn_undo.configure(state="disabled")

        def arbeit():
            try:
                n = rueckgaengig_lauf(
                    ordner, on_zeile=lambda t: self.meldungen.put(("log", t)))
                self.meldungen.put(("undo_fertig", n))
            except Exception as e:
                self.meldungen.put(("fehler", f"Rueckgaengig-Fehler: {e}"))

        threading.Thread(target=arbeit, daemon=True).start()

    # ---- Zeile bearbeiten (Kategorie aendern) ---------------------------
    def _zeile_bearbeiten(self, event):
        iid = self.tabelle.identify_row(event.y)
        if not iid or iid not in self.item_index:
            return
        idx = self.item_index[iid]
        eintrag = self.plan[idx]

        dlg = tk.Toplevel(self)
        dlg.title("Kategorie aendern")
        dlg.transient(self)
        dlg.grab_set()
        ttk.Label(dlg, text=eintrag["datei"], padding=10).pack()
        wahl = tk.StringVar(value=eintrag.get("kategorie", self.kategorien[0]))
        box = ttk.Combobox(dlg, textvariable=wahl, values=self.kategorien,
                           state="readonly", width=30)
        box.pack(padx=10)

        def uebernehmen():
            neu = wahl.get()
            eintrag["kategorie"] = neu
            eintrag["zielordner"] = neu
            eintrag["editiert"] = True
            self.tabelle.item(iid, values=(
                neu, eintrag["sicherheit"], eintrag["neuer_name"],
                eintrag.get("begruendung", "")), tags=("editiert",))
            dlg.destroy()

        knoepfe = ttk.Frame(dlg, padding=10)
        knoepfe.pack()
        ttk.Button(knoepfe, text="Uebernehmen", command=uebernehmen).pack(side="left")
        ttk.Button(knoepfe, text="Abbrechen", command=dlg.destroy).pack(side="left", padx=6)

    # ---- Meldungen aus den Threads verarbeiten --------------------------
    def _queue_abfragen(self):
        try:
            while True:
                m = self.meldungen.get_nowait()
                art = m[0]
                if art == "status":
                    self.status_var.set(m[1])
                elif art == "datei":
                    _, i, g, e = m
                    self.plan.append(e)
                    self._zeile_einfuegen(len(self.plan) - 1, e)
                    self.fortschritt.configure(maximum=g, value=i)
                elif art == "analyse_fertig":
                    self.status_var.set(
                        f"Analyse fertig: {len(self.plan)} Dokument(e). "
                        f"Bitte pruefen, dann 'Anwenden'.")
                    self.arbeitet = False
                    self.btn_analyse.configure(state="normal")
                    self.btn_anwenden.configure(
                        state="normal" if self.plan else "disabled")
                    self._log("Plan gespeichert (plan.json / plan.csv).")
                elif art == "log":
                    self._log(m[1])
                elif art == "anwenden_fertig":
                    _, v, u = m
                    self.status_var.set(f"Angewendet. Verschoben: {v}, "
                                        f"uebersprungen: {u}.")
                    self._log(f"Fertig. Verschoben: {v}, uebersprungen: {u}.")
                    self.arbeitet = False
                    self.btn_analyse.configure(state="normal")
                    self.btn_anwenden.configure(state="disabled")
                    self._tabelle_leeren()
                    self.plan = []
                elif art == "undo_fertig":
                    self.status_var.set(f"Rueckgaengig: {m[1]} Datei(en) "
                                        f"zurueckbewegt.")
                    self._log(f"Rueckgaengig: {m[1]} Datei(en).")
                    self.arbeitet = False
                    self.btn_undo.configure(state="normal")
                elif art == "ollama_status":
                    zustand = m[1]
                    if zustand == "bereit":
                        self.status_var.set("Ollama laeuft jetzt. Bereit.")
                        self._log("Ollama wurde gestartet.")
                    elif zustand == "nicht_gefunden":
                        self.status_var.set("Ollama nicht gefunden.")
                        messagebox.showwarning(
                            "Ollama nicht gefunden",
                            "Der Befehl 'ollama' wurde nicht gefunden. Bitte "
                            "installiere bzw. starte Ollama manuell (ollama.com).")
                    else:
                        self.status_var.set("Ollama antwortet noch nicht.")
                        messagebox.showwarning(
                            "Ollama startet nicht",
                            "Ollama konnte nicht rechtzeitig gestartet werden. "
                            "Bitte starte es manuell und versuche es erneut.")
                elif art == "pull":
                    _, status, prozent = m
                    if prozent is not None:
                        self.fortschritt.configure(mode="determinate",
                                                   maximum=100, value=prozent)
                        self.status_var.set(f"Modell laden: {status} ({prozent}%)")
                    else:
                        self.status_var.set(f"Modell laden: {status}")
                elif art == "pull_fertig":
                    _, name, ok = m
                    self.arbeitet = False
                    self.btn_analyse.configure(state="normal")
                    self.btn_modell.configure(state="normal")
                    self.fortschritt.configure(value=0)
                    if ok:
                        self.status_var.set(f"Modell {name} ist bereit.")
                        self._log(f"Modell {name} erfolgreich geladen.")
                    else:
                        self.status_var.set("Modell konnte nicht geladen werden.")
                        messagebox.showerror(
                            "Fehler",
                            f"Das Modell {name} konnte nicht geladen werden. "
                            f"Laeuft Ollama?")
                elif art == "fehler":
                    self.arbeitet = False
                    self.btn_analyse.configure(state="normal")
                    self.btn_undo.configure(state="normal")
                    self.status_var.set("Fehler.")
                    self._log(m[1])
                    messagebox.showerror("Fehler", m[1])
        except queue.Empty:
            pass
        self.after(100, self._queue_abfragen)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
