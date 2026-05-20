@echo off
REM Build a standalone Windows executable using PyInstaller.
REM Ensure your virtual environment is activated before running this script.
uv run pyinstaller --onefile --name inzen_cli_bot run_inzen_cli_bot.py
