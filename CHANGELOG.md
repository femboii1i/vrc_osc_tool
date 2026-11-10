# Changelog

Alle wichtigen Änderungen am VRC OSC Tool. Format angelehnt an [Keep a Changelog](https://keepachangelog.com/de/).

## [2.0] - 2026-11-10

Große Überarbeitung: neues Layout, neue Farben, YouTube Music und Unterstützung für Windows und Linux.

### Neu
- **Neues Layout:** Tab-Menüleiste oben statt Seitenleiste, Statusleiste unten mit OSC-Status, VRChat-Verbindung und Copyright
- **Bunte Seiten:** jede Seite hat ihre eigene Farbe (Tab-Unterstrich, Farbstreifen, Überschrift), abschaltbar unter *Aussehen*
- **10 Farbschemata:** Tarkov (Standard), Neon, Wald, Blut, Ozean, Sakura, VRChat, Dunkel, AMOLED, Hell, mit Vorschau-Kacheln und automatisch passendem Akzent
- **19 Akzentfarben** als Raster, dazu eigene Hex-Farbe
- **YouTube Music:** Erkennung über Desktop-App oder Browser (Chrome, Edge, Firefox, Brave, Opera, Vivaldi)
- **Musikquelle:** neue Einstellung Spotify / YouTube Music / Beliebig, ersetzt den Schalter "Nur Spotify"
- **Chatbox komplett neu:** zwei Spalten, Zeichen-Balken, Live-Vorschau, Schnelltexte, Verlauf mit "Laden" und "Senden", "Verlauf leeren"
- **Tarkov-Look:** eckige Panels, Großbuchstaben, Khaki-Akzent, Schrift Bahnschrift (Windows)
- **Copyright und Autor** in der Statusleiste, im Fenstertitel und in der "Über"-Karte unter *Einstellungen*
- **Linux-Unterstützung:** Musik-Erkennung über MPRIS (`busctl`, Fallback `playerctl`)
- **Windows-Unterstützung:** Musik-Erkennung über die Mediensteuerung (`winrt`, Fallback `winsdk`)
- **Getrennte Pakete** für Windows (`start.bat`, `build_exe.bat`) und Linux (`start.sh`, `.desktop`-Starter)

### Verbessert
- Einheitlicher Look für alle Buttons, Eingabefelder, Schalter, Slider und Scrollbars
- Überschriften mit Untertitel auf jeder Seite
- Rundung der Panels jetzt ab 0 px einstellbar
- Lesbarere Umschalter (Kontrast von gewählt/nicht gewählt)
- "Künstler - Topic" wird zu "Künstler"
- Windows: Fenster passt sich an Bildschirmgröße und Skalierung (125 %/150 %) an, vorher wurde es unten abgeschnitten
- Windows: neues `start.bat` findet Python selbst und bietet die Installation per winget an
- README neu geschrieben, mit Fehlerbehebung zum Aufklappen

### Hinweis
- Die internen Entwicklungsstände 3.0 bis 3.7 sind in dieser Version zusammengefasst. Ab jetzt zählt die Version 2.0.
- Eine vorhandene `.vrc_osc_tool.json` behält alte Farbeinstellungen. Unter *Aussehen* ein Farbschema wählen und auf "Anwenden" klicken, um den neuen Look zu bekommen.
