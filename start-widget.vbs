' 静默启动悬浮红绿灯(无控制台窗口、不阻塞)。
' 双击运行,或放进 shell:startup 实现开机自启。
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
widget = scriptDir & "\src\widget.pyw"
sh.Run "pythonw """ & widget & """", 0, False
