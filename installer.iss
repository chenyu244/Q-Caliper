; Q-Caliper Inno Setup 安装脚本
; 使用方法: 安装 Inno Setup 6 后, 右键本文件 -> Compile

#define MyAppName "Q-Caliper"
#define MyAppVersion "1.0.4"
#define MyAppPublisher "Q-Caliper"
#define MyAppURL "https://github.com/chenyu244/Q-Caliper"
#define MyAppExeName "Q-Caliper.exe"

; Nuitka standalone 输出目录 (build.py 产出)
#define DistDir "dist\main.dist"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=Q-Caliper-{#MyAppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=none
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=images\Q-caliper.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "chinesesimplified"; MessagesFile: "installer\Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; 复制 Nuitka standalone 输出的所有文件
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 Q-Caliper"; Flags: nowait postinstall skipifsilent
