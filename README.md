# VRC OSC Tool

Modernes OSC-Tool für VRChat im VRChat-Menü-Look, gebaut mit Python und customtkinter.
**Nur für Windows.**

## Features

- **Spotify Now Playing** (Cover, Titel, Fortschritt) automatisch in der Chatbox, optional mit synchronen Lyrics (LRCLIB)
- **Uhr** in der Chatbox, wenn keine Musik läuft
- **Furry-Detektor** (Spaßscan per Button oder Avatar-Parameter)
- **Chatbox:** manuelle Nachrichten, Tipp-Indikator, Auto-Resend, Verlauf
- **Parameter:** Avatar-Parameter senden (bool/int/float), Slider, Favoriten
- **Monitor:** eingehende OSC-Nachrichten live ansehen
- **Aussehen:** Paletten (VRChat, Dunkel, AMOLED, Hell), Akzentfarben, Templates

Die Spotify-Erkennung braucht keine API-Keys oder Logins und funktioniert mit der Spotify-Desktop-App
(über die Windows-Mediensteuerung).

## Installation

1. [Python 3.12](https://www.python.org/downloads/) installieren (beim Installer **"Add python.exe to PATH"** anhaken)
2. Repo als ZIP herunterladen (grüner Button **Code** → **Download ZIP**) und entpacken
3. **`start.bat`** doppelklicken. Beim ersten Start werden die Pakete automatisch installiert.

Oder per Terminal:

```bat
git clone https://github.com/DEIN-NAME/vrc-osc-tool.git
cd vrc-osc-tool
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python vrc_osc_tool.py
```

### Als .exe bauen (optional)

`build_exe.bat` doppelklicken. Danach liegt `dist\VRC-OSC-Tool.exe` bereit.

## VRChat einrichten

Action Menu → Options → OSC → **Enabled**.
Standard-Ports: `9000` (VRChat empfängt) und `9001` (VRChat sendet).

## Hinweise

- Python 3.12 wird empfohlen, weil `winsdk` für neuere Versionen teils keine fertigen Pakete hat.
- Windows fragt beim ersten Start evtl. nach einer Firewall-Freigabe (für den OSC-Empfang auf Port 9001).

## Autor

- VRChat: `:femboii1i`
- Discord: `evil femboy`

## Lizenz

MIT, siehe [LICENSE](LICENSE).
