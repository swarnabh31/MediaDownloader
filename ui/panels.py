import flet as ft

from ui.components import card, status_chip
from core import history_manager


INPUT_HEIGHT = 60


def _icon_btn(icon, tooltip, on_click, icon_color=None):
    return ft.IconButton(
        icon,
        tooltip=tooltip,
        icon_color=icon_color,
        icon_size=20,
        on_click=on_click,
        size_constraints=ft.BoxConstraints(min_width=40, min_height=40),
    )


class NewDownloadPanel(ft.Column):
    """The "New Download" card: URL field (hero), quality dropdown,
    Preview / Formats / Add to Queue, preview metadata and the cookies row.

    All handlers are delegated to the `owner` (MainView) so the state
    stays where it always was."""

    def __init__(self, owner):
        view = owner
        super().__init__(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.url_input = ft.TextField(
            label="Paste Video URL",
            hint_text="https://www.youtube.com/watch?v=...",
            value="",
            prefix_icon=ft.Icons.LINK,
            height=INPUT_HEIGHT,
            dense=True,
            text_size=16,
            border_radius=12,
            on_change=view._on_url_change,
            on_submit=lambda _: view._on_add_click(None),
            autofocus=True,
            suffix_icon=ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.PASTE,
                        tooltip="Paste from clipboard",
                        icon_size=20,
                        icon_color="onSurfaceVariant",
                        on_click=lambda _: view._on_paste_url(),
                        size_constraints=ft.BoxConstraints(min_width=40, min_height=40),
                    ),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        tooltip="Clear",
                        icon_size=18,
                        icon_color="onSurfaceVariant",
                        on_click=lambda _: view._on_clear_url(),
                        size_constraints=ft.BoxConstraints(min_width=40, min_height=40),
                    ),
                ],
                spacing=2,
                tight=True,
            ),
        )

        self.quality_dropdown = ft.Dropdown(
            label="Quality",
            width=180,
            height=INPUT_HEIGHT,
            dense=True,
            options=[
                ft.dropdown.Option("2160p"),
                ft.dropdown.Option("1440p"),
                ft.dropdown.Option("1080p"),
                ft.dropdown.Option("720p"),
                ft.dropdown.Option("Audio"),
            ],
            value=view.app_state.settings.get("default_quality", "720p"),
        )

        self.preview_btn = ft.OutlinedButton(
            "Preview",
            icon=ft.Icons.INFO_OUTLINE,
            height=INPUT_HEIGHT,
            on_click=view._on_preview_click,
            disabled=True,
            tooltip="Enter a valid URL first",
        )

        self.formats_btn = ft.OutlinedButton(
            "Formats",
            icon=ft.Icons.LIST_ALT,
            height=INPUT_HEIGHT,
            on_click=view._on_formats_click,
            disabled=True,
            tooltip="Enter a URL first",
        )

        self.add_btn = ft.Button(
            "Add to Queue",
            icon=ft.Icons.ADD,
            height=INPUT_HEIGHT,
            on_click=view._on_add_click,
            style=ft.ButtonStyle(
                color="onPrimary",
                bgcolor="primary",
                shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(12)),
            ),
        )

        self.cookies_btn = ft.OutlinedButton(
            "Load Cookies",
            icon=ft.Icons.COOKIE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.all(10)),
                padding=ft.Padding(left=12, top=8, right=12, bottom=8),
            ),
            on_click=view._on_load_cookies_click,
        )
        view._load_cookies_btn = self.cookies_btn
        self.cookies_status = ft.Text("", size=12, color="onSurfaceVariant")

        self.thumbnail = ft.Image(
            src="",
            width=180,
            height=100,
            fit=ft.BoxFit.COVER,
            visible=False,
            border_radius=8,
        )
        self.meta_title = ft.Text(
            "",
            size=15,
            weight=ft.FontWeight.W_600,
            selectable=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.meta_uploader = ft.Text("", size=12, color="onSurfaceVariant")
        self.meta_duration = ft.Text("", size=12, color="onSurfaceVariant")
        self.meta_website = ft.Text("", size=12, color="onSurfaceVariant")
        self.meta_card = ft.Container(
            content=ft.Row(
                [
                    self.thumbnail,
                    ft.Column(
                        [self.meta_title, self.meta_uploader, self.meta_duration, self.meta_website],
                        spacing=2,
                        tight=True,
                        expand=True,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor="surfaceContainerHigh",
            border_radius=12,
            visible=False,
        )

        self.status_text = ft.Text(
            "",
            size=13,
            italic=True,
            color="onSurfaceVariant",
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        # Non-modal, inline error banner. Shown directly in the UI (never as a
        # modal dialog) whenever a download fails, so the app never hangs and
        # the failure is always visible. Hidden by default.
        self.error_banner_text = ft.Text(
            "",
            size=13,
            color="error",
            selectable=True,
        )
        self.error_banner = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color="error", size=22),
                    ft.Column(
                        [
                            ft.Text(
                                "Download failed",
                                size=14,
                                weight=ft.FontWeight.W_600,
                                color="error",
                            ),
                            self.error_banner_text,
                        ],
                        spacing=3,
                        expand=True,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="surfaceContainerHigh",
            border=ft.BorderSide(1, "error"),
            border_radius=12,
            padding=ft.Padding(left=14, top=12, right=14, bottom=12),
            visible=False,
        )

        self.controls = [
            ft.Text("New Download", size=21, weight=ft.FontWeight.W_600),
            ft.Row([self.url_input], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row(
                [self.quality_dropdown, self.preview_btn, self.formats_btn, self.add_btn],
                wrap=True,
                spacing=10,
                run_spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            self.meta_card,
            self.error_banner,
            self.status_text,
            ft.Row([self.cookies_btn, self.cookies_status], spacing=8,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ]


class QueuePanel(ft.Column):
    """The "Download Queue" card.

    - Expands to fill its container; internal ListView scrolls
    - When empty: designed empty state (icon, heading, sub-text, Recent list)
    """

    def __init__(self, owner):
        self._owner = owner
        self._recent_added = False
        super().__init__(spacing=10, expand=True)

        self.heading = ft.Text("Download Queue", size=21, weight=ft.FontWeight.W_600, no_wrap=True)
        self.header_row = ft.Row(
            [
                self.heading,
                ft.Container(expand=True),
                _icon_btn(ft.Icons.CLEANING_SERVICES, "Clear Finished",
                          lambda _: owner._on_clear_finished(None)),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._empty_core = ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.CLOUD_DOWNLOAD, size=56, color="onSurfaceVariant"),
                    width=96,
                    height=96,
                    alignment=ft.alignment.Alignment(0, 0),
                    bgcolor="surfaceContainerHigh",
                    border_radius=48,
                ),
                ft.Container(height=8),
                ft.Text("No downloads yet", size=18, weight=ft.FontWeight.W_600),
                ft.Container(height=8),
                ft.Text(
                    "Paste a video link on the left and click Add to Queue",
                    size=13,
                    color="onSurfaceVariant",
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            spacing=0,
        )
        self._empty_wrap = ft.Column([self._empty_core],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    align=ft.MainAxisAlignment.CENTER,
                                    expand=True)
        self.empty_state = ft.Container(
            content=self._empty_wrap,
            expand=True,
        )

        self.queue_list = ft.ListView(
            spacing=12,
            padding=ft.Padding(left=14, top=14, right=14, bottom=14),
            auto_scroll=True,
            expand=True,
            visible=False,
        )

        self.controls = [
            self.header_row,
            self.empty_state,
            self.queue_list,
        ]

    # ----- helpers ---------------------------------------------------------
    def _meta_row_text(self, item):
        view = self._owner
        txt = view._meta_for(item)
        if not txt:
            if item["status"] == "queued":
                txt = "Waiting to start..."
            elif item["status"] == "downloading":
                txt = "Starting..."
        return txt

    def _host(self, url):
        if not url:
            return ""
        if "//" not in url:
            return ""
        rest = url.split("//", 1)[1]
        parts = rest.split("/", 1)
        if not parts:
            return ""
        return parts[0]

    def _thumb_for(self, item):
        thumb = item.get("thumbnail") or ""
        if not thumb:
            url = item.get("url", "")
            thumb = self._owner._item_thumb(item, url) or ""
        return thumb

    def _build_row(self, item):
        view = self._owner
        title = item.get("title") or item.get("url", "Untitled")
        site = self._host(item.get("url", ""))

        thumb_url = self._thumb_for(item)
        if thumb_url:
            thumb = ft.Image(
                src=thumb_url,
                width=96,
                height=60,
                fit=ft.BoxFit.COVER,
                border_radius=10,
            )
        else:
            thumb = ft.Container(
                content=ft.Icon(ft.Icons.MOVIE_CREATION, size=24, color="onSurfaceVariant"),
                width=96,
                height=60,
                alignment=ft.alignment.Alignment(0, 0),
                bgcolor="surfaceContainerHigh",
                border_radius=10,
            )

        quality = item.get("quality") or "?"
        ext = "MP3" if quality == "Audio" else "MP4"
        chip = ft.Container(
            content=ft.Text(f"{quality}  •  {ext}".upper(),
                            size=11, weight=ft.FontWeight.W_600, color="onSurfaceVariant"),
            bgcolor="surfaceContainerHigh",
            border_radius=8,
            padding=ft.Padding(left=8, top=3, right=8, bottom=3),
        )

        progress = ft.ProgressBar(
            value=item.get("progress", 0.0),
            bar_height=6,
            border_radius=3,
            expand=True,
            color="primary" if item["status"] in ("downloading", "processing") else None,
        )
        pct = ft.Text(f"{int(item.get('progress', 0.0) * 100)}%",
                      size=12, weight=ft.FontWeight.W_600)
        meta = ft.Text(self._meta_row_text(item), size=12, color="onSurfaceVariant",
                       no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)

        buttons = []
        active = item["status"] in ("queued", "downloading", "processing")
        if active:
            buttons.append(_icon_btn(ft.Icons.STOP, "Cancel",
                                     lambda e, iid=item["id"]: view._cancel_item(iid),
                                     icon_color="error"))
        if item["status"] == "done":
            buttons.append(_icon_btn(ft.Icons.FOLDER_OPEN, "Open downloads folder",
                                     lambda e, p=view._downloads_dir(): view._open_folder(p)))
        buttons.append(_icon_btn(ft.Icons.DELETE_OUTLINE, "Remove",
                                 lambda e, iid=item["id"]: view._remove_item(iid)))

        row = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            thumb,
                            ft.Column(
                                [
                                    ft.Text(
                                        title,
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                        no_wrap=True,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        selectable=True,
                                    ),
                                    ft.Row(
                                        [
                                            ft.Text(site, size=11, color="onSurfaceVariant",
                                                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                                            chip,
                                        ],
                                        spacing=8,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=2,
                                tight=True,
                                expand=True,
                            ),
                            status_chip(item["status"], page=self._page()),
                            ft.Row(buttons, spacing=2, tight=True,
                                  vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row([progress, pct], spacing=10,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    meta,
                ],
                spacing=8,
            ),
            padding=ft.Padding(left=14, top=12, right=8, bottom=12),
            **card(),
        )
        view._row_controls[item["id"]] = (progress, pct, meta)
        return row

    def _page(self):
        """Best-effort access to the live Page (for chip theming)."""
        try:
            return self._owner._page
        except Exception:
            return None

    # ----- recent section -------------------------------------------------
    def _recent_section(self):
        owner = self._owner
        history = history_manager.load_history()[:5]
        if not history:
            return None
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Recent downloads", size=15, weight=ft.FontWeight.W_600),
                        ft.Container(expand=True),
                        ft.TextButton("View all", icon=ft.Icons.HISTORY,
                                      on_click=lambda _: owner._go_history()),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.DOWNLOAD_DONE, size=20, color="green"),
                                    ft.Column(
                                        [
                                            ft.Text(str(r.get("title", "?"))[:70],
                                                    size=13, weight=ft.FontWeight.W_600,
                                                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                                                    selectable=True),
                                            ft.Text(
                                                f"{r.get('quality', '?')}   •   {r.get('size_mb', 0)} MB   •   {r.get('date', '')}",
                                                size=11, color="onSurfaceVariant"),
                                        ],
                                        spacing=1,
                                        tight=True,
                                        expand=True,
                                    ),
                                    _icon_btn(ft.Icons.REPLAY, "Re-download",
                                              lambda e, u=r.get("url", ""): owner._redownload(u)),
                                ],
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            padding=ft.Padding(left=12, top=10, right=6, bottom=10),
                            bgcolor="surfaceContainerHigh",
                            border_radius=12,
                        )
                        for r in history
                    ],
                    spacing=8,
                ),
            ],
            spacing=10,
        )

    def _sync_recent(self):
        """Add or drop the Recent section inside the empty-state column."""
        wrap = self._empty_wrap
        recent = self._recent_section() if not self._recent_added else None
        if recent is None and self._recent_added:
            # drop the recent column (index 1, since index 0 is core)
            if len(wrap.controls) > 1 and wrap.controls[1] is not self._empty_core:
                wrap.controls.pop(1)
            wrap.controls = [self._empty_core]
            self._recent_added = False
        elif recent is not None and not self._recent_added:
            wrap.controls.append(recent)
            wrap.controls.append(ft.Container(height=12))
            self._recent_added = True

    # ----- public API ------------------------------------------------------
    def render(self):
        view = self._owner
        items = view.app_state.queue.list_items()
        self.heading.value = "Download Queue" + (f" ({len(items)})" if items else "")

        if not items:
            self.queue_list.visible = False
            self.queue_list.controls = []
            view._row_controls = {}
            self.empty_state.visible = True
            self._sync_recent()
        else:
            self._sync_recent()  # no-op: keeps state consistent
            self.empty_state.visible = False
            self.queue_list.visible = True
            self.queue_list.controls = [self._build_row(it) for it in items]
