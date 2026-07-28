@echo off
:: Substack Notes drip. Runs on Aaron's PC, NOT the VPS.
::
:: Why here: Substack refuses note-writing POSTs from the VPS's datacenter IP
:: (403 with an HTML page), while the identical request from this machine is
:: accepted. Verified 2026-07-26. Reads still work fine from the VPS, so
:: everything else in the pipeline stays there.
::
:: DO NOT POINT TASK SCHEDULER AT THIS FILE. It is launched by
:: run_notes_drip.vbs, which runs it with no console window. Pointing the task
:: straight at this .bat pops a cmd window every hour and steals focus from
:: whatever is fullscreen. The .vbs header explains why that launcher exists and
:: why the obvious alternative does not work.
::
:: Schedule via Windows Task Scheduler, every 60 minutes, all day. The script
:: decides whether to post: at most 2 notes/day, at least 5h apart, only between
:: 09:00 and 21:00 ET, and only notes Aaron has set to `approved` in
:: data/manual/notes_queue.yaml. If the PC was off at any given hour it simply
:: posts at the next opportunity, which is the whole reason for a wide window.
::
:: Nothing posts unless it is BOTH approved in the queue AND passes validation.

set PROJECT_DIR=C:\Users\Aaron\Desktop\NBA_ELO\nba-elo-engine
set PYTHON=C:\Python314\python.exe

:: TWO LOGS, AND THEY MUST STAY TWO.
::
:: drip_notes.py opens logs\notes_drip.log itself and appends its own timestamped
:: lines. cmd's `>>` holds an EXCLUSIVE write handle for the whole command, so
:: redirecting python into that same file made every scheduled run die with
:: PermissionError [Errno 13] on the drip's first log() call. Not theoretical: it
:: happened 22 times over 2026-07-26 and 2026-07-27, meaning the scheduled task
:: never once completed a run and every note that went out was sent by hand.
:: Found 2026-07-27 while fixing the console window.
::
:: So python owns notes_drip.log and this wrapper writes somewhere else. The
:: wrapper log is only for what python cannot report itself: a traceback that
:: kills it before it can log, or git failing.
set WRAPLOG=%PROJECT_DIR%\logs\notes_drip_wrapper.log

cd /d "%PROJECT_DIR%"
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

echo [%DATE% %TIME%] wrapper start >> "%WRAPLOG%"

:: Pick up any approvals Aaron made from his phone (GitHub edit -> pull here).
:: Never let a git problem stop the drip; the queue on disk is still valid.
git pull --autostash --quiet origin master >> "%WRAPLOG%" 2>&1

"%PYTHON%" scripts\drip_notes.py --live >> "%WRAPLOG%" 2>&1
echo [%DATE% %TIME%] wrapper exit %ERRORLEVEL% >> "%WRAPLOG%"

exit /b 0
