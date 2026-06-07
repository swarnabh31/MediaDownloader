import flet as ft
import logging

from ui.components import build_app_bar


log = logging.getLogger("downloader")


class SettingsView(ft.View):
    def __init__(self, page: ft.Page, app_state):
        super().__init__(
            route="/settings",
            padding=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
        )
        self._page = page
        self.app_state = app_state
        self.settings = app_state.settings.copy()

        self.output_dir_text = ft.Text(
            self.settings.get("output_dir", "downloads"),
            size=13,
            selectable=True,
        )

        self.cookies_picker = None

        self.default_quality_dd = ft.Dropdown(
            label="Default Quality",
            width=240,
            options=[
                ft.dropdown.Option("2160p"),
                ft.dropdown.Option("1440p"),
                ft.dropdown.Option("1080p"),
                ft.dropdown.Option("720p"),
                ft.dropdown.Option("Audio"),
            ],
            value=self.settings.get("default_quality", "720p"),
        )

        self.theme_dd = ft.Dropdown(
            label="Theme",
            width=240,
            options=[
                ft.dropdown.Option("light"),
                ft.dropdown.Option("dark"),
            ],
            value=self.settings.get("theme", "light"),
        )

        self.proxy_input = ft.TextField(
            label="Proxy URL (optional)",
            width=420,
            hint_text="http://user:pass@host:port  or  socks5://host:port",
            value=self.settings.get("proxy", ""),
        )

        self.cookies_path_text = ft.Text(
            self.settings.get("cookiefile", "") or "None",
            size=12,
            selectable=True,
        )

        self.concurrency_dd = ft.Dropdown(
            label="Concurrent downloads",
            width=240,
            options=[ft.dropdown.Option(str(i)) for i in range(1, 5)],
            value=str(self.settings.get("max_concurrent", 1)),
        )

        self.update_status = ft.Text("", size=12, italic=True)

        # Build the settings content separately so we can reference it from _build without needing page context
        self._settings_content = self._create_settings_content()
        self._build()

    def _create_settings_content(self):
        """Create the full settings UI as a column (doesn't need page)."""
        return ft.Container(
            content=ft.Column(
                [
                    self._section("Downloads Folder", [
                        ft.Row(
                            [
                                self.output_dir_text,
                                ft.Button(
                                    "Choose Folder",
                                    icon=ft.Icons.FOLDER_OPEN,
                                    on_click=self._on_folder_picked,
                                ),
                            ],
                            spacing=12,
                        ),
                    ]),
                    self._section("Defaults", [
                        ft.Row([self.default_quality_dd, self.theme_dd, self.concurrency_dd], spacing=12, wrap=True),
                    ]),
                    self._section("Network", [
                        self.proxy_input,
                    ]),
                    self._section("Cookies (for age-restricted / login content)", [
                        ft.Row(
                            [
                                self.cookies_path_text,
                                ft.OutlinedButton(
                                    "Load cookies.txt",
                                    icon=ft.Icons.UPLOAD_FILE,
                                    on_click=self._on_cookies_picked,
                                ),
                                ft.TextButton(
                                    "Clear",
                                    icon=ft.Icons.CLOSE,
                                    on_click=self._on_clear_cookies,
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.Text(
                            "Export cookies from your browser using the 'Get cookies.txt LOCALLY' extension.",
                            size=11,
                            italic=True,
                        ),
                    ]),
                    self._section("Maintenance", [
                        ft.Row(
                            [
                                ft.Button(
                                    "Update yt-dlp",
                                    icon=ft.Icons.SYSTEM_UPDATE_ALT,
                                    on_click=self._on_update_ytdlp,
                                ),
                                self.update_status,
                            ],
                            spacing=12,
                        ),
                    ]),
                    ft.Row(
                        [
                            ft.Button(
                                "Save Settings",
                                icon=ft.Icons.SAVE,
                                on_click=self._on_save,
                                style=ft.ButtonStyle(
                                    color="white",
                                    bgcolor="primary",
                                ),
                            ),
                            ft.OutlinedButton(
                                "Discard Changes",
                                icon=ft.Icons.RESTORE,
                                on_click=self._on_discard,
                            ),
                        ],
                        spacing=12,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=14,
            ),
            width=760,
        )

    def _build(self):
        self.appbar = build_app_bar(
            self._page, "Settings", self._page.route, self.app_state.navigate
        )
        self.controls = [
            ft.Container(
                content=ft.Column([self._settings_content], scroll=ft.ScrollMode.AUTO),
                width=760,
            )
        ]

    def _section(self, title, controls):
        return ft.Container(
            content=ft.Column(
                [ft.Text(title, size=15, weight=ft.FontWeight.BOLD)] + list(controls),
                spacing=8,
            ),
            border_radius=8,
            padding=14,
            width=720,
        )

    def _on_folder_picked(self, e):
        from ui.native_dialogs import pick_folder
        path = pick_folder("Choose download folder")
        if path:
            self.settings["output_dir"] = path
            self.output_dir_text.value = path
            self.page.update()

    def _on_cookies_picked(self, e):
        from ui.native_dialogs import pick_file
        path = pick_file("Select cookies.txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self.settings["cookiefile"] = path
            self.cookies_path_text.value = path
            self.page.update()

    def _on_clear_cookies(self, e):
        self.settings["cookiefile"] = ""
        self.cookies_path_text.value = "None"
        self.page.update()

    def _on_update_ytdlp(self, e):
        import subprocess, sys
        self.update_status.value = "Updating yt-dlp..."
        self.page.update()

        import threading
        def run():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                    capture_output=True, text=True, timeout=180,
                )
                if result.returncode == 0:
                    self.update_status.value = "yt-dlp updated successfully."
                else:
                    err = (result.stderr or result.stdout or "").strip()[:200]
                    self.update_status.value = f"Update failed: {err}"
                log.info("yt-dlp update: %s", self.update_status.value)
            except Exception as ex:
                log.exception("yt-dlp update failed")
                self.update_status.value = f"Error: {ex}"
            self.page.update()

        threading.Thread(target=run, daemon=True).start()

    def _on_save(self, e):
        from core import settings_manager
        self.settings["default_quality"] = self.default_quality_dd.value or "720p"
        self.settings["theme"] = self.theme_dd.value or "light"
        self.settings["proxy"] = self.proxy_input.value or ""
        self.settings["max_concurrent"] = int(self.concurrency_dd.value or 1)
        self.settings["concurrent_downloads"] = self.settings["max_concurrent"]
        settings_manager.save(self.settings)
        self.app_state.apply_settings(self.settings)
        if hasattr(self.page, "show_snack_bar"):
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("Settings saved.")))
        else:
            log.info("settings saved")

    def _on_discard(self, e):
        self.settings = self.app_state.settings.copy()
        self.output_dir_text.value = self.settings.get("output_dir", "downloads")
        self.default_quality_dd.value = self.settings.get("default_quality", "720p")
        self.theme_dd.value = self.settings.get("theme", "light")
        self.proxy_input.value = self.settings.get("proxy", "")
        self.cookies_path_text.value = self.settings.get("cookiefile", "") or "None"
        self.concurrency_dd.value = str(self.settings.get("max_concurrent", 1))
        if hasattr(self.page, "show_snack_bar"):
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("Reverted to saved settings.")))
