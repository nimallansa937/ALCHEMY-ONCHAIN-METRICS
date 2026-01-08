@echo off
REM ===============================================
REM HIMARI Dune Regime Check - Windows Scheduled Task
REM Run every 6 hours via Windows Task Scheduler
REM ===============================================

cd /d "c:\Users\chari\OneDrive\Documents\HIMARI OPUS 2\dune_analytics"
python dune_regime_check.py >> logs\regime_check.log 2>&1
