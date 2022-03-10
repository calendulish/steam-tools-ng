#define AppName 'steam-tools-ng'
#define FancyAppName 'Steam Tools NG'

#include "environment.iss"

[Setup]
AppId={{983543BE-2504-48BF-B6E7-308EA032DAB3}
AppName={#FancyAppName}
AppVersion={#AppVersion}
AppCopyright=Lara Maia <dev@lara.monster> 2022
AppPublisherURL=https://lara.monster
AppSupportURL=https://github.com/ShyPixie/{#AppName}/issues
AppUpdatesURL=https://github.com/ShyPixie/{#AppName}/releases
WizardStyle=modern
WizardSmallImageFile=logo.bmp
SetupIconFile={#AppName}.ico
DefaultDirName={autopf}\{#FancyAppName}
;DefaultDirName={autopf}\STNG
;UsePreviousAppDir=no
;DisableDirPage=yes
AllowNoIcons=yes
DefaultGroupName={#FancyAppName}
OutputDir=build
OutputBaseFileName={#AppName}-setup
Uninstallable=True
Compression=lzma2/ultra64
ArchitecturesAllowed=x64 arm64
ArchitecturesInstallIn64BitMode=x64 arm64
DisableDirPage=False
SolidCompression=True
ChangesEnvironment=True
LicenseFile=../LICENSE

[Types]
Name: "full"; Description: "Full installation"
Name: "compact"; Description: "Compact installation"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "main"; Description: "Main Files"; Types: full compact custom; Flags: fixed
Name: "plugins"; Description: "Plugins Files"; Types: full
Name: "plugins\steamgifts"; Description: "Steamgifts Plugin"; Types: full
Name: "plugins\steamtrades"; Description: "Steamtrades Plugin"; Types: full

[Tasks]
Name: "envpath"; Description: "Add STNG to PATH"; GroupDescription: "Additional Settings"; Flags: unchecked
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\build\{#ReleaseName}\steam-tools-ng.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "..\build\{#ReleaseName}\*.dll"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "..\build\{#ReleaseName}\share\*"; DestDir: "{app}\share"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "..\build\{#ReleaseName}\etc\*"; DestDir: "{app}\etc"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "..\build\{#ReleaseName}\lib\*"; DestDir: "{app}\lib"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "..\build\{#ReleaseName}\plugins\steamgifts.pyc"; DestDir: "{app}\plugins"; Flags: ignoreversion; Components: plugins\steamgifts
Source: "..\build\{#ReleaseName}\plugins\steamtrades.pyc"; DestDir: "{app}\plugins"; Flags: ignoreversion; Components: plugins\steamtrades

[Icons]
Name: "{group}\Steam Tools NG"; Filename: "{app}\steam-tools-ng.exe"; IconFilename: "{app}\lib\steam_tools_ng\icons\stng.ico"
Name: "{group}\(console) steamguard"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--cli steamguard"; IconFilename: "{app}\lib\steam_tools_ng\icons\stng_console.ico"
Name: "{group}\(console) steamtrades"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--cli steamtrades"; Components: plugins\steamtrades; IconFilename: "{app}\lib\steam_tools_ng\icons\stng_console.ico"
Name: "{group}\(console) steamgifts"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--cli steamgifts"; Components: plugins\steamgifts; IconFilename: "{app}\lib\steam_tools_ng\icons\stng_console.ico"
Name: "{group}\(console) cardfarming"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--cli cardfarming"; IconFilename: "{app}\lib\steam_tools_ng\icons\stng_console.ico"
Name: "{group}\Config Files"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--config-dir"; IconFilename: "{app}\lib\steam_tools_ng\icons\stng_nc.ico"
Name: "{group}\Log Files"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--log-dir"; IconFilename: "{app}\lib\steam_tools_ng\icons\stng_nc.ico"
Name: "{group}\Uninstaller"; Filename: "{uninstallexe}"; IconFilename: "{app}\lib\steam_tools_ng\icons\stng_nc.ico"
Name: "{commondesktop}\Steam Tools NG"; Filename: "{app}\steam-tools-ng.exe"; Tasks: desktopicon; IconFilename: "{app}\lib\steam_tools_ng\icons\stng.ico"

[InstallDelete]
Type: files; Name: "{group}\(console) authenticator.lnk"
Type: files; Name: "{app}\steam-tools-ng.exe"
Type: files; Name: "{app}\share\icons\steam-tools-ng*"
Type: filesandordirs; Name: "{app}\lib\src"

[Run]
Filename: "{app}\steam-tools-ng.exe"; Description: "{cm:LaunchProgram,Steam Tools NG}"; Flags: nowait postinstall skipifsilent
