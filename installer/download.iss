#include "shutdown.iss"

[CustomMessages]
DownloadPage={#DownloadPage}
AppName={#AppName}

[code]
{ Based on CodeDownloadFiles at issrc repository }
var
  ProgressPage: TOutputProgressWizardPage;
  DownloadPage: TDownloadWizardPage;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if Progress = ProgressMax then
    Log(Format('Successfully downloaded file to {tmp}: %s', [FileName]));
  Result := True;
end;

procedure InitializeWizard;
begin
  ProgressPage := CreateOutputProgressPage('Finalization of installation', '');
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), @OnDownloadProgress);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  if CurPageID = wpReady then begin
    DownloadPage.Clear;
    DownloadPage.Add(CustomMessage('DownloadPage'), CustomMessage('AppName') + '-setup.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
        Result := True;
      except
        if DownloadPage.AbortedByUser then
          Log('Aborted by user.')
        else
          SuppressibleMsgBox(AddPeriod(GetExceptionMessage), mbCriticalError, MB_OK, IDOK);
        Result := False;
      end;
    finally
      DownloadPage.Hide;
    end;
  end else
      Result := True;
end;

procedure CallInstaller;
var
  ResultCode: Integer;
begin
  if Exec(ExpandConstant('{tmp}\' + CustomMessage('AppName') + '-setup.exe'), '', '', SW_SHOW, ewNoWait, ResultCode) then begin
    PostMessage(WizardForm.Handle, 274, $F020, 0);
    Shutdown;
  end;
end;
