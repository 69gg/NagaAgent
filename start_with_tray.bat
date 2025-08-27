@echo off
chcp 65001 >nul
title Naga Agent - Tray Mode
cd /d %~dp0
call .venv\Scripts\activate.bat
pip install -r requirements.txt
echo Starting NagaAgent with tray support...
echo Console will be automatically hidden after 3 seconds
echo Console will also be hidden from taskbar
echo Tip: Right-click tray icon to show/hide console window
python main.py
pause
