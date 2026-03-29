"""Transparent fullscreen overlay used for drawing result highlights."""

import logging
import tkinter as tk

import win32con
import win32clipboard
import win32gui

KEY_COLOR = "#010101"
HIGHLIGHT_COLOR = "#FFD700"
FLASH_COLOR = "#FFFFFF"

logger = logging.getLogger("uniseba.ui.overlay")


class OverlayWindow:
    """Manage a click-through fullscreen overlay for highlight rectangles."""

    def __init__(self, master):
        self.match_regions = []
        self.flash_generation = 0
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
        self.canvas.bind("<Button-1>", self._handle_click)
        self.window.update_idletasks()

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
        self.match_regions = []
        self.flash_generation += 1
        self.canvas.delete("highlight")

    def _copy_text_to_clipboard(self, text):
        """Copy matched text into the Windows clipboard."""
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

    def _find_clicked_region(self, x, y):
        """Return the match region that contains the clicked canvas point."""
        for region in self.match_regions:
            if region["x1"] <= x <= region["x2"] and region["y1"] <= y <= region["y2"]:
                return region
        return None

    def _flash_region(self, region):
        """Flash a clicked region briefly so copy feedback is visible."""
        item_id = region["canvas_id"]
        generation = self.flash_generation
        self.canvas.itemconfig(item_id, outline=FLASH_COLOR)

        def _restore():
            if not self.exists() or generation != self.flash_generation:
                return
            self.canvas.itemconfig(item_id, outline=HIGHLIGHT_COLOR)

        self.window.after(200, _restore)

    def _handle_click(self, event):
        """Copy the clicked word and flash its rectangle without activating the overlay."""
        if not self.exists():
            return
        region = self._find_clicked_region(event.x, event.y)
        if region is None:
            return
        text = region.get("text", "")
        if not text:
            return
        logger.debug("Copied overlay match text=%r", text)
        self._copy_text_to_clipboard(text)
        self._flash_region(region)

    def draw_matches(self, matches):
        """Draw gold rectangles at absolute screen coordinates."""
        if not self.exists():
            return
        self.clear()
        if not matches:
            return
        self.flash_generation += 1
        # Logging every rectangle is extremely noisy and can impact perceived latency.
        logger.debug("Drawing %s highlight rectangles", len(matches))
        for item in matches:
            x1 = int(item["x"])
            y1 = int(item["y"])
            x2 = x1 + int(item["w"])
            y2 = y1 + int(item["h"])
            canvas_id = self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                outline=HIGHLIGHT_COLOR,
                width=4,
                tags="highlight",
            )
            self.match_regions.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "text": item.get("original", ""),
                    "canvas_id": canvas_id,
                }
            )
        self.canvas.tag_raise("highlight")
        self.window.lift()
        self.canvas.update_idletasks()
