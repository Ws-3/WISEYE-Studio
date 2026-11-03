Option Explicit
Dim fs, sh, root, entry, command, exitCode
Set fs = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fs.GetParentFolderName(WScript.ScriptFullName)
entry = root & "\scripts\Start-Desktop.ps1"
If Not fs.FileExists(entry) Then
    MsgBox "Missing launcher: " & entry, 16, "WISEYE Studio"
    WScript.Quit 1
End If
command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & entry & Chr(34)
exitCode = sh.Run(command, 0, True)
If exitCode <> 0 Then
    MsgBox "Launch failed. Run this command in PowerShell for details:" & vbCrLf & command, 16, "WISEYE Studio"
End If
WScript.Quit exitCode
