; Windows installer. Build with: iscc packaging\windows\vth.iss
; Expects the PyInstaller output in dist\VTH and the version in VTH_VERSION.

#define AppVersion GetEnv("VTH_VERSION")

[Setup]
AppId={{61C23AAA-4067-43A7-87C3-E53FF7AC427E}
AppName=Voice to Hotkey
AppVersion={#AppVersion}
AppPublisher=Voice to Hotkey
DefaultDirName={autopf}\Voice to Hotkey
DefaultGroupName=Voice to Hotkey
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=VTH-Setup-{#AppVersion}
UninstallDisplayIcon={app}\VTH.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Files]
Source: "..\..\dist\VTH\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Voice to Hotkey"; Filename: "{app}\VTH.exe"

[Registry]
; VTH adds this itself when "Open on login" is on. Clean it up on uninstall.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "Voice to Hotkey"; Flags: dontcreatekey uninsdeletevalue

[Run]
Filename: "{app}\VTH.exe"; Description: "Open Voice to Hotkey"; Flags: nowait postinstall skipifsilent
