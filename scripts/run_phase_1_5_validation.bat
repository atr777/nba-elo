@echo off
REM ============================================================
REM Phase 1.5 Validation - Quick Start Script
REM ============================================================

echo.
echo ============================================================
echo NBA ELO Intelligence Engine - Phase 1.5 Validation
echo ============================================================
echo.

cd /d "%~dp0\.."

REM Step 1: Validate Data Quality
echo [Step 1/4] Validating data quality...
python scripts/validate_phase_1_5.py
if errorlevel 1 (
    echo.
    echo ERROR: Data validation failed!
    echo Please check data/raw/nba_games_all.csv exists
    pause
    exit /b 1
)

echo.
echo [Step 2/4] Running Phase 1.5 Enhanced ELO Engine...
echo This may take 30-60 seconds...
python src/engines/team_elo_engine.py --input data/raw/nba_games_all.csv --output data/exports/team_elo_history_phase_1_5.csv

if errorlevel 1 (
    echo.
    echo ERROR: ELO engine failed!
    pause
    exit /b 1
)

echo.
echo [Step 3/4] Calculating prediction accuracy...
python scripts/validate_phase_1_5.py

echo.
echo [Step 4/4] Validation complete!
echo.
echo Report saved to: data\exports\validation_report_phase_1_5.txt
echo.

type data\exports\validation_report_phase_1_5.txt

echo.
echo ============================================================
echo Validation Complete!
echo ============================================================
echo.

pause
