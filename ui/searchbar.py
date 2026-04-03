"""Floating search bar UI base for the integrated overlay application."""

import logging
import customtkinter as ctk

from config import DEBOUNCE_MS
from ui.overlay import OverlayWindow

logger = logging.getLogger("uniseba.ui.searchbar")


class SearchbarApp(ctk.CTk):
    """Own the search window and overlay, but not OCR/search orchestration."""

    def __init__(self):
        super().__init__()
        self.title("Uniseba Search")
        self.geometry("620x140+80+80")
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
        """Create the redesigned dark UI with sharp, high-contrast controls."""
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#0d1117")
        self.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text="Search visible text...",
            fg_color="#161b22",
            border_color="#30363d",
            text_color="#e6edf3",
            placeholder_text_color="#484f58",
            font=("Courier New", 13),
            height=42,
            corner_radius=8,
            border_width=1,
        )
        self.entry.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")
        self.entry.bind("<KeyRelease>", self._on_query_changed)

        self.result_label = ctk.CTkLabel(
            self,
            text="0 matches",
            text_color="#8b949e",
            font=("Segoe UI", 10),
            fg_color="transparent",
        )
        self.result_label.grid(row=1, column=0, padx=12, sticky="w")

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="e")

        self.ai_var = ctk.BooleanVar(value=True)
        self.ai_toggle = ctk.CTkSwitch(
            button_frame,
            text="AI",
            variable=self.ai_var,
            text_color="#8b949e",
            button_color="#00d4ff",
            button_hover_color="#00b8d9",
            progress_color="#00d4ff",
        )
        self.ai_toggle.pack(side="left")

        self.record_btn = ctk.CTkButton(
            button_frame,
            text="⏺ Record",
            fg_color="#1a1f29",
            hover_color="#2d1f1f",
            text_color="#f59e0b",
            border_color="#f59e0b",
            border_width=1,
            corner_radius=6,
            font=("Segoe UI", 9, "bold"),
            width=80,
            height=28,
            command=self._on_record_clicked,
        )
        self.record_btn.pack(side="left", padx=(4, 0))

        self.summarize_btn = ctk.CTkButton(
            button_frame,
            text="Summarize",
            fg_color="#1a1f29",
            hover_color="#1a2632",
            text_color="#8b949e",
            border_color="#30363d",
            border_width=1,
            corner_radius=6,
            font=("Segoe UI", 9),
            width=80,
            height=28,
            command=self._on_summarize_clicked,
        )
        self.summarize_btn.pack(side="left", padx=(4, 0))

        self.graph_btn = ctk.CTkButton(
            button_frame,
            text="⬡ Graph",
            fg_color="#1a1f29",
            hover_color="#1a2632",
            text_color="#00d4ff",
            border_color="#00d4ff",
            border_width=1,
            corner_radius=6,
            font=("Segoe UI", 9, "bold"),
            width=70,
            height=28,
            command=self._on_graph_clicked,
        )
        self.graph_btn.pack(side="left", padx=(4, 0))

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
        logger.debug("query_typed=%r", query)
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
