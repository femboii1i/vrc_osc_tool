<div align="center">

# VRC OSC Tool

**Chatbox, Musik-Anzeige und Avatar-Parameter für VRChat, per OSC, ohne Zusatz-Accounts.**

![Plattform](https://img.shields.io/badge/Plattform-Linux-b9a572?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.9%2B-b9a572?style=flat-square)
![Version](https://img.shields.io/badge/Version-2.0-b9a572?style=flat-square)
![Lizenz](https://img.shields.io/badge/Lizenz-MIT-b9a572?style=flat-square)

Dunkle, eckige Oberfläche im Escape-from-Tarkov-Stil mit Tab-Menüleiste oben, farbigen Seiten und 10 Farbschemata.
Gebaut mit Python und customtkinter.

</div>

<!-- Screenshot einfügen: Bild nach docs/screenshot.png legen und diese Zeile aktivieren
![Screenshot](docs/screenshot.png)
-->

---

## Features

| Bereich | Was es macht |
|---|---|
| **Musik** | Zeigt Titel, Künstler, Cover und Fortschritt als Chatbox-Text. Optional mit synchronen Lyrics (LRCLIB). Quellen: Spotify, YouTube Music oder jeder Mediaplayer |
| **Chatbox** | Eigene Nachrichten, Tipp-Indikator, Auto-Resend, Verlauf, Rate-Limit-Schutz |
| **Uhr** | Uhrzeit und Datum in der Chatbox, wenn keine Musik läuft |
| **Furry-Detektor** | Spaßscan per Button oder Avatar-Parameter |
| **Parameter** | Avatar-Parameter senden (bool, int, float) mit Slider und Favoriten |
| **Monitor** | Eingehende OSC-Nachrichten live ansehen |
| **Aussehen** | 10 Farbschemata (Tarkov, Neon, Wald, Blut, Ozean, Sakura, VRChat, Dunkel, AMOLED, Hell), 19 Akzentfarben, "Bunte Seiten", Rundung, Skalierung, Transparenz, Vorlagen |

Es werden **keine API-Keys und keine Logins** gebraucht. Die Musik-Erkennung liest die Mediensteuerung deines Systems.

---

## Schnellstart

### Installation

```bash
git clone https://github.com/femboii1i/vrc-osc-tool.git
cd vrc-osc-tool
./start.sh
```

`start.sh` legt beim ersten Start eine venv an und installiert die Pakete.

Voraussetzungen:

- Python 3.9 oder neuer
- Tkinter: `sudo dnf install python3-tkinter` (Fedora) oder `sudo apt install python3-tk` (Debian/Ubuntu)
- `busctl` (bei den meisten Distributionen vorinstalliert), `playerctl` wird nur als Fallback genutzt

Optional: `vrc-osc-tool.desktop` anpassen und nach `~/.local/share/applications/` kopieren, dann erscheint das Tool im Anwendungsmenü.

### Manuell

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python vrc_osc_tool.py
```

---

## VRChat einrichten

1. Im Spiel: **Action Menu → Options → OSC → Enabled**
2. Im Tool unter **Einstellungen** prüfen: IP `127.0.0.1`, Senden-Port `9000`, Empfangen-Port `9001` (das sind VRChats Standardwerte)
3. Auf **Anwenden** klicken. Fertig.

---

## Musikquelle

Unter **Einstellungen → Musikquelle** wählst du, woher die Musik kommt:

| Quelle | Erkannt wird |
|---|---|
| **Spotify** | Spotify-Desktop-App |
| **YouTube Music** | Desktop-App (z. B. YouTube Music Desktop) oder Browser: Chrome/Chromium, Edge, Firefox, Brave, Opera, Vivaldi |
| **Beliebig** | Jeder MPRIS-fähige Player |

> **Hinweis zum Browser:** Die Mediensteuerung kann YouTube Music nicht von normalem YouTube unterscheiden.
> Im Browser wird deshalb alles erkannt, was dort gerade läuft. Bei Künstlern wie „Name - Topic" wird „- Topic" entfernt.

Die Erkennung läuft über MPRIS per D-Bus (`busctl`, Fallback `playerctl`).

---

## Konfiguration

Alle Einstellungen werden automatisch gespeichert:

`~/.vrc_osc_tool.json`

Zum Zurücksetzen die Datei einfach löschen.

---

## Fehlerbehebung

<details>
<summary><b>Fehlermeldung zu busctl oder playerctl</b></summary>

Mindestens eins der beiden muss vorhanden sein: `sudo dnf install playerctl` oder `sudo apt install playerctl`.
</details>

<details>
<summary><b>Die Chatbox zeigt nichts an</b></summary>

- Ist OSC in VRChat aktiviert? (Action Menu → Options → OSC → Enabled)
- Stimmen IP und Ports unter Einstellungen?
- Läuft gerade Musik in der gewählten Quelle? Sonst wird nichts gesendet.
- Nach einer VRChat-Neuinstallation OSC-Config zurücksetzen: Action Menu → Options → OSC → Reset Config
</details>

---

## Mitmachen

Ideen, Bugs und Pull Requests sind willkommen, siehe [CONTRIBUTING.md](CONTRIBUTING.md).
Änderungen stehen im [CHANGELOG](CHANGELOG.md).

## Autor

- VRChat: `:femboii1i`
- Discord: `finn454454`

## Lizenz

MIT, siehe [LICENSE](LICENSE).
