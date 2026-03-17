"""Transparent fullscreen overlay used for drawing result highlights."""

import tkinter as tk

import win32con
import win32gui

KEY_COLOR = "#010101"
HIGHLIGHT_COLOR = "#FFD700"


class OverlayWindow:
    """Manage a click-through fullscreen overlay for highlight rectangles."""

    def __init__(self, master):
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=KEY_COLOR)

        width = self.window.winfo_screenwidth()
        height = self.window.winfo_screenheight()
        self.window.geometry(f"{width}x{height}+0+0")
        self.window.wm_attributes("-transparentcolor", KEY_COLOR)

        self.canvas = tk.Canvas(
            self.window,
            bg=KEY_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.window.update_idletasks()
        self._apply_click_through()

    def _apply_click_through(self):
        """Apply Windows extended styles so clicks pass through the overlay."""
        hwnd = self.window.winfo_id()
        styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        styles |= (
            win32con.WS_EX_LAYERED
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_TOOLWINDOW
        )
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, styles)

    def exists(self):
        """Return True while the overlay window and canvas still exist."""
        return bool(self.window.winfo_exists() and self.canvas.winfo_exists())

    def show(self):
        """Show the overlay above all windows."""
        if not self.exists():
            return
        self.window.attributes("-topmost", True)
        self.window.deiconify()
        self.window.lift()
        self.window.update_idletasks()

    def hide(self):
        """Hide the overlay window."""
        if not self.exists():
            return
        self.window.withdraw()

    def clear(self):
        """Remove all drawn highlight rectangles."""
        if not self.exists():
            return
        self.canvas.delete("highlight")

    def draw_matches(self, matches):
        """Draw gold rectangles at absolute screen coordinates."""
        if not self.exists():
            return
        self.clear()
        for item in matches:
            x1 = int(item["x"])
            y1 = int(item["y"])
            x2 = x1 + int(item["w"])
            y2 = y1 + int(item["h"])
            self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline=HIGHLIGHT_COLOR,
                width=4,
                tags="highlight",
            )
        sample = matches[0] if matches else None
        print(f"[overlay] drawing rectangles={len(matches)} sample={sample}")
        self.canvas.lift("highlight")
        self.canvas.update_idletasks()
