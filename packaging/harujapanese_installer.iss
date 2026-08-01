; Inno Setup 6 script for HaruJapanese.
; The version is injected by build_installer.ps1 via /D defines.
; To compile manually:
;   iscc /DMyAppVersion=1.0.0 /DSourceExe=..\dist\HaruJapanese.exe packaging\harujapanese_installer.iss

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef SourceExe
  #define SourceExe "..\dist\HaruJapanese.exe"
#endif

#define MyAppName "HaruJapanese"
#define MyAppPublisher "Haru Japanese"
#define MyAppExeName "HaruJapanese.exe"
#define MyAppAssocName "HaruJapanese learning record archive"
#define MyAppAssocExt ".harujp"
#define MyAppAssocKey "HaruJapaneseBackup"

[Setup]
AppId={{EB852EC4-90FB-408B-8D7E-5D9A69E65C92}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HaruJapanese
DefaultGroupName=HaruJapanese
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=HaruJapaneseSetup-{#MyAppVersion}
OutputDir=..\dist\installer
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
ChangesAssociations=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

#ifndef VoiceSourceDir
  #define VoiceSourceDir ""
#endif

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; Flags: ignoreversion
#if VoiceSourceDir != ""
Source: "{#VoiceSourceDir}\*"; DestDir: "{app}\zundamon-gpt-sovits-api"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif


[Registry]
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
