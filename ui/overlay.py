"""Transparent fullscreen overlay used for drawing result highlights."""

import ctypes
import tkinter as tk

import win32con
import win32gui

KEY_COLOR = "#010101"
HIGHLIGHT_COLOR = "#FFD700"
user32 = ctypes.windll.user32


class OverlayWindow:
    """Manage a click-through fullscreen overlay for highlight rectangles."""

    def __init__(self, master):
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.9)
        self.window.configure(bg="#010101")

        width = self.window.winfo_screenwidth()
        height = self.window.winfo_screenheight()
        self.window.geometry(f"{width}x{height}+0+0")
        self.window.attributes("-transparentcolor", "#010101")

        self.canvas = tk.Canvas(
            self.window,
            bg="#010101",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.window.update_idletasks()
        # self._apply_click_through()
        self.window.after(1000, self.test_static_rectangle)

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

    def test_static_rectangle(self):
        print("[TEST] drawing static rectangle")
        self.canvas.create_rectangle(
            300, 300, 600, 400,
            fill="#FFD700",
            outline="#FFD700",
            width=3
        )
        self.window.lift()
        self.canvas.update()

    def draw_matches(self, matches):
        """Draw gold rectangles at absolute screen coordinates."""
        if not self.exists():
            return
        try:
            self.clear()
            print(f"[SCREEN] {user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}")
            print(f"[OVERLAY] drawing {len(matches)} rectangles")
            print(f"[overlay] drawing {len(matches)} rectangles")
            print(matches[:3])
            self.canvas.create_rectangle(100, 100, 400, 200, fill="blue", outline="blue", width=5)
            for item in matches:
                x1 = int(item["x"])
                y1 = int(item["y"])
                x2 = x1 + int(item["w"])
                y2 = y1 + int(item["h"])
                print(f"[RECT] x={x1}, y={y1}, w={x2-x1}, h={y2-y1}")
                self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill="red",
                    outline="red",
                    width=4,
                    tags="highlight",
                )
            self.canvas.tag_raise("highlight")
            self.window.lift()
            self.canvas.update()
            self.canvas.update_idletasks()
            print("[OVERLAY] draw_matches completed")
        except Exception as exc:
            print(f"[OVERLAY] draw_matches failed: {exc}")
