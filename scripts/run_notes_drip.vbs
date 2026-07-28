' Hidden launcher for the Substack Notes drip.
'
' WHY THIS FILE EXISTS. Task Scheduler ran run_notes_drip.bat directly, as the
' logged-on interactive user. That allocates a console, so every hour a blank cmd
' window opened and stole focus from whatever Aaron was doing (2026-07-27). The
' script itself was fine; the window was the whole problem.
'
' WHY NOT "run whether user is logged on or not", the usual advice: that mode runs
' the task with an S4U token, which has no access to the DPAPI user keys that Git
' Credential Manager needs. `git pull` would start failing, and the pull is what
' carries Aaron's phone approvals from GitHub to this machine. It would have broken
' the approval workflow silently, in exchange for hiding a window.
'
' So the task keeps the interactive logon and identical credentials, and only the
' visibility changes. wscript.exe has no console of its own; the batch file and
' every child it spawns (git, python) inherit the hidden window.
'
' Run style 0 = hidden. True = wait for it to finish, so Task Scheduler sees the
' real runtime and its "do not start a new instance if already running" rule can
' actually prevent overlapping drips.

Option Explicit

Dim shell, fso, here, batch
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Resolve the batch file next to this script, so moving the repo does not break it.
here = fso.GetParentFolderName(WScript.ScriptFullName)
batch = fso.BuildPath(here, "run_notes_drip.bat")

If Not fso.FileExists(batch) Then
    ' No console to complain to, so leave a trace where the drip's own log lives.
    Dim logPath, stream
    logPath = fso.BuildPath(fso.GetParentFolderName(here), "logs\notes_drip.log")
    On Error Resume Next
    Set stream = fso.OpenTextFile(logPath, 8, True)
    stream.WriteLine "[" & Now & "] launcher: cannot find " & batch
    stream.Close
    WScript.Quit 1
End If

WScript.Quit shell.Run("""" & batch & """", 0, True)
