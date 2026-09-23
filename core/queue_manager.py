import queue
import re
import threading
import yt_dlp.utils as ytdl_utils
import logging

from core.downloader_engine import annotate_error

log = logging.getLogger("downloader")


def _classify_error(e, item):
    msg = str(e).lower()
    if "cancelled" in msg or (isinstance(e, ytdl_utils.DownloadError) and item.get("cancelled")):
        item["status"] = "cancelled"
        item["error"] = "Cancelled by user"
        return
    item["status"] = "error"
    item["error"] = annotate_error(e)[:300]
    item["blocked_403"] = bool(re.search(r"(403|forbidden|geo.restricted)", str(e), re.IGNORECASE))


class QueueManager:
    def __init__(self, engine, on_item_update, max_concurrent=1):
        self._queue = queue.Queue()
        self._engine = engine
        self._on_item_update = on_item_update
        self._max_concurrent = max_concurrent
        self._items = []
        self._lock = threading.Lock()
        self._stop = False
        self._workers = []
        for _ in range(max(1, max_concurrent)):
            t = threading.Thread(target=self._process, daemon=True)
            t.start()
            self._workers.append(t)

    def add(self, url, quality, format_id=None):
        with self._lock:
            item = {
                "id": len(self._items) + 1,
                "url": url,
                "quality": quality,
                "format_id": format_id,
                "status": "queued",
                "title": "",
                "progress": 0.0,
                "speed": "",
                "eta": "",
                "error": "",
                "cancelled": False,
                "blocked_403": False,
            }
            self._items.append(item)
        self._queue.put(item)
        self._on_item_update(item, "queued")
        return item

    def remove(self, item_id):
        with self._lock:
            self._items = [i for i in self._items if i["id"] != item_id]

    def cancel_item(self, item_id):
        """Mark an item as cancelled so the progress hook aborts the download."""
        with self._lock:
            for i in self._items:
                if i["id"] == item_id and i["status"] in ("queued", "downloading", "processing"):
                    i["cancelled"] = True
                    break

    def clear_finished(self):
        with self._lock:
            self._items = [i for i in self._items if i["status"] in ("queued", "downloading")]

    def list_items(self):
        with self._lock:
            return list(self._items)

    def _process(self):
        while not self._stop:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._download_item(item)
            except Exception as e:
                log.exception("queue worker error")
                _classify_error(e, item)
                self._on_item_update(item, item["status"])
            finally:
                self._queue.task_done()

    def _download_item(self, item):
        item["status"] = "downloading"
        self._on_item_update(item, "downloading")

        def hook(d):
            if d.get("status") == "downloading":
                # Check cancellation
                if item.get("cancelled"):
                    raise ytdl_utils.DownloadError("Download cancelled by user")
                # Use correct yt-dlp progress dict keys
                try:
                    pct = d.get("percent", 0.0)
                    item["progress"] = float(pct) / 100.0
                except (ValueError, TypeError):
                    pass
                speed = d.get("speed")
                if speed is not None:
                    item["speed"] = ytdl_utils.format_bytes(speed)
                eta = d.get("eta")
                if eta is not None:
                    item["eta"] = str(eta) + "s"
                self._on_item_update(item, "downloading")
            elif d.get("status") == "finished":
                item["progress"] = 1.0
                item["status"] = "processing"
                self._on_item_update(item, "processing")

        try:
            info = self._engine.download(
                item["url"],
                item["quality"],
                progress_hook=hook,
                format_id=item.get("format_id"),
            )
            item["title"] = info.get("title", "Unknown") if isinstance(info, dict) else "Unknown"
            if item.get("cancelled"):
                item["status"] = "cancelled"
                item["error"] = "Cancelled by user"
                self._on_item_update(item, "cancelled")
            else:
                item["status"] = "done"
                self._on_item_update(item, "done")
        except Exception as e:
            _classify_error(e, item)
            self._on_item_update(item, item["status"])
            raise

    def stop(self):
        self._stop = True
