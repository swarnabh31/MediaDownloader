import json
import os

SETTINGS_FILE = "settings.json"

DEFAULTS = {
    "output_dir": "downloads",
    "default_quality": "720p",
    "theme": "light",
    "max_concurrent": 1,
    "proxy": "",
    "cookiefile": "",
    "concurrent_downloads": 1,
}


def load():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULTS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            stored = json.load(f)
        return {**DEFAULTS, **stored}
    except (json.JSONDecodeError, OSError):
        return DEFAULTS.copy()


def save(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
