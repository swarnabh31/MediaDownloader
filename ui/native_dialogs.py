import subprocess
import os
import sys
import tempfile


def pick_folder(title="Choose folder"):
    """Open a native Windows folder picker. Returns the selected path or None."""
    if sys.platform != "win32":
        return _generic_askdirectory(title)
    script = (
        "Add-Type -AssemblyName System.Windows.Forms | Out-Null; "
        "$dlg = New-Object System.Windows.Forms.FolderBrowserDialog; "
        f"$dlg.Description = '{title.replace(chr(39), chr(39)*2)}'; "
        "$dlg.ShowNewFolderButton = $true; "
        "if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) "
        "{ Write-Output $dlg.SelectedPath }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=300,
    )
    path = (result.stdout or "").strip()
    return path if path and os.path.isdir(path) else None


def pick_file(title="Choose file", filetypes=None):
    """Open a native Windows file picker. Returns the selected path or None.

    `filetypes` is a list of (description, pattern) tuples, e.g.
    [("Text files", "*.txt"), ("All files", "*.*")].
    """
    if sys.platform != "win32":
        return _generic_askopenfilename(title, filetypes)
    if not filetypes:
        filetypes = [("All files", "*.*")]
    filter_parts = [f"{desc}|{pat}" for desc, pat in filetypes]
    filter_str = "|".join(filter_parts).replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms | Out-Null; "
        "$dlg = New-Object System.Windows.Forms.OpenFileDialog; "
        f"$dlg.Title = '{title.replace(chr(39), chr(39)*2)}'; "
        f"$dlg.Filter = '{filter_str}'; "
        "if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) "
        "{ Write-Output $dlg.FileName }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, timeout=300,
    )
    path = (result.stdout or "").strip()
    return path if path and os.path.isfile(path) else None


def _generic_askdirectory(title):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title=title)
        root.destroy()
        return path or None
    except Exception:
        return None


def _generic_askopenfilename(title, filetypes):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        types = [(desc, pat) for desc, pat in (filetypes or [("All files", "*.*")])]
        path = filedialog.askopenfilename(title=title, filetypes=types)
        root.destroy()
        return path or None
    except Exception:
        return None
