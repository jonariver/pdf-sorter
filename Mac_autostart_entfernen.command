#!/bin/bash
# ---------------------------------------------------------------------------
# PDF-Sortierer - Waechter-Autostart auf dem Mac wieder entfernen
# ---------------------------------------------------------------------------
PLIST="$HOME/Library/LaunchAgents/com.pdfsortierer.waechter.plist"

if [ ! -f "$PLIST" ]; then
  echo "Kein Autostart eingerichtet (nichts zu tun)."
  read -n1 -s -r -p "Taste ..."; echo; exit 0
fi

launchctl unload "$PLIST" 2>/dev/null
rm -f "$PLIST"
echo "Autostart entfernt. Der Waechter startet nicht mehr automatisch."
read -n1 -s -r -p "Zum Schliessen eine Taste druecken ..."; echo
