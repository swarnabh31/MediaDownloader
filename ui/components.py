import flet as ft


STATUS_COLORS = {
    "queued": "grey400",
    "downloading": "blue",
    "processing": "amber",
    "done": "green",
    "error": "red",
}

STATUS_ICONS = {
    "queued": ft.Icons.SCHEDULE,
    "downloading": ft.Icons.DOWNLOADING,
    "processing": ft.Icons.AUTORENEW,
    "done": ft.Icons.CHECK_CIRCLE,
    "error": ft.Icons.ERROR,
}


def status_chip(status: str):
    color = STATUS_COLORS.get(status, "grey")
    icon = STATUS_ICONS.get(status, ft.Icons.HELP)
    label = status.capitalize() if status != "processing" else "Processing"
    return ft.Row(
        [
            ft.Icon(icon, color=color, size=16),
            ft.Text(label, color=color, size=12, weight=ft.FontWeight.BOLD),
        ],
        spacing=4,
        tight=True,
    )


def build_app_bar(page: ft.Page, title: str, current_route: str, on_navigate, toggle_theme_fn=None):
    return ft.AppBar(
        title=ft.Text(title),
        center_title=False,
        bgcolor="surfaceContainerHigh",
        actions=[
            ft.IconButton(
                ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE,
                tooltip="Toggle theme",
                on_click=lambda _: (toggle_theme_fn() if toggle_theme_fn else None),
            ),
        ],
    )


def build_footer_links(on_history, on_settings):
    """Spotify-style footer with History and Settings links."""
    return ft.Row(
        [
            ft.TextButton("History", icon=ft.Icons.HISTORY, on_click=lambda _: on_history()),
            ft.TextButton("Settings", icon=ft.Icons.SETTINGS, on_click=lambda _: on_settings()),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
    )
