; Inno Setup script for Dictate.
;
; Installs into the user's own profile, so it needs no administrator rights and no UAC
; prompt. The program files carry no CUDA and no Whisper weights: DictateSetup.exe
; downloads those on first run, which is what keeps this installer small.
;
; Build:
;   "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" packaging\dictate.iss

#define AppName "Dictate"
#define AppVersion "0.1.0"
#define AppPublisher "Agora"
#define AppExe "Dictate.exe"

[Setup]
AppId={{7C1B4E42-9E2C-4A6E-9E8B-1D3F5A6C7B21}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\build_installer
OutputBaseFilename=DictateSetup-{#AppVersion}
SetupIconFile=..\assets\dictate.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start Dictate when I sign in"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\build_dist\Dictate\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} setup"; Filename: "{app}\DictateSetup.exe"
Name: "{group}\How {#AppName} works"; Filename: "{app}\DictateSetup.exe"; Parameters: "--help-page"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
; The wizard checks the GPU, downloads the models, and asks which microphone to use.
; It runs before the app starts, because the app cannot transcribe without it.
Filename: "{app}\DictateSetup.exe"; Description: "Set up models and microphone"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Code]
// The downloaded models are 2 GB and live outside {app}. Reinstalling is common during
// development, so they are kept unless the user says otherwise.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\Dictate');
    // A silent uninstall must not stop on a question. Measured: /VERYSILENT still showed
    // this box and waited, because MsgBox does not care how the uninstaller was started.
    if DirExists(DataDir) and not UninstallSilent then
    begin
      if MsgBox('Delete the downloaded models and settings too?' + #13#10 + #13#10 +
                DataDir + #13#10 + #13#10 +
                'Keep them to avoid a 2 GB download if you reinstall.',
                mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
