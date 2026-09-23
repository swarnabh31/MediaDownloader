import flet as ft
import threading
import logging
import time

from core import history_manager
from core.downloader_engine import DownloaderEngine
from ui.components import status_chip, build_app_bar, snack
from ui.native_dialogs import pick_file

log = logging.getLogger("downloader")


class MainView(ft.View):
    def __init__(self, page: ft.Page, app_state):
        super().__init__(
            route="/",
            padding=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
        self._page = page
        self.app_state = app_state
        self.engine: DownloaderEngine = app_state.engine

        self.url_input = ft.TextField(
            label="Paste Video URL",
            width=620,
            hint_text="https://www.youtube.com/watch?v=...",
            prefix_icon=ft.Icons.LINK,
            on_submit=lambda _: self._on_add_click(None),
            autofocus=True,
        )

        self.quality_dropdown = ft.Dropdown(
            label="Quality",
            width=180,
            options=[
                ft.dropdown.Option("2160p"),
                ft.dropdown.Option("1440p"),
                ft.dropdown.Option("1080p"),
                ft.dropdown.Option("720p"),
                ft.dropdown.Option("Audio"),
            ],
            value=app_state.settings.get("default_quality", "720p"),
        )

        self.preview_btn = ft.Button(
            "Preview",
            icon=ft.Icons.INFO_OUTLINE,
            on_click=self._on_preview_click,
        )

        self.formats_btn = ft.OutlinedButton(
            "Formats",
            icon=ft.Icons.LIST_ALT,
            on_click=self._on_formats_click,
            disabled=True,
        )

        self.add_btn = ft.Button(
            "Add to Queue",
            icon=ft.Icons.ADD,
            on_click=self._on_add_click,
            style=ft.ButtonStyle(
                color="white",
                bgcolor="primary",
            ),
        )

        self.cookies_btn = ft.TextButton(
            "Load Cookies",
            icon=ft.Icons.COOKIE,
            on_click=self._on_load_cookies_click,
        )
        self._load_cookies_btn = self.cookies_btn

        self.thumbnail = ft.Image(
            src="",
            width=180,
            height=100,
            fit=ft.BoxFit.COVER,
            visible=False,
            border_radius=8,
        )

        self.meta_title = ft.Text("", size=16, weight=ft.FontWeight.BOLD, selectable=True)
        self.meta_uploader = ft.Text("", size=12)
        self.meta_duration = ft.Text("", size=12)
        self.meta_website = ft.Text("", size=12)

        self.meta_card = ft.Card(
            visible=False,
            content=ft.Container(
                content=ft.Row(
                    [
                        self.thumbnail,
                        ft.Column(
                            [
                                self.meta_title,
                                self.meta_uploader,
                                self.meta_duration,
                                self.meta_website,
                            ],
                            spacing=2,
                            tight=True,
                        ),
                    ],
                    spacing=14,
                ),
                padding=12,
            ),
        )

        self.status_text = ft.Text("", size=13, italic=True)
        self.cookies_status = ft.Text("", size=11)

        self.cookies_picker = None
        self._selected_format_id = None

        self.queue_list = ft.ListView(
            spacing=8,
            height=320,
            padding=4,
            auto_scroll=True,
        )
        self._row_controls = {}
        self._last_progress_at = {}

        # Build without page context — create the content separately
        self._main_content = self._create_main_content()
        self._build()

    def _create_main_content(self):
        """Create the full main view content without needing page."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Download videos & audio from 1800+ sites", size=14, text_align=ft.TextAlign.CENTER),
                    ft.Row([self.url_input], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row(
                        [self.quality_dropdown, self.preview_btn, self.formats_btn, self.add_btn],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                        wrap=True,
                    ),
                    ft.Row([self.cookies_btn, self.cookies_status], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
                    self.meta_card,
                    self.status_text,
                    ft.Divider(),
                    ft.Row(
                        [
                            ft.Text("Download Queue", size=18, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.TextButton(
                                "Clear Finished",
                                icon=ft.Icons.CLEANING_SERVICES,
                                on_click=self._on_clear_finished,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.queue_list,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=12,
            ),
            padding=ft.Padding.symmetric(horizontal=24),
            expand=True,
        )

    def _build(self):
        def _go_history():
            if self.app_state and self.app_state.page:
                self.app_state.navigate("/history")

        def _go_settings():
            if self.app_state and self.app_state.page:
                self.app_state.navigate("/settings")

        self.appbar = build_app_bar(
            self._page, "Media Downloader",
            getattr(self._page, "route", None), self.app_state.navigate,
            toggle_theme_fn=self.app_state.toggle_theme if hasattr(self.app_state, 'toggle_theme') else None,
            extra_actions=[
                ft.IconButton(ft.Icons.HISTORY, tooltip="History", on_click=lambda _: _go_history()),
                ft.IconButton(ft.Icons.SETTINGS, tooltip="Settings", on_click=lambda _: _go_settings()),
            ],
        )

        self.controls = [
            ft.Column([
                self._main_content,
            ], scroll=ft.ScrollMode.AUTO, expand=True),
        ]

    def did_mount(self):
        self._refresh_cookies_label()

    def _refresh_cookies_label(self):
        cf = self.app_state.settings.get("cookiefile", "")
        self.cookies_status.value = f"Cookies: {cf}" if cf else "No cookies file loaded"
        if self.page is not None:
            self.cookies_status.update()

    def _on_load_cookies_click(self, e):
        self._load_cookies_btn.disabled = True
        self._load_cookies_btn.update()

        def run():
            try:
                path = pick_file(title="Select cookies.txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
            except Exception as ex:
                log.exception("cookies pick failed")
                self._set_status(f"Cookie picker failed: {ex}", error=True)
                return
            finally:
                if hasattr(self, '_load_cookies_btn'):
                    self._load_cookies_btn.disabled = False
            if not path:
                return
            self.app_state.settings["cookiefile"] = path
            self.engine.update_config(cookiefile=path)
            self._refresh_cookies_label()
            self._set_status(f"Cookies loaded: {path}")
            if self.page is not None:
                self.page.update()

        threading.Thread(target=run, daemon=True).start()

    def _on_preview_click(self, e):
        url = (self.url_input.value or "").strip()
        if not url:
            self._set_status("Please enter a URL first!", error=True)
            return
        self._set_status("Fetching metadata...")
        self.preview_btn.disabled = True
        self.preview_btn.update()

        def run():
            try:
                meta = self.engine.fetch_metadata(url)
                self.meta_title.value = meta.get("title", "Unknown")
                self.meta_uploader.value = f"Uploader: {meta.get('uploader', 'Unknown')}"
                self.meta_duration.value = f"Duration: {meta.get('duration', '?')}"
                self.meta_website.value = f"Site: {meta.get('website', '?')}"
                thumb = meta.get("thumbnail")
                if thumb:
                    self.thumbnail.src = thumb
                    self.thumbnail.visible = True
                else:
                    self.thumbnail.visible = False
                self.meta_card.visible = True
                self.formats_btn.disabled = False
                self._set_status("Metadata loaded.")
            except Exception as ex:
                log.exception("preview failed")
                self._set_status(f"Preview failed: {ex}", error=True)
            finally:
                self.preview_btn.disabled = False
                if self.page is not None:
                    self.page.update()

        threading.Thread(target=run, daemon=True).start()

    def _on_formats_click(self, e):
        url = (self.url_input.value or "").strip()
        if not url:
            self._set_status("Enter a URL first!", error=True)
            return
        self._set_status("Fetching available formats...")
        self.formats_btn.disabled = True
        self.formats_btn.update()

        def run():
            try:
                formats = self.engine.fetch_formats(url)
                self._open_formats_dialog(formats)
            except Exception as ex:
                log.exception("formats failed")
                self._set_status(f"Failed to fetch formats: {ex}", error=True)
            finally:
                self.formats_btn.disabled = False
                if self.page is not None:
                    self.page.update()

        threading.Thread(target=run, daemon=True).start()

    def _open_formats_dialog(self, formats):
        rows = []
        for f in formats[:80]:
            size = f"{f['size_mb']} MB" if f.get("size_mb") else "?"
            rows.append(ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(f.get("id", "?")))),
                    ft.DataCell(ft.Text(str(f.get("res", "?")))),
                    ft.DataCell(ft.Text(str(f.get("fps", "?")))),
                    ft.DataCell(ft.Text(str(f.get("ext", "?")))),
                    ft.DataCell(ft.Text(str(f.get("vcodec", "?")))),
                    ft.DataCell(ft.Text(str(f.get("acodec", "?")))),
                    ft.DataCell(ft.Text(size)),
                ],
                on_select_changed=lambda e, fid=f.get("id"): self._pick_format(fid),
            ))

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Res")),
                ft.DataColumn(ft.Text("FPS")),
                ft.DataColumn(ft.Text("Ext")),
                ft.DataColumn(ft.Text("Video")),
                ft.DataColumn(ft.Text("Audio")),
                ft.DataColumn(ft.Text("Size")),
            ],
            rows=rows,
            heading_row_height=36,
            data_row_min_height=32,
            data_row_max_height=40,
        )

        dialog = ft.AlertDialog(
            title=ft.Text("Available Formats"),
            content=ft.Container(content=table, width=720, height=420),
            actions=[
                ft.TextButton("Close", on_click=lambda _: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)

    def _pick_format(self, format_id):
        self._selected_format_id = format_id
        self._set_status(f"Selected format: {format_id}")
        if self.page is not None:
            self.page.pop_dialog()

    def _on_add_click(self, e):
        url = (self.url_input.value or "").strip()
        if not url:
            self._set_status("Please enter a URL first!", error=True)
            return
        quality = self.quality_dropdown.value
        item = self.app_state.queue.add(url, quality, format_id=self._selected_format_id)
        self._set_status(f"Queued: {url[:60]}{'...' if len(url) > 60 else ''}")
        self._render_queue()
        self.url_input.value = ""
        self._selected_format_id = None
        if self.page is not None:
            self.page.update()

    def _on_clear_finished(self, e):
        self.app_state.queue.clear_finished()
        self._render_queue()
        if self.page is not None:
            self.page.update()

    def _set_status(self, msg, error=False):
        self.status_text.value = msg
        self.status_text.color = "red" if error else None
        if self.page is not None and self.status_text.page is not None:
            self.status_text.update()

    def _render_queue(self):
        items = self.app_state.queue.list_items()
        self.queue_list.controls = [self._build_queue_row(it) for it in items] or [
            ft.Container(
                content=ft.Text("Queue is empty. Paste a URL and click 'Add to Queue'."),
                padding=20,
            )
        ]

    def _meta_for(self, item):
        if item["status"] == "downloading":
            speed = item.get("speed", "")
            eta = item.get("eta", "")
            return f"{speed}  •  ETA: {eta}" if speed or eta else "Starting..."
        if item["status"] in ("error", "cancelled"):
            return item.get("error", "Unknown error")[:80]
        if item["status"] == "processing":
            return "Processing..."
        return ""

    def _build_queue_row(self, item):
        title = item.get("title") or item.get("url", "")
        if len(title) > 60:
            title = title[:57] + "..."

        progress = ft.ProgressBar(value=item.get("progress", 0.0), expand=True, bar_height=6)
        meta = ft.Text(self._meta_for(item), size=11, italic=True)

        buttons = [ft.IconButton(
            ft.Icons.DELETE_OUTLINE,
            tooltip="Remove",
            on_click=lambda e, iid=item["id"]: self._remove_item(iid),
        )]
        if item["status"] in ("queued", "downloading", "processing"):
            buttons.insert(0, ft.IconButton(
                ft.Icons.STOP,
                tooltip="Cancel",
                icon_color="red",
                on_click=lambda e, iid=item["id"]: self._cancel_item(iid),
            ))

        card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(title, weight=ft.FontWeight.BOLD, size=13, selectable=True),
                                        ft.Text(item.get("url", ""), size=10, color=None, selectable=True),
                                    ],
                                    expand=True,
                                    spacing=2,
                                ),
                                status_chip(item["status"]),
                                ft.Row(buttons, spacing=4),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        progress,
                        meta,
                    ],
                    spacing=6,
                ),
                padding=10,
            )
        )
        self._row_controls[item["id"]] = (progress, meta)
        return card

    def _patch_row(self, item):
        controls = self._row_controls.get(item["id"])
        if not controls:
            return
        progress, meta = controls
        progress.value = item.get("progress", 0.0)
        progress.update()
        meta.value = self._meta_for(item)
        meta.update()

    def _remove_item(self, item_id):
        self.app_state.queue.remove(item_id)
        self._row_controls.pop(item_id, None)
        self._render_queue()
        if self.page is not None:
            self.page.update()

    def _cancel_item(self, item_id):
        self.app_state.queue.cancel_item(item_id)
        self._render_queue()
        if self.page is not None:
            self.page.update()

    def on_queue_update(self, item, status):
        if self.page is None or self.page.session is None:
            return
        try:
            self.page.run_task(self._apply_queue_update, item, status)
        except Exception:
            log.exception("on_queue_update failed to schedule")

    async def _apply_queue_update(self, item, status):
        try:
            if status == "downloading":
                now = time.time()
                last = self._last_progress_at.get(item["id"], 0.0)
                if now - last < 0.15:
                    return
                self._last_progress_at[item["id"]] = now
                self._patch_row(item)
                return
            if status == "processing":
                try:
                    self._patch_row(item)
                except Exception:
                    pass
                self._render_queue()
            else:
                self._render_queue()

            if status == "done":
                title = item.get("title") or item.get("url", "Unknown")
                history_manager.add_entry(
                    title=title,
                    url=item.get("url", ""),
                    quality=item.get("quality", ""),
                    file_path="",
                    size_mb=0.0,
                )
                self.app_state.notify(f'Download complete: "{title}"')
            elif status == "error" and item.get("blocked_403"):
                self._show_blocked_toast()
            if self.page is not None:
                self.page.update()
        except Exception:
            log.exception("on_queue_update failed")

    def _show_blocked_toast(self):
        if self.page is None:
            return
        msg = (
            "YouTube blocked this download (HTTP 403).\n"
            "Add login cookies in Settings, set a proxy, or switch networks (restart router / mobile hotspot)."
        )
        snack(self.page, msg, bgcolor="red")
