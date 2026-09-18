' TrendPulse AI - Silent Background Stock Sync Runner
' Headless zero-window execution using WScript.Shell and pythonw.exe

Option Explicit

Dim WshShell, fso, scriptDir, projectDir, pythonwExe, syncScript, cmd

Set WshShell = WScript.CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Resolve project root (parent directory of scripts/)
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectDir = fso.GetParentFolderName(scriptDir)

' Determine pythonw.exe path (.venv preferred, then fallback to python.exe or system PATH)
If fso.FileExists(projectDir & "\.venv\Scripts\pythonw.exe") Then
    pythonwExe = Chr(34) & projectDir & "\.venv\Scripts\pythonw.exe" & Chr(34)
ElseIf fso.FileExists(projectDir & "\venv\Scripts\pythonw.exe") Then
    pythonwExe = Chr(34) & projectDir & "\venv\Scripts\pythonw.exe" & Chr(34)
ElseIf fso.FileExists(projectDir & "\.venv\Scripts\python.exe") Then
    pythonwExe = Chr(34) & projectDir & "\.venv\Scripts\python.exe" & Chr(34)
Else
    pythonwExe = "pythonw.exe"
End If

syncScript = Chr(34) & projectDir & "\sync_stocks.py" & Chr(34)

' Window style 0 = vbHide (completely hidden, zero console window popup)
' Third argument False = asynchronous execution (returns immediately)
cmd = "cmd.exe /c cd /d " & Chr(34) & projectDir & Chr(34) & " && " & pythonwExe & " " & syncScript & " --silent --source background"
WshShell.Run cmd, 0, False
