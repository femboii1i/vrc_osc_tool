#!/usr/bin/env python3
"""
VRC OSC Tool
------------
(c) 2026 VRChat: :femboii1i  |  Discord: evil femboy

Modernes Tool für VRChat OSC:
  * Spotify:   Now Playing (Cover, Titel, Fortschritt) + automatisch in die Chatbox
               inkl. synchroner Lyrics (zur Laufzeit von LRCLIB geladen)
  * Uhr:       Uhrzeit/Datum in der Chatbox (wenn keine Musik läuft)
  * Furry-Detektor: Zufalls-Spaßscan, per Button oder Avatar-Parameter
  * Chatbox:   manuelle Nachrichten, Tipp-Indikator, Auto-Resend, Verlauf
  * Parameter: Avatar-Parameter senden (bool/int/float), Slider, Favoriten
  * Monitor:   eingehende OSC-Nachrichten live ansehen

Installation:
  pip install -r requirements.txt
In VRChat: Action Menu -> Options -> OSC -> Enabled

Die Spotify-Erkennung braucht KEINE API-Keys oder Logins und funktioniert
mit der Spotify-Desktop-App:
  * Windows: liest die Mediensteuerung (SMTC) über das Paket 'winsdk'
  * Linux:   liest MPRIS direkt über D-Bus (busctl, bei Fedora & Co. vorinstalliert),
             'playerctl' wird nur als Fallback genutzt
"""

import asyncio
import base64
import io
import json
import os
import queue
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

try:
    import customtkinter as ctk
    from PIL import Image
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient
except ImportError as exc:  # pragma: no cover
    sys.exit(f"Fehlendes Paket ({exc.name}). Bitte ausführen: pip install -r requirements.txt")

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
    from winsdk.windows.storage.streams import Buffer, DataReader, InputStreamOptions

    HAS_WINSDK = True
except Exception:
    HAS_WINSDK = False

# ----------------------------------------------------------------- Konstanten
CONFIG_FILE = Path.home() / ".vrc_osc_tool.json"
CHATBOX_LIMIT = 144
CHATBOX_MIN_GAP = 1.6  # VRChat limitiert die Chatbox auf ca. 1 Nachricht / 1,5 s
MONITOR_MAX_LINES = 1000
DEFAULT_TEMPLATE = "🎵 {artist} – {title}\n{bar} {pos}/{dur}"

APP_VERSION = "3.1"
AUTHOR_VRC = ":femboii1i"
AUTHOR_DISCORD = "evil femboy"
COPYRIGHT = f"© {time.strftime('%Y')} VRChat: {AUTHOR_VRC}  ·  Discord: {AUTHOR_DISCORD}"

# --- Theme: Diese Werte werden von apply_theme() beim Start / bei "Anwenden" überschrieben
BG = "#121212"
SIDEBAR = "#0a0a0a"
CARD = "#1b1b1b"
CARD_INNER = "#101010"
NEUTRAL = "#2a2a2a"
NEUTRAL_HOVER = "#383838"
ROW = "#222222"
ROW_HOVER = "#2e2e2e"
NAV_ACTIVE = "#1f1f1f"
TEXT_DIM = "#9a9a9a"
TEXT_MAIN = "#d8d8d8"
TEXT_SOFT = "#cfcfcf"
TEXT_LYRIC = "#e8e8e8"
TRACK = "#333333"
ART_FG = "#555555"
ACCENT = "#1DB954"
ACCENT_HOVER = "#1ed760"
ON_ACCENT = "black"
CARD_RADIUS = 20
INNER_RADIUS = 16
SIDEBAR_W = 200
WARN = "#f0a030"
DANGER = "#e5484d"

PALETTES = {
    "VRChat": dict(
        MODE="dark", BG="#0b1218", SIDEBAR="#070d12", CARD="#15222c", CARD_INNER="#0e1a22", NEUTRAL="#223441",
        NEUTRAL_HOVER="#2e4658", ROW="#1a2a36", ROW_HOVER="#243947", NAV_ACTIVE="#1c3340", TEXT_DIM="#7f98a8",
        TEXT_MAIN="#dbe9f1", TEXT_SOFT="#c3d6e1", TEXT_LYRIC="#eaf6fc", TRACK="#2a3f4e", ART_FG="#4d6677",
    ),
    "Dunkel": dict(
        MODE="dark", BG="#121212", SIDEBAR="#0a0a0a", CARD="#1b1b1b", CARD_INNER="#101010", NEUTRAL="#2a2a2a",
        NEUTRAL_HOVER="#383838", ROW="#222222", ROW_HOVER="#2e2e2e", NAV_ACTIVE="#1f1f1f", TEXT_DIM="#9a9a9a",
        TEXT_MAIN="#d8d8d8", TEXT_SOFT="#cfcfcf", TEXT_LYRIC="#e8e8e8", TRACK="#333333", ART_FG="#555555",
    ),
    "AMOLED": dict(
        MODE="dark", BG="#000000", SIDEBAR="#000000", CARD="#0d0d0d", CARD_INNER="#050505", NEUTRAL="#1a1a1a",
        NEUTRAL_HOVER="#2a2a2a", ROW="#111111", ROW_HOVER="#1c1c1c", NAV_ACTIVE="#151515", TEXT_DIM="#8a8a8a",
        TEXT_MAIN="#e0e0e0", TEXT_SOFT="#d0d0d0", TEXT_LYRIC="#f0f0f0", TRACK="#2a2a2a", ART_FG="#4a4a4a",
    ),
    "Hell": dict(
        MODE="light", BG="#f3f3f6", SIDEBAR="#e6e6ec", CARD="#ffffff", CARD_INNER="#f0f0f4", NEUTRAL="#dcdce3",
        NEUTRAL_HOVER="#cbcbd4", ROW="#efeff3", ROW_HOVER="#e3e3ea", NAV_ACTIVE="#d9d9e1", TEXT_DIM="#6a6a74",
        TEXT_MAIN="#2a2a32", TEXT_SOFT="#3a3a44", TEXT_LYRIC="#1a1a20", TRACK="#cfcfd8", ART_FG="#aaaaaa",
    ),
}
ACCENTS = {
    "VRChat-Cyan": "#1fc8d4",
    "Spotify-Grün": "#1DB954",
    "Neon-Pink": "#ff4fa3",
    "Ozean-Blau": "#3b9eff",
    "Sonnenuntergang": "#ff8a3d",
    "Violett": "#9b6bff",
    "Türkis": "#22d3c5",
    "Rot": "#ff4d5a",
    "Gelb": "#f5c518",
}
TEMPLATE_PRESETS = {
    "Standard": DEFAULT_TEMPLATE,
    "Minimal": "🎵 {artist} – {title}",
    "Kompakt": "🎵 {title} · {artist}\n{pos}/{dur}",
    "Mit Album": "🎵 {title}\n👤 {artist}\n💿 {album}",
    "Mit Lyrics": "🎵 {artist} – {title}\n{bar} {pos}/{dur}\n{lyric}",
    "Clean": "▶ {title}\n{artist}\n{bar}  {pos} / {dur}",
}

DEFAULT_CONFIG = {
    "ip": "127.0.0.1",
    "send_port": 9000,
    "recv_port": 9001,
    "favorites": [
        {"name": "VRCEmote", "type": "int", "value": "1"},
        {"name": "MuteSelf", "type": "bool", "value": "true"},
    ],
    "history": [],
    "template": DEFAULT_TEMPLATE,
    "interval": 5,
    "pause_mode": "Anzeigen",
    "show_bar": True,
    "only_spotify": True,
    "spotify_on": False,
    "ascii_mode": False,
    "clock_on": False,
    "clock_template": "🕐 {time} Uhr\n{weekday}, {date}",
    "show_lyrics": False,
    "lyric_offset": 0.0,
    "scan_param": "FurryScan",
    "scan_param_on": False,
    "scan_name": "",
    "palette": "VRChat",
    "accent": "#1fc8d4",
    "card_radius": 20,
    "ui_scale": 1.0,
    "opacity": 1.0,
    "compact_sidebar": False,
    "hidden_pages": [],
    "start_page": "",
}

FURRY_TIERS = [
    (10, ["Reiner Mensch. Fast schon langweilig.", "Kein Fell, keine Ohren, kein Verdacht.", "Zu 100% Hautfarbe."]),
    (30, ["Leicht verdächtig, aber noch okay.", "Hat bestimmt mal einen Fuchs süß gefunden.", "Ein Hauch von Flausch erkannt."]),
    (60, ["Hat definitiv schon mal Ohren anprobiert.", "Der Flausch ist stark in dir.", "Verdacht verdichtet sich."]),
    (85, ["Ohren-Verdacht bestätigt!", "Fursuit im Schrank. Ganz sicher.", "Der Schwanz wedelt schon."]),
    (100, ["MAXIMALER FLAUSCH-LEVEL!", "Offiziell: Vollblut-Fluffball.", "Das Fell hat gesprochen."]),
]
FURRY_PROOFS = [
    "Beweis: UwU-Rate kritisch",
    "Beweis: Schwanzwedel-Index hoch",
    "Beweis: Pfotenabdrücke gefunden",
    "Beweis: sagt 'rawr' ohne Anlass",
    "Beweis: Ohren zucken im Wind",
    "Beweis: Flauschfaktor gemessen",
]
FURRY_SCAN_LINES = ["Messe Flauschfaktor...", "Suche nach Fell...", "Zähle Schwänze...", "Analysiere UwU-Level..."]


# ------------------------------------------------------------------- Helfer
def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    try:
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def lighten(h, f=0.18):
    return "#%02x%02x%02x" % tuple(int(c + (255 - c) * f) for c in _rgb(h))


def on_color(h):
    r, g, b = _rgb(h)
    return "black" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "white"


def apply_theme(cfg):
    """Setzt die globalen Theme-Variablen aus der Config. Danach muss die UI neu gebaut werden."""
    pal = PALETTES.get(cfg.get("palette"), PALETTES["VRChat"])
    accent = cfg.get("accent") if _HEX_RE.match(str(cfg.get("accent", ""))) else "#1fc8d4"
    g = globals()
    for key, value in pal.items():
        if key != "MODE":
            g[key] = value
    g["ACCENT"], g["ACCENT_HOVER"], g["ON_ACCENT"] = accent, lighten(accent), on_color(accent)
    radius = max(4, min(30, int(cfg.get("card_radius", 14))))
    g["CARD_RADIUS"], g["INNER_RADIUS"] = radius, max(4, radius - 4)
    g["SIDEBAR_W"] = 72 if cfg.get("compact_sidebar") else 200
    ctk.set_appearance_mode("light" if pal["MODE"] == "light" else "dark")
    try:
        for widget in ("CTkButton", "CTkEntry", "CTkSegmentedButton"):
            ctk.ThemeManager.theme[widget]["corner_radius"] = max(6, radius - 2)
    except Exception:  # noqa: BLE001
        pass


def parse_value(vtype, raw):
    raw = str(raw).strip()
    if vtype == "bool":
        if raw.lower() in ("1", "true", "t", "yes", "y", "on"):
            return True
        if raw.lower() in ("0", "false", "f", "no", "n", "off"):
            return False
        raise ValueError(f"Ungültiger Bool-Wert: {raw!r}")
    if vtype == "int":
        return int(raw)
    return float(raw.replace(",", "."))


_ASCII_MAP = {"▬": "-", "●": "o", "–": "-", "—": "-", "⏸": "||", "▶": ">", "’": "'", "“": '"', "”": '"'}


def to_ascii(text):
    """Reduziert Text auf ASCII (Kompatibilitätsmodus, falls Sonderzeichen Probleme machen)."""
    for k, v in _ASCII_MAP.items():
        text = text.replace(k, v)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def to_photo(img):
    """PIL-Bild -> tk.PhotoImage (ohne PIL.ImageTk, nutzt Tk's eingebautes PNG)."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))


def fmt_time(seconds):
    s = int(max(0, seconds))
    return f"{s // 60}:{s % 60:02d}"


def make_bar(pos, dur, length=10):
    if dur <= 0:
        return "▬" * length
    i = min(length - 1, int(pos / dur * length))
    return "▬" * i + "●" + "▬" * (length - 1 - i)


def truncate(text, n):
    return text if len(text) <= n else text[: n - 1] + "…"


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def time_fields():
    lt = time.localtime()
    return dict(
        time=time.strftime("%H:%M", lt),
        time_s=time.strftime("%H:%M:%S", lt),
        date=time.strftime("%d.%m.", lt),
        weekday=_WEEKDAYS[lt.tm_wday],
    )


def build_clock_text(template):
    """Platzhalter: {time} {time_s} {date} {weekday}"""
    try:
        text = template.format_map(_SafeDict(**time_fields()))
    except (ValueError, IndexError, KeyError):
        text = template
    return text[:CHATBOX_LIMIT]


def build_chat_text(template, st, show_bar=True, paused=False, append_lyric=False):
    """Baut den Chatbox-Text aus dem Template. Platzhalter:
    {title} {artist} {album} {bar} {pos} {dur}"""
    title = truncate(st.get("title", ""), 45)
    artist = truncate(st.get("artist", ""), 30)
    if paused:
        text = f"⏸ {artist} – {title}" if artist else f"⏸ {title}"
        return text[:CHATBOX_LIMIT]
    fields = _SafeDict(
        title=title,
        artist=artist,
        album=truncate(st.get("album", ""), 30),
        bar=make_bar(st.get("pos", 0), st.get("dur", 0)) if show_bar else "",
        pos=fmt_time(st.get("pos", 0)),
        dur=fmt_time(st.get("dur", 0)),
        lyric=truncate(st.get("lyric", ""), 60),
        **time_fields(),
    )
    try:
        text = template.format_map(fields)
    except (ValueError, IndexError, KeyError):
        text = template
    text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
    if append_lyric and st.get("lyric") and "{lyric}" not in template:
        text = text.rstrip("\n") + "\n" + truncate(st["lyric"], 60)
    return text[:CHATBOX_LIMIT]


# ------------------------------------------------------- Windows Media Watcher
class LyricsFetcher:
    """Holt synchronisierte Lyrics zur Laufzeit von LRCLIB (https://lrclib.net).
    Es wird nichts dauerhaft gespeichert, nur kurz im Arbeitsspeicher gecacht."""

    UA = "VRC-OSC-Tool/2.0"

    def __init__(self):
        self.lock = threading.Lock()
        self.key = None
        self.lines = []  # [(sekunden, text)]
        self.status = "none"  # none | loading | found | missing | error
        self._cache = {}

    def request(self, key, artist, title, album, duration):
        with self.lock:
            if key == self.key:
                return
            self.key = key
            cached = self._cache.get(key)
            if cached is not None:
                self.lines, self.status = cached
                return
            self.lines, self.status = [], "loading"
        threading.Thread(target=self._work, args=(key, artist, title, album, duration), daemon=True).start()

    def _fetch(self, path, params):
        url = "https://lrclib.net/api/" + path + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": self.UA})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _find(self, artist, title, album, duration):
        if duration > 0 and album:
            try:
                return self._fetch(
                    "get",
                    {"artist_name": artist, "track_name": title, "album_name": album, "duration": int(round(duration))},
                )
            except urllib.error.HTTPError as exc:
                if exc.code not in (400, 404):
                    raise
        for r in self._fetch("search", {"track_name": title, "artist_name": artist}) or []:
            if not r.get("syncedLyrics"):
                continue
            if duration > 0 and abs((r.get("duration") or 0) - duration) > 4:
                continue
            return r
        return None

    @staticmethod
    def parse(lrc):
        out = []
        for raw in (lrc or "").splitlines():
            stamps = re.findall(r"\[(\d+):(\d+(?:\.\d+)?)\]", raw)
            if not stamps:
                continue
            text = re.sub(r"\[[^\]]*\]", "", raw).strip()
            for m, s in stamps:
                out.append((int(m) * 60 + float(s), text))
        out.sort(key=lambda x: x[0])
        return out

    def _work(self, key, artist, title, album, duration):
        lines, status = [], "missing"
        try:
            data = self._find(artist, title, album, duration)
            lines = self.parse((data or {}).get("syncedLyrics", ""))
            status = "found" if lines else "missing"
        except Exception:  # noqa: BLE001
            status = "error"
        with self.lock:
            if self.key == key:
                self.lines, self.status = lines, status
            if status != "error":
                if len(self._cache) > 50:
                    self._cache.clear()
                self._cache[key] = (lines, status)

    def line_at(self, pos):
        with self.lock:
            lines = self.lines
        current = ""
        for t, text in lines:
            if t <= pos:
                current = text
            else:
                break
        return current


# ------------------------------------------------------- Media Watcher
class MediaWatcher(threading.Thread):
    """Liest im Hintergrund die Windows-Mediensteuerung (SMTC) aus."""

    def __init__(self, only_spotify=True):
        super().__init__(daemon=True)
        self.only_spotify = only_spotify
        self._halt = threading.Event()
        self.lock = threading.Lock()
        if IS_WINDOWS:
            err = None if HAS_WINSDK else "Paket 'winsdk' fehlt: pip install winsdk (bei Fehlern Python 3.12 nutzen)."
        elif IS_LINUX:
            err = None if (shutil.which("busctl") or shutil.which("playerctl")) else (
                "Weder 'busctl' noch 'playerctl' gefunden. Installieren: sudo dnf install playerctl "
                "(Debian/Ubuntu: sudo apt install playerctl)"
            )
        else:
            err = "Die Spotify-Erkennung funktioniert nur unter Windows und Linux."
        self.state = {
            "error": err,
            "active": False,
            "playing": False,
            "title": "",
            "artist": "",
            "album": "",
            "pos": 0.0,
            "dur": 0.0,
            "art": None,
            "art_version": 0,
            "app": "",
        }

    def snapshot(self):
        with self.lock:
            return dict(self.state)

    def stop(self):
        self._halt.set()

    def run(self):
        if self.state["error"]:
            return
        try:
            if IS_WINDOWS:
                asyncio.run(self._loop())
            else:
                self._run_linux()
        except Exception as exc:  # noqa: BLE001
            with self.lock:
                self.state["error"] = f"Media-Watcher abgestürzt: {exc}"

    # ---- Linux: MPRIS über playerctl
    @staticmethod
    def _fetch_art_url(url):
        if not url:
            return None
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return Image.open(io.BytesIO(resp.read())).convert("RGB")
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _unwrap(v):
        """Entfernt die {"type":..,"data":..}-Hüllen aus busctl --json."""
        if isinstance(v, dict):
            if set(v.keys()) == {"type", "data"}:
                return MediaWatcher._unwrap(v["data"])
            return {k: MediaWatcher._unwrap(x) for k, x in v.items()}
        if isinstance(v, list):
            return [MediaWatcher._unwrap(x) for x in v]
        return v

    def _read_busctl(self):
        """MPRIS direkt über D-Bus (busctl ist bei systemd-Distros wie Fedora dabei)."""
        base = ["busctl", "--user"]
        out = subprocess.run(base + ["--no-legend", "list"], capture_output=True, text=True, timeout=3).stdout
        names = [ln.split()[0] for ln in out.splitlines() if ln.startswith("org.mpris.MediaPlayer2.")]
        if self.only_spotify:
            names = [n for n in names if "spotify" in n.lower()]
        best = None
        for name in names:
            res = subprocess.run(
                base + ["--json=short", "call", name, "/org/mpris/MediaPlayer2",
                        "org.freedesktop.DBus.Properties", "GetAll", "s", "org.mpris.MediaPlayer2.Player"],
                capture_output=True, text=True, timeout=3,
            )
            if res.returncode != 0:
                continue
            data = self._unwrap(json.loads(res.stdout))
            props = data[0] if isinstance(data, list) and data else data
            if not isinstance(props, dict):
                continue
            md = props.get("Metadata") or {}
            if not isinstance(md, dict):
                md = {}
            artist = md.get("xesam:artist", "")
            if isinstance(artist, list):
                artist = ", ".join(str(a) for a in artist)
            row = [
                str(props.get("PlaybackStatus", "")),
                str(md.get("xesam:title", "")),
                str(artist),
                str(md.get("xesam:album", "")),
                str(md.get("mpris:length", 0)),
                str(props.get("Position", 0)),
                str(md.get("mpris:artUrl", "")),
            ]
            if best is None or row[0] == "Playing":
                best = row
            if row[0] == "Playing":
                break
        return best

    def _read_playerctl(self):
        fmt = "{{status}}\t{{title}}\t{{artist}}\t{{album}}\t{{mpris:length}}\t{{position}}\t{{mpris:artUrl}}"
        cmd = ["playerctl"] + (["-p", "spotify"] if self.only_spotify else []) + ["metadata", "--format", fmt]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.rstrip("\n").split("\t")
        return None

    def _read_linux(self):
        if shutil.which("busctl"):
            try:
                row = self._read_busctl()
                if row:
                    return row
            except Exception:  # noqa: BLE001
                pass
        if shutil.which("playerctl"):
            try:
                return self._read_playerctl()
            except Exception:  # noqa: BLE001
                return None
        return None

    def _run_linux(self):
        last_key = None
        art_version = 0
        while not self._halt.is_set():
            parts = self._read_linux()

            if not parts or len(parts) < 7:
                with self.lock:
                    self.state.update(active=False, playing=False)
                last_key = None
            else:
                status, title, artist, album, length, position, art_url = parts[:7]

                def to_sec(v):
                    try:
                        return max(0.0, int(v) / 1_000_000)
                    except ValueError:
                        return 0.0

                key = (title, artist, album)
                art, art_changed = None, False
                if key != last_key:
                    art = self._fetch_art_url(art_url)
                    art_version += 1
                    art_changed = True
                    last_key = key
                with self.lock:
                    self.state.update(
                        active=bool(title or artist),
                        playing=status.strip().lower() == "playing",
                        title=title,
                        artist=artist,
                        album=album,
                        pos=to_sec(position),
                        dur=to_sec(length),
                        app="spotify",
                    )
                    if art_changed:
                        self.state["art"] = art
                        self.state["art_version"] = art_version
            self._halt.wait(0.8)

    def _pick(self, mgr):
        sessions = list(mgr.get_sessions())
        for s in sessions:
            if "spotify" in (s.source_app_user_model_id or "").lower():
                return s
        if self.only_spotify:
            return None
        return mgr.get_current_session() or (sessions[0] if sessions else None)

    @staticmethod
    async def _fetch_art(props):
        ref = props.thumbnail
        if ref is None:
            return None
        stream = await ref.open_read_async()
        size = stream.size
        buf = Buffer(size)
        await stream.read_async(buf, size, InputStreamOptions.READ_AHEAD)
        reader = DataReader.from_buffer(buf)
        data = bytearray(buf.length)
        reader.read_bytes(data)
        return Image.open(io.BytesIO(bytes(data))).convert("RGB")

    async def _loop(self):
        mgr = await MediaManager.request_async()
        last_key = None
        base_pos = 0.0
        base_t = time.monotonic()
        last_rep = None
        cur_pos = 0.0
        art_version = 0

        while not self._halt.is_set():
            try:
                session = self._pick(mgr)
                if session is None:
                    with self.lock:
                        self.state.update(active=False, playing=False)
                    last_key = None
                else:
                    props = await session.try_get_media_properties_async()
                    info = session.get_playback_info()
                    tl = session.get_timeline_properties()
                    playing = info.playback_status == PlaybackStatus.PLAYING
                    title = props.title or ""
                    artist = props.artist or ""
                    album = props.album_title or ""
                    dur = max(0.0, (tl.end_time - tl.start_time).total_seconds())
                    rep = tl.position.total_seconds()
                    now = time.monotonic()
                    key = (title, artist, album)

                    art_changed = False
                    art = None
                    if key != last_key:
                        try:
                            art = await self._fetch_art(props)
                        except Exception:  # noqa: BLE001
                            art = None
                        art_version += 1
                        art_changed = True
                        cur_pos = rep
                        base_pos, base_t, last_rep = rep, now, rep
                        last_key = key
                    elif rep != last_rep:
                        base_pos, base_t, last_rep = rep, now, rep
                        cur_pos = rep

                    if playing:
                        cur_pos = base_pos + (now - base_t)
                    if dur > 0:
                        cur_pos = min(cur_pos, dur)

                    with self.lock:
                        self.state.update(
                            active=bool(title or artist),
                            playing=playing,
                            title=title,
                            artist=artist,
                            album=album,
                            pos=cur_pos,
                            dur=dur,
                            app=session.source_app_user_model_id or "",
                        )
                        if art_changed:
                            self.state["art"] = art
                            self.state["art_version"] = art_version
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(0.5)


# ------------------------------------------------------------------------ App
class App(ctk.CTk):
    NAV = [
        ("🎵  Spotify", "spotify"),
        ("💬  Chatbox", "chat"),
        ("🕐  Uhr", "clock"),
        ("🐾  Furry-Detektor", "furry"),
        ("🎛  Parameter", "params"),
        ("📡  Monitor", "monitor"),
        ("🎨  Aussehen", "look"),
        ("⚙  Einstellungen", "settings"),
    ]

    def __init__(self):
        cfg = load_config()
        ctk.set_default_color_theme("green")
        apply_theme(cfg)
        scale = float(cfg.get("ui_scale", 1.0))
        ctk.set_widget_scaling(scale)
        ctk.set_window_scaling(scale)
        super().__init__(fg_color=BG)
        self.title(f"VRC OSC Tool v{APP_VERSION} · {AUTHOR_VRC}")
        self.geometry("1040x700")
        self.minsize(920, 620)
        try:
            self.attributes("-alpha", float(cfg.get("opacity", 1.0)))
        except Exception:  # noqa: BLE001
            pass

        self.cfg = cfg
        self._current_page = "spotify"
        self.client = None
        self.server = None
        self.msg_queue = queue.Queue()
        self.last_values = {}
        self.last_osc_ts = 0.0  # wann zuletzt Daten von VRChat kamen
        self.sent_count = 0
        self.last_sent_time = ""
        self.lyrics = LyricsFetcher()
        self._hold_until = 0.0  # solange pausiert die Auto-Anzeige (z. B. während eines Scans)
        self._scan_trigger = False
        self._scan_prev = False
        self.auto_job = None

        # Spotify-Zustand
        self.watcher = MediaWatcher(self.cfg["only_spotify"])
        self.watcher.start()
        self._art_img = None
        self._art_version = -1
        self._chat_ts = 0.0
        self._sp_key = None
        self._sp_playing = False
        self._sp_ts = 0.0
        self._sp_shown = False

        self._build_layout()
        self._apply_connection()
        start = self.cfg.get("start_page") or "spotify"
        if start not in self.nav_buttons:
            start = next(iter(self.nav_buttons))
        if self.cfg.get("start_page"):
            self.cfg["start_page"] = ""
            save_config(self.cfg)
        self.show_page(start)
        self.after(150, self._poll_osc)
        self.after(300, self._ui_tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----------------------------------------------------------- Grundlayout
    def _card(self, parent, **kw):
        return ctk.CTkFrame(
            parent, fg_color=CARD, corner_radius=CARD_RADIUS, border_width=1, border_color=TRACK, **kw
        )

    def _h1(self, parent, text):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=26, weight="bold"), anchor="w")

    def _h2(self, parent, text):
        return ctk.CTkLabel(
            parent, text=text, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_DIM, anchor="w"
        )

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        side = ctk.CTkFrame(self, width=SIDEBAR_W, fg_color=SIDEBAR, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        compact = bool(self.cfg.get("compact_sidebar"))

        # Logo-Plakette im VRChat-Stil
        logo = ctk.CTkFrame(side, fg_color=ACCENT, corner_radius=22, height=44, width=44 if compact else 150)
        logo.pack(anchor="center" if compact else "w", padx=0 if compact else 18, pady=(24, 4))
        logo.pack_propagate(False)
        ctk.CTkLabel(
            logo, text="VRC" if compact else "VRC OSC", font=ctk.CTkFont(size=18, weight="bold"), text_color=ON_ACCENT
        ).pack(expand=True)
        ctk.CTkLabel(side, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=12), text_color=TEXT_DIM).pack(
            anchor="center" if compact else "w", padx=0 if compact else 24, pady=(0, 18)
        )

        self.nav_buttons = {}
        hidden = set(self.cfg.get("hidden_pages", [])) - {"look", "settings"}
        for label, key in self.NAV:
            if key in hidden:
                continue
            b = ctk.CTkButton(
                side,
                text=label.split()[0] if compact else label,
                anchor="center" if compact else "w",
                height=44,
                corner_radius=22,
                fg_color="transparent",
                hover_color=NAV_ACTIVE,
                text_color=TEXT_MAIN,
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda k=key: self.show_page(k),
            )
            b.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = b

        # Copyright unten in der Seitenleiste
        self.lbl_copy = ctk.CTkLabel(
            side,
            text="©\n:femboii1i" if compact else f"© {time.strftime('%Y')}\nVRChat: {AUTHOR_VRC}\nDiscord: {AUTHOR_DISCORD}",
            font=ctk.CTkFont(size=10), text_color=TEXT_DIM, justify="center" if compact else "left",
            anchor="center" if compact else "w",
        )
        self.lbl_copy.pack(side="bottom", anchor="center" if compact else "w", padx=0 if compact else 18, pady=(6, 16))

        self.lbl_status = ctk.CTkLabel(
            side, text="", font=ctk.CTkFont(size=11), text_color=TEXT_DIM, justify="left", anchor="w"
        )
        self.lbl_vrc = ctk.CTkLabel(
            side, text="", font=ctk.CTkFont(size=11), text_color=TEXT_DIM, justify="left", anchor="w"
        )
        if not compact:  # in der schmalen Seitenleiste ist kein Platz für die Statustexte
            self.lbl_status.pack(side="bottom", anchor="w", padx=18, pady=(10, 4))
            self.lbl_vrc.pack(side="bottom", anchor="w", padx=18)

        container = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        container.grid(row=0, column=1, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.pages = {}
        for _, key in self.NAV:
            page = ctk.CTkFrame(container, fg_color=BG, corner_radius=0)
            page.grid(row=0, column=0, sticky="nsew", padx=24, pady=20)
            page.grid_columnconfigure(0, weight=1)
            self.pages[key] = page

        self._build_spotify(self.pages["spotify"])
        self._build_chat(self.pages["chat"])
        self._build_clock(self.pages["clock"])
        self._build_furry(self.pages["furry"])
        self._build_params(self.pages["params"])
        self._build_look(self.pages["look"])
        self._build_monitor(self.pages["monitor"])
        self._build_settings(self.pages["settings"])

        self.footer = ctk.CTkLabel(
            container, text="Bereit.", anchor="w", text_color=TEXT_DIM, font=ctk.CTkFont(size=11)
        )
        self.footer.grid(row=1, column=0, sticky="ew", padx=26, pady=(0, 8))
        ctk.CTkLabel(
            container, text=COPYRIGHT, anchor="e", text_color=TEXT_DIM, font=ctk.CTkFont(size=11)
        ).grid(row=1, column=0, sticky="e", padx=26, pady=(0, 8))
        self._layout_widgets = [side, container]

    def show_page(self, key):
        self._current_page = key
        self.pages[key].tkraise()
        for k, b in self.nav_buttons.items():
            b.configure(
                fg_color=ACCENT if k == key else "transparent",
                text_color=ON_ACCENT if k == key else TEXT_MAIN,
                hover_color=ACCENT_HOVER if k == key else NAV_ACTIVE,
            )

    def log(self, msg):
        self.footer.configure(text=f"{time.strftime('%H:%M:%S')}  {msg}")

    # --------------------------------------------------------- Spotify-Seite
    def _build_spotify(self, page):
        page.grid_rowconfigure(2, weight=1)
        self._h1(page, "Spotify · Now Playing").grid(row=0, column=0, sticky="w", pady=(0, 12))

        np = self._card(page)
        np.grid(row=1, column=0, sticky="ew")
        np.grid_columnconfigure(1, weight=1)

        self._placeholder = to_photo(Image.new("RGB", (220, 220), NEUTRAL))
        self.lbl_art = tk.Label(
            np, text="♪", image=self._placeholder, compound="center", font=("Segoe UI", 54), fg=ART_FG,
            bg=CARD, bd=0, highlightthickness=0,
        )
        self.lbl_art.grid(row=0, column=0, rowspan=2, padx=20, pady=20)

        info = ctk.CTkFrame(np, fg_color="transparent")
        info.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=(24, 0))
        info.grid_columnconfigure(0, weight=1)
        self.lbl_title = ctk.CTkLabel(
            info, text="Nichts läuft", font=ctk.CTkFont(size=28, weight="bold"), anchor="w", justify="left", wraplength=480
        )
        self.lbl_title.grid(row=0, column=0, sticky="w")
        self.lbl_artist = ctk.CTkLabel(info, text="", font=ctk.CTkFont(size=17), anchor="w", text_color=TEXT_SOFT)
        self.lbl_artist.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.lbl_album = ctk.CTkLabel(info, text="", font=ctk.CTkFont(size=13), anchor="w", text_color=TEXT_DIM)
        self.lbl_album.grid(row=2, column=0, sticky="w")
        self.lbl_state = ctk.CTkLabel(info, text="", font=ctk.CTkFont(size=12, weight="bold"), anchor="w", text_color=ACCENT)
        self.lbl_state.grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.lbl_lyric = ctk.CTkLabel(
            info, text="", font=ctk.CTkFont(size=15, slant="italic"), anchor="w", justify="left",
            wraplength=480, text_color=TEXT_LYRIC,
        )
        self.lbl_lyric.grid(row=4, column=0, sticky="w", pady=(10, 0))

        prog = ctk.CTkFrame(np, fg_color="transparent")
        prog.grid(row=1, column=1, sticky="sew", padx=(0, 20), pady=(0, 24))
        prog.grid_columnconfigure(1, weight=1)
        self.lbl_pos = ctk.CTkLabel(prog, text="0:00", text_color=TEXT_DIM, width=44)
        self.lbl_pos.grid(row=0, column=0)
        self.bar = ctk.CTkProgressBar(prog, height=8, progress_color=ACCENT, fg_color=TRACK)
        self.bar.set(0)
        self.bar.grid(row=0, column=1, sticky="ew", padx=8)
        self.lbl_dur = ctk.CTkLabel(prog, text="0:00", text_color=TEXT_DIM, width=44)
        self.lbl_dur.grid(row=0, column=2)

        # Chatbox-Anzeige
        cb = self._card(page)
        cb.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        cb.grid_columnconfigure(0, weight=1)
        cb.grid_columnconfigure(1, weight=1)

        head = ctk.CTkFrame(cb, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 4))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="In VRChat-Chatbox anzeigen", font=ctk.CTkFont(size=16, weight="bold"), anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        self.sp_on = ctk.BooleanVar(value=self.cfg["spotify_on"])
        ctk.CTkButton(
            head, text="Jetzt senden", width=110, fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER, command=self._send_now
        ).grid(row=0, column=1, sticky="e", padx=(0, 14))
        ctk.CTkSwitch(
            head, text="Aktiv", variable=self.sp_on, progress_color=ACCENT, command=self._on_sp_toggle
        ).grid(row=0, column=2, sticky="e")

        left = ctk.CTkFrame(cb, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(4, 16))
        left.grid_columnconfigure(0, weight=1)
        self._h2(left, "VORSCHAU").grid(row=0, column=0, sticky="w")
        prev = ctk.CTkFrame(left, fg_color=CARD_INNER, corner_radius=INNER_RADIUS)
        prev.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.lbl_preview = ctk.CTkLabel(
            prev, text="", justify="left", anchor="w", font=ctk.CTkFont(size=14), wraplength=360
        )
        self.lbl_preview.pack(fill="x", padx=14, pady=12)
        self.lbl_sp_hint = ctk.CTkLabel(left, text="", text_color=WARN, justify="left", anchor="w", wraplength=380)
        self.lbl_sp_hint.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.lbl_sent = ctk.CTkLabel(left, text="", text_color=TEXT_DIM, justify="left", anchor="w")
        self.lbl_sent.grid(row=3, column=0, sticky="w", pady=(8, 0))
        ctk.CTkLabel(
            left, text="Platzhalter: {title} {artist} {album} {bar} {pos} {dur} {lyric} {time} {date} {weekday}",
            text_color=TEXT_DIM, justify="left", anchor="w", wraplength=380, font=ctk.CTkFont(size=11),
        ).grid(row=4, column=0, sticky="w", pady=(8, 0))

        right = ctk.CTkFrame(cb, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(4, 16))
        right.grid_columnconfigure(0, weight=1)
        trow = ctk.CTkFrame(right, fg_color="transparent")
        trow.grid(row=0, column=0, sticky="ew")
        trow.grid_columnconfigure(0, weight=1)
        self._h2(trow, "TEMPLATE").grid(row=0, column=0, sticky="w")
        self.preset_menu = ctk.CTkOptionMenu(
            trow, values=list(TEMPLATE_PRESETS), width=130, height=26, fg_color=NEUTRAL,
            button_color=NEUTRAL_HOVER, button_hover_color=ACCENT, text_color=TEXT_MAIN,
            dynamic_resizing=False, command=self._load_preset,
        )
        self.preset_menu.set("Vorlage wählen…")
        self.preset_menu.grid(row=0, column=1, sticky="e")
        self.txt_template = ctk.CTkTextbox(right, height=64, fg_color=CARD_INNER, corner_radius=INNER_RADIUS)
        self.txt_template.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.txt_template.insert("1.0", self.cfg["template"])
        self.txt_template.bind("<KeyRelease>", lambda e: self._on_template_change())

        row = ctk.CTkFrame(right, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew")
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(row, text="Update alle").grid(row=0, column=0, padx=(0, 8))
        self.sp_interval = ctk.DoubleVar(value=float(self.cfg["interval"]))
        ctk.CTkSlider(
            row, from_=2, to=25, number_of_steps=23, variable=self.sp_interval, progress_color=ACCENT,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER, command=self._on_interval,
        ).grid(row=0, column=1, sticky="ew")
        self.lbl_interval = ctk.CTkLabel(row, text=f"{int(self.cfg['interval'])} s", width=40)
        self.lbl_interval.grid(row=0, column=2, padx=(8, 0))

        self.show_bar = ctk.BooleanVar(value=self.cfg["show_bar"])
        ctk.CTkSwitch(
            right, text="Fortschrittsbalken", variable=self.show_bar, progress_color=ACCENT,
            command=self._on_template_change,
        ).grid(row=3, column=0, sticky="w", pady=(10, 0))

        prow = ctk.CTkFrame(right, fg_color="transparent")
        prow.grid(row=4, column=0, sticky="w", pady=(10, 0))
        ctk.CTkLabel(prow, text="Bei Pause:").pack(side="left", padx=(0, 8))
        self.pause_mode = ctk.StringVar(value=self.cfg["pause_mode"])
        ctk.CTkSegmentedButton(
            prow, values=["Anzeigen", "Ausblenden"], variable=self.pause_mode, selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER, command=lambda v: self._on_template_change(),
        ).pack(side="left")

        self.show_lyrics = ctk.BooleanVar(value=self.cfg["show_lyrics"])
        ctk.CTkSwitch(
            right, text="Lyrics anzeigen (synchron, via LRCLIB)", variable=self.show_lyrics,
            progress_color=ACCENT, command=self._on_template_change,
        ).grid(row=5, column=0, sticky="w", pady=(10, 0))
        lrow = ctk.CTkFrame(right, fg_color="transparent")
        lrow.grid(row=6, column=0, sticky="ew", pady=(6, 0))
        lrow.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(lrow, text="Lyric-Versatz").grid(row=0, column=0, padx=(0, 8))
        self.lyric_offset = ctk.DoubleVar(value=float(self.cfg["lyric_offset"]))
        ctk.CTkSlider(
            lrow, from_=-3, to=3, number_of_steps=24, variable=self.lyric_offset, progress_color=ACCENT,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER, command=lambda v: self._on_template_change(),
        ).grid(row=0, column=1, sticky="ew")
        self.lbl_offset = ctk.CTkLabel(lrow, text=f"{float(self.cfg['lyric_offset']):+.1f} s", width=56)
        self.lbl_offset.grid(row=0, column=2, padx=(8, 0))

    def _load_preset(self, name):
        self.txt_template.delete("1.0", "end")
        self.txt_template.insert("1.0", TEMPLATE_PRESETS[name])
        self.preset_menu.set("Vorlage wählen…")
        self._on_template_change()

    def _send_now(self):
        st = self.watcher.snapshot()
        if not st["active"]:
            messagebox.showinfo("Hinweis", "In Spotify läuft gerade nichts, deshalb wird nichts gesendet.")
            return
        paused = not st["playing"] and self.pause_mode.get() == "Anzeigen"
        self.chat_send(self._render_chat(st, paused=paused), force=True)

    def _on_sp_toggle(self):
        self.cfg["spotify_on"] = bool(self.sp_on.get())
        save_config(self.cfg)
        if self.sp_on.get():
            self._sp_key, self._sp_playing, self._sp_ts = None, False, 0.0
        elif self._sp_shown and not self.clock_on.get():
            self.chat_send("", force=True)
            self._sp_shown = False

    def _on_interval(self, v):
        self.lbl_interval.configure(text=f"{int(float(v))} s")
        self.cfg["interval"] = int(float(v))
        save_config(self.cfg)

    def _on_template_change(self):
        self.cfg["template"] = self.txt_template.get("1.0", "end-1c")
        self.cfg["show_bar"] = bool(self.show_bar.get())
        self.cfg["pause_mode"] = self.pause_mode.get()
        self.cfg["show_lyrics"] = bool(self.show_lyrics.get())
        self.cfg["lyric_offset"] = round(float(self.lyric_offset.get()), 1)
        self.lbl_offset.configure(text=f"{self.cfg['lyric_offset']:+.1f} s")
        save_config(self.cfg)

    # -------------------------------------------------------- Spotify-Logik
    def _render_chat(self, st, paused=False):
        return build_chat_text(
            self.txt_template.get("1.0", "end-1c"), st, bool(self.show_bar.get()), paused,
            append_lyric=bool(self.show_lyrics.get()),
        )

    def _spotify_autosend(self, st):
        """Zentrale Auto-Anzeige: Musik > Uhr > leer. Während eines Scans pausiert sie."""
        sp_on = bool(self.sp_on.get())
        clock_on = bool(self.clock_on.get())
        now = time.monotonic()
        if not (sp_on or clock_on) or now < self._hold_until:
            return

        music = sp_on and st["active"]
        text, key = "", None
        if music and st["playing"]:
            key = ("music", st["title"], st["artist"], st.get("lyric") if self.show_lyrics.get() else None)
            text = self._render_chat(st)
        elif music and self.pause_mode.get() == "Anzeigen" and not clock_on:
            key = ("paused", st["title"], st["artist"])
            text = self._render_chat(st, paused=True)
        elif clock_on:
            text = build_clock_text(self.txt_clock.get("1.0", "end-1c"))
            key = ("clock", text)

        if not text:
            if self._sp_shown and self.chat_send(""):
                self._sp_shown = False
                self._sp_key = None
            return
        if key != self._sp_key or now - self._sp_ts >= self.sp_interval.get():
            if self.chat_send(text):
                self._sp_key, self._sp_ts, self._sp_shown = key, now, True

    def _ui_tick(self):
        st = self.watcher.snapshot()

        if self._scan_trigger:
            self._scan_trigger = False
            self._run_scan()

        st["lyric"] = ""
        lyric_txt = ""
        if st["active"] and self.show_lyrics.get():
            self.lyrics.request(
                (st["title"], st["artist"], st["album"]),
                st["artist"].split(",")[0].strip(), st["title"], st["album"], st["dur"],
            )
            st["lyric"] = self.lyrics.line_at(st["pos"] + float(self.lyric_offset.get()))
            lyric_txt = ("♪ " + st["lyric"]) if st["lyric"] else {
                "loading": "Lyrics werden geladen…",
                "missing": "Keine synchronisierten Lyrics gefunden",
                "error": "Lyrics-Server nicht erreichbar",
            }.get(self.lyrics.status, "")
        self.lbl_lyric.configure(text=lyric_txt)

        tf = time_fields()
        self.lbl_clock.configure(text=tf["time_s"])
        self.lbl_clock_prev.configure(text=build_clock_text(self.txt_clock.get("1.0", "end-1c")))

        if self.last_osc_ts:
            self.lbl_vrc.configure(text="● VRChat-Daten empfangen ✓", text_color=ACCENT)
        else:
            self.lbl_vrc.configure(text="● Noch keine Daten von VRChat", text_color=WARN)
        if self.sent_count:
            self.lbl_sent.configure(text=f"Zuletzt an VRChat gesendet: {self.last_sent_time}  ({self.sent_count}×)")
        else:
            self.lbl_sent.configure(text="Noch nichts an VRChat gesendet.")

        if st["error"]:
            self.lbl_sp_hint.configure(text=st["error"])
        else:
            self.lbl_sp_hint.configure(text="")

        if st["active"]:
            self.lbl_title.configure(text=st["title"] or "Unbekannter Titel")
            self.lbl_artist.configure(text=st["artist"])
            self.lbl_album.configure(text=st["album"])
            self.lbl_state.configure(text="▶  SPIELT" if st["playing"] else "⏸  PAUSIERT")
            self.lbl_pos.configure(text=fmt_time(st["pos"]))
            self.lbl_dur.configure(text=fmt_time(st["dur"]))
            self.bar.set(min(1.0, st["pos"] / st["dur"]) if st["dur"] > 0 else 0)
            self.lbl_preview.configure(text=self._render_chat(st, paused=not st["playing"] and self.pause_mode.get() == "Anzeigen"))
        else:
            self.lbl_title.configure(text="Nichts läuft")
            self.lbl_artist.configure(text="Starte Spotify (Desktop-App) und spiele einen Song." if not st["error"] else "")
            self.lbl_album.configure(text="")
            self.lbl_state.configure(text="")
            self.lbl_pos.configure(text="0:00")
            self.lbl_dur.configure(text="0:00")
            self.bar.set(0)
            self.lbl_preview.configure(text="–")

        if st["art_version"] != self._art_version:
            self._art_version = st["art_version"]
            if st["art"] is not None:
                self._art_img = to_photo(st["art"].resize((220, 220), Image.LANCZOS))
                self.lbl_art.configure(image=self._art_img, text="")
            else:
                self.lbl_art.configure(image=self._placeholder, text="♪")

        self._spotify_autosend(st)
        self.after(500, self._ui_tick)

    # ---------------------------------------------------------- Chatbox-Seite
    def _build_chat(self, page):
        page.grid_rowconfigure(2, weight=1)
        self._h1(page, "Chatbox").grid(row=0, column=0, sticky="w", pady=(0, 12))

        card = self._card(page)
        card.grid(row=1, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        self.txt_chat = ctk.CTkTextbox(card, height=110, fg_color=CARD_INNER, corner_radius=INNER_RADIUS, font=ctk.CTkFont(size=14))
        self.txt_chat.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 4))
        self.txt_chat.bind("<KeyRelease>", self._on_chat_key)
        self.txt_chat.bind("<Control-Return>", lambda e: (self._send_chat(), "break")[1])
        self.lbl_count = ctk.CTkLabel(card, text=f"0/{CHATBOX_LIMIT}", text_color=TEXT_DIM, anchor="e")
        self.lbl_count.grid(row=1, column=0, sticky="e", padx=22)

        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.grid(row=2, column=0, sticky="ew", padx=18, pady=6)
        self.var_immediate = ctk.BooleanVar(value=True)
        self.var_sound = ctk.BooleanVar(value=False)
        self.var_typing = ctk.BooleanVar(value=True)
        for text, var in (
            ("Sofort senden", self.var_immediate),
            ("Ton", self.var_sound),
            ("Tipp-Indikator", self.var_typing),
        ):
            ctk.CTkSwitch(opts, text=text, variable=var, progress_color=ACCENT).pack(side="left", padx=(0, 18))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=18, pady=(6, 6))
        ctk.CTkButton(
            btns, text="Senden  (Strg+Enter)", fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
            command=self._send_chat,
        ).pack(side="left")
        ctk.CTkButton(
            btns, text="Chatbox leeren", fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER, command=self._clear_chatbox
        ).pack(side="left", padx=8)

        auto = ctk.CTkFrame(card, fg_color="transparent")
        auto.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 16))
        self.var_auto = ctk.BooleanVar(value=False)
        self.var_auto_interval = ctk.StringVar(value="5")
        ctk.CTkSwitch(
            auto, text="Auto-Wiederholung alle", variable=self.var_auto, progress_color=ACCENT, command=self._toggle_auto
        ).pack(side="left")
        ctk.CTkEntry(auto, textvariable=self.var_auto_interval, width=50).pack(side="left", padx=8)
        ctk.CTkLabel(auto, text="Sekunden (min. 2)", text_color=TEXT_DIM).pack(side="left")

        hist = self._card(page)
        hist.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        hist.grid_rowconfigure(1, weight=1)
        hist.grid_columnconfigure(0, weight=1)
        self._h2(hist, "VERLAUF").grid(row=0, column=0, sticky="w", padx=20, pady=(14, 0))
        self.hist_frame = ctk.CTkScrollableFrame(hist, fg_color="transparent")
        self.hist_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        self.hist_frame.grid_columnconfigure(0, weight=1)
        self._refresh_history()

    def _refresh_history(self):
        for w in self.hist_frame.winfo_children():
            w.destroy()
        for i, item in enumerate(self.cfg["history"]):
            ctk.CTkButton(
                self.hist_frame, text=item.replace("\n", " ⏎ "), anchor="w", fg_color=ROW, hover_color=ROW_HOVER,
                command=lambda t=item: self._history_pick(t),
            ).grid(row=i, column=0, sticky="ew", pady=2)

    def _history_pick(self, text):
        self.txt_chat.delete("1.0", "end")
        self.txt_chat.insert("1.0", text)
        self._on_chat_key()

    def _on_chat_key(self, _event=None):
        text = self.txt_chat.get("1.0", "end-1c")
        n = len(text)
        self.lbl_count.configure(text=f"{n}/{CHATBOX_LIMIT}", text_color=DANGER if n > CHATBOX_LIMIT else TEXT_DIM)
        if self.var_typing.get() and self.client:
            self.client.send_message("/chatbox/typing", bool(text))

    def chat_send(self, text, force=False):
        """Sendet in die Chatbox. Gibt False zurück, wenn wegen Rate-Limit übersprungen."""
        now = time.monotonic()
        if not force and now - self._chat_ts < CHATBOX_MIN_GAP:
            return False
        sound = bool(self.var_sound.get()) if hasattr(self, "var_sound") else False
        if getattr(self, "ascii_mode", None) is not None and self.ascii_mode.get():
            text = to_ascii(text)
        try:
            self.client.send_message("/chatbox/input", [text[:CHATBOX_LIMIT], True, sound])
            self.client.send_message("/chatbox/typing", False)
        except OSError as exc:
            self.log(f"Senden fehlgeschlagen: {exc}")
            return False
        self._chat_ts = now
        self.sent_count += 1
        self.last_sent_time = time.strftime("%H:%M:%S")
        self.log(f"Chatbox: {len(text)} Zeichen gesendet" if text else "Chatbox geleert")
        return True

    def _send_chat(self):
        text = self.txt_chat.get("1.0", "end-1c")[:CHATBOX_LIMIT]
        if not text.strip():
            return
        self.client.send_message(
            "/chatbox/input", [text, bool(self.var_immediate.get()), bool(self.var_sound.get())]
        )
        self.client.send_message("/chatbox/typing", False)
        self._chat_ts = time.monotonic()
        self.log(f"Chatbox gesendet ({len(text)} Zeichen)")
        hist = self.cfg["history"]
        if text in hist:
            hist.remove(text)
        hist.insert(0, text)
        del hist[20:]
        save_config(self.cfg)
        self._refresh_history()

    def _clear_chatbox(self):
        self.chat_send("", force=True)
        self._sp_shown = False

    def _toggle_auto(self):
        if self.var_auto.get():
            self._auto_tick()
        elif self.auto_job:
            self.after_cancel(self.auto_job)
            self.auto_job = None

    def _auto_tick(self):
        if not self.var_auto.get():
            return
        text = self.txt_chat.get("1.0", "end-1c")[:CHATBOX_LIMIT]
        if text.strip():
            self.chat_send(text, force=True)
        try:
            interval = max(2.0, float(self.var_auto_interval.get().replace(",", ".")))
        except ValueError:
            interval = 5.0
        self.auto_job = self.after(int(interval * 1000), self._auto_tick)

    # ------------------------------------------------------- Aussehen-Seite
    def _build_look(self, page):
        page.grid_rowconfigure(1, weight=1)
        self._h1(page, "Aussehen").grid(row=0, column=0, sticky="w", pady=(0, 12))
        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        self._look = dict(
            palette=ctk.StringVar(value=self.cfg["palette"]),
            accent=ctk.StringVar(value=self.cfg["accent"]),
            radius=ctk.IntVar(value=int(self.cfg["card_radius"])),
            scale=ctk.DoubleVar(value=float(self.cfg["ui_scale"])),
            opacity=ctk.DoubleVar(value=float(self.cfg["opacity"])),
            compact=ctk.BooleanVar(value=bool(self.cfg["compact_sidebar"])),
            hidden=set(self.cfg.get("hidden_pages", [])),
        )

        # --- Farbschema
        c1 = self._card(scroll)
        c1.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self._h2(c1, "FARBSCHEMA").pack(anchor="w", padx=20, pady=(14, 6))
        ctk.CTkSegmentedButton(
            c1, values=list(PALETTES), variable=self._look["palette"], selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        # --- Akzentfarbe
        c2 = self._card(scroll)
        c2.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self._h2(c2, "AKZENTFARBE").pack(anchor="w", padx=20, pady=(14, 6))
        swatches = ctk.CTkFrame(c2, fg_color="transparent")
        swatches.pack(anchor="w", padx=20)
        for name, hexv in ACCENTS.items():
            ctk.CTkButton(
                swatches, text="", width=34, height=34, corner_radius=17, fg_color=hexv, hover_color=lighten(hexv),
                border_width=2, border_color=CARD, command=lambda h=hexv: self._pick_accent(h),
            ).pack(side="left", padx=3)
        hexrow = ctk.CTkFrame(c2, fg_color="transparent")
        hexrow.pack(anchor="w", padx=20, pady=(10, 16))
        ctk.CTkLabel(hexrow, text="Eigene Farbe (Hex):").pack(side="left")
        self.ent_accent = ctk.CTkEntry(hexrow, textvariable=self._look["accent"], width=110)
        self.ent_accent.pack(side="left", padx=8)
        self.accent_preview = ctk.CTkLabel(hexrow, text="  Vorschau  ", fg_color=ACCENT, text_color=ON_ACCENT, corner_radius=8)
        self.accent_preview.pack(side="left")
        self.ent_accent.bind("<KeyRelease>", lambda e: self._update_accent_preview())

        # --- Form & Größe
        c3 = self._card(scroll)
        c3.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        c3.grid_columnconfigure(1, weight=1)
        self._h2(c3, "FORM & GRÖSSE").grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(14, 6))
        self._look_slider(c3, 1, "Rundung", self._look["radius"], 4, 30, 26, lambda v: f"{int(v)} px")
        self._look_slider(c3, 2, "UI-Größe", self._look["scale"], 0.8, 1.4, 12, lambda v: f"{int(round(v * 100))} %")
        self._look_slider(c3, 3, "Deckkraft", self._look["opacity"], 0.5, 1.0, 10, lambda v: f"{int(round(v * 100))} %",
                          live=lambda v: self.attributes("-alpha", float(v)))
        ctk.CTkSwitch(
            c3, text="Schmale Seitenleiste (nur Symbole)", variable=self._look["compact"], progress_color=ACCENT
        ).grid(row=4, column=0, columnspan=3, sticky="w", padx=20, pady=(8, 16))

        # --- Seiten ein-/ausblenden
        c4 = self._card(scroll)
        c4.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self._h2(c4, "SEITEN IN DER SEITENLEISTE").pack(anchor="w", padx=20, pady=(14, 6))
        grid = ctk.CTkFrame(c4, fg_color="transparent")
        grid.pack(anchor="w", padx=20, pady=(0, 16))
        for i, (label, key) in enumerate(self.NAV):
            if key in ("look", "settings"):
                continue
            var = ctk.BooleanVar(value=key not in self._look["hidden"])
            ctk.CTkCheckBox(
                grid, text=label, variable=var, fg_color=ACCENT, hover_color=ACCENT_HOVER, checkmark_color=ON_ACCENT,
                command=lambda k=key, v=var: self._look["hidden"].discard(k) if v.get() else self._look["hidden"].add(k),
            ).grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 22), pady=4)

        # --- Aktionen
        bar = ctk.CTkFrame(scroll, fg_color="transparent")
        bar.grid(row=4, column=0, sticky="w", pady=(0, 8))
        ctk.CTkButton(
            bar, text="Anwenden (startet neu)", fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
            command=self._apply_look,
        ).pack(side="left")
        ctk.CTkButton(
            bar, text="Zurücksetzen", fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER, text_color=TEXT_MAIN,
            command=self._reset_look,
        ).pack(side="left", padx=8)
        ctk.CTkLabel(
            scroll, text="Beim Anwenden startet das Tool kurz neu, damit alles sauber neu gezeichnet wird. "
            "Deine Einstellungen bleiben erhalten.", text_color=TEXT_DIM, justify="left", anchor="w", wraplength=640,
        ).grid(row=5, column=0, sticky="w")

    def _look_slider(self, parent, row, label, var, lo, hi, steps, fmt, live=None):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="e", padx=(20, 10), pady=6)
        val = ctk.CTkLabel(parent, text=fmt(var.get()), width=60)

        def on_change(v):
            val.configure(text=fmt(float(v)))
            if live:
                live(v)

        ctk.CTkSlider(
            parent, from_=lo, to=hi, number_of_steps=steps, variable=var, progress_color=ACCENT,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER, command=on_change,
        ).grid(row=row, column=1, sticky="ew", pady=6)
        val.grid(row=row, column=2, padx=(10, 20))

    def _pick_accent(self, hexv):
        self._look["accent"].set(hexv)
        self._update_accent_preview()

    def _update_accent_preview(self):
        h = self._look["accent"].get().strip()
        if _HEX_RE.match(h):
            self.accent_preview.configure(fg_color=h, text_color=on_color(h))

    def _restart(self, page):
        self.cfg["start_page"] = page
        save_config(self.cfg)
        self.watcher.stop()
        self._stop_server()
        try:
            self.destroy()
        finally:
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def _apply_look(self):
        accent = self._look["accent"].get().strip()
        if not _HEX_RE.match(accent):
            messagebox.showerror("Fehler", "Die Akzentfarbe muss ein Hex-Wert wie #1DB954 sein.")
            return
        self.cfg.update(
            palette=self._look["palette"].get(),
            accent=accent,
            card_radius=int(self._look["radius"].get()),
            ui_scale=round(float(self._look["scale"].get()), 2),
            opacity=round(float(self._look["opacity"].get()), 2),
            compact_sidebar=bool(self._look["compact"].get()),
            hidden_pages=sorted(self._look["hidden"]),
        )
        self.cfg["template"] = self.txt_template.get("1.0", "end-1c")
        self.cfg["clock_template"] = self.txt_clock.get("1.0", "end-1c")
        self._restart("look")

    def _reset_look(self):
        if not messagebox.askyesno("Zurücksetzen", "Aussehen auf Standard zurücksetzen?"):
            return
        for k in ("palette", "accent", "card_radius", "ui_scale", "opacity", "compact_sidebar", "hidden_pages"):
            self.cfg[k] = DEFAULT_CONFIG[k]
        self._restart("look")

    # --------------------------------------------------------------- Uhr-Seite
    def _build_clock(self, page):
        self._h1(page, "Uhr").grid(row=0, column=0, sticky="w", pady=(0, 12))
        card = self._card(page)
        card.grid(row=1, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            head, text="Uhrzeit in VRChat-Chatbox anzeigen", font=ctk.CTkFont(size=16, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")
        self.clock_on = ctk.BooleanVar(value=self.cfg["clock_on"])
        ctk.CTkSwitch(
            head, text="Aktiv", variable=self.clock_on, progress_color=ACCENT, command=self._on_clock_change
        ).grid(row=0, column=1, sticky="e")

        self.lbl_clock = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=56, weight="bold"), text_color=ACCENT)
        self.lbl_clock.grid(row=1, column=0, pady=(10, 6))

        self._h2(card, "TEMPLATE  ({time} {time_s} {date} {weekday})").grid(row=2, column=0, sticky="w", padx=20)
        self.txt_clock = ctk.CTkTextbox(card, height=64, fg_color=CARD_INNER, corner_radius=INNER_RADIUS)
        self.txt_clock.grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 10))
        self.txt_clock.insert("1.0", self.cfg["clock_template"])
        self.txt_clock.bind("<KeyRelease>", lambda e: self._on_clock_change())

        self._h2(card, "VORSCHAU").grid(row=4, column=0, sticky="w", padx=20)
        prev = ctk.CTkFrame(card, fg_color=CARD_INNER, corner_radius=INNER_RADIUS)
        prev.grid(row=5, column=0, sticky="ew", padx=20, pady=(4, 10))
        self.lbl_clock_prev = ctk.CTkLabel(prev, text="", justify="left", anchor="w", font=ctk.CTkFont(size=14))
        self.lbl_clock_prev.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(
            card, justify="left", anchor="w", text_color=TEXT_DIM, wraplength=620,
            text=(
                "Regeln: Läuft Musik und die Spotify-Anzeige ist aktiv, hat die Musik Vorrang. "
                "Sonst (nichts läuft oder Pause) zeigt die Chatbox die Uhr. "
                "Das Update-Intervall stellst du auf der Spotify-Seite ein."
            ),
        ).grid(row=6, column=0, sticky="w", padx=20, pady=(0, 16))

    def _on_clock_change(self):
        self.cfg["clock_on"] = bool(self.clock_on.get())
        self.cfg["clock_template"] = self.txt_clock.get("1.0", "end-1c")
        save_config(self.cfg)
        self._sp_key = None
        if not self.cfg["clock_on"] and not self.sp_on.get() and self._sp_shown:
            self.chat_send("", force=True)
            self._sp_shown = False

    # -------------------------------------------------------- Furry-Detektor
    def _build_furry(self, page):
        page.grid_rowconfigure(2, weight=1)
        self._h1(page, "Furry-Detektor 🐾").grid(row=0, column=0, sticky="w", pady=(0, 12))

        card = self._card(page)
        card.grid(row=1, column=0, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="Reiner Zufallsspaß: Der Detektor rät einfach, jedes Mal neu.",
            text_color=TEXT_DIM, anchor="w",
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(16, 6))

        ctk.CTkLabel(card, text="Wer wird gescannt?").grid(row=1, column=0, padx=(20, 8), pady=6, sticky="e")
        self.var_scan_name = ctk.StringVar(value=self.cfg["scan_name"])
        ctk.CTkEntry(card, textvariable=self.var_scan_name, placeholder_text="Name (leer = Du)").grid(
            row=1, column=1, sticky="ew", pady=6
        )
        ctk.CTkButton(
            card, text="🔍  Scannen", fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
            command=self._run_scan,
        ).grid(row=1, column=2, padx=20)

        self.lbl_scan_pct = ctk.CTkLabel(card, text="–", font=ctk.CTkFont(size=64, weight="bold"), text_color=ACCENT)
        self.lbl_scan_pct.grid(row=2, column=0, columnspan=3, pady=(10, 0))
        self.lbl_scan_verdict = ctk.CTkLabel(card, text="Noch nicht gescannt.", font=ctk.CTkFont(size=15), text_color=TEXT_MAIN)
        self.lbl_scan_verdict.grid(row=3, column=0, columnspan=3, pady=(0, 10))

        trig = ctk.CTkFrame(card, fg_color="transparent")
        trig.grid(row=4, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 16))
        self.scan_param_on = ctk.BooleanVar(value=self.cfg["scan_param_on"])
        ctk.CTkSwitch(
            trig, text="Auslösen per Avatar-Parameter (Bool):", variable=self.scan_param_on,
            progress_color=ACCENT, command=self._on_scan_cfg,
        ).pack(side="left")
        self.var_scan_param = ctk.StringVar(value=self.cfg["scan_param"])
        e = ctk.CTkEntry(trig, textvariable=self.var_scan_param, width=160)
        e.pack(side="left", padx=8)
        e.bind("<KeyRelease>", lambda ev: self._on_scan_cfg())

        hist = self._card(page)
        hist.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        hist.grid_rowconfigure(1, weight=1)
        hist.grid_columnconfigure(0, weight=1)
        self._h2(hist, "ERGEBNISSE").grid(row=0, column=0, sticky="w", padx=20, pady=(14, 0))
        self.scan_hist = ctk.CTkScrollableFrame(hist, fg_color="transparent")
        self.scan_hist.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        self.scan_hist.grid_columnconfigure(0, weight=1)
        self._scan_results = []

    def _on_scan_cfg(self):
        self.cfg["scan_param_on"] = bool(self.scan_param_on.get())
        self.cfg["scan_param"] = self.var_scan_param.get().strip()
        self.cfg["scan_name"] = self.var_scan_name.get().strip()
        save_config(self.cfg)

    def _run_scan(self):
        if time.monotonic() < self._hold_until:
            return  # es läuft schon ein Scan
        self._on_scan_cfg()
        name = truncate(self.var_scan_name.get().strip() or "Du", 24)
        pct = random.randint(0, 100)
        tier = next(v for limit, v in FURRY_TIERS if pct <= limit)
        verdict, proof = random.choice(tier), random.choice(FURRY_PROOFS)
        self._hold_until = time.monotonic() + 10
        self.lbl_scan_pct.configure(text="…")
        self.lbl_scan_verdict.configure(text=f"Scanne {name}…")
        self.chat_send(f"🔍 Scanne {name}...\n{random.choice(FURRY_SCAN_LINES)}", force=True)
        self.after(2500, lambda: self._finish_scan(name, pct, verdict, proof))

    def _finish_scan(self, name, pct, verdict, proof):
        self.chat_send(f"🐾 {name}: {pct}% Furry\n{verdict}\n{proof}", force=True)
        self._sp_key = None
        self.lbl_scan_pct.configure(text=f"{pct}%")
        self.lbl_scan_verdict.configure(text=f"{name}: {verdict}")
        self._scan_results.insert(0, f"{time.strftime('%H:%M:%S')}   {name}   →   {pct}%   {verdict}")
        del self._scan_results[15:]
        for w in self.scan_hist.winfo_children():
            w.destroy()
        for i, line in enumerate(self._scan_results):
            ctk.CTkLabel(self.scan_hist, text=line, anchor="w", fg_color=ROW, corner_radius=8).grid(
                row=i, column=0, sticky="ew", pady=2, ipady=6
            )

    # --------------------------------------------------------- Parameter-Seite
    def _build_params(self, page):
        page.grid_rowconfigure(2, weight=1)
        self._h1(page, "Avatar-Parameter").grid(row=0, column=0, sticky="w", pady=(0, 12))

        card = self._card(page)
        card.grid(row=1, column=0, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        self.var_pname = ctk.StringVar()
        self.var_ptype = ctk.StringVar(value="bool")
        self.var_pvalue = ctk.StringVar(value="true")

        ctk.CTkLabel(card, text="Name").grid(row=0, column=0, padx=(18, 8), pady=(18, 6), sticky="e")
        ctk.CTkEntry(card, textvariable=self.var_pname, placeholder_text="z. B. VRCEmote").grid(
            row=0, column=1, sticky="ew", padx=(0, 18), pady=(18, 6)
        )
        ctk.CTkLabel(card, text="Typ").grid(row=1, column=0, padx=(18, 8), pady=6, sticky="e")
        ctk.CTkSegmentedButton(
            card, values=["bool", "int", "float"], variable=self.var_ptype, selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER, command=self._on_type_change,
        ).grid(row=1, column=1, sticky="w", pady=6)
        ctk.CTkLabel(card, text="Wert").grid(row=2, column=0, padx=(18, 8), pady=6, sticky="e")
        ctk.CTkEntry(card, textvariable=self.var_pvalue, width=140).grid(row=2, column=1, sticky="w", pady=6)

        ctk.CTkLabel(card, text="Slider").grid(row=3, column=0, padx=(18, 8), pady=6, sticky="e")
        self.slider = ctk.CTkSlider(
            card, from_=-1, to=1, number_of_steps=200, progress_color=ACCENT, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, command=self._on_slider,
        )
        self.slider.set(0)
        self.slider.grid(row=3, column=1, sticky="ew", padx=(0, 18), pady=6)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=4, column=0, columnspan=2, sticky="w", padx=18, pady=(8, 18))
        ctk.CTkButton(
            btns, text="Senden", fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT, command=self._send_param
        ).pack(side="left")
        ctk.CTkButton(
            btns, text="★ Als Favorit merken", fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER, command=self._add_favorite
        ).pack(side="left", padx=8)

        fav = self._card(page)
        fav.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        fav.grid_rowconfigure(1, weight=1)
        fav.grid_columnconfigure(0, weight=1)
        self._h2(fav, "FAVORITEN").grid(row=0, column=0, sticky="w", padx=20, pady=(14, 0))
        self.fav_frame = ctk.CTkScrollableFrame(fav, fg_color="transparent")
        self.fav_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        self.fav_frame.grid_columnconfigure(0, weight=1)
        self._refresh_favs()

    def _on_type_change(self, t):
        self.var_pvalue.set({"bool": "true", "int": "0", "float": "0.0"}[t])

    def _on_slider(self, val):
        self.var_ptype.set("float")
        self.var_pvalue.set(str(round(float(val), 3)))
        if self.var_pname.get().strip():
            self._send_param(quiet=True)

    def _send_param(self, quiet=False):
        name = self.var_pname.get().strip()
        if not name:
            if not quiet:
                messagebox.showinfo("Hinweis", "Bitte einen Parameter-Namen eingeben.")
            return
        try:
            value = parse_value(self.var_ptype.get(), self.var_pvalue.get())
        except ValueError as e:
            messagebox.showerror("Fehler", str(e))
            return
        addr = f"/avatar/parameters/{name}"
        self.client.send_message(addr, value)
        self.log(f"{addr} = {value!r}")

    def _add_favorite(self):
        name = self.var_pname.get().strip()
        if not name:
            return
        self.cfg["favorites"].append({"name": name, "type": self.var_ptype.get(), "value": self.var_pvalue.get()})
        save_config(self.cfg)
        self._refresh_favs()

    def _refresh_favs(self):
        for w in self.fav_frame.winfo_children():
            w.destroy()
        for i, fav in enumerate(self.cfg["favorites"]):
            row = ctk.CTkFrame(self.fav_frame, fg_color=ROW, corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", pady=2)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=f"{fav['name']}   [{fav['type']}] = {fav['value']}", anchor="w").grid(
                row=0, column=0, sticky="w", padx=12, pady=8
            )
            ctk.CTkButton(
                row, text="Senden", width=70, fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
                command=lambda f=fav: self._fav_send(f),
            ).grid(row=0, column=1, padx=4)
            ctk.CTkButton(
                row, text="Laden", width=60, fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER,
                command=lambda f=fav: self._fav_load(f),
            ).grid(row=0, column=2, padx=4)
            ctk.CTkButton(
                row, text="✕", width=32, fg_color=NEUTRAL, hover_color=DANGER,
                command=lambda idx=i: self._fav_delete(idx),
            ).grid(row=0, column=3, padx=(4, 8))

    def _fav_send(self, fav):
        try:
            value = parse_value(fav["type"], fav["value"])
        except ValueError as e:
            messagebox.showerror("Fehler", str(e))
            return
        addr = f"/avatar/parameters/{fav['name']}"
        self.client.send_message(addr, value)
        self.log(f"{addr} = {value!r}")

    def _fav_load(self, fav):
        self.var_pname.set(fav["name"])
        self.var_ptype.set(fav["type"])
        self.var_pvalue.set(fav["value"])

    def _fav_delete(self, idx):
        del self.cfg["favorites"][idx]
        save_config(self.cfg)
        self._refresh_favs()

    # ------------------------------------------------------------ Monitor-Seite
    def _build_monitor(self, page):
        page.grid_rowconfigure(2, weight=1)
        self._h1(page, "OSC-Monitor").grid(row=0, column=0, sticky="w", pady=(0, 12))

        bar = self._card(page)
        bar.grid(row=1, column=0, sticky="ew")
        self.var_filter = ctk.StringVar()
        ctk.CTkEntry(bar, textvariable=self.var_filter, placeholder_text="Filter (z. B. Emote)", width=220).pack(
            side="left", padx=14, pady=12
        )
        self.var_pause = ctk.BooleanVar(value=False)
        self.var_changes_only = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(bar, text="Pause", variable=self.var_pause, progress_color=ACCENT).pack(side="left", padx=10)
        ctk.CTkSwitch(bar, text="Nur Änderungen", variable=self.var_changes_only, progress_color=ACCENT).pack(
            side="left", padx=10
        )
        ctk.CTkButton(bar, text="Leeren", width=80, fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER, command=self._clear_monitor).pack(
            side="right", padx=14
        )

        self.txt_mon = ctk.CTkTextbox(page, fg_color=CARD, corner_radius=CARD_RADIUS, font=("Consolas", 12), wrap="none")
        self.txt_mon.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        self.txt_mon.configure(state="disabled")

    def _poll_osc(self):
        lines = []
        try:
            while True:
                ts, addr, args = self.msg_queue.get_nowait()
                if self.var_pause.get():
                    continue
                flt = self.var_filter.get().strip().lower()
                if flt and flt not in addr.lower():
                    continue
                if self.var_changes_only.get():
                    if self.last_values.get(addr) == args:
                        continue
                    self.last_values[addr] = args
                lines.append(f"[{ts}] {addr}  {' '.join(repr(a) for a in args)}\n")
        except queue.Empty:
            pass
        if lines:
            self.txt_mon.configure(state="normal")
            self.txt_mon.insert("end", "".join(lines))
            total = int(self.txt_mon.index("end-1c").split(".")[0])
            if total > MONITOR_MAX_LINES:
                self.txt_mon.delete("1.0", f"{total - MONITOR_MAX_LINES}.0")
            self.txt_mon.see("end")
            self.txt_mon.configure(state="disabled")
        self.after(100, self._poll_osc)

    def _clear_monitor(self):
        self.last_values.clear()
        self.txt_mon.configure(state="normal")
        self.txt_mon.delete("1.0", "end")
        self.txt_mon.configure(state="disabled")

    # -------------------------------------------------------- Einstellungen
    def _build_settings(self, page):
        self._h1(page, "Einstellungen").grid(row=0, column=0, sticky="w", pady=(0, 12))
        card = self._card(page)
        card.grid(row=1, column=0, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        self.var_ip = ctk.StringVar(value=self.cfg["ip"])
        self.var_send_port = ctk.StringVar(value=str(self.cfg["send_port"]))
        self.var_recv_port = ctk.StringVar(value=str(self.cfg["recv_port"]))
        rows = (
            ("IP-Adresse (VRChat-PC)", self.var_ip),
            ("Sende-Port (an VRChat)", self.var_send_port),
            ("Empfangs-Port (von VRChat)", self.var_recv_port),
        )
        for i, (label, var) in enumerate(rows):
            ctk.CTkLabel(card, text=label).grid(row=i, column=0, padx=(18, 12), pady=8 if i else (18, 8), sticky="e")
            ctk.CTkEntry(card, textvariable=var, width=200).grid(
                row=i, column=1, sticky="w", pady=8 if i else (18, 8)
            )

        self.var_only_spotify = ctk.BooleanVar(value=self.cfg["only_spotify"])
        ctk.CTkSwitch(
            card, text="Nur Spotify als Quelle (aus = beliebiger Mediaplayer)", variable=self.var_only_spotify,
            progress_color=ACCENT,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=8)

        self.ascii_mode = ctk.BooleanVar(value=self.cfg["ascii_mode"])
        ctk.CTkSwitch(
            card, text="Kompatibler Modus (nur ASCII, ohne Emoji/Sonderzeichen)", variable=self.ascii_mode,
            progress_color=ACCENT, command=self._on_ascii_toggle,
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=18, pady=8)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=5, column=0, columnspan=2, sticky="w", padx=18, pady=(8, 18))
        ctk.CTkButton(
            btns, text="Übernehmen", fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
            command=self._apply_connection,
        ).pack(side="left")
        ctk.CTkButton(
            btns, text="Test-Nachricht an VRChat", fg_color=NEUTRAL, hover_color=NEUTRAL_HOVER, command=self._send_test
        ).pack(side="left", padx=8)

        info = self._card(page)
        info.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        ctk.CTkLabel(
            info,
            justify="left",
            anchor="w",
            text_color=TEXT_DIM,
            text=(
                "VRChat: Action Menu → Options → OSC → Enabled.\n"
                "Standard-Ports: 9000 (VRChat empfängt) und 9001 (VRChat sendet).\n"
                f"Konfiguration: {CONFIG_FILE}"
            ),
        ).pack(fill="x", padx=18, pady=16)

        about = self._card(page)
        about.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        ctk.CTkLabel(about, text="Über", font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(
            fill="x", padx=18, pady=(16, 2)
        )
        ctk.CTkLabel(
            about, justify="left", anchor="w", text_color=TEXT_SOFT,
            text=f"VRC OSC Tool v{APP_VERSION}\nVRChat: {AUTHOR_VRC}\nDiscord: {AUTHOR_DISCORD}\n{COPYRIGHT}",
        ).pack(fill="x", padx=18, pady=(0, 16))

    # ---------------------------------------------------------- Verbindung
    def _on_ascii_toggle(self):
        self.cfg["ascii_mode"] = bool(self.ascii_mode.get())
        save_config(self.cfg)

    def _send_test(self):
        self._apply_connection()
        if self.chat_send("VRC OSC Test - es funktioniert!", force=True):
            messagebox.showinfo(
                "Test gesendet",
                f"Test-Nachricht an {self.cfg['ip']}:{self.cfg['send_port']} gesendet.\n\n"
                "Sieh in VRChat nach (Chatbox über deinem Kopf, z. B. im Spiegel oder mit Kamera).\n"
                "Wenn nichts erscheint: OSC aktiviert? Chatbox in den VRChat-Einstellungen an? "
                "Läuft VRChat auf diesem PC (sonst IP ändern)?",
            )

    def _apply_connection(self):
        try:
            ip = self.var_ip.get().strip()
            sp = int(self.var_send_port.get())
            rp = int(self.var_recv_port.get())
        except ValueError:
            messagebox.showerror("Fehler", "Ports müssen Zahlen sein.")
            return

        self.client = SimpleUDPClient(ip, sp)
        self.cfg.update(ip=ip, send_port=sp, recv_port=rp, only_spotify=bool(self.var_only_spotify.get()))
        self.watcher.only_spotify = self.cfg["only_spotify"]
        save_config(self.cfg)

        self._stop_server()
        try:
            disp = Dispatcher()
            disp.set_default_handler(self._on_osc)
            self.server = ThreadingOSCUDPServer(("0.0.0.0", rp), disp)
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
            self.lbl_status.configure(text=f"● Senden → {ip}:{sp}\n● Empfang  :{rp}", text_color=ACCENT)
        except OSError as e:
            self.server = None
            self.lbl_status.configure(
                text=f"● Senden → {ip}:{sp}\n● Empfang FEHLER\n  ({e.strerror or e})", text_color=WARN
            )

    def _on_osc(self, addr, *args):
        self.last_osc_ts = time.monotonic()
        # Furry-Scan per Avatar-Parameter (Flanke False -> True)
        if self.cfg.get("scan_param_on") and addr == "/avatar/parameters/" + str(self.cfg.get("scan_param", "")):
            val = bool(args[0]) if args else False
            if val and not self._scan_prev:
                self._scan_trigger = True
            self._scan_prev = val
        self.msg_queue.put((time.strftime("%H:%M:%S"), addr, args))

    def _stop_server(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:  # noqa: BLE001
                pass
            self.server = None

    def _on_close(self):
        self.cfg["template"] = self.txt_template.get("1.0", "end-1c")
        save_config(self.cfg)
        self.watcher.stop()
        self._stop_server()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
