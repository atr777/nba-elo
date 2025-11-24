@echo off
REM Fetch all NBA seasons from 2000-2025
REM This script can be run from anywhere

echo Setting up environment...

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Change to the project root (one level up from scripts/)
cd /d "%SCRIPT_DIR%.."

REM Set Python path to current directory (project root)
set PYTHONPATH=%CD%

echo Working directory: %CD%
echo.

REM Verify we're in the right place
if not exist "src\etl\fetch_scoreboard.py" (
    echo ERROR: Cannot find src\etl\fetch_scoreboard.py
    echo Make sure this script is in the scripts\ folder of the project
    pause
    exit /b 1
)

echo.
echo ====================================
echo Fetching NBA Data (2000-2025)
echo This will take 2-3 hours...
echo ====================================
echo.

REM Create directories if they don't exist
if not exist "data\raw" mkdir "data\raw"
if not exist "data\exports" mkdir "data\exports"

REM 2000-01 season
echo Fetching 2000-01 season...
python src\etl\fetch_scoreboard.py --start-date 20001031 --end-date 20010430 --output data\raw\nba_games_2000-01.csv
timeout /t 2 /nobreak >nul

REM 2001-02 season
echo Fetching 2001-02 season...
python src\etl\fetch_scoreboard.py --start-date 20011030 --end-date 20020430 --output data\raw\nba_games_2001-02.csv
timeout /t 2 /nobreak >nul

REM 2002-03 season
echo Fetching 2002-03 season...
python src\etl\fetch_scoreboard.py --start-date 20021029 --end-date 20030430 --output data\raw\nba_games_2002-03.csv
timeout /t 2 /nobreak >nul

REM 2003-04 season
echo Fetching 2003-04 season...
python src\etl\fetch_scoreboard.py --start-date 20031028 --end-date 20040430 --output data\raw\nba_games_2003-04.csv
timeout /t 2 /nobreak >nul

REM 2004-05 season
echo Fetching 2004-05 season...
python src\etl\fetch_scoreboard.py --start-date 20041102 --end-date 20050430 --output data\raw\nba_games_2004-05.csv
timeout /t 2 /nobreak >nul

REM 2005-06 season
echo Fetching 2005-06 season...
python src\etl\fetch_scoreboard.py --start-date 20051101 --end-date 20060430 --output data\raw\nba_games_2005-06.csv
timeout /t 2 /nobreak >nul

REM 2006-07 season
echo Fetching 2006-07 season...
python src\etl\fetch_scoreboard.py --start-date 20061031 --end-date 20070430 --output data\raw\nba_games_2006-07.csv
timeout /t 2 /nobreak >nul

REM 2007-08 season
echo Fetching 2007-08 season...
python src\etl\fetch_scoreboard.py --start-date 20071030 --end-date 20080430 --output data\raw\nba_games_2007-08.csv
timeout /t 2 /nobreak >nul

REM 2008-09 season
echo Fetching 2008-09 season...
python src\etl\fetch_scoreboard.py --start-date 20081028 --end-date 20090430 --output data\raw\nba_games_2008-09.csv
timeout /t 2 /nobreak >nul

REM 2009-10 season
echo Fetching 2009-10 season...
python src\etl\fetch_scoreboard.py --start-date 20091027 --end-date 20100430 --output data\raw\nba_games_2009-10.csv
timeout /t 2 /nobreak >nul

REM 2010-11 season
echo Fetching 2010-11 season...
python src\etl\fetch_scoreboard.py --start-date 20101026 --end-date 20110430 --output data\raw\nba_games_2010-11.csv
timeout /t 2 /nobreak >nul

REM 2011-12 season (lockout - started Dec 25)
echo Fetching 2011-12 season (lockout)...
python src\etl\fetch_scoreboard.py --start-date 20111225 --end-date 20120430 --output data\raw\nba_games_2011-12.csv
timeout /t 2 /nobreak >nul

REM 2012-13 season
echo Fetching 2012-13 season...
python src\etl\fetch_scoreboard.py --start-date 20121030 --end-date 20130430 --output data\raw\nba_games_2012-13.csv
timeout /t 2 /nobreak >nul

REM 2013-14 season
echo Fetching 2013-14 season...
python src\etl\fetch_scoreboard.py --start-date 20131029 --end-date 20140430 --output data\raw\nba_games_2013-14.csv
timeout /t 2 /nobreak >nul

REM 2014-15 season
echo Fetching 2014-15 season...
python src\etl\fetch_scoreboard.py --start-date 20141028 --end-date 20150430 --output data\raw\nba_games_2014-15.csv
timeout /t 2 /nobreak >nul

REM 2015-16 season
echo Fetching 2015-16 season...
python src\etl\fetch_scoreboard.py --start-date 20151027 --end-date 20160430 --output data\raw\nba_games_2015-16.csv
timeout /t 2 /nobreak >nul

REM 2016-17 season
echo Fetching 2016-17 season...
python src\etl\fetch_scoreboard.py --start-date 20161025 --end-date 20170430 --output data\raw\nba_games_2016-17.csv
timeout /t 2 /nobreak >nul

REM 2017-18 season
echo Fetching 2017-18 season...
python src\etl\fetch_scoreboard.py --start-date 20171017 --end-date 20180430 --output data\raw\nba_games_2017-18.csv
timeout /t 2 /nobreak >nul

REM 2018-19 season
echo Fetching 2018-19 season...
python src\etl\fetch_scoreboard.py --start-date 20181016 --end-date 20190430 --output data\raw\nba_games_2018-19.csv
timeout /t 2 /nobreak >nul

REM 2019-20 season (COVID)
echo Fetching 2019-20 season (COVID shortened)...
python src\etl\fetch_scoreboard.py --start-date 20191022 --end-date 20200430 --output data\raw\nba_games_2019-20.csv
timeout /t 2 /nobreak >nul

REM 2020-21 season (COVID delayed start)
echo Fetching 2020-21 season (COVID delayed)...
python src\etl\fetch_scoreboard.py --start-date 20201222 --end-date 20210430 --output data\raw\nba_games_2020-21.csv
timeout /t 2 /nobreak >nul

REM 2021-22 season
echo Fetching 2021-22 season...
python src\etl\fetch_scoreboard.py --start-date 20211019 --end-date 20220430 --output data\raw\nba_games_2021-22.csv
timeout /t 2 /nobreak >nul

REM 2022-23 season
echo Fetching 2022-23 season...
python src\etl\fetch_scoreboard.py --start-date 20221018 --end-date 20230430 --output data\raw\nba_games_2022-23.csv
timeout /t 2 /nobreak >nul

REM 2023-24 season
echo Fetching 2023-24 season...
python src\etl\fetch_scoreboard.py --start-date 20231024 --end-date 20240430 --output data\raw\nba_games_2023-24.csv
timeout /t 2 /nobreak >nul

REM 2024-25 season (current)
echo Fetching 2024-25 season (current, through November 2025)...
python src\etl\fetch_scoreboard.py --start-date 20241022 --end-date 20251130 --output data\raw\nba_games_2024-25.csv
timeout /t 2 /nobreak >nul

echo.
echo ====================================
echo Combining all seasons...
echo ====================================
echo.

REM Combine all CSVs
copy data\raw\nba_games_2000-01.csv data\raw\nba_games_all.csv >nul
for %%f in (data\raw\nba_games_2001-*.csv data\raw\nba_games_2002-*.csv data\raw\nba_games_2003-*.csv data\raw\nba_games_2004-*.csv data\raw\nba_games_2005-*.csv data\raw\nba_games_2006-*.csv data\raw\nba_games_2007-*.csv data\raw\nba_games_2008-*.csv data\raw\nba_games_2009-*.csv data\raw\nba_games_2010-*.csv data\raw\nba_games_2011-*.csv data\raw\nba_games_2012-*.csv data\raw\nba_games_2013-*.csv data\raw\nba_games_2014-*.csv data\raw\nba_games_2015-*.csv data\raw\nba_games_2016-*.csv data\raw\nba_games_2017-*.csv data\raw\nba_games_2018-*.csv data\raw\nba_games_2019-*.csv data\raw\nba_games_2020-*.csv data\raw\nba_games_2021-*.csv data\raw\nba_games_2022-*.csv data\raw\nba_games_2023-*.csv data\raw\nba_games_2024-*.csv) do (
    more +1 "%%f" >> data\raw\nba_games_all.csv
)

echo.
echo ====================================
echo Complete! 
echo ====================================
echo.
echo Total lines in combined file:
find /c /v "" data\raw\nba_games_all.csv

echo.
echo Now run:
echo python src\engines\team_elo_engine.py --input data\raw\nba_games_all.csv --output data\exports\team_elo_history_2000-2025.csv
echo.

pause
