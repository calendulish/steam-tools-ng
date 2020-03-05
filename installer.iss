#define STNG_VERSION "0.9.4"
#define STNG_PATH "build\STNG-WIN64-" + STNG_VERSION + "-Py38"

[Setup]
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
AppId={{983543BE-2504-48BF-B6E7-308EA032DAB3}
AppName=Steam Tools NG
AppVersion=0.9.4
;AppVerName=Steam Tools NG 0.9.4
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
SetupIconFile=icons\steam-tools-ng.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

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
Source: "{#STNG_PATH}\steam-tools-ng.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "{#STNG_PATH}\*.dll"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "{#STNG_PATH}\share\*"; DestDir: "{app}\share"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "{#STNG_PATH}\etc\*"; DestDir: "{app}\etc"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "{#STNG_PATH}\lib\*"; DestDir: "{app}\lib"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "{#STNG_PATH}\plugins\steamgifts.pyc"; DestDir: "{app}\plugins"; Flags: ignoreversion; Components: plugins\steamgifts
Source: "{#STNG_PATH}\plugins\steamtrades.pyc"; DestDir: "{app}\plugins"; Flags: ignoreversion; Components: plugins\steamtrades

[Icons]
Name: "{group}\Steam Tools NG"; Filename: "{app}\steam-tools-ng.exe"
Name: "{group}\(console) authenticator"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--cli authenticator"
Name: "{group}\(console) steamtrades"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--cli steamtrades"; Components: plugins\steamtrades
Name: "{group}\(console) steamgifts"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--cli steamgifts"; Components: plugins\steamgifts
Name: "{group}\(console) cardfarming"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--cli cardfarming"
Name: "{group}\Config Files"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--config-dir"
Name: "{group}\Log Files"; Filename: "{app}\steam-tools-ng.exe"; Parameters: "--log-dir"
Name: "{group}\Uninstaller"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Steam Tools NG"; Filename: "{app}\steam-tools-ng.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\steam-tools-ng.exe"; Description: "{cm:LaunchProgram,Steam Tools NG}"; Flags: nowait postinstall skipifsilent
