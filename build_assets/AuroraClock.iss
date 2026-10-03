; ============================================================
;  Aurora Clock - Windows installer script (Inno Setup 6)
; ============================================================

#define MyAppName        "Aurora Clock"
#define MyAppVersion     "1.5.0"
#define MyAppPublisher   "Aurora Software"
#define MyAppExeName     "AuroraClock.exe"
#define MyAppId          "{{9C3A7F41-6B2E-4D58-9E0A-AURORACLOCK11}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}

; Per-user install: no administrator rights, no UAC prompt, no "blocked by
; your organisation" problems. The user may still choose a machine-wide
; install from the privileges dialog.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=no
AllowNoIcons=yes

OutputDir=.
OutputBaseFilename=AuroraClock-Setup-{#MyAppVersion}
SetupIconFile=aurora.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
CloseApplications=force
CloseApplicationsFilter=*.exe
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";  Description: "Create a &desktop shortcut"; \
    GroupDescription: "Shortcuts:"
Name: "startupicon";  Description: "Start {#MyAppName} automatically when Windows starts"; \
    GroupDescription: "Startup:"; Flags: checkedonce
Name: "launchnow";    Description: "Open {#MyAppName} when setup finishes"; \
    GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "dist\AuroraClock\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\AuroraClock\_internal\*";     DestDir: "{app}\_internal"; \
    Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md";                     DestDir: "{app}"; \
    DestName: "README.md"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}";                  Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} Settings";         Filename: "{app}\{#MyAppExeName}"; \
    Parameters: "--settings"
Name: "{group}\Uninstall {#MyAppName}";        Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";            Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Registry]
; Start with Windows (per user - the correct, admin-free way)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "AuroraClock"; \
    ValueData: """{app}\{#MyAppExeName}"" --tray"; \
    Flags: uninsdeletevalue; Tasks: startupicon
; Remove the autostart entry when the task is not selected
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: none; ValueName: "AuroraClock"; \
    Flags: deletevalue uninsdeletevalue; Tasks: not startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--settings"; \
    Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent; \
    Tasks: launchnow

[UninstallRun]
; make sure the tray app is gone before files are deleted
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#MyAppExeName} /F"; \
    Flags: runhidden; RunOnceId: "KillAuroraClock"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: dirifempty;     Name: "{app}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  SettingsDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    SettingsDir := ExpandConstant('{userappdata}\AuroraClock');
    if DirExists(SettingsDir) then
    begin
      if MsgBox('Do you also want to delete your Aurora Clock settings' + #13#10 +
                '(clock layouts, themes, alarms and imported fonts)?' + #13#10 + #13#10 +
                'Choose No if you plan to reinstall later.',
                mbConfirmation, MB_YESNO) = IDYES then
        DelTree(SettingsDir, True, True, True);
    end;
  end;
end;
