#define STNG_VERSION "1.0"
#define STNG_PATH "build\STNG-WIN64-" + STNG_VERSION + "-Py38"

[Setup]
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
AppId={{983543BE-2504-48BF-B6E7-308EA032DAB3}
AppName=Steam Tools NG
AppVersion={#STNG_VERSION}
AppPublisherURL=https://lara.click
AppSupportURL=https://github.com/ShyPixie/steam-tools-ng/issues
AppUpdatesURL=https://github.com/ShyPixie/steam-tools-ng/releases
DefaultDirName={autopf}\STNG
UsePreviousAppDir=no
DisableDirPage=yes
DefaultGroupName=Steam Tools NG
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer_build
OutputBaseFilename=stng_setup
SetupIconFile=icons\stng.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
WizardImageFile=icons\stng_left.bmp
WizardSmallImageFile=icons\stng.bmp

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
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#STNG_PATH}\steam_tools_ng.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "{#STNG_PATH}\*.dll"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "{#STNG_PATH}\share\*"; DestDir: "{app}\share"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "{#STNG_PATH}\etc\*"; DestDir: "{app}\etc"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "{#STNG_PATH}\lib\*"; DestDir: "{app}\lib"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "{#STNG_PATH}\plugins\steamgifts.pyc"; DestDir: "{app}\plugins"; Flags: ignoreversion; Components: plugins\steamgifts
Source: "{#STNG_PATH}\plugins\steamtrades.pyc"; DestDir: "{app}\plugins"; Flags: ignoreversion; Components: plugins\steamtrades

[Icons]
Name: "{group}\Steam Tools NG"; Filename: "{app}\steam_tools_ng.exe"; IconFilename: "{app}\share\icons\stng.ico"
Name: "{group}\(console) authenticator"; Filename: "{app}\steam_tools_ng.exe"; Parameters: "--cli authenticator"; IconFilename: "{app}\share\icons\stng_console.ico"
Name: "{group}\(console) steamtrades"; Filename: "{app}\steam_tools_ng.exe"; Parameters: "--cli steamtrades"; Components: plugins\steamtrades; IconFilename: "{app}\share\icons\stng_console.ico"
Name: "{group}\(console) steamgifts"; Filename: "{app}\steam_tools_ng.exe"; Parameters: "--cli steamgifts"; Components: plugins\steamgifts; IconFilename: "{app}\share\icons\stng_console.ico"
Name: "{group}\(console) cardfarming"; Filename: "{app}\steam_tools_ng.exe"; Parameters: "--cli cardfarming"; IconFilename: "{app}\share\icons\stng_console.ico"
Name: "{group}\Config Files"; Filename: "{app}\steam_tools_ng.exe"; Parameters: "--config-dir"; IconFilename: "{app}\share\icons\stng_nc.ico"
Name: "{group}\Log Files"; Filename: "{app}\steam_tools_ng.exe"; Parameters: "--log-dir"; IconFilename: "{app}\share\icons\stng_nc.ico"
Name: "{group}\Uninstaller"; Filename: "{uninstallexe}"; IconFilename: "{app}\icons\stng_nc.ico"
Name: "{commondesktop}\Steam Tools NG"; Filename: "{app}\steam_tools_ng.exe"; Tasks: desktopicon; IconFilename: "{app}\share\icons\stng.ico"

[InstallDelete]
Type: files; Name: "{app}\steam-tools-ng.exe"
Type: files; Name: "{app}\share\icons\steam-tools-ng*"
Type: filesandordirs; Name: "{app}\lib\src"

[Run]
Filename: "{app}\steam_tools_ng.exe"; Description: "{cm:LaunchProgram,Steam Tools NG}"; Flags: nowait postinstall skipifsilent
