@echo off
title SD Model Manager
cd /d "%~dp0"
python app.py
if errorlevel 1 pause
