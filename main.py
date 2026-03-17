"""Application entry point for the integrated Uniseba desktop flow."""

import ctypes
import logging
import queue
import threading

# Set DPI awareness before UI modules create any windows.
ctypes.windll.user32.SetProcessDPIAware()

import config
import keyboard

from search.fuzzy import fuzzy_search
from threads.ocr_thread import OCRThread
from threads.search_thread import SearchThread
from ui.searchbar import SearchbarApp
from ui.tray import TrayController

DEBOUNCE_MS = getattr(config, "DEBOUNCE_MS", 250)
MAX_RESULTS = getattr(config, "MAX_RESULTS", 50)
FUZZY_WEIGHT = getattr(config, "FUZZY_WEIGHT", 0.4)
SEMANTIC_WEIGHT = getattr(config, "SEMANTIC_WEIGHT", 0.6)
POLL_MS = getattr(config, "POLL_MS", 100)


class IntegratedSearchbarApp(SearchbarApp):
    """Connect the existing overlay UI to background OCR and semantic workers."""

    def __init__(self, index_queue, semantic_request_queue, semantic_result_queue, stop_event):
        self.external_index_queue = index_queue
        self.semantic_request_queue = semantic_request_queue
        self.semantic_result_queue = semantic_result_queue
        self.stop_event = stop_event
        self.global_hotkey = None
        self.tray = None
        self.search_poll_job = None
        self.index_poll_job = None
        self.search_token = 0
        self.latest_query = ""
        self.latest_fuzzy_results = []
        super().__init__()
        self.index_queue = self.external_index_queue
        self.current_index = []
        if self.refresh_job is not None:
            self.after_cancel(self.refresh_job)
            self.refresh_job = None
        self.bind("<Escape>", lambda _event: self.hide_overlay())
        self.index_poll_job = self.after(POLL_MS, self._poll_index_queue)
        self.search_poll_job = self.after(POLL_MS, self._poll_semantic_results)

    def _register_hotkey(self):
        """Delay hotkey registration until main wires the full app together."""
        self.hotkey_handle = None

    def _refresh_loop(self):
        """Disable the Phase 4 local OCR refresh in favor of the OCR thread."""
        return

    def set_tray(self, tray):
        """Attach the tray controller after construction."""
        self.tray = tray

    def register_global_shortcut(self):
        """Expose Ctrl+Shift+U from the app entry point."""
        self.global_hotkey = keyboard.add_hotkey(
            "ctrl+shift+u",
            lambda: self.after(0, self.toggle_visibility),
        )

    def hide_overlay(self):
        """Hide the overlay and clear any current highlights."""
        if self.visible:
            self.toggle_visibility()

    def _apply_search(self):
        """Use fuzzy results immediately and semantic reranking asynchronously."""
        self.debounce_job = None
        if not self.running or not self.winfo_exists():
            return

        query = self.entry.get().strip()
        self.latest_query = query
        if len(query) < 2:
            self.result_label.configure(text="0 matches")
            self.overlay.clear()
            return

        index = self._drain_latest_index()
        if index is None:
            index = self.current_index
        fuzzy_results = fuzzy_search(query, index, limit=MAX_RESULTS)
        self.latest_fuzzy_results = fuzzy_results
        sample = fuzzy_results[0] if fuzzy_results else None
        print(f"[search] query={query!r} matches={len(fuzzy_results)} sample={sample}")
        self.result_label.configure(text=f"{len(fuzzy_results)} matches")
        self.overlay.draw_matches(fuzzy_results)

        if self.ai_var.get():
            self.search_token += 1
            self.semantic_request_queue.put(
                {
                    "token": self.search_token,
                    "query": query,
                    "index": index,
                    "limit": MAX_RESULTS,
                }
            )

    def _poll_index_queue(self):
        """Keep the current OCR index fresh without blocking the UI thread."""
        if not self.running or not self.winfo_exists():
            return

        updated = self._drain_latest_index()
        if updated is not None:
            print(f"[MAIN] received index size: {len(updated)}")
            print(f"[main] received index with {len(updated)} words from OCR queue")
        if updated is not None and self.visible and len(self.entry.get().strip()) >= 2:
            self._apply_search()
        self.index_poll_job = self.after(POLL_MS, self._poll_index_queue)

    def _poll_semantic_results(self):
        """Apply semantic reranking results when the worker thread finishes."""
        if not self.running or not self.winfo_exists():
            return

        latest = None
        while not self.semantic_result_queue.empty():
            latest = self.semantic_result_queue.get_nowait()

        if latest is not None and latest["token"] == self.search_token and self.ai_var.get():
            merged = self._merge_results(self.latest_fuzzy_results, latest["results"])
            self.result_label.configure(text=f"{len(merged)} matches")
            self.overlay.draw_matches(merged)

        self.search_poll_job = self.after(POLL_MS, self._poll_semantic_results)

    def _merge_results(self, fuzzy_results, semantic_results):
        """Combine fuzzy and semantic results into one ranked list."""
        merged = {}
        for item in fuzzy_results:
            merged[(item["x"], item["y"])] = {
                **item,
                "fuzzy_score": item.get("fuzzy_score", 0.0),
                "semantic_score": 0.0,
            }

        for item in semantic_results:
            key = (item["x"], item["y"])
            current = merged.setdefault(
                key,
                {
                    **item,
                    "fuzzy_score": 0.0,
                    "semantic_score": 0.0,
                },
            )
            current["semantic_score"] = max(current["semantic_score"], item.get("semantic_score", 0.0))

        results = []
        for item in merged.values():
            item["final_score"] = (
                item.get("fuzzy_score", 0.0) * FUZZY_WEIGHT
                + item.get("semantic_score", 0.0) * SEMANTIC_WEIGHT
            )
            results.append(item)

        results.sort(key=lambda entry: entry.get("final_score", 0.0), reverse=True)
        return results[:MAX_RESULTS]

    def own_window_handles(self):
        """Return the current Uniseba top-level windows for OCR exclusion."""
        handles = set()
        if self.winfo_exists():
            handles.add(self.winfo_id())
        if self.overlay.exists():
            handles.add(self.overlay.window.winfo_id())
        return handles

    def shutdown(self):
        """Stop workers, tray, hotkeys, and then close the base UI cleanly."""
        if not self.running:
            return

        self.stop_event.set()
        if self.index_poll_job is not None:
            self.after_cancel(self.index_poll_job)
            self.index_poll_job = None
        if self.search_poll_job is not None:
            self.after_cancel(self.search_poll_job)
            self.search_poll_job = None
        if self.global_hotkey is not None:
            keyboard.remove_hotkey(self.global_hotkey)
            self.global_hotkey = None
        if self.tray is not None:
            self.tray.stop()
            self.tray = None
        super().shutdown()


def configure_logging():
    """Send OCR and integration errors to uniseba.log."""
    logging.basicConfig(
        filename="uniseba.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main():
    """Launch the full overlay, tray, OCR, and search integration flow."""
    configure_logging()
    stop_event = threading.Event()
    index_queue = queue.Queue()
    semantic_request_queue = queue.Queue()
    semantic_result_queue = queue.Queue()

    app = IntegratedSearchbarApp(index_queue, semantic_request_queue, semantic_result_queue, stop_event)
    tray = TrayController(
        on_toggle=lambda: app.after(0, app.toggle_visibility),
        on_quit=lambda: app.after(0, app.shutdown),
    )
    app.set_tray(tray)
    app.register_global_shortcut()

    ocr_thread = OCRThread(
        index_queue,
        stop_event,
        excluded_hwnds=app.own_window_handles,
        preferred_hwnd=lambda: app.target_hwnd,
    )
    semantic_thread = SearchThread(semantic_request_queue, semantic_result_queue, stop_event)
    ocr_thread.start()
    semantic_thread.start()
    print("[main] OCR thread started")
    print("[main] semantic thread started")
    tray.start()
    print("[main] tray started")
    app.mainloop()


if __name__ == "__main__":
    main()
