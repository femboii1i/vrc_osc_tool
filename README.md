# VRC OSC Tool

Modernes OSC-Tool für VRChat im VRChat-Menü-Look, gebaut mit Python und customtkinter.

## Features

- **Spotify Now Playing** (Cover, Titel, Fortschritt) automatisch in der Chatbox, optional mit synchronen Lyrics (LRCLIB)
- **Uhr** in der Chatbox, wenn keine Musik läuft
- **Furry-Detektor** (Spaßscan per Button oder Avatar-Parameter)
- **Chatbox:** manuelle Nachrichten, Tipp-Indikator, Auto-Resend, Verlauf
- **Parameter:** Avatar-Parameter senden (bool/int/float), Slider, Favoriten
- **Monitor:** eingehende OSC-Nachrichten live ansehen
- **Aussehen:** Paletten (VRChat, Dunkel, AMOLED, Hell), Akzentfarben, Templates

Die Spotify-Erkennung braucht keine API-Keys oder Logins und funktioniert mit der Spotify-Desktop-App.

## Installation (Linux)

```bash
git clone https://github.com/femboii1i/vrc-osc-tool.git
cd vrc-osc-tool
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python vrc_osc_tool.py
```

Oder einfach `./start.sh` ausführen, das legt die venv beim ersten Start selbst an.
Für einen Starter im Anwendungsmenü: `vrc-osc-tool.desktop` anpassen und nach `~/.local/share/applications/` kopieren.

Voraussetzungen: Python 3.9+, Tkinter (z. B. `sudo dnf install python3-tkinter`),
`busctl` (bei den meisten Distributionen vorinstalliert). `playerctl` wird nur als Fallback genutzt.

## VRChat einrichten

Action Menu → Options → OSC → **Enabled**.
Standard-Ports: `9000` (VRChat empfängt) und `9001` (VRChat sendet).

## Hinweis

Aktuell wird nur Linux aktiv unterstützt. Der Windows-Zweig (SMTC über `winsdk`) ist enthalten, aber ungetestet.

## Autor

- VRChat: `:femboii1i`
- Discord: `finn454454`

## Lizenz

MIT, siehe [LICENSE](LICENSE).
