@echo off
:: Substack Notes drip. Runs on Aaron's PC, NOT the VPS.
::
:: Why here: Substack refuses note-writing POSTs from the VPS's datacenter IP
:: (403 with an HTML page), while the identical request from this machine is
:: accepted. Verified 2026-07-26. Reads still work fine from the VPS, so
:: everything else in the pipeline stays there.
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
set LOG=%PROJECT_DIR%\logs\notes_drip.log

cd /d "%PROJECT_DIR%"

:: Pick up any approvals Aaron made from his phone (GitHub edit -> pull here).
:: Never let a git problem stop the drip; the queue on disk is still valid.
git pull --autostash --quiet origin master >> "%LOG%" 2>&1

"%PYTHON%" scripts\drip_notes.py --live >> "%LOG%" 2>&1

exit /b 0
