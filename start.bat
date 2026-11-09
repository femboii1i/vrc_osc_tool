@echo off
REM Startet das VRC OSC Tool (legt beim ersten Mal automatisch eine venv an)
cd /d "%~dp0"
if not exist .venv (
    echo Erstelle virtuelle Umgebung ...
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
)
start "" .venv\Scripts\pythonw.exe vrc_osc_tool.py
