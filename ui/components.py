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


STATUS_ICONS = {
    "queued": ft.Icons.SCHEDULE,
    "downloading": ft.Icons.DOWNLOADING,
    "processing": ft.Icons.AUTORENEW,
    "done": ft.Icons.CHECK_CIRCLE,
    "cancelled": ft.Icons.CANCEL,
    "error": ft.Icons.ERROR,
}

# Per-theme chip backgrounds and foreground colors, picked so each status has
# clearly readable contrast in both modes (dark theme uses mid-tone tints).
_LIGHT = {
    "queued":    ("grey200",    "grey700"),
    "downloading": ("blue100",   "blue700"),
    "processing": ("amber100",   "amber700"),
    "done":      ("green100",   "green700"),
    "cancelled": ("orange100",  "orange700"),
    "error":     ("red100",     "red700"),
}
_DARK = {
    "queued":    ("grey600",    "grey50"),
    "downloading": ("bluegrey900", "blue200"),
    "processing": ("amber900",   "amber100"),
    "done":      ("green900",   "green100"),
    "cancelled": ("orange900",  "orange100"),
    "error":     ("red900",     "red100"),
}


def _is_dark(page):
    try:
        return bool(page) and (page.theme_mode == ft.ThemeMode.DARK)
    except Exception:
        return False


def status_chip(status: str, page=None):
    """Material 3 status chip: icon + label (status is never conveyed by color alone)."""
    icon = STATUS_ICONS.get(status, ft.Icons.HELP)
    label = status.capitalize() if status != "processing" else "Processing"
    if _is_dark(page):
        bg, fg = _DARK.get(status, ("grey600", "grey50"))
    else:
        bg, fg = _LIGHT.get(status, ("grey200", "grey700"))
    return ft.Container(
        content=ft.Row(
            [ft.Icon(icon, color=fg, size=14),
             ft.Text(label, color=fg, size=12, weight=ft.FontWeight.BOLD)],
            spacing=4,
            tight=True,
        ),
        bgcolor=bg,
        border_radius=10,
        padding=ft.Padding(left=8, top=3, right=8, bottom=3),
    )


def card(kwargs=None):
    """Neutral card surface: 16px radius, theme surface tone, 1px outline, no shadow.

    The caller can merge in additional kwargs (e.g. border_radius, bg) if needed.
    """
    d = dict(
        bgcolor="surfaceContainerLow",
        border=ft.BorderSide(1, "outlineVariant"),
        border_radius=16,
    )
    if kwargs:
        d.update(kwargs)
    return d


def build_app_bar(page, title, current_route, on_navigate, toggle_theme_fn=None, extra_actions=None, on_back=None):
    actions = list(extra_actions or [])
    actions.append(
        ft.IconButton(
            ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE,
            tooltip="Toggle theme",
            on_click=lambda _: (toggle_theme_fn() if toggle_theme_fn else None),
            size_constraints=ft.BoxConstraints(min_width=40, min_height=40),
        ),
    )
    if on_back:
        title_widget = ft.Row(
            [
                ft.IconButton(
                    ft.Icons.ARROW_BACK,
                    tooltip="Back",
                    on_click=lambda _: on_back(),
                    size_constraints=ft.BoxConstraints(min_width=40, min_height=40),
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
    return ft.Row(
        [
            ft.TextButton("History", icon=ft.Icons.HISTORY, on_click=lambda _: on_history()),
            ft.TextButton("Settings", icon=ft.Icons.SETTINGS, on_click=lambda _: on_settings()),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
    )
