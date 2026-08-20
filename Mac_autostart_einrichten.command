#!/bin/bash
# ---------------------------------------------------------------------------
# PDF-Sortierer - Waechter-Autostart auf dem Mac einrichten
# Legt einen LaunchAgent an, der den Waechter bei jeder Anmeldung startet.
# (Das Autostart-Haekchen im Programm ist Windows-only; auf dem Mac uebernimmt
#  das dieser LaunchAgent.)
# ---------------------------------------------------------------------------
cd "$(dirname "$0")" || exit 1
REPO="$(pwd)"
PY="$REPO/.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "FEHLER: Umgebung fehlt. Bitte zuerst 'Mac_einrichten.command' ausfuehren."
  read -n1 -s -r -p "Taste ..."; echo; exit 1
fi

AGENTS="$HOME/Library/LaunchAgents"
PLIST="$AGENTS/com.pdfsortierer.waechter.plist"
mkdir -p "$AGENTS"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.pdfsortierer.waechter</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$REPO/pdf_watcher_ui.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$REPO</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null
if launchctl load "$PLIST"; then
  echo "Autostart eingerichtet."
  echo "Der Waechter startet ab jetzt bei jeder Anmeldung."
  echo "Zum Entfernen: Mac_autostart_entfernen.command"
else
  echo "FEHLER: LaunchAgent konnte nicht geladen werden."
fi
read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo
