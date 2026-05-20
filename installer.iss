; installer.iss - Inno Setup script for Inzen CLI Bot
; This script creates a Windows installer for your app

[Setup]
AppName=Inzen CLI Bot
AppVersion=1.0
DefaultDirName={autopf}\InzenCLIBot
DefaultGroupName=Inzen CLI Bot
OutputBaseFilename=inzen_cli_bot_installer
Compression=lzma
SolidCompression=yes
ChangesEnvironment=yes

[Files]
; Main executable
Source: "dist\inzen_cli_bot.exe"; DestDir: "{app}"; Flags: ignoreversion
; CLI aliases for compatibility and convenience
Source: "dist\inzen_cli_bot.exe"; DestDir: "{app}"; DestName: "bot.exe"; Flags: ignoreversion
; Optional: include README and .env.example
Source: "README.md"; DestDir: "{app}"; Flags: isreadme
Source: ".env.example"; DestDir: "{app}"

[Icons]
Name: "{group}\Inzen CLI Bot"; Filename: "{app}\inzen_cli_bot.exe"
Name: "{group}\Run Inzen CLI Bot setup"; Filename: "{cmd}"; Parameters: "/K """"{app}\inzen_cli_bot.exe"" --setup"""; WorkingDir: "{app}"
Name: "{group}\Uninstall Inzen CLI Bot"; Filename: "{uninstallexe}"

[Run]
Filename: "{cmd}"; Parameters: "/K """"{app}\inzen_cli_bot.exe"" --setup"""; Description: "Run first-time setup now (recommended)"; Flags: nowait postinstall skipifsilent unchecked

[Code]
var AddToPathCheckbox: TNewCheckBox;

function SendMessageTimeout(hWnd: Integer; Msg: Integer; wParam: Integer; lParam: string; fuFlags: Integer; uTimeout: Integer; var lpdwResult: Integer): Integer;
	external 'SendMessageTimeoutW@user32.dll stdcall';

procedure BroadcastEnvironmentChange;
var
	ResultCode: Integer;
begin
	SendMessageTimeout($FFFF, $001A, 0, 'Environment', $0002, 5000, ResultCode);
end;

function ContainsPathSegment(PathValue: string; Segment: string): Boolean;
var
	Needle: string;
	Haystack: string;
begin
	Needle := ';' + Uppercase(Segment) + ';';
	Haystack := ';' + Uppercase(PathValue) + ';';
	Result := Pos(Needle, Haystack) > 0;
end;

procedure InitializeWizard;
begin
	AddToPathCheckbox := TNewCheckBox.Create(WizardForm);
	AddToPathCheckbox.Parent := WizardForm.SelectDirPage;
	AddToPathCheckbox.Top := WizardForm.DirEdit.Top + WizardForm.DirEdit.Height + 16;
	AddToPathCheckbox.Left := WizardForm.DirEdit.Left;
	AddToPathCheckbox.Width := WizardForm.DirEdit.Width;
	AddToPathCheckbox.Caption := 'Add Inzen CLI Bot to the system PATH';
	AddToPathCheckbox.Checked := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
	Path, NewPath, AppPath: string;
begin
	if (CurStep = ssPostInstall) and AddToPathCheckbox.Checked then
	begin
		AppPath := ExpandConstant('{app}');
		if not RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment', 'Path', Path) then
			Path := '';
		if not ContainsPathSegment(Path, AppPath) then
		begin
			if (Path <> '') and (Copy(Path, Length(Path), 1) <> ';') then
				Path := Path + ';';
			NewPath := Path + AppPath;
			RegWriteExpandStringValue(HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment', 'Path', NewPath);
			BroadcastEnvironmentChange;
		end;
	end;
end;
