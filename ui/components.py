import logging

import flet as ft


log = logging.getLogger("downloader")


def snack(page, message, bgcolor=None, duration=None):
    """Show a SnackBar across Flet versions.

    Flet 0.85.x removed page.show_snack_bar/open_snack_bar; SnackBars are
    dialogs there and must go through page.show_dialog.
    """
    if page is None:
        return
    bar = ft.SnackBar(content=ft.Text(message))
    if bgcolor is not None:
        bar.bgcolor = bgcolor
    if duration is not None:
        bar.duration = duration
    for method in ("open_snack_bar", "show_snack_bar"):
        fn = getattr(page, method, None)
        if callable(fn):
            try:
                fn(bar)
                return
            except Exception as ex:
                log.warning("%s failed: %s", method, ex)
    try:
        page.show_dialog(bar)
    except Exception as ex:
        log.warning("show_dialog snackbar failed: %s", ex)
        log.info("snackbar message: %s", message)


STATUS_COLORS = {
    "queued": "grey400",
    "downloading": "blue",
    "processing": "amber",
    "done": "green",
    "cancelled": "orange",
    "error": "red",
}

STATUS_ICONS = {
    "queued": ft.Icons.SCHEDULE,
    "downloading": ft.Icons.DOWNLOADING,
    "processing": ft.Icons.AUTORENEW,
    "done": ft.Icons.CHECK_CIRCLE,
    "cancelled": ft.Icons.CANCEL,
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


def build_app_bar(page: ft.Page, title: str, current_route: str, on_navigate, toggle_theme_fn=None, extra_actions=None, on_back=None):
    actions = list(extra_actions or [])
    actions.append(
        ft.IconButton(
            ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE,
            tooltip="Toggle theme",
            on_click=lambda _: (toggle_theme_fn() if toggle_theme_fn else None),
        ),
    )
    if on_back:
        title_widget = ft.Row(
            [
                ft.IconButton(
                    ft.Icons.ARROW_BACK,
                    tooltip="Back",
                    on_click=lambda _: on_back(),
                ),
                ft.Text(title),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    else:
        title_widget = ft.Text(title)
    return ft.AppBar(
        title=title_widget,
        center_title=False,
        bgcolor="surfaceContainerHigh",
        actions=actions,
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
