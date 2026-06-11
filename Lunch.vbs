Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

sDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' Commande bat en arriere plan, fenetre cachee (0)
oShell.Run "cmd /c chcp 65001 >nul & """ & sDir & "run.bat""", 0, False
