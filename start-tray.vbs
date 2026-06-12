' 静默启动红绿灯托盘程序(无控制台窗口、不阻塞)。
' 双击运行,或放进 shell:startup 实现开机自启。
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
tray = scriptDir & "\src\tray.pyw"
sh.Run "pythonw """ & tray & """", 0, False
