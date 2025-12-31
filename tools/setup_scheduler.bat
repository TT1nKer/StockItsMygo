@echo off
REM ========================================
REM Daily Update Scheduler Batch File
REM 每日更新调度批处理文件
REM ========================================

REM Change to project directory
cd /d d:\strategy=Z

REM Create logs directory if not exists
if not exist "logs" mkdir logs

REM Run daily update and append output to log file
REM Log filename includes date: daily_update_YYYYMMDD.log
python tools\daily_update.py >> logs\daily_update_%date:~-4,4%%date:~-10,2%%date:~-7,2%.log 2>&1

REM Exit with the same error code as Python script
exit /b %ERRORLEVEL%
