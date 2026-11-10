@echo off
REM Baut eine einzelne .exe (Ergebnis: dist\VRC-OSC-Tool.exe)
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
)
.venv\Scripts\python -m pip install pyinstaller
.venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name VRC-OSC-Tool --collect-all customtkinter --collect-submodules winrt --hidden-import winrt.windows.media.control --hidden-import winrt.windows.storage.streams vrc_osc_tool.py
echo.
echo Fertig: dist\VRC-OSC-Tool.exe
pause
