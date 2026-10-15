#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{3EF35475-3F75-4F61-80BA-33F8D7F1A9A1}
AppName=CjChatBot
AppVersion={#MyAppVersion}
AppPublisher=Cjhackeryt
AppPublisherURL=https://github.com/Cjhackeryt/CjChatBot
DefaultDirName={localappdata}\Programs\CjChatBot
DefaultGroupName=CjChatBot
UninstallDisplayIcon={app}\CjChatBot.exe
LicenseFile=..\LICENSE
SetupIconFile=..\web\assets\favicon.ico
OutputDir=..\dist
OutputBaseFilename=CjChatBot-Setup
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\CjChatBot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\CjChatBot"; Filename: "{app}\CjChatBot.exe"
Name: "{autodesktop}\CjChatBot"; Filename: "{app}\CjChatBot.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CjChatBot.exe"; Description: "Launch CjChatBot"; Flags: postinstall nowait skipifsilent
