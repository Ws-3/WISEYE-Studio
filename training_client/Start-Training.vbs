Option Explicit
Dim shell, files, folder, root, pythonw, command
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
root = files.GetParentFolderName(folder)
shell.CurrentDirectory = root
pythonw = files.BuildPath(root, "Tools\Python\pythonw.exe")
If Not files.FileExists(pythonw) Then pythonw = files.BuildPath(root, "builds\python-env\Scripts\pythonw.exe")
If Not files.FileExists(pythonw) Then pythonw = files.BuildPath(folder, ".venv\Scripts\pythonw.exe")
If Not files.FileExists(pythonw) Then pythonw = "pythonw.exe"
command = Chr(34) & pythonw & Chr(34) & " -m training_client.preview"
On Error Resume Next
shell.Run command, 0, False
If Err.Number <> 0 Then
    MsgBox "Cannot start WISEYE Training. Install Python and training_client/requirements.txt first.", 16, "WISEYE Training"
End If
