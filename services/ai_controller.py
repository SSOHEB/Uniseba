"""AI feature controller for recording."""

from services.corpus_recorder import CorpusRecorder


class AIController:
    """Own recording state and AI feature actions for the integrated app."""

    def __init__(self, app, logger):
        self.app = app
        self.logger = logger
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
        return set()

    def shutdown(self):
        pass
