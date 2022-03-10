#define DownloadPage 'https://github.com/ShyPixie/python-template/releases/latest/download/python-template-setup.exe'
#define AppName 'steam-tools-ng'
#define FancyAppName 'Steam Tools NG'

#include "custom_messages.iss"
#include "download.iss"

[Setup]
AppName={#FancyAppName}
AppVersion=latest
AppCopyright=Lara Maia <dev@lara.monster> 2022
AppPublisherURL=https://lara.monster
AppSupportURL=https://github.com/ShyPixie/{#AppName}/issues
AppUpdatesURL=https://github.com/ShyPixie/{#AppName}/releases
WizardStyle=modern
WizardSmallImageFile=logo.bmp
SetupIconFile={#AppName}.ico
DefaultDirName={tmp}
OutputDir=build
OutputBaseFileName={#AppName}-latest
Uninstallable=False
Compression=lzma2/ultra64
ArchitecturesAllowed=x64 arm64
ArchitecturesInstallIn64BitMode=x64 arm64
DisableDirPage=True
SolidCompression=True
ChangesEnvironment=False

[Files]
Source: "{tmp}\{#AppName}-setup.exe"; DestDir: "{tmp}"; Flags: external ignoreversion deleteafterinstall; AfterInstall: CallInstaller
