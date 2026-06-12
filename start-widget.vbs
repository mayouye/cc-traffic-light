' Silently launch the floating traffic light (no console window, non-blocking).
' Double-click to run, or put a shortcut in shell:startup for auto-start.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
widget = scriptDir & "\src\widget.pyw"
sh.Run "pythonw """ & widget & """", 0, False
