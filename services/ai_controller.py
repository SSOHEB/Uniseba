"""AI feature controller for recording, summarization, and graph generation."""

import threading

from ai.gemini import build_knowledge_graph, summarize_screen_text
from services.corpus_recorder import CorpusRecorder
from ui.graph_panel import open_graph
from ui.summary_panel import SummaryPanel


class AIController:
    """Own recording state and AI feature actions for the integrated app."""

    def __init__(self, app, logger):
        self.app = app
        self.logger = logger
        self.summary_panel = SummaryPanel(app)
        self._is_recording = False
        self._corpus_state = CorpusRecorder()

    @property
    def is_recording(self):
        return self._is_recording

    def on_record_clicked(self):
        if not self._is_recording:
            self._is_recording = True
            self._corpus_state.reset()
            self.app.record_btn.configure(
                text="\u23f9 Stop",
                fg_color="#2d1f1f",
                text_color="#ef4444",
                border_color="#ef4444",
            )
            self.logger.info("Corpus recording started")
            return

        self._is_recording = False
        self.app.record_btn.configure(
            text="\u23fa Record",
            fg_color="#1a1f29",
            text_color="#f59e0b",
            border_color="#f59e0b",
        )
        self.logger.info(
            "Corpus recording stopped corpus_size=%s",
            len(self._corpus_state),
        )

    def on_summarize_clicked(self):
        if self._is_recording:
            self.summary_panel.show_summary("Please click Stop before summarizing.")
            return
        if not self._corpus_state.has_items():
            self.summary_panel.show_summary(
                "Nothing recorded yet. Click Record, scroll through content, then click Stop."
            )
            return
        text = self._corpus_state.joined_text()
        self.summary_panel.show_loading()
        threading.Thread(
            target=self._run_summarize,
            args=(text,),
            daemon=True,
        ).start()

    def _run_summarize(self, text):
        summary = summarize_screen_text(text)
        self.app.after(0, lambda: self.summary_panel.show_summary(summary))

    def on_graph_clicked(self):
        if self._is_recording:
            self.summary_panel.show_summary("Please click Stop before generating graph.")
            return
        if not self._corpus_state.has_items():
            self.summary_panel.show_summary(
                "Nothing recorded yet. Click Record, scroll through content, then click Stop."
            )
            return
        focus = self._corpus_state.infer_focus()
        text = self._corpus_state.joined_text()
        open_graph(
            {
                "nodes": [
                    {"id": "1", "label": focus},
                    {"id": "2", "label": "Generating graph..."},
                ],
                "edges": [
                    {"from": "1", "to": "2", "label": "building now"},
                ],
            },
            focus,
        )
        self.summary_panel.show_summary("Generating graph...")
        threading.Thread(
            target=self._run_graph,
            args=(text, focus),
            daemon=True,
        ).start()

    def _run_graph(self, text, focus):
        graph = build_knowledge_graph(text)
        if isinstance(graph, str):
            self.app.after(0, lambda: self.summary_panel.show_summary(graph))
            return
        self.app.after(0, lambda: open_graph(graph, focus))
        self.app.after(0, lambda: self.summary_panel.show_summary("Graph generated."))

    def ingest_index_for_recording(self, index, set_status):
        """Capture new OCR phrases while recording and update user status text."""
        if not self._is_recording or not index:
            return
        before, after, stable_count = self._corpus_state.ingest_index(index)
        if stable_count >= 3:
            set_status(f"\u2705 Captured \u2014 scroll now ({after} phrases)")
        elif stable_count < 3 and after != before:
            set_status(f"\u23fa Capturing... {after} phrases")

    def own_window_handles(self):
        handles = set()
        if self.summary_panel.winfo_exists():
            handles.add(self.summary_panel.winfo_id())
        return handles

    def shutdown(self):
        if self.summary_panel.winfo_exists():
            self.summary_panel.destroy()
