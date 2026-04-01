"""Floating search bar UI base for the integrated overlay application."""

import customtkinter as ctk
import tkinter as tk

from config import DEBOUNCE_MS
from ui.overlay import OverlayWindow


class SearchbarApp(ctk.CTk):
    """Own the search window and overlay, but not OCR/search orchestration."""

    def __init__(self):
        super().__init__()
        self.title("Uniseba Search")
        self.geometry("420x110+80+80")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self.overlay = OverlayWindow(self)
        self.visible = False
        self.running = True
        self.debounce_job = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.withdraw()

    def _build_ui(self):
        """Create the entry, result counter, and AI toggle."""
        ctk.set_appearance_mode("dark")
        self.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(self, placeholder_text="Search visible text...")
        self.entry.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")
        self.entry.bind("<KeyRelease>", self._on_query_changed)

        self.result_label = ctk.CTkLabel(self, text="0 matches")
        self.result_label.grid(row=1, column=0, padx=12, sticky="w")

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="e")

        self.ai_var = ctk.BooleanVar(value=True)
        self.ai_toggle = ctk.CTkSwitch(button_frame, text="AI", variable=self.ai_var)
        self.ai_toggle.pack(side="left")

        self.record_btn = tk.Button(
            button_frame,
            text="⏺ Record",
            bg="#c0392b",
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            command=self._on_record_clicked,
        )
        self.record_btn.pack(side=tk.LEFT, padx=(4, 0))

        self.summarize_btn = tk.Button(
            button_frame,
            text="Summarize",
            bg="#3a3a3a",
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            command=self._on_summarize_clicked,
        )
        self.summarize_btn.pack(side=tk.LEFT, padx=(4, 0))

        self.graph_btn = tk.Button(
            button_frame,
            text="🔗 Graph",
            bg="#1a6b8a",
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            command=self._on_graph_clicked,
        )
        self.graph_btn.pack(side=tk.LEFT, padx=(4, 0))

    def _on_record_clicked(self):
        pass

    def _on_summarize_clicked(self):
        pass

    def _on_graph_clicked(self):
        pass

    def toggle_visibility(self):
        """Show or hide the search bar and fullscreen overlay together."""
        if not self.running or not self.winfo_exists():
            return
        if self.visible:
            self.visible = False
            self.overlay.clear()
            self.overlay.hide()
            self.withdraw()
            self.on_hidden()
            return

        self.visible = True
        self.deiconify()
        self.lift()
        self.update_idletasks()
        self.overlay.show()
        self.after(100, lambda: (self.focus_force(), self.entry.focus_set()))
        self.on_shown()

    def _on_query_changed(self, _event=None):
        """Debounce keystrokes so subclasses can search without per-key churn."""
        if not self.running:
            return
        query = self.entry.get().strip()
        print(f"[UI] query typed: {query}")
        print(f"[searchbar] key query={query!r}")
        if self.debounce_job is not None:
            self.after_cancel(self.debounce_job)
        self.debounce_job = self.after(DEBOUNCE_MS, self._apply_search)

    def _apply_search(self):
        """Run the active search strategy for the current query."""
        raise NotImplementedError("SearchbarApp subclasses must implement _apply_search().")

    def on_shown(self):
        """Hook for subclasses that need to react after the UI becomes visible."""

    def on_hidden(self):
        """Hook for subclasses that need to react after the UI hides."""

    def own_window_handles(self):
        """Return the top-level windows owned by the search UI."""
        handles = set()
        if self.winfo_exists():
            handles.add(self.winfo_id())
        if self.overlay.exists():
            handles.add(self.overlay.window.winfo_id())
        return handles

    def shutdown(self):
        """Close the UI and overlay cleanly."""
        if not self.running:
            return
        self.running = False
        self.visible = False
        if self.debounce_job is not None:
            self.after_cancel(self.debounce_job)
            self.debounce_job = None
        self.overlay.clear()
        self.overlay.hide()
        if self.overlay.window.winfo_exists():
            self.overlay.window.destroy()
        self.destroy()
