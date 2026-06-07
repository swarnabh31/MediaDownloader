import json
import os
from datetime import datetime

HISTORY_FILE = "history.json"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def add_entry(title, url, quality, file_path, size_mb):
    history = load_history()
    history.insert(0, {
        "title": title or "Unknown",
        "url": url,
        "quality": quality,
        "file": file_path or "",
        "size_mb": round(size_mb, 2) if size_mb else 0.0,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def clear_history() -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)


def remove_entry(index: int) -> None:
    history = load_history()
    if 0 <= index < len(history):
        history.pop(index)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
