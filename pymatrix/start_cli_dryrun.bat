@echo off
title SD Model Manager - CLI Dry-Run
cd /d "%~dp0"
python model_manager.py --cli --dry-run --verbose
pause
