#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF-Sortierer - Waechter mit Oberflaeche (Dauerbetrieb)
=======================================================

Ein kleines Fenster, das den ScanSnap-Ordner ueberwacht und neue, sichere Scans
automatisch einsortiert. Man sieht, ob er laeuft, kann ihn starten/stoppen und
einstellen, dass er beim Windows-Start automatisch mitlaeuft. Beim Start prueft
er, ob Ollama laeuft, und versucht es sonst selbst zu starten.

Gehoert in denselben Ordner wie pdf_sortierer.py / pdf_anwenden.py / pdf_watcher.py.
Start:  python .\\pdf_watcher_ui.py     (oder als gebaute PDF-Waechter.exe)
"""

import os
import sys
import json
import time
import queue
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pdf_sortierer as kern
import pdf_watcher as watch

MODELLE = ["qwen3:4b", "qwen3:8b"]
AUTOSTART_NAME = "PDF-Waechter"


# ---------------------------------------------------------------------------
# EINSTELLUNGEN (eigener kleiner Zustand neben der App)
# ---------------------------------------------------------------------------

def _state_pfad():
    return os.path.join(kern.app_verzeichnis(), "watcher_einstellungen.json")


def _state_laden():
    try:
        with open(_state_pfad(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _state_speichern(state):
    try:
        with open(_state_pfad(), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# WINDOWS-AUTOSTART (Registry Run-Key)
# ---------------------------------------------------------------------------

def _startbefehl():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    return f'"{pyw}" "{os.path.abspath(__file__)}"'


def autostart_setzen(an):
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        if an:
            winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, _startbefehl())
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def autostart_aktiv():
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run")
        try:
            winreg.QueryValueEx(key, AUTOSTART_NAME)
            da = True
        except FileNotFoundError:
            da = False
        winreg.CloseKey(key)
        return da
    except Exception:
        return False


# ---------------------------------------------------------------------------
# OBERFLAECHE
# ---------------------------------------------------------------------------

class Waechter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF-Waechter")
        self.geometry("720x520")
        self.minsize(640, 460)

        self.meldungen = queue.Queue()
        self.stop_event = None
        self.thread = None
        self.laeuft = False

        self._baue_oberflaeche()
        self._zustand_laden()
        self.after(100, self._queue_abfragen)
        self.protocol("WM_DELETE_WINDOW", self._schliessen)

        # Beim Programmstart sofort ueberwachen, wenn gewuenscht und ein
        # gueltiger Ordner gemerkt ist (egal ob manuell oder per Windows-Autostart)
        if self.sofort_var.get() and os.path.isdir(self.ordner_var.get().strip()):
            self.after(1500, self._start)

    # ---- Aufbau ----------------------------------------------------------
    def _baue_oberflaeche(self):
        oben = ttk.Frame(self, padding=10)
        oben.pack(fill="x")

        ttk.Label(oben, text="Ueberwachter Ordner:").grid(row=0, column=0, sticky="w")
        self.ordner_var = tk.StringVar()
        ttk.Entry(oben, textvariable=self.ordner_var, width=58).grid(
            row=0, column=1, padx=6, sticky="we")
        self.btn_durch = ttk.Button(oben, text="Durchsuchen...",
                                    command=self._ordner_waehlen)
        self.btn_durch.grid(row=0, column=2)
        oben.columnconfigure(1, weight=1)

        zeile2 = ttk.Frame(oben)
        zeile2.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(zeile2, text="Modell:").pack(side="left")
        self.modell_var = tk.StringVar(value=MODELLE[0])   # 4b = laeuft auch auf schwaecheren Rechnern
        self.cb_modell = ttk.Combobox(zeile2, textvariable=self.modell_var,
                                      values=MODELLE, width=12, state="readonly")
        self.cb_modell.pack(side="left", padx=(4, 12))
        ttk.Label(zeile2, text="Auto-Schwelle:").pack(side="left")
        self.schwelle_var = tk.IntVar(value=85)
        self.sp_schwelle = ttk.Spinbox(zeile2, from_=0, to=100, width=5,
                                       textvariable=self.schwelle_var)
        self.sp_schwelle.pack(side="left", padx=(4, 12))
        ttk.Label(zeile2, text="Intervall (s):").pack(side="left")
        self.intervall_var = tk.IntVar(value=15)
        self.sp_intervall = ttk.Spinbox(zeile2, from_=3, to=600, width=5,
                                        textvariable=self.intervall_var)
        self.sp_intervall.pack(side="left", padx=(4, 12))
        self.nur_melden_var = tk.BooleanVar(value=False)
        self.cb_melden = ttk.Checkbutton(
            zeile2, text="Nur melden (nichts verschieben)",
            variable=self.nur_melden_var)
        self.cb_melden.pack(side="left")

        # Statuszeile + Knoepfe
        leiste = ttk.Frame(self, padding=(10, 0))
        leiste.pack(fill="x")
        self.status_lampe = tk.Label(leiste, text="\u25CF gestoppt",
                                     fg="#b00000", font=("", 11, "bold"))
        self.status_lampe.pack(side="left")
        self.btn_start = ttk.Button(leiste, text="Start", command=self._start)
        self.btn_start.pack(side="right")
        self.btn_stop = ttk.Button(leiste, text="Stopp", command=self._stop,
                                   state="disabled")
        self.btn_stop.pack(side="right", padx=6)

        opt = ttk.Frame(self, padding=(10, 6))
        opt.pack(fill="x")
        self.autostart_var = tk.BooleanVar(value=autostart_aktiv())
        ttk.Checkbutton(opt, text="Beim Windows-Start automatisch mitlaufen",
                        variable=self.autostart_var,
                        command=self._autostart_umschalten).pack(side="left")
        self.sofort_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text="Beim Programmstart sofort ueberwachen",
                        variable=self.sofort_var,
                        command=self._zustand_speichern).pack(side="left", padx=(16, 0))

        opt2 = ttk.Frame(self, padding=(10, 0))
        opt2.pack(fill="x")
        self.speicher_frei_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opt2,
            text="Speicher nach der Arbeit freigeben  "
                 "(spart RAM/VRAM; jedes neue Dokument laedt das Modell neu - "
                 "auf schwachen Rechnern lieber aus)",
            variable=self.speicher_frei_var,
            command=self._zustand_speichern).pack(side="left")

        rahmen = ttk.Frame(self, padding=10)
        rahmen.pack(fill="both", expand=True)
        ttk.Label(rahmen, text="Aktivitaet:").pack(anchor="w")
        self.log = tk.Text(rahmen, height=12, state="disabled", wrap="word")
        scroll = ttk.Scrollbar(rahmen, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ---- Hilfen ----------------------------------------------------------
    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _ordner_waehlen(self):
        p = filedialog.askdirectory(title="Zu ueberwachenden Ordner waehlen")
        if p:
            self.ordner_var.set(p)

    def _eingaben_sperren(self, gesperrt):
        z = "disabled" if gesperrt else "normal"
        for w in (self.btn_durch, self.cb_modell, self.sp_schwelle,
                  self.sp_intervall, self.cb_melden):
            try:
                w.configure(state=z if w not in (self.cb_modell,)
                            else ("disabled" if gesperrt else "readonly"))
            except tk.TclError:
                pass

    def _zustand_laden(self):
        st = _state_laden()
        if os.path.isdir(st.get("ordner", "")):
            self.ordner_var.set(st["ordner"])
        if st.get("modell") in MODELLE:
            self.modell_var.set(st["modell"])
        if isinstance(st.get("schwelle"), int):
            self.schwelle_var.set(st["schwelle"])
        if isinstance(st.get("intervall"), int):
            self.intervall_var.set(st["intervall"])
        self.nur_melden_var.set(bool(st.get("nur_melden", False)))
        self.sofort_var.set(bool(st.get("sofort", True)))
        self.speicher_frei_var.set(bool(st.get("speicher_frei", False)))

    def _zustand_speichern(self):
        _state_speichern({
            "ordner": self.ordner_var.get().strip(),
            "modell": self.modell_var.get(),
            "schwelle": self.schwelle_var.get(),
            "intervall": self.intervall_var.get(),
            "nur_melden": self.nur_melden_var.get(),
            "sofort": self.sofort_var.get(),
            "speicher_frei": self.speicher_frei_var.get(),
        })

    def _autostart_umschalten(self):
        an = self.autostart_var.get()
        ok = autostart_setzen(an)
        if not ok:
            self.autostart_var.set(autostart_aktiv())
            messagebox.showwarning(
                "Autostart",
                "Der Autostart konnte nicht gesetzt werden (nur unter Windows "
                "moeglich).")
            return
        self._zustand_speichern()
        self._log("Autostart " + ("aktiviert." if an else "deaktiviert."))

    # ---- Start / Stopp ---------------------------------------------------
    def _start(self):
        if self.laeuft:
            return
        ordner = self.ordner_var.get().strip()
        if not os.path.isdir(ordner):
            messagebox.showerror("Ordner fehlt",
                                 "Bitte zuerst einen gueltigen Ordner waehlen.")
            return
        self._zustand_speichern()
        self.laeuft = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self._eingaben_sperren(True)
        self.status_lampe.configure(text="\u25CF startet...", fg="#b08000")

        self.stop_event = threading.Event()
        args = (ordner, self.modell_var.get(), self.schwelle_var.get(),
                max(3, self.intervall_var.get()), self.nur_melden_var.get(),
                self.speicher_frei_var.get(), self.stop_event)
        self.thread = threading.Thread(target=self._loop, args=args, daemon=True)
        self.thread.start()

    def _stop(self):
        if self.stop_event:
            self.stop_event.set()
        self.status_lampe.configure(text="\u25CF stoppt...", fg="#b08000")
        self.btn_stop.configure(state="disabled")

    def _schliessen(self):
        if self.laeuft:
            if not messagebox.askyesno(
                    "Beenden",
                    "Der Waechter laeuft noch. Wirklich beenden?\n"
                    "(Neue Scans werden dann nicht mehr automatisch einsortiert.)"):
                return
            if self.stop_event:
                self.stop_event.set()
        self.destroy()

    # ---- Ueberwachungs-Schleife (Hintergrund-Thread) --------------------
    def _loop(self, ordner, modell, schwelle, intervall, nur_melden, speicher_frei, stop_event):
        def log(t):
            self.meldungen.put(("log", t))

        # 1) Ollama sicherstellen
        log("Starte - pruefe, ob Ollama laeuft...")
        if kern.ollama_erreichbar():
            log("Ollama laeuft.")
        else:
            log("Ollama laeuft nicht - versuche, es zu starten...")
            kern.ollama_starten()
            bereit = False
            for i in range(30):
                if kern.ollama_erreichbar(timeout=1):
                    bereit = True
                    break
                if i in (4, 9, 14, 19, 24):
                    log(f"  warte auf Ollama... ({i + 1}s)")
                time.sleep(1)
            if bereit:
                log("Ollama laeuft jetzt.")
            else:
                log("Ollama noch nicht erreichbar - bitte ggf. manuell starten. "
                    "Ich ueberwache trotzdem weiter.")

        # 2) Modell vorhanden? sonst herunterladen
        if kern.ollama_erreichbar():
            log(f"Pruefe Modell {modell}...")
            if kern.modell_vorhanden(modell):
                log("Modell ist vorhanden.")
            else:
                log(f"Modell {modell} fehlt - lade es herunter. Das sind "
                    f"mehrere GB und kann einige Minuten dauern...")
                stand = {"status": "", "prozent": -5}

                def cb(status, prozent):
                    if status and status != stand["status"]:
                        stand["status"] = status
                        log(f"  {status}")
                    if prozent is not None and prozent >= stand["prozent"] + 5:
                        stand["prozent"] = prozent - (prozent % 5)
                        log(f"  ... {prozent}%")

                if kern.modell_laden(modell, fortschritt=cb):
                    log("Modell geladen.")
                else:
                    log("Modell konnte nicht geladen werden - es wird spaeter "
                        "Fehler bei der Verarbeitung geben.")

        # 3) Konfiguration
        log("Lese Konfiguration...")
        config, config_pfad = kern.config_laden()
        kern.KATEGORIEN = config["kategorien"]
        kern.BEKANNTE_ABSENDER = config["bekannte_absender"]

        groessen, erledigt = {}, set()
        fehler_zaehler = {}       # datei -> Anzahl bisheriger (evtl. transienter) Fehler
        benutzt_gesamt = False    # wurde das Modell ueberhaupt jemals gebraucht?
        self.meldungen.put(("status", "laeuft"))
        log(f"Ueberwachung aktiv: {ordner}"
            + ("   [NUR MELDEN]" if nur_melden else ""))

        while not stop_event.is_set():
            try:
                aktuelle = {f for f in os.listdir(ordner)
                            if f.lower().endswith(".pdf")}
            except OSError:
                aktuelle = set()

            benutzt_zyklus = False   # wurde in diesem Durchlauf etwas verarbeitet?

            for f in sorted(aktuelle):
                if stop_event.is_set():
                    break
                pfad = os.path.join(ordner, f)
                try:
                    groesse = os.path.getsize(pfad)
                except OSError:
                    continue
                vorher = groessen.get(f)
                groessen[f] = groesse
                if f in erledigt:
                    continue
                if vorher is None or vorher != groesse or groesse == 0:
                    continue   # noch nicht stabil (Scan wird evtl. geschrieben)

                # Ein neues, stabiles Dokument ist da: erst JETZT wird das Modell
                # tatsaechlich gebraucht (und von Ollama in den Speicher geladen).
                benutzt_zyklus = True
                benutzt_gesamt = True
                status, info, absender = watch.verarbeite_pdf(
                    ordner, f, modell, schwelle, nur_melden)
                stempel = datetime.now().strftime("%H:%M:%S")
                if status == "verschoben":
                    self.meldungen.put(("log", f"[{stempel}] OK    {f}\n"
                                        f"            -> {info}"))
                    watch._absender_merken(config, config_pfad, absender)
                    fehler_zaehler.pop(f, None)
                elif status == "wuerde":
                    self.meldungen.put(("log", f"[{stempel}] WUERDE {f}\n"
                                        f"            -> {info}"))
                    watch._absender_merken(config, config_pfad, absender)
                    erledigt.add(f)
                elif status == "unsicher":
                    self.meldungen.put(("log", f"[{stempel}] ??    {f}  "
                                        f"(bleibt liegen: {info})"))
                    watch._absender_merken(config, config_pfad, absender)
                    erledigt.add(f)
                else:   # fehler - oft nur voruebergehend (z.B. Ollama nicht bereit)
                    n = fehler_zaehler.get(f, 0) + 1
                    fehler_zaehler[f] = n
                    if n >= 3:
                        self.meldungen.put((
                            "log", f"[{stempel}] FEHLER {f}: {info} "
                            f"(gebe nach {n} Versuchen auf)"))
                        erledigt.add(f)
                    else:
                        self.meldungen.put((
                            "log", f"[{stempel}] FEHLER {f}: {info} "
                            f"(Versuch {n} - probiere es gleich erneut)"))

            for f in list(groessen):
                if f not in aktuelle:
                    groessen.pop(f, None)
                    erledigt.discard(f)
                    fehler_zaehler.pop(f, None)

            # Wenn gewuenscht und in diesem Durchlauf gearbeitet wurde: Modell
            # wieder aus dem Speicher entladen, um RAM/VRAM freizugeben (auf
            # schwachen Rechnern besser aus, weil sonst jedes Dokument neu laedt).
            if benutzt_zyklus and speicher_frei:
                if kern.modell_entladen(modell):
                    log("Modell aus dem Speicher entladen (frei bis zum "
                        "naechsten Dokument).")

            # in 1-Sekunden-Schritten warten, damit Stopp schnell wirkt
            for _ in range(intervall):
                if stop_event.is_set():
                    break
                time.sleep(1)

        # Beim Stoppen ebenfalls entladen, falls die Option aktiv ist
        if benutzt_gesamt and speicher_frei:
            kern.modell_entladen(modell)
        self.meldungen.put(("status", "gestoppt"))

    # ---- Meldungen verarbeiten ------------------------------------------
    def _queue_abfragen(self):
        try:
            while True:
                m = self.meldungen.get_nowait()
                if m[0] == "log":
                    self._log(m[1])
                elif m[0] == "status":
                    if m[1] == "laeuft":
                        self.status_lampe.configure(text="\u25CF laeuft",
                                                    fg="#0a7a0a")
                    elif m[1] == "gestoppt":
                        self.laeuft = False
                        self.status_lampe.configure(text="\u25CF gestoppt",
                                                    fg="#b00000")
                        self.btn_start.configure(state="normal")
                        self.btn_stop.configure(state="disabled")
                        self._eingaben_sperren(False)
                        self._log("Ueberwachung gestoppt.")
        except queue.Empty:
            pass
        self.after(200, self._queue_abfragen)


def main():
    app = Waechter()
    app.mainloop()


if __name__ == "__main__":
    main()
