# 🚀 Professional Upgrade Guide — Video & Audio Downloader
> All tools mentioned are **100% free and open-source**.

---

## Overview

This guide covers every upgrade needed to transform the current app into a professional-grade desktop tool. Each upgrade includes **what to do**, **which library to use**, and **exact implementation notes** tied to your existing code.

---

## 1. Architecture Refactor — Separate Concerns Properly

**Current problem:** `main.py` mixes UI layout, event handlers, and threading all in one flat function.

**What to do:**
Split the codebase into clean modules:

```
file_downloader/
├── bin/
├── downloads/
├── core/
│   ├── __init__.py
│   ├── downloader_engine.py   # (existing, move here)
│   ├── queue_manager.py       # NEW — manages download queue
│   ├── history_manager.py     # NEW — read/write history.json
│   └── settings_manager.py   # NEW — read/write settings.json
├── ui/
│   ├── __init__.py
│   ├── main_view.py           # Main download screen
│   ├── history_view.py        # History screen
│   ├── settings_view.py       # Settings screen
│   └── components.py          # Reusable UI widgets
├── main.py                    # Entry point only (calls ft.run)
├── requirements.txt
└── README.md
```

**How to implement:**
- `main.py` becomes a 5-line entry point that just calls `ft.run(main)`.
- Each `_view.py` file returns a `ft.View` or `ft.Column` that gets added to `page.views`.
- Use `page.go("/")`, `page.go("/history")`, `page.go("/settings")` for navigation between screens via Flet's built-in routing.

---

## 2. Multi-URL Download Queue

**What to do:**
Let users add multiple URLs to a queue and process them one by one (or with concurrency control).

**Library:** No extra library needed — use Python's built-in `queue.Queue` + `threading`.

**How to implement in `core/queue_manager.py`:**

```python
import queue
import threading

class QueueManager:
    def __init__(self, engine, on_item_update):
        self._queue = queue.Queue()
        self._engine = engine
        self._on_item_update = on_item_update  # callback to update UI
        self._worker = threading.Thread(target=self._process, daemon=True)
        self._worker.start()

    def add(self, url, quality):
        item = {"url": url, "quality": quality, "status": "queued"}
        self._queue.put(item)
        self._on_item_update(item)

    def _process(self):
        while True:
            item = self._queue.get()
            item["status"] = "downloading"
            self._on_item_update(item)
            try:
                self._engine.download(item["url"], item["quality"])
                item["status"] = "done"
            except Exception as e:
                item["status"] = f"error: {e}"
            self._on_item_update(item)
            self._queue.task_done()
```

**UI change:** Replace single Download button with **Add to Queue** button. Show a `ft.ListView` below it, with each queue item showing URL (truncated), status icon, and progress.

---

## 3. Metadata Preview Before Download

**What to do:**
Before downloading, fetch and show the video title, thumbnail, uploader, and duration in the UI — so the user confirms they have the right video.

**Library:** yt-dlp itself (no extra install needed).

**How to implement in `downloader_engine.py`:**

```python
def fetch_metadata(self, url):
    """Returns dict with title, uploader, duration, thumbnail URL."""
    opts = {
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'ffmpeg_location': self.ffmpeg_path,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", "Unknown"),
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration_string", "?"),
            "thumbnail": info.get("thumbnail", None),
        }
```

**UI change:** When the user pastes a URL and presses Tab or clicks a **Preview** button, call `fetch_metadata()` in a thread and update a card below the input with the info. Use `ft.Image(src=thumbnail_url)` to show the thumbnail directly.

---

## 4. Download History with Persistence

**What to do:**
Every completed download is saved to `history.json` and shown in a History tab.

**Library:** Python's built-in `json` module.

**How to implement in `core/history_manager.py`:**

```python
import json, os
from datetime import datetime

HISTORY_FILE = "history.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def add_entry(title, url, quality, file_path, size_mb):
    history = load_history()
    history.insert(0, {
        "title": title,
        "url": url,
        "quality": quality,
        "file": file_path,
        "size_mb": round(size_mb, 2),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
```

Call `add_entry()` inside `downloader_engine.py`'s `download()` method after `ydl.download()` succeeds. Retrieve title from `extract_info()` before downloading.

**UI:** A second tab/screen with a scrollable `ft.DataTable` or `ft.ListView` showing all entries, with a **Clear History** button at the top.

---

## 5. Persistent User Settings

**What to do:**
Save and restore user preferences: output folder, default quality, dark/light mode.

**Library:** Python's built-in `json` module.

**How to implement in `core/settings_manager.py`:**

```python
import json, os

SETTINGS_FILE = "settings.json"
DEFAULTS = {
    "output_dir": "downloads",
    "default_quality": "720p",
    "theme": "light",
    "max_concurrent": 1,
}

def load():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULTS.copy()
    with open(SETTINGS_FILE, "r") as f:
        return {**DEFAULTS, **json.load(f)}

def save(settings: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
```

On app start, call `load()` and apply the theme mode and default quality to the UI.

---

## 6. Custom Output Folder Picker

**What to do:**
Let users browse and choose where downloads are saved, instead of the hardcoded `downloads/` path.

**Library:** Flet's built-in `ft.FilePicker`.

**How to implement in `main.py` / `ui/settings_view.py`:**

```python
folder_picker = ft.FilePicker(on_result=on_folder_selected)
page.overlay.append(folder_picker)

def on_folder_selected(e: ft.FilePickerResultEvent):
    if e.path:
        settings["output_dir"] = e.path
        settings_manager.save(settings)
        output_folder_text.value = e.path
        page.update()

pick_folder_btn = ft.ElevatedButton(
    "Choose Folder",
    icon=ft.icons.FOLDER_OPEN,
    on_click=lambda _: folder_picker.get_directory_path()
)
```

Pass `settings["output_dir"]` into `DownloaderEngine` at download time instead of the hardcoded string.

---

## 7. Dark Mode Toggle

**What to do:**
A toggle in the header or Settings screen to switch between light and dark themes.

**Library:** Flet's built-in theme system (no extra install).

**How to implement:**

```python
def toggle_theme(e):
    page.theme_mode = (
        ft.ThemeMode.DARK 
        if page.theme_mode == ft.ThemeMode.LIGHT 
        else ft.ThemeMode.LIGHT
    )
    settings["theme"] = "dark" if page.theme_mode == ft.ThemeMode.DARK else "light"
    settings_manager.save(settings)
    page.update()

theme_toggle = ft.IconButton(
    icon=ft.icons.DARK_MODE,
    on_click=toggle_theme,
    tooltip="Toggle Dark Mode"
)
```

Place `theme_toggle` in the AppBar. On startup, read `settings["theme"]` and set `page.theme_mode` before calling `page.update()`.

---

## 8. Real Progress: Speed + ETA Display

**What to do:**
Show download speed (e.g., `3.2 MB/s`) and estimated time remaining, not just a percentage.

**Library:** yt-dlp provides this data already in the progress hook dict.

**How to implement — update `update_progress()` in `main.py`:**

```python
def update_progress(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%').strip()
        speed = d.get('_speed_str', '? KB/s').strip()
        eta = d.get('_eta_str', '?').strip()
        
        try:
            val = float(percent.replace('%', '')) / 100
            progress_bar.value = val
        except ValueError:
            pass
        
        status_text.value = f"{percent}  •  {speed}  •  ETA: {eta}"
    elif d['status'] == 'finished':
        status_text.value = "✅ Processing with FFmpeg..."
        progress_bar.value = 1.0
    page.update()
```

---

## 9. Desktop Notifications on Completion

**What to do:**
Pop a system notification when a download finishes, even if the app is minimized.

**Library:** `plyer` — `pip install plyer` (MIT license, cross-platform).

**How to implement:**

```python
from plyer import notification

def notify_done(title):
    notification.notify(
        title="Download Complete",
        message=f'"{title}" saved to your downloads folder.',
        app_name="Media Downloader",
        timeout=5,
    )
```

Call `notify_done(title)` at the end of the `run()` thread in `start_download()`.

Add to `requirements.txt`:
```
plyer
```

---

## 10. yt-dlp Auto-Updater Button

**What to do:**
A button that runs `pip install --upgrade yt-dlp` and streams output to the UI, so extractors stay fresh.

**Library:** Python's built-in `subprocess`.

**How to implement in `ui/settings_view.py`:**

```python
import subprocess, sys

def update_ytdlp(e):
    update_btn.disabled = True
    update_status.value = "Updating yt-dlp..."
    page.update()
    
    def run():
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            update_status.value = "✅ yt-dlp updated successfully!"
        else:
            update_status.value = f"❌ Update failed:\n{result.stderr[:200]}"
        update_btn.disabled = False
        page.update()
    
    threading.Thread(target=run, daemon=True).start()
```

---

## 11. Keyboard Shortcuts

**What to do:**
- `Ctrl+V` → auto-paste clipboard URL into the input field
- `Enter` → trigger download
- `Ctrl+L` → clear the URL field

**Library:** Flet's built-in `page.on_keyboard_event`.

**How to implement:**

```python
def on_keyboard(e: ft.KeyboardEvent):
    if e.ctrl and e.key == "V":
        # Flet handles paste natively in TextField; 
        # this can trigger a preview fetch automatically
        pass
    elif e.key == "Enter":
        start_download(None)
    elif e.ctrl and e.key == "L":
        url_input.value = ""
        page.update()

page.on_keyboard_event = on_keyboard
```

---

## 12. Cookies Support (Age-Restricted & Login Content)

**What to do:**
Let users load a `cookies.txt` file (exported from their browser) to download content they have legitimate access to.

**Library:** Flet's `ft.FilePicker` (already used for folder picker).

**How to implement in `downloader_engine.py`:**

Add optional `cookiefile` parameter to `get_download_options()`:

```python
def get_download_options(self, quality, progress_hook=None, cookiefile=None):
    opts = { ... }  # existing opts
    if cookiefile and os.path.exists(cookiefile):
        opts['cookiefile'] = cookiefile
    return opts
```

In the UI, add a small **Load Cookies** button next to the URL field that opens a file picker (filter for `.txt` files). Store the path in settings.

**Browser extension to export cookies:** [Get cookies.txt LOCALLY](https://github.com/kairi003/Get-cookies.txt-LOCALLY) — open source, MIT.

---

## 13. Format & Quality Info Panel (Available Formats)

**What to do:**
After pasting a URL, show all available formats with their resolution, codec, filesize, and fps — so users can pick exactly what they want.

**Library:** yt-dlp (no extra install).

**How to implement in `downloader_engine.py`:**

```python
def fetch_formats(self, url):
    opts = {'quiet': True, 'skip_download': True, 'ffmpeg_location': self.ffmpeg_path}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = []
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none':
                formats.append({
                    "id": f.get("format_id"),
                    "res": f.get("resolution", "?"),
                    "fps": f.get("fps", "?"),
                    "vcodec": f.get("vcodec", "?"),
                    "size_mb": round(f.get("filesize", 0) / 1e6, 1) if f.get("filesize") else "?",
                })
        return formats
```

Show results in a `ft.DataTable` in a dialog (`ft.AlertDialog`). When the user picks a row, populate the quality dropdown with the selected `format_id`, which yt-dlp accepts directly in the `format` option.

---

## 14. Proxy Support

**What to do:**
An optional proxy field in Settings for users dealing with geo-restricted content.

**Library:** No extra library. yt-dlp natively accepts a `proxy` key.

**How to implement:**

Add a `proxy` field to `settings.json`:
```json
{ "proxy": "" }
```

In Settings view, add:
```python
proxy_input = ft.TextField(
    label="Proxy URL (optional)",
    hint_text="http://user:pass@host:port  or  socks5://host:port",
    width=400
)
```

In `get_download_options()`:
```python
if settings.get("proxy"):
    opts['proxy'] = settings["proxy"]
```

---

## 15. Proper Error Handling & Logging

**What to do:**
Write all errors to a rotating log file (`app.log`) for debugging, instead of only showing them in the UI.

**Library:** Python's built-in `logging` module.

**How to implement — add to `main.py` entry point:**

```python
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler("app.log", maxBytes=1_000_000, backupCount=3)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])
log = logging.getLogger("downloader")
```

In the `run()` thread inside `start_download()`:
```python
except Exception as ex:
    log.error(f"Download failed for {url}: {ex}", exc_info=True)
    status_text.value = f"Error: {str(ex)}"
```

---

## 16. App Packaging — Standalone `.exe`

**What to do:**
Package the entire app (including FFmpeg binaries and Python) into a single distributable folder or `.exe` that runs without Python installed.

**Library:** `PyInstaller` — `pip install pyinstaller` (GPL license).

**How to build:**

```bash
pyinstaller main.py ^
  --name "MediaDownloader" ^
  --windowed ^
  --icon=assets/icon.ico ^
  --add-data "bin;bin" ^
  --add-data "assets;assets" ^
  --hidden-import flet ^
  --hidden-import yt_dlp
```

This produces a `dist/MediaDownloader/` folder. Zip it and share. The FFmpeg binaries in `bin/` are bundled automatically via `--add-data`.

**Note:** In packaged mode, adjust the `FFMPEG_BIN_PATH` in `main.py` to be relative to the executable:

```python
import sys
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
FFMPEG_BIN_PATH = os.path.join(BASE_DIR, "bin")
```

---

## Priority Order (Recommended Build Sequence)

| Priority | Feature | Effort | Impact |
|---|---|---|---|
| 1 | Architecture refactor | Medium | Foundation for everything |
| 2 | Persistent settings + folder picker | Low | Removes hardcoded paths |
| 3 | Metadata preview | Low | Big UX win |
| 4 | Real progress (speed + ETA) | Low | Already in yt-dlp data |
| 5 | Dark mode toggle | Low | Polish |
| 6 | Download queue + history | Medium | Professional feel |
| 7 | Desktop notifications | Low | plyer is one-liner |
| 8 | Format picker | Medium | Power user feature |
| 9 | Cookies support | Low | Niche but useful |
| 10 | Logging | Low | Essential for debugging |
| 11 | yt-dlp auto-updater | Low | Maintenance quality-of-life |
| 12 | Keyboard shortcuts | Low | Developer feel |
| 13 | Proxy support | Low | Power user feature |
| 14 | PyInstaller packaging | Low | Distribution |

---

## Complete `requirements.txt` After All Upgrades

```
flet
yt-dlp
plyer
pyinstaller
```

That's it. Everything else uses Python's standard library.

---

*All libraries: Flet (Apache 2.0), yt-dlp (Unlicense), plyer (MIT), PyInstaller (GPL + bootloader exception — distributing apps built with it is allowed).*
