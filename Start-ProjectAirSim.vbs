Set fs = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fs.GetParentFolderName(WScript.ScriptFullName)
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & root & "\scripts\Start-ProjectAirSim.ps1" & Chr(34) & " -SkipBuild", 0, False
