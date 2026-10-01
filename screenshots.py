"""Launch Media Downloader, sweep through the acceptance window sizes
while seeding the queue for the screenshots, and save PNGs.

    python screenshots.py

Screenshots land in %USERPROFILE%\\AppData\\Local\\Temp\\opencode\\screenshots.
The app stays running afterwards so you can visually inspect it.
"""
import ctypes
import ctypes.wintypes as wt
import json
import logging
import os
import sys
import threading
import time
from ctypes.wintypes import BOOL, HWND, LPARAM, INT, DWORD

import flet as ft

import main as app
from ui.main_view import MainView

log = logging.getLogger("downloader")

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)

SCREENSHOT_DIR = os.path.join(
    os.environ["USERPROFILE"], "AppData", "Local", "Temp", "opencode", "screenshots"
)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

STATE = {"app_state": None, "locked": threading.Lock(), "hwnd": None}


def _register_state_init():
    orig = app.AppState.__init__

    def patched(self, page):
        orig(self, page)
        with STATE["locked"]:
            STATE["app_state"] = self

    app.AppState.__init__ = patched


_register_state_init()


def _seed_empty(q):
    with q._lock:
        q._items = []


def _seed_demo(q):
    with q._lock:
        q._items = [
            {"id": 1, "url": "https://youtube.com/watch?v=abc123", "quality": "1080p",
             "format_id": None, "status": "downloading",
             "title": "React 19 - Full 2026 Crash Course (4 hours 12 min)",
             "progress": 0.42, "speed": "2.4 MiB/s", "eta": "148",
             "error": "", "cancelled": False, "blocked_403": False,
             "thumbnail": "https://i.ytimg.com/vi/abc123/hq720.jpg"},
            {"id": 2, "url": "https://example.com/episode-1", "quality": "720p",
             "format_id": None, "status": "queued", "title": "Episode 1 - The Beginning",
             "progress": 0.0, "speed": "", "eta": "",
             "error": "", "cancelled": False, "blocked_403": False, "thumbnail": ""},
            {"id": 3, "url": "https://vimeo.com/12345678", "quality": "1440p",
             "format_id": None, "status": "done",
             "title": "A Short Product Demo Video (v2 final 4k master)",
             "progress": 1.0, "speed": "", "eta": "",
             "error": "", "cancelled": False, "blocked_403": False,
             "thumbnail": "https://i.ytimg.com/vi/vm1/hq720.jpg"},
            {"id": 4, "url": "https://dailymotion.com/video/x8abcd1", "quality": "Audio",
             "format_id": None, "status": "error",
             "title": "Podcast: The Software Engineer's Guide to 2026",
             "progress": 0.31, "speed": "", "eta": "",
             "error": "HTTP 403 - YouTube is blocking this IP. Fixes: (1) add login cookies in Settings, set a proxy, or switch networks ...",
             "cancelled": False, "blocked_403": True, "thumbnail": ""},
            {"id": 5, "url": "https://soundcloud.com/artist/track-9", "quality": "720p",
             "format_id": None, "status": "processing",
             "title": "Track 9 - Live Remix (Extended)",
             "progress": 1.0, "speed": "", "eta": "",
             "error": "", "cancelled": False, "blocked_403": False, "thumbnail": ""},
            {"id": 6, "url": "https://example.com/video-100-hours", "quality": "2160p",
             "format_id": None, "status": "cancelled",
             "title": "100 Hours of Coding - Complete Marathon (unofficial)",
             "progress": 0.73, "speed": "", "eta": "",
             "error": "Cancelled by user", "cancelled": True, "blocked_403": False, "thumbnail": ""},
        ]


def _resize_window(width: int, height: int) -> bool:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    found = []

    @ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return 1
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if buf.value.lower().startswith("media downloader"):
            found.append(hwnd)
        return 1

    user32.EnumWindows(cb, 0)
    if not found:
        log.warning("resize: no 'Media Downloader' window found")
        return False
    STATE["hwnd"] = found[0]
    SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010
    ok = user32.SetWindowPos(found[0], 0, 0, 0, width, height, SWP_NOZORDER | SWP_NOACTIVATE)
    return bool(ok)


def _window_rect():
    if "hwnd" not in STATE:
        return None
    rect = wt.RECT()
    ctypes.windll.user32.GetWindowRect(STATE["hwnd"], ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def _grab(path: str):
    from PIL import ImageGrab
    bbox = _window_rect()
    if bbox:
        img = ImageGrab.grab(bbox=bbox)
    else:
        img = ImageGrab.grab()
    img.save(path, "PNG")
    return img.size


def _set_theme(dark: bool):
    st = STATE["app_state"]
    if st is None:
        return
    target = "dark" if dark else "light"
    current = st.settings.get("theme", "light")
    if current == target:
        return
    try:
        st.toggle_theme()
    except Exception:
        log.exception("toggle_theme failed")


def _requeue(st, page):
    if st._main_view is None:
        return
    try:
        st._main_view.queue_panel.render()
    except Exception:
        log.exception("queue render failed")
    try:
        page.update()
    except Exception:
        log.warning("page.update failed")
    time.sleep(0.5)


def _sweep():
    time.sleep(2.5)  # let the app fully boot
    with STATE["locked"]:
        st = STATE["app_state"]
    if st is None:
        log.error("sweep aborted: no AppState")
        return
    page = st.page
    manifest = []

    def step(name, w, h, dark, seed):
        seed(st.queue)
        _set_theme(dark)
        ok = _resize_window(w, h)
        _requeue(st, page)
        time.sleep(0.6)
        path = os.path.join(SCREENSHOT_DIR, f"{name}_{w}x{h}_{'dark' if dark else 'light'}.png")
        try:
            w_px, h_px = _grab(path)
            manifest.append((path, w_px, h_px, ok))
            log.info("saved %s (%dx%d client) [resize OK=%s]", path, w_px, h_px, ok)
        except Exception as ex:
            log.exception("grab failed for %s", path)
            manifest.append((path, -1, -1, "FAIL: " + str(ex)))

    for (w, h) in [(800, 600), (1280, 720), (1920, 1080), (2560, 1440)]:
        for dark in (False, True):
            step("empty", w, h, dark, _seed_empty)
    for (w, h) in [(800, 600), (1280, 720), (1920, 1080), (2560, 1440)]:
        for dark in (False, True):
            step("queue", w, h, dark, _seed_demo)

    # reset to a tidy state for the user to inspect
    with st.queue._lock:
        st.queue._items = []
    _set_theme(False)  # return to light
    _resize_window(1100, 800)
    _requeue(st, page)

    log.info("=== screenshot manifest ===")
    for m in manifest:
        log.info("  %s", m)


def _main(page):
    app.main(page)
    threading.Thread(target=_sweep, daemon=True).start()


if __name__ == "__main__":
    app._setup_logging()
    try:
        ft.run(_main)
    except TypeError:
        ft.app(target=_main)
