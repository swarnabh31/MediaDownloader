import warnings
warnings.filterwarnings("ignore", message="urllib3.*or chardet.*doesn't match")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="flet")

import flet as ft
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from core import settings_manager
from core.downloader_engine import DownloaderEngine
from core.queue_manager import QueueManager
from ui.main_view import MainView
from ui.history_view import HistoryView
from ui.settings_view import SettingsView


def _setup_logging():
    handler = RotatingFileHandler("app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
    logging.getLogger("yt_dlp").setLevel(logging.WARNING)


_setup_logging()
log = logging.getLogger("downloader")


class AppState:
    def __init__(self, page: ft.Page):
        self.page = page
        self.settings = settings_manager.load()
        self.engine = DownloaderEngine(
            ffmpeg_path=os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "bin"),
            output_dir=self.settings.get("output_dir", "downloads"),
            proxy=self.settings.get("proxy", ""),
            cookiefile=self.settings.get("cookiefile", ""),
        )
        self.queue = QueueManager(
            engine=self.engine,
            on_item_update=self._on_queue_update,
            max_concurrent=int(self.settings.get("max_concurrent", 1)),
        )
        self._main_view = None
        self._views = {}

    def _on_queue_update(self, item, status):
        if self._main_view is not None:
            try:
                self._main_view.on_queue_update(item, status)
            except Exception:
                log.exception("queue update callback failed")

    def navigate(self, route):
        """Navigate to a route (called from views)."""
        if self.page is not None:
            try:
                # In Flet desktop mode, push_route is sync. Use it directly.
                self.page.push_route(route)
            except Exception as ex:
                log.error("navigate failed: %s", ex)

    def get_or_create_view(self, route):
        """Get existing view or create a new one — prevents blank screens on route changes."""
        if route not in self._views:
            if route == "/history":
                v = HistoryView(self.page, self)
            elif route == "/settings":
                v = SettingsView(self.page, self)
            else:
                v = MainView(self.page, self)
                self._main_view = v
            self._views[route] = v
        return self._views[route]

    def apply_settings(self, settings):
        self.settings = settings
        self.engine.update_config(
            output_dir=settings.get("output_dir", "downloads"),
            proxy=settings.get("proxy", ""),
            cookiefile=settings.get("cookiefile", ""),
        )
        # Theme is handled separately — page.theme_mode doesn't change mid-session in Flet desktop
        if self._main_view is not None:
            try:
                self._main_view.quality_dropdown.value = settings.get("default_quality", "720p")
                if self.page is not None:
                    self._main_view.quality_dropdown.update()
            except Exception:
                pass
        if self.page is not None:
            self.page.update()

    def toggle_theme(self):
        new_theme = "dark" if self.settings.get("theme", "light") == "light" else "light"
        self.settings["theme"] = new_theme
        settings_manager.save(self.settings)
        # Apply theme to page (Flet desktop supports this)
        try:
            if hasattr(ft, 'ThemeMode'):
                self.page.theme_mode = ft.ThemeMode.DARK if new_theme == "dark" else ft.ThemeMode.LIGHT
        except Exception:
            pass
        if self._main_view is not None:
            try:
                self._main_view.quality_dropdown.value = self.settings.get("default_quality", "720p")
                if self.page is not None:
                    self._main_view.quality_dropdown.update()
            except Exception:
                pass
        if self.page is not None:
            self.page.update()
        log.info("theme toggled: %s", new_theme)

    def notify(self, message, title="Downloader"):
        try:
            from plyer import notification
            notification.notify(title=title, message=message, app_name="Media Downloader", timeout=5)
        except Exception as ex:
            log.warning("notification failed: %s", ex)


def main(page: ft.Page):
    app_state = AppState(page)

    page.title = "Media Downloader"
    page.window_width = 980
    page.window_height = 720
    page.window_min_width = 760
    page.window_min_height = 560
    page.padding = 0
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Route handler — key fix: use views directly, don't rely on push_route for initial load
    def route_change(e):
        route = page.route or "/"
        view = app_state.get_or_create_view(route)

        # Clear and rebuild views list
        page.views.clear()
        page.views.append(view)
        page.update()

    def view_pop(e):
        if len(page.views) > 1:
            page.views.pop()
            top = page.views[-1]
            page.push_route(top.route)
        else:
            # Only one view — re-add root
            root_view = app_state.get_or_create_view("/")
            page.views.clear()
            page.views.append(root_view)
            page.update()

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    def on_keyboard(e: ft.KeyboardEvent):
        active = page.views[-1] if page.views else None
        if not isinstance(active, MainView):
            return
        if e.key == "Enter" and not e.shift:
            active._on_add_click(None)
        elif hasattr(e, 'ctrl') and e.ctrl and (e.key == "L" or e.key == "l"):
            active.url_input.value = ""
            active.url_input.update()
        elif hasattr(e, 'ctrl') and e.ctrl and (e.key == "P" or e.key == "p"):
            active._on_preview_click(None)
        elif hasattr(e, 'ctrl') and e.ctrl and (e.key == "H" or e.key == "h"):
            page.push_route("/history")
        elif hasattr(e, 'ctrl') and e.ctrl and (e.key == "S" or e.key == "s"):
            page.push_route("/settings")

    page.on_keyboard_event = on_keyboard

    # Set initial route
    page.views.append(app_state.get_or_create_view("/"))
    page.update()
    log.info("app started")


if __name__ == "__main__":
    try:
        ft.run(main)
    except TypeError:
        ft.app(target=main)
