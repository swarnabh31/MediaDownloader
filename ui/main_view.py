import logging
import re
import subprocess
import threading
import time

import flet as ft

from core import history_manager
from core.downloader_engine import DownloaderEngine
from ui.components import build_app_bar
from ui.native_dialogs import pick_file
from ui.panels import NewDownloadPanel, QueuePanel

log = logging.getLogger("downloader")

URL_RE = re.compile(r"^\s*(https?|ftp)://\S+\.\S+(/\S*)?\s*$", re.IGNORECASE)

TWO_COLUMN_MIN = 1400
SINGLE_COLUMN_MAX_WIDTH = 1100
PAGE_PADDING = 28
PANEL_GAP = 24
INPUT_MIN_WIDTH = 420
INPUT_MAX_WIDTH = 600


def open_in_os(path):
    """Open a file/folder in the OS default app (platform aware)."""
    if not path:
        return
    import sys
    try:
        if sys.platform == "win32":
            import os
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        log.exception("open_in_os failed")


class MainView(ft.View):
    def __init__(self, page: ft.Page, app_state):
        super().__init__(
            route="/",
            padding=PAGE_PADDING,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self._page = page
        self.app_state = app_state
        self.engine: DownloaderEngine = app_state.engine

        self.input_panel = NewDownloadPanel(self)
        self.queue_panel = QueuePanel(self)

        self._row_controls = {}
        self._last_progress_at = {}
        self._thumbs_by_url = {}
        self._selected_format_id = None
        self._cookies_picker = None

        self.layout = ft.Container(expand=True)
        self._relayout()

        self.build_app_bar()

        # Controls list for ft.View: appbar on top, layout below
        self.controls = [self.appbar, ft.Column([self.layout], scroll=ft.ScrollMode.AUTO, expand=True)]

    # ----- layout ---------------------------------------------------------
    def _relayout(self, width=None):
        if width is None:
            width = max(800, float(getattr(self._page, "width", 0) or 0))
        two_col = width >= TWO_COLUMN_MIN

        def _wrap(panel, **kw):
            return ft.Container(
                content=panel,
                bgcolor="surfaceContainerLow",
                border=ft.BorderSide(1, "outlineVariant"),
                border_radius=16,
                padding=ft.Padding(left=24, top=20, right=24, bottom=20),
                **kw,
            )

        if two_col:
            available = max(width - PAGE_PADDING * 2, 700)
            left_w = min(max(int(available * 0.38), INPUT_MIN_WIDTH), INPUT_MAX_WIDTH)
            input_card = _wrap(self.input_panel, width=left_w)
            queue_card = _wrap(self.queue_panel, expand=True)
            inner = ft.Row(
                [input_card, queue_card],
                spacing=PANEL_GAP,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            self.layout.width = None
            self.layout.max_width = None
            self.layout.alignment = None
            self.layout.content = inner
            self.layout.expand = True
        else:
            single = ft.Column(
                [
                    _wrap(self.input_panel),
                    _wrap(self.queue_panel, expand=True, height=520),
                ],
                spacing=PANEL_GAP,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                expand=True,
            )
            self.layout.width = None
            self.layout.max_width = SINGLE_COLUMN_MAX_WIDTH
            self.layout.alignment = ft.alignment.Alignment(0, 0)
            self.layout.content = single
            self.layout.expand = True

    # ----- appbar ---------------------------------------------------------
    def _go_history(self):
        self.app_state.navigate("/history")

    def _go_settings(self):
        self.app_state.navigate("/settings")

    def build_app_bar(self):
        self.appbar = build_app_bar(
            self._page, "Media Downloader",
            getattr(self._page, "route", None), self.app_state.navigate,
            toggle_theme_fn=self.app_state.toggle_theme if hasattr(self.app_state, 'toggle_theme') else None,
            extra_actions=[
                ft.IconButton(ft.Icons.HISTORY, tooltip="History (Ctrl+H)", on_click=lambda _: self._go_history(),
                              size_constraints=ft.BoxConstraints(min_width=40, min_height=40)),
                ft.IconButton(ft.Icons.SETTINGS, tooltip="Settings (Ctrl+S)", on_click=lambda _: self._go_settings(),
                              size_constraints=ft.BoxConstraints(min_width=40, min_height=40)),
            ],
        )

    # ----- lifecycle ------------------------------------------------------
    def did_mount(self):
        self._refresh_cookies_label()
        if self._page is not None:
            self._page.update()

    # ----- cookies --------------------------------------------------------
    def _refresh_cookies_label(self):
        cf = self.app_state.settings.get("cookiefile", "")
        status = self.input_panel.cookies_status
        status.value = (f"Cookies: {cf.split('/')[-2]}/{cf.split('/')[-1]}" if cf else "No cookies file loaded")
        if self._page is not None:
            status.update()

    def _on_load_cookies_click(self, e):
        btn = self.input_panel.cookies_btn
        btn.disabled = True
        if self._page is not None:
            btn.update()

        def run():
            path = None
            try:
                path = pick_file(title="Select cookies.txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
            except Exception as ex:
                log.exception("cookies pick failed")
                self._set_status(f"Cookie picker failed: {ex}", error=True)
            finally:
                btn.disabled = False
            if not path:
                if self._page is not None:
                    btn.update()
                return
            self.app_state.settings["cookiefile"] = path
            self.engine.update_config(cookiefile=path)
            self._refresh_cookies_label()
            self._set_status(f"Cookies loaded: {path}")
            if self._page is not None:
                self._page.update()

        threading.Thread(target=run, daemon=True).start()

    # ----- URL ------------------------------------------------------------
    def _valid_url(self) -> bool:
        url = (self.input_panel.url_input.value or "").strip()
        return bool(url) and bool(URL_RE.match(url))

    def _update_button_states(self):
        valid = self._valid_url()
        for b in (self.input_panel.preview_btn, self.input_panel.formats_btn):
            b.disabled = not valid
            b.tooltip = "Enter a valid URL first" if not valid else None
        if self._page is not None:
            for b in (self.input_panel.preview_btn, self.input_panel.formats_btn):
                try:
                    b.update()
                except Exception:
                    pass

    def _on_url_change(self, e):
        self._update_button_states()

    def _on_paste_url(self):
        try:
            text = self._page.clipboard.get() or ""
        except Exception:
            text = ""
        if not text:
            self._set_status("Clipboard is empty", error=True)
            return
        self.input_panel.url_input.value = text.strip()
        self._update_button_states()
        if self._page is not None:
            try:
                self.input_panel.url_input.update()
            except Exception:
                pass

    def _on_clear_url(self):
        self.input_panel.url_input.value = ""
        self._update_button_states()
        self.input_panel.meta_card.visible = False
        self.input_panel.meta_title.value = ""
        self._selected_format_id = None
        if self._page is not None:
            try:
                self.input_panel.url_input.update()
            except Exception:
                pass
            try:
                self.input_panel.meta_card.update()
            except Exception:
                pass

    # ----- preview -------------------------------------------------------
    def _on_preview_click(self, e):
        url = (self.input_panel.url_input.value or "").strip()
        if not url:
            self._set_status("Please enter a URL first!", error=True)
            return
        self._set_status("Fetching metadata...")
        pbtn = self.input_panel.preview_btn
        pbtn.disabled = True
        if self._page is not None:
            pbtn.update()

        def run():
            try:
                meta = self.engine.fetch_metadata(url)
                panel = self.input_panel
                panel.meta_title.value = meta.get("title", "Unknown")
                panel.meta_uploader.value = f"Uploader: {meta.get('uploader', 'Unknown')}"
                panel.meta_duration.value = f"Duration: {meta.get('duration', '?')}"
                panel.meta_website.value = f"Site: {meta.get('website', '?')}"
                thumb = meta.get("thumbnail")
                if thumb:
                    panel.thumbnail.src = thumb
                    panel.thumbnail.visible = True
                    self._remember_thumb(url, thumb)
                else:
                    panel.thumbnail.visible = False
                    panel.thumbnail.src = ""
                panel.meta_card.visible = True
                self.input_panel.formats_btn.disabled = False
                self._set_status("Metadata loaded.")
            except Exception as ex:
                log.exception("preview failed")
                self._set_status(f"Preview failed: {ex}", error=True)
            finally:
                pbtn.disabled = False
                if self._page is not None:
                    self._page.update()

        threading.Thread(target=run, daemon=True).start()

    # ----- formats -------------------------------------------------------
    def _on_formats_click(self, e):
        url = (self.input_panel.url_input.value or "").strip()
        if not url:
            self._set_status("Enter a URL first!", error=True)
            return
        self._set_status("Fetching available formats...")
        fbtn = self.input_panel.formats_btn
        fbtn.disabled = True
        if self._page is not None:
            fbtn.update()

        def run():
            try:
                formats = self.engine.fetch_formats(url)
                self._open_formats_dialog(formats)
            except Exception as ex:
                log.exception("formats failed")
                self._set_status(f"Failed to fetch formats: {ex}", error=True)
            finally:
                fbtn.disabled = False
                if self._page is not None:
                    self._page.update()

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
                ft.TextButton("Close", on_click=lambda _: self._page.pop_dialog()),
            ],
        )
        self._page.show_dialog(dialog)

    def _pick_format(self, format_id):
        self._selected_format_id = format_id
        self._set_status(f"Selected format: {format_id}")
        if self._page is not None:
            self._page.pop_dialog()

    # ----- queue ---------------------------------------------------------
    def _on_add_click(self, e):
        url = (self.input_panel.url_input.value or "").strip()
        if not url:
            self._set_status("Please enter a URL first!", error=True)
            return
        quality = self.input_panel.quality_dropdown.value
        item = self.app_state.queue.add(url, quality, format_id=self._selected_format_id)
        self._clear_error_banner()
        self._set_status(f"Queued: {url[:60]}{'...' if len(url) > 60 else ''}")
        self.queue_panel.render()
        self.input_panel.url_input.value = ""
        self.input_panel.meta_card.visible = False
        self.input_panel.meta_title.value = ""
        self.input_panel.thumbnail.visible = False
        self.input_panel.thumbnail.src = ""
        self._selected_format_id = None
        self._update_button_states()
        if self._page is not None:
            self._page.update()

    def _on_clear_finished(self, e):
        self.app_state.queue.clear_finished()
        self.queue_panel.render()
        if self._page is not None:
            self._page.update()

    def _remove_item(self, item_id):
        self.app_state.queue.remove(item_id)
        self.queue_panel.render()
        if self._page is not None:
            self._page.update()

    def _cancel_item(self, item_id):
        self.app_state.queue.cancel_item(item_id)
        self.queue_panel.render()
        if self._page is not None:
            self._page.update()

    def _redownload(self, url):
        if not url:
            return
        quality = self.input_panel.quality_dropdown.value
        self.app_state.queue.add(url, quality, format_id=self._selected_format_id)
        self.queue_panel.render()
        self._set_status(f"Re-queued: {url[:60]}{'...' if len(url) > 60 else ''}")
        if self._page is not None:
            self._page.update()

    def _open_url(self, url):
        if not url:
            return
        import webbrowser
        webbrowser.open(url)

    def _open_folder(self, path):
        if not path:
            self._set_status("Download still in progress — no file yet", error=False)
            return
        open_in_os(path)
        if self._page is not None:
            self._page.update()

    def _set_status(self, msg, error=False):
        t = self.input_panel.status_text
        t.value = msg
        t.color = "error" if error else "onSurfaceVariant"
        if self._page is not None:
            try:
                t.update()
            except Exception:
                pass

    # ----- row / meta helpers (used by QueuePanel) -----------------------
    def _meta_for(self, item):
        if item["status"] == "downloading":
            speed = item.get("speed", "")
            eta = item.get("eta", "")
            if speed or eta:
                parts = []
                if speed:
                    parts.append(speed)
                if eta:
                    parts.append(f"ETA {eta}")
                return "  •  ".join(parts)
            return "Starting..."
        if item["status"] in ("error", "cancelled"):
            return (item.get("error") or "Unknown error")[:120]
        if item["status"] == "processing":
            return "Processing..."
        if item["status"] == "done":
            p = item.get("file_path")
            if p:
                return f"Saved to {p}"
            return "Download complete"
        return ""

    def _item_thumb(self, item, url):
        """Return the thumbnail URL for a queue item (item dict may carry 'thumbnail')."""
        return item.get("thumbnail", "") or ""

    def _downloads_dir(self):
        return self.app_state.settings.get("output_dir", "downloads")

    def _remember_thumb(self, url, thumb):
        if url and thumb:
            self._thumbs_by_url[url] = thumb

    # ----- queue updates --------------------------------------------------
    def on_queue_update(self, item, status):
        if self._page is None or self._page.session is None:
            return
        try:
            self._page.run_task(self._apply_queue_update, item, status)
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
                self.queue_panel.render()
            else:
                self.queue_panel.render()

            if status == "done":
                title = item.get("title") or item.get("url", "Unknown")
                self._clear_error_banner()
                history_manager.add_entry(
                    title=title,
                    url=item.get("url", ""),
                    quality=item.get("quality", ""),
                    file_path="",
                    size_mb=0.0,
                )
                self.app_state.notify(f'Download complete: "{title}"')
            elif status == "error":
                # Inline, non-modal error banner: always visible in the UI and
                # guaranteed non-blocking (no modal dialog, no page snackbar).
                try:
                    self._show_download_error(item)
                except Exception:
                    log.exception("error banner failed; falling back to status text")
                    try:
                        self._set_status(
                            item.get("error") or "The download could not be completed.",
                            error=True,
                        )
                    except Exception:
                        pass
            if self._page is not None:
                self._page.update()
        except Exception:
            log.exception("on_queue_update failed")

    def _patch_row(self, item):
        controls = self._row_controls.get(item["id"])
        if not controls:
            return
        progress, pct, meta = (controls + (None, None, None))[:3]
        progress.value = item.get("progress", 0.0)
        if pct is not None:
            pct.value = f"{int(item.get('progress', 0.0) * 100)}%"
        meta.value = self._meta_for(item)
        if self._page is not None:
            progress.update()
            if pct is not None:
                pct.update()
            meta.update()

    def _show_download_error(self, item):
        """Show a download failure as an inline, non-modal banner on the UI.

        Never raises and never blocks: the message is rendered straight into the
        panel's DOM (no modal dialog, no page-level snackbar), so the app can
        never hang when a download fails. Also mirrors the message into the
        small status line for good measure.
        """
        err = (item.get("error") or "The download could not be completed.").strip()
        if not err:
            err = "The download could not be completed."

        try:
            panel = self.input_panel
            if getattr(panel, "error_banner_text", None) is not None:
                panel.error_banner_text.value = err
                panel.error_banner.visible = True
            self._set_status(err[:160], error=True)
        except Exception:
            log.exception("failed to render download error banner")
        finally:
            if self._page is not None:
                try:
                    self._page.update()
                except Exception:
                    pass

    def _clear_error_banner(self):
        try:
            panel = self.input_panel
            if getattr(panel, "error_banner", None) is not None and panel.error_banner.visible:
                panel.error_banner.visible = False
                panel.error_banner_text.value = ""
        except Exception:
            pass
