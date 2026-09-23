import flet as ft

from core import history_manager
from ui.components import build_app_bar, snack


class HistoryView(ft.View):
    def __init__(self, page: ft.Page, app_state):
        super().__init__(
            route="/history",
            padding=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
        self._page = page
        self.app_state = app_state

        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Title")),
                ft.DataColumn(ft.Text("Quality")),
                ft.DataColumn(ft.Text("Size (MB)")),
                ft.DataColumn(ft.Text("Date")),
                ft.DataColumn(ft.Text("URL")),
                ft.DataColumn(ft.Text("")),
            ],
            rows=[],
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=60,
        )

        self.table_container = ft.Container(
            content=ft.Row([self.table], scroll=ft.ScrollMode.AUTO),
            width=900,
        )

        self.empty_text = ft.Text(
            "No downloads yet. Your download history will appear here.",
            italic=True,
        )

        # Build the controls without needing page context
        self._content = self._create_content()
        self._build()

    def _create_content(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Download History", size=22, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.OutlinedButton(
                                "Refresh",
                                icon=ft.Icons.REFRESH,
                                on_click=lambda _: self.refresh(),
                            ),
                            ft.Button(
                                "Clear History",
                                icon=ft.Icons.DELETE_FOREVER,
                                on_click=self._on_clear,
                                style=ft.ButtonStyle(
                                    color="white",
                                    bgcolor="red",
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(),
                    self.empty_text,
                    self.table_container,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            width=940,
        )

    def _build(self):
        self.appbar = build_app_bar(
            self._page, "Download History", self._page.route, self.app_state.navigate,
            on_back=lambda: self.app_state.navigate("/"),
        )
        self.controls = [self._content]

    def did_mount(self):
        self.refresh()

    def refresh(self):
        history = history_manager.load_history()
        if not history:
            self.empty_text.visible = True
            self.table_container.visible = False
            if self.page is not None:
                self.page.update()
            return
        self.empty_text.visible = False
        self.table_container.visible = True

        rows = []
        for i, item in enumerate(history):
            url_cell = ft.Container(
                content=ft.Text(
                    str(item.get("url", ""))[:40],
                    size=11,
                    color="primary",
                    selectable=True,
                ),
                on_click=lambda e, u=item.get("url", ""): self._copy_url(u),
                tooltip="Click to copy",
            )
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(item.get("title", "?"))[:60], selectable=True)),
                        ft.DataCell(ft.Text(str(item.get("quality", "?")))),
                        ft.DataCell(ft.Text(str(item.get("size_mb", "?")))),
                        ft.DataCell(ft.Text(str(item.get("date", "?")))),
                        ft.DataCell(url_cell),
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE,
                                tooltip="Remove",
                                on_click=lambda e, idx=i: self._on_remove(idx),
                            )
                        ),
                    ]
                )
            )

        self.table.rows = rows
        if self.page is not None:
            self.page.update()

    def _on_clear(self, e):
        history_manager.clear_history()
        self.refresh()

    def _on_remove(self, index):
        history_manager.remove_entry(index)
        self.refresh()

    def _copy_url(self, url):
        try:
            if hasattr(self.page, "clipboard"):
                self.page.clipboard.set(url)
                self._show_snack(f"Copied: {url[:60]}")
            else:
                self._show_snack(url[:80])
        except Exception:
            self._show_snack(url[:80])

    def _show_snack(self, msg):
        snack(self.page, msg)
