import queue
import threading
import logging

log = logging.getLogger("downloader")


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
            }
            self._items.append(item)
        self._queue.put(item)
        self._on_item_update(item, "queued")
        return item

    def remove(self, item_id):
        with self._lock:
            self._items = [i for i in self._items if i["id"] != item_id]

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
                item["status"] = "error"
                item["error"] = str(e)
                self._on_item_update(item, "error")
            finally:
                self._queue.task_done()

    def _download_item(self, item):
        item["status"] = "downloading"
        self._on_item_update(item, "downloading")

        def hook(d):
            if d.get("status") == "downloading":
                try:
                    pct = d.get("_percent_str", "0%").replace("%", "").strip()
                    item["progress"] = float(pct) / 100.0
                except (ValueError, TypeError):
                    pass
                item["speed"] = d.get("_speed_str", "").strip()
                item["eta"] = d.get("_eta_str", "").strip()
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
            item["status"] = "done"
            self._on_item_update(item, "done")
        except Exception as e:
            item["status"] = "error"
            item["error"] = str(e)
            self._on_item_update(item, "error")
            raise

    def stop(self):
        self._stop = True
