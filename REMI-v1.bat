cls
@echo off
echo ----------------- Checking for Updates ----------------
git pull origin main
echo --------------------- Starting Up ---------------------
python3.13.exe -u ./v1/main.py
cls
call REMI-v1.bat