cls
@echo off
echo ----------------- Checking for Updates ----------------
git pull origin main
echo --------------------- Starting Up ---------------------
python3.13.exe -u ./v1/Remi-1.0.0.py
cls
call REMI-v1.bat