"""Floating search bar UI for testing overlay highlights."""

import asyncio
import queue
import threading

import customtkinter as ctk
import keyboard
from mss import mss
from PIL import Image
import win32gui

from capture.change import has_significant_change
from ocr.engine import recognize_image
from ocr.index import build_ocr_index
from search.fuzzy import fuzzy_search
from search.hybrid import hybrid_search
from ui.overlay import OverlayWindow

REFRESH_MS = 200
DEBOUNCE_MS = 250
SAMPLE_INDEX = [
    {"word": "soheb", "original": "SOHEB", "x": 120, "y": 120, "w": 84, "h": 26},
    {"word": "success", "original": "SUCCESS", "x": 120, "y": 170, "w": 118, "h": 26},
    {"word": "phase", "original": "Phase", "x": 120, "y": 220, "w": 78, "h": 26},
    {"word": "hello", "original": "Hello", "x": 120, "y": 270, "w": 66, "h": 26},
    {"word": "world", "original": "world", "x": 205, "y": 270, "w": 70, "h": 26},
    {"word": "test", "original": "TEST", "x": 120, "y": 320, "w": 58, "h": 26},
]


class SearchbarApp(ctk.CTk):
    """Floating search bar paired with a transparent fullscreen overlay."""

    def __init__(self):
        super().__init__()
        self.title("Uniseba Search")
        self.geometry("420x110+80+80")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self.overlay = OverlayWindow(self)
        self.visible = False
        self.current_image = None
        self.current_rect = None
        self.current_index = list(SAMPLE_INDEX)
        self.index_queue = queue.Queue()
        self.debounce_job = None
        self.refresh_job = None
        self.running = True
        self.hotkey_handle = None
        self.ocr_busy = False
        self.target_hwnd = None

        self._build_ui()
        self._register_hotkey()
        self.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.withdraw()
        self.refresh_job = self.after(REFRESH_MS, self._refresh_loop)

    def _build_ui(self):
        """Create the entry, result counter, and AI toggle."""
        ctk.set_appearance_mode("dark")
        self.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(self, placeholder_text="Search visible text...")
        self.entry.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")
        self.entry.bind("<KeyRelease>", self._on_query_changed)

        self.result_label = ctk.CTkLabel(self, text="0 matches")
        self.result_label.grid(row=1, column=0, padx=12, sticky="w")

        self.ai_var = ctk.BooleanVar(value=True)
        self.ai_toggle = ctk.CTkSwitch(self, text="AI", variable=self.ai_var)
        self.ai_toggle.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="e")

    def _register_hotkey(self):
        """Expose a global shortcut for showing and hiding the overlay UI."""
        self.hotkey_handle = keyboard.add_hotkey(
            "ctrl+shift+u",
            lambda: self.after(0, self.toggle_visibility),
        )

    def toggle_visibility(self):
        """Show or hide the search bar and fullscreen overlay together."""
        if not self.running or not self.winfo_exists():
            return
        if self.visible:
            self.visible = False
            self.overlay.clear()
            self.overlay.hide()
            self.withdraw()
            return

        self._remember_target_window()
        self.visible = True
        self.deiconify()
        self.lift()
        self.update_idletasks()
        self.overlay.show()
        self.after(100, lambda: (self.focus_force(), self.entry.focus_set()))
        print("[searchbar] overlay shown")
        self._apply_search()

    def _on_query_changed(self, _event=None):
        """Debounce keystrokes so search is not run on every key press."""
        if not self.running:
            return
        query = self.entry.get().strip()
        print(f"[UI] query typed: {query}")
        print(f"[searchbar] key query={self.entry.get().strip()!r}")
        if self.debounce_job is not None:
            self.after_cancel(self.debounce_job)
        self.debounce_job = self.after(DEBOUNCE_MS, self._apply_search)

    def _apply_search(self):
        """Run fuzzy or hybrid search and redraw highlight rectangles."""
        self.debounce_job = None
        if not self.running or not self.winfo_exists():
            return
        query = self.entry.get().strip()
        if len(query) < 2:
            self.result_label.configure(text="0 matches")
            self.overlay.clear()
            return

        index = self._drain_latest_index() or self.current_index
        if self.ai_var.get():
            matches = hybrid_search(query, index, limit=50)
        else:
            matches = fuzzy_search(query, index, limit=50)

        self.result_label.configure(text=f"{len(matches)} matches")
        self.overlay.draw_matches(matches)

    def _drain_latest_index(self):
        """Pick the most recent OCR index update from the queue."""
        latest = None
        while not self.index_queue.empty():
            latest = self.index_queue.get_nowait()
        if latest is not None:
            self.current_index = latest
        return latest

    def _refresh_loop(self):
        """Refresh the OCR index when the active window content changes."""
        if not self.running or not self.winfo_exists():
            return

        self._drain_latest_index()
        if self.visible and not self.ocr_busy:
            self.ocr_busy = True
            threading.Thread(target=self._refresh_worker, daemon=True).start()
        if self.visible:
            self._apply_search()
        if self.running and self.winfo_exists():
            self.refresh_job = self.after(REFRESH_MS, self._refresh_loop)

    def _refresh_worker(self):
        """Capture and OCR in a worker thread so the UI stays responsive."""
        try:
            image, rect = self._capture_target_window()
            if image is None:
                return
            if not has_significant_change(self.current_image, image):
                return

            self.current_image = image
            self.current_rect = rect
            words = asyncio.run(recognize_image(image, rect))
            index = build_ocr_index(words)
            if index:
                self.index_queue.put(index)
        except Exception:
            # Keep the hardcoded sample index available for UI testing.
            pass
        finally:
            self.ocr_busy = False

    def _remember_target_window(self):
        """Remember the app window that was active before the search UI opened."""
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and hwnd not in self._own_window_handles():
            self.target_hwnd = hwnd

    def _own_window_handles(self):
        """Return the top-level windows owned by the search UI."""
        handles = {self.winfo_id()}
        if self.overlay.exists():
            handles.add(self.overlay.window.winfo_id())
        return handles

    def _capture_target_window(self):
        """Capture the window that was active before the search UI took focus."""
        hwnd = self.target_hwnd
        if not hwnd or not win32gui.IsWindow(hwnd):
            return None, None

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return None, None

        rect = {"left": left, "top": top, "width": width, "height": height}
        with mss() as sct:
            shot = sct.grab(rect)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
        return image, rect

    def shutdown(self):
        """Cleanly remove the hotkey registration and close the UI."""
        if not self.running:
            return
        self.running = False
        self.visible = False
        if self.debounce_job is not None:
            self.after_cancel(self.debounce_job)
            self.debounce_job = None
        if self.refresh_job is not None:
            self.after_cancel(self.refresh_job)
            self.refresh_job = None
        if self.hotkey_handle is not None:
            keyboard.remove_hotkey(self.hotkey_handle)
            self.hotkey_handle = None
        self.overlay.clear()
        self.overlay.hide()
        if self.overlay.window.winfo_exists():
            self.overlay.window.destroy()
        self.destroy()


if __name__ == "__main__":
    app = SearchbarApp()
    app.mainloop()
