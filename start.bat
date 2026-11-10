@echo off
setlocal enableextensions
cd /d "%~dp0"
title VRC OSC Tool - Start

rem ---------------------------------------------------------------
rem  1) Echtes Python finden (der Microsoft-Store-Platzhalter zaehlt nicht)
rem     Bevorzugt 3.12 / 3.13, weil 'winsdk' (Spotify unter Windows) dort sicher installierbar ist.
rem ---------------------------------------------------------------
set "PY="
for %%V in (3.12 3.13 3.11 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
    python -c "import sys" >nul 2>&1 && set "PY=python"
)
if not defined PY goto :nopython

rem ---------------------------------------------------------------
rem  2) Virtuelle Umgebung anlegen (kaputte .venv wird neu erstellt)
rem ---------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    if exist ".venv" rmdir /s /q ".venv"
    echo Erstelle virtuelle Umgebung ...
    %PY% -m venv .venv
    if errorlevel 1 goto :venvfail
)
if not exist ".venv\Scripts\python.exe" goto :venvfail

rem ---------------------------------------------------------------
rem  3) Pakete installieren (nur beim ersten Start bzw. nach Aenderung)
rem ---------------------------------------------------------------
if not exist ".venv\.deps_v3" (
    echo Installiere Pakete - das dauert beim ersten Mal etwas ...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
    ".venv\Scripts\python.exe" -m pip install python-osc customtkinter pillow
    if errorlevel 1 goto :pipfail
    echo Installiere Windows-Medienerkennung fuer Spotify ...
    ".venv\Scripts\python.exe" -m pip install winrt-runtime winrt-Windows.Foundation winrt-Windows.Foundation.Collections winrt-Windows.Media.Control winrt-Windows.Storage.Streams
    if errorlevel 1 (
        echo winrt nicht verfuegbar, versuche winsdk ...
        ".venv\Scripts\python.exe" -m pip install winsdk
        if errorlevel 1 (
            echo.
            echo [Hinweis] Die Spotify-Erkennung konnte nicht installiert werden. Das Tool startet
            echo           trotzdem, nur die Musik-Anzeige ist dann aus. Tipp: Python 3.12 installieren.
            echo.
        )
    )
    echo ok> ".venv\.deps_v3"
)

rem ---------------------------------------------------------------
rem  4) Tool starten (Konsole bleibt offen, damit Fehler sichtbar sind)
rem ---------------------------------------------------------------
echo Starte VRC OSC Tool ...
".venv\Scripts\python.exe" vrc_osc_tool.py
if errorlevel 1 (
    echo.
    echo Das Tool wurde mit einem Fehler beendet. Bitte die Meldung oben kopieren.
    pause
)
goto :eof

:nopython
echo.
echo  Es wurde KEIN echtes Python gefunden.
echo  (Die Meldung "Python wurde nicht gefunden" kommt vom Microsoft-Store-Platzhalter.)
echo.
where winget >nul 2>&1
if errorlevel 1 goto :manual
echo  Python 3.12 jetzt automatisch installieren? (ca. 1 Minute)
choice /c JN /m "Installieren (J/N)"
if errorlevel 2 goto :manual
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
echo.
echo  Fertig. Bitte dieses Fenster schliessen und start.bat NOCH EINMAL starten.
pause
goto :eof

:manual
echo  Bitte Python 3.12 installieren:  https://www.python.org/downloads/windows/
echo  WICHTIG: Beim Installieren unten "Add python.exe to PATH" anhaken!
echo  Danach start.bat nochmal starten.
start "" "https://www.python.org/downloads/windows/"
pause
goto :eof

:venvfail
echo.
echo  Die virtuelle Umgebung konnte nicht erstellt werden.
echo  Loesche den Ordner .venv (falls vorhanden) und starte start.bat erneut.
pause
goto :eof

:pipfail
echo.
echo  Pakete konnten nicht installiert werden. Internetverbindung pruefen und erneut starten.
if exist ".venv\.deps_v3" del ".venv\.deps_v3"
pause
goto :eof
