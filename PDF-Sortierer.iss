; ============================================================
;  PDF-Sortierer - Installer-Skript (Inno Setup 6.1 oder neuer)
;  ----------------------------------------------------------
;  Baut eine Setup.exe, die installiert:
;    - PDF-Sortierer.exe (Oberflaeche) und PDF-Waechter.exe (Waechter)
;    - Verknuepfungen im Startmenue und optional auf dem Desktop
;    - optional den Waechter-Autostart (Windows-Anmeldung)
;    - optional Ollama: wird bei Bedarf WAEHREND der Installation direkt
;      von ollama.com heruntergeladen und still installiert
;      (kein manuelles Vorab-Herunterladen noetig; Internet erforderlich)
;
;  VORHER bauen (mit den .bat-Dateien):
;    dist\PDF-Sortierer.exe   und   dist\PDF-Waechter.exe
;
;  Bauen: diese Datei mit Inno Setup oeffnen und auf "Compile" klicken
;         (oder Installer_bauen.bat / Alles_bauen.bat doppelklicken).
;         Benoetigt Inno Setup 6.1+ (wegen der eingebauten Download-Funktion).
;  Ergebnis:  Output\PDF-Sortierer-Setup.exe
; ============================================================

#define AppName "PDF-Sortierer"
#define AppVersion "1.0"
#define Publisher "jonariver"
#define AppURL "https://github.com/jonariver/pdf-sorter"
; Stabiler Direktlink; leitet automatisch auf die aktuelle Ollama-Version weiter.
; Falls Ollama den Link aendert, hier eine versionierte GitHub-Release-URL eintragen,
; z.B. https://github.com/ollama/ollama/releases/download/v0.32.5/OllamaSetup.exe
#define OllamaURL "https://ollama.com/download/OllamaSetup.exe"

[Setup]
AppId={{B8F3B4B0-7C2E-4E9A-9F1D-2A6C5E7D8901}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputBaseFilename=PDF-Sortierer-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Kein Administrator noetig - alles im Benutzerprofil (dort ist die App auch
; schreibberechtigt fuer ihre config.json).
PrivilegesRequired=lowest

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung fuer den PDF-Sortierer anlegen"; GroupDescription: "Verknuepfungen:"
Name: "watcherautostart"; Description: "PDF-Waechter beim Windows-Start automatisch mitlaufen lassen"; GroupDescription: "Dauerbetrieb:"; Flags: unchecked
Name: "installollama"; Description: "Ollama (die KI im Hintergrund) herunterladen und installieren, falls noch nicht vorhanden"; GroupDescription: "KI-Komponente:"

[Files]
Source: "dist\PDF-Sortierer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\PDF-Waechter.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\PDF-Sortierer"; Filename: "{app}\PDF-Sortierer.exe"
Name: "{group}\PDF-Waechter"; Filename: "{app}\PDF-Waechter.exe"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PDF-Sortierer"; Filename: "{app}\PDF-Sortierer.exe"; Tasks: desktopicon

[Registry]
; Waechter beim Windows-Start automatisch mitlaufen lassen (pro Benutzer)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "PDF-Waechter"; \
    ValueData: """{app}\PDF-Waechter.exe"""; \
    Tasks: watcherautostart; Flags: uninsdeletevalue

[Run]
; Das heruntergeladene Ollama-Setup still ausfuehren (nur wenn es geladen wurde)
Filename: "{tmp}\OllamaSetup.exe"; Parameters: "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART"; \
    StatusMsg: "Ollama wird installiert (das kann einen Moment dauern)..."; \
    Check: OllamaHeruntergeladen; Flags: waituntilterminated
; Am Ende optional den PDF-Sortierer starten
Filename: "{app}\PDF-Sortierer.exe"; Description: "PDF-Sortierer jetzt starten"; \
    Flags: nowait postinstall skipifsilent

[Messages]
; Kurzer Hinweis auf der Abschluss-Seite
de.FinishedLabel=Die Installation ist abgeschlossen.%n%nBeim ERSTEN Start laedt das Programm bei Bedarf das KI-Modell herunter (mehrere GB) - dafuer wird einmalig Internet benoetigt. Danach arbeitet alles lokal.

[Code]
var
  DownloadPage: TDownloadWizardPage;

function OllamaInstalliert(): Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'));
end;

function OllamaHeruntergeladen(): Boolean;
begin
  Result := FileExists(ExpandConstant('{tmp}\OllamaSetup.exe'));
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing),
    SetupMessage(msgPreparingDesc), @OnDownloadProgress);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpReady) and WizardIsTaskSelected('installollama')
     and (not OllamaInstalliert()) then
  begin
    DownloadPage.Clear;
    DownloadPage.Add('{#OllamaURL}', 'OllamaSetup.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
      except
        if DownloadPage.AbortedByUser then
          Result := False
        else
        begin
          SuppressibleMsgBox(
            'Ollama konnte nicht heruntergeladen werden (kein Internet?).' + #13#10 +
            'Die Programme werden trotzdem installiert. Bitte Ollama spaeter' + #13#10 +
            'manuell von ollama.com installieren.',
            mbInformation, MB_OK, IDOK);
          Result := True;
        end;
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;
