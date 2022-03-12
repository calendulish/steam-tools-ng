[Messages]
WizardReady=Ready to Download
ReadyLabel1=Setup is now ready to being downloading the latest version of [name] on your computer.
ReadyLabel2a=Click Download & Install to continue with the installation
ReadyLabel2b=Click Download & Install to continue with the installation
FinishedHeadingLabel=Error when installing [name]
FinishedLabel=Setup has failed to install [name] on your computer.
FinishedLabelNoIcons=Setup has failed to install [name] on your computer.

[Code]
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = WpReady then begin
    WizardForm.NextButton.Caption := 'Download && Install';
    WizardForm.NextButton.Left := WizardForm.NextButton.Left - 25;
    WizardForm.NextButton.Width := 105;
  end;
end;
