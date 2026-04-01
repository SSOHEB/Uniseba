"""Application entry point for the integrated Uniseba desktop flow."""

import ctypes
import logging
import queue
import threading
import time

# Set DPI awareness before UI modules create any windows.
ctypes.windll.user32.SetProcessDPIAware()

import keyboard
import win32gui

from ai.gemini import build_knowledge_graph, summarize_screen_text
from config import (
    BLOCKED_CONSOLE_KEYWORDS,
    BLOCKED_WINDOW_PREFIXES,
    BLOCKED_WINDOW_TITLES,
    DESKTOP_WINDOW_KEYWORD,
    FUZZY_WEIGHT,
    GLOBAL_SHORTCUT,
    MAX_RESULTS,
    MIN_TARGET_TITLE_LENGTH,
    MIN_QUERY_LENGTH,
    POLL_MS,
    SEARCH_UI_EXCLUSION_PADDING,
    SEMANTIC_WEIGHT,
    SELF_UI_PHRASES,
)
from search.fuzzy import fuzzy_search
from threads.ocr_thread import OCRThread
from threads.search_thread import SearchThread
from ui.searchbar import SearchbarApp
from ui.graph_panel import open_graph
from ui.summary_panel import SummaryPanel
from ui.tray import TrayController

logger = logging.getLogger("uniseba.main")


class IntegratedSearchbarApp(SearchbarApp):
    """Connect the existing overlay UI to background OCR and semantic workers."""

    PHRASE_VERTICAL_THRESHOLD = 100
    PHRASE_HORIZONTAL_THRESHOLD = 500

    def __init__(self, index_queue, semantic_request_queue, semantic_result_queue, stop_event):
        self.index_queue = index_queue
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
        self.last_draw_signature = None
        self.last_search_signature = None
        self.last_search_query = ""
        self.last_search_index_version = -1
        self.ocr_ready = False
        self.current_index = []
        self.current_index_signature = None
        self.current_index_version = 0
        self.ocr_refreshing = False
        self.target_hwnd = None
        self.locked_hwnd = None
        self._last_content_hwnd = None
        super().__init__()
        self.summary_panel = SummaryPanel(self)
        self._is_recording = False
        self._corpus = []
        self._corpus_seen = set()
        self.bind("<Escape>", lambda _event: self.hide_overlay())
        self.index_poll_job = self.after(POLL_MS, self._poll_index_queue)
        self.search_poll_job = self.after(POLL_MS, self._poll_semantic_results)

    def set_tray(self, tray):
        """Attach the tray controller after construction."""
        self.tray = tray

    def register_global_shortcut(self):
        """Expose Ctrl+Shift+U from the app entry point."""
        self.global_hotkey = keyboard.add_hotkey(
            GLOBAL_SHORTCUT,
            self._handle_global_shortcut,
        )

    def _handle_global_shortcut(self):
        hwnd = self._last_content_hwnd
        if hwnd and win32gui.IsWindow(hwnd) and self._is_valid_shortcut_target(hwnd):
            self.target_hwnd = hwnd
            self.locked_hwnd = hwnd
            title = win32gui.GetWindowText(hwnd)
            logger.info("Shortcut locked content window hwnd=%s title=%r", hwnd, title)
        else:
            logger.debug("Shortcut fired but no valid content window was tracked")
        self.after(0, self.toggle_visibility)

    def _is_valid_shortcut_target(self, hwnd):
        """Reject obvious non-content windows before locking the current foreground window."""
        if not hwnd or not win32gui.IsWindow(hwnd) or hwnd in self.own_window_handles():
            return False

        class_name = win32gui.GetClassName(hwnd).lower()
        if class_name in {"progman", "workerw"}:
            return False

        raw_title = win32gui.GetWindowText(hwnd).strip()
        if len(raw_title) < MIN_TARGET_TITLE_LENGTH:
            return False

        title = raw_title.lower()
        if DESKTOP_WINDOW_KEYWORD in title:
            return False
        if title in BLOCKED_WINDOW_TITLES or title.startswith(BLOCKED_WINDOW_PREFIXES):
            return False
        if class_name == "consolewindowclass" and any(keyword in title for keyword in BLOCKED_CONSOLE_KEYWORDS):
            return False
        return True

    def on_hidden(self):
        """Clear overlay state when the base UI hides."""
        self.last_draw_signature = None
        self.locked_hwnd = None

    def hide_overlay(self):
        """Hide the overlay and clear any current highlights."""
        if self.visible:
            self.toggle_visibility()

    def _on_query_changed(self, event=None):
        """Keep OCR pinned to the chosen content window while the user is searching."""
        if self.visible and self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
            self.locked_hwnd = self.target_hwnd
            logger.debug(
                "Reinforced locked target window hwnd=%s title=%r",
                self.locked_hwnd,
                win32gui.GetWindowText(self.locked_hwnd),
            )
        super()._on_query_changed(event)

    def _on_record_clicked(self):
        if not self._is_recording:
            self._is_recording = True
            self._corpus = []
            self._corpus_seen = set()
            self.record_btn.configure(
                text="⏹ Stop",
                bg="#27ae60",
            )
            logger.info("Corpus recording started")
        else:
            self._is_recording = False
            self.record_btn.configure(
                text="⏺ Record",
                bg="#c0392b",
            )
            logger.info(
                "Corpus recording stopped corpus_size=%s",
                len(self._corpus),
            )

    def _on_summarize_clicked(self):
        if self._is_recording:
            self.summary_panel.show_summary(
                "Please click Stop before summarizing."
            )
            return
        if not self._corpus:
            self.summary_panel.show_summary(
                "Nothing recorded yet. Click Record, scroll through content, then click Stop."
            )
            return
        text = " ".join(self._corpus)
        self.summary_panel.show_loading()
        import threading
        threading.Thread(
            target=self._run_summarize,
            args=(text,),
            daemon=True,
        ).start()

    def _run_summarize(self, text):
        summary = summarize_screen_text(text)
        self.after(0, lambda: self.summary_panel.show_summary(summary))

    def _on_graph_clicked(self):
        if self._is_recording:
            self.summary_panel.show_summary(
                "Please click Stop before generating graph."
            )
            return
        if not self._corpus:
            self.summary_panel.show_summary(
                "Nothing recorded yet. Click Record, scroll through content, then click Stop."
            )
            return
        query = self.entry.get().strip()
        if not query:
            self.summary_panel.show_summary(
                "Type a word in the search bar first."
            )
            return
        text = " ".join(self._corpus)
        self.summary_panel.show_loading()
        threading.Thread(
            target=self._run_graph,
            args=(text, query),
            daemon=True,
        ).start()

    def _run_graph(self, text, query):
        graph = build_knowledge_graph(text, query)
        if isinstance(graph, str):
            self.after(0, lambda: self.summary_panel.show_summary(graph))
            return
        self.after(0, lambda: open_graph(graph, query))

    def _set_matches(self, matches):
        """Redraw only when the overlay input actually changed."""
        signature = self._build_signature(matches)
        if signature == self.last_draw_signature:
            return 0.0
        self.last_draw_signature = signature
        draw_started_at = time.perf_counter()
        self.overlay.draw_matches(matches)
        return (time.perf_counter() - draw_started_at) * 1000.0

    def _drain_latest_index(self):
        """Pick the most recent OCR index update from the queue."""
        latest = None
        while not self.index_queue.empty():
            item = self.index_queue.get_nowait()
            if isinstance(item, dict):
                item_type = item.get("type")
                if item_type == "refreshing":
                    self.ocr_refreshing = True
                    continue
                if item_type == "index":
                    latest = item.get("index", [])
                    self.ocr_refreshing = False
                    continue
            latest = item
            self.ocr_refreshing = False
        if latest is not None:
            latest_signature = self._build_signature(latest)
            if latest_signature != self.current_index_signature:
                self.current_index = latest
                self.current_index_signature = latest_signature
                self.current_index_version += 1
                return latest
            self.current_index = latest
        return None

    def _build_signature(self, items):
        """Create a stable signature for OCR indexes and visible result sets."""
        return tuple(
            (item["x"], item["y"], item["w"], item["h"], item.get("original", ""))
            for item in items
        )

    def _search_ui_exclusion_rects(self):
        """Return the visible search window bounds so OCR/highlights can ignore our own UI."""
        if not self.visible or not self.winfo_exists():
            return []
        try:
            left = self.winfo_rootx()
            top = self.winfo_rooty()
            right = left + self.winfo_width()
            bottom = top + self.winfo_height()
        except Exception:
            return []
        if right <= left or bottom <= top:
            return []
        return [
            {
                "left": left - SEARCH_UI_EXCLUSION_PADDING,
                "top": top - SEARCH_UI_EXCLUSION_PADDING,
                "right": right + SEARCH_UI_EXCLUSION_PADDING,
                "bottom": bottom + SEARCH_UI_EXCLUSION_PADDING,
            }
        ]

    def _filter_excluded_matches(self, matches):
        """Drop matches that overlap the floating search UI itself."""
        exclusion_rects = self._search_ui_exclusion_rects()

        filtered = []
        for item in matches:
            original = str(item.get("original", "")).strip().lower()
            if any(phrase in original for phrase in SELF_UI_PHRASES):
                continue
            left = item["x"]
            top = item["y"]
            right = left + item["w"]
            bottom = top + item["h"]
            overlaps = False
            if exclusion_rects:
                for rect in exclusion_rects:
                    if right <= rect["left"] or left >= rect["right"] or bottom <= rect["top"] or top >= rect["bottom"]:
                        continue
                    overlaps = True
                    break
            if not overlaps:
                filtered.append(item)
        return filtered

    def _phrase_tokens(self, query):
        """Return normalized tokens for phrase-mode matching."""
        return [token for token in query.strip().lower().split() if token]

    def _can_join_phrase_cluster(self, cluster, candidate):
        """Keep phrase matches spatially tight so unrelated hits do not merge."""
        min_x = min(item["x"] for item in cluster)
        max_x = max(item["x"] + item["w"] for item in cluster)
        min_y = min(item["y"] for item in cluster)
        max_y = max(item["y"] + item["h"] for item in cluster)
        candidate_left = candidate["x"]
        candidate_right = candidate["x"] + candidate["w"]
        candidate_top = candidate["y"]
        candidate_bottom = candidate["y"] + candidate["h"]
        vertical_gap = max(0, max(candidate_top - max_y, min_y - candidate_bottom))
        horizontal_gap = max(0, max(candidate_left - max_x, min_x - candidate_right))
        return (
            vertical_gap <= self.PHRASE_VERTICAL_THRESHOLD
            and horizontal_gap <= self.PHRASE_HORIZONTAL_THRESHOLD
        )

    def _build_phrase_results(self, query, index):
        """Lift multi-word queries into nearby word clusters before whole-query fuzzy search."""
        tokens = self._phrase_tokens(query)
        if len(tokens) < 2:
            return []

        token_results = {}
        for token in tokens:
            matches = fuzzy_search(token, index, limit=MAX_RESULTS)
            if not matches:
                return []
            token_results[token] = matches

        seed_token = min(token_results, key=lambda token: len(token_results[token]))
        cluster_signatures = set()
        phrase_results = []

        for seed in token_results[seed_token]:
            cluster = [seed]
            for token in tokens:
                if token == seed_token:
                    continue
                nearby = [
                    candidate
                    for candidate in token_results[token]
                    if self._can_join_phrase_cluster(cluster, candidate)
                ]
                if not nearby:
                    cluster = []
                    break
                nearby.sort(
                    key=lambda item: (
                        -item.get("fuzzy_score", 0.0),
                        abs(item["y"] - seed["y"]) + abs(item["x"] - seed["x"]),
                    )
                )
                cluster.append(nearby[0])

            if not cluster:
                continue

            deduped_cluster = []
            seen_items = set()
            for item in sorted(cluster, key=lambda entry: (entry["y"], entry["x"])):
                item_key = (item["x"], item["y"], item["w"], item["h"], item.get("original", ""))
                if item_key in seen_items:
                    continue
                seen_items.add(item_key)
                deduped_cluster.append(item)

            cluster_signature = tuple(
                (item["x"], item["y"], item["w"], item["h"], item.get("original", ""))
                for item in deduped_cluster
            )
            if cluster_signature in cluster_signatures:
                continue
            cluster_signatures.add(cluster_signature)

            for item in deduped_cluster:
                phrase_results.append(
                    {
                        **item,
                        "phrase_match": True,
                        "phrase_score": 1.0,
                    }
                )

        return phrase_results[:MAX_RESULTS]

    def _combine_phrase_and_single_results(self, phrase_results, fuzzy_results):
        """Show phrase-cluster hits first, then fall back to normal full-query fuzzy results."""
        if not phrase_results:
            return fuzzy_results

        combined = []
        seen = set()
        for item in phrase_results + fuzzy_results:
            key = (item["x"], item["y"], item["w"], item["h"], item.get("original", ""))
            if key in seen:
                continue
            seen.add(key)
            combined.append(item)
        return combined[:MAX_RESULTS]

    def _apply_search(self):
        """Use fuzzy results immediately and semantic reranking asynchronously."""
        self.debounce_job = None
        if not self.running or not self.winfo_exists():
            return

        query = self.entry.get().strip()
        self.latest_query = query
        if not self.ocr_ready:
            self.result_label.configure(text="Waiting for OCR...")
            self.overlay.clear()
            return
        if len(query) < MIN_QUERY_LENGTH:
            self.result_label.configure(text="0 matches")
            self.overlay.clear()
            return

        current_index_version = self.current_index_version
        if (
            query == self.last_search_query
            and current_index_version == self.last_search_index_version
        ):
            self.result_label.configure(text=f"{len(self.latest_fuzzy_results)} matches")
            return

        index = self._drain_latest_index()
        if index is None:
            index = self.current_index
        if self.ocr_refreshing:
            # Keep the last stable results visible while OCR catches up. This avoids
            # the UI feeling "stuck" during long OCR cycles.
            self.result_label.configure(text="Updating visible text...")
        search_started_at = time.perf_counter()
        phrase_started_at = time.perf_counter()
        phrase_results = self._build_phrase_results(query, index)
        phrase_ms = (time.perf_counter() - phrase_started_at) * 1000.0
        fuzzy_started_at = time.perf_counter()
        fuzzy_results = fuzzy_search(query, index, limit=MAX_RESULTS)
        fuzzy_ms = (time.perf_counter() - fuzzy_started_at) * 1000.0
        fuzzy_results = self._combine_phrase_and_single_results(phrase_results, fuzzy_results)
        fuzzy_results = self._filter_excluded_matches(fuzzy_results)
        result_signature = self._build_signature(fuzzy_results)
        if (
            query == self.last_search_query
            and result_signature == self.last_search_signature
            and self.current_index_version == self.last_search_index_version
        ):
            logger.debug(
                "Skipped redundant search apply query=%r matches=%s index_version=%s",
                query,
                len(fuzzy_results),
                self.current_index_version,
            )
            self.result_label.configure(text=f"{len(fuzzy_results)} matches")
            return
        self.latest_fuzzy_results = fuzzy_results
        self.last_search_query = query
        self.last_search_signature = result_signature
        self.last_search_index_version = self.current_index_version
        sample = fuzzy_results[0] if fuzzy_results else None
        overlay_ms = self._set_matches(fuzzy_results)
        total_search_ms = (time.perf_counter() - search_started_at) * 1000.0
        logger.info(
            "Search applied query=%r matches=%s phrase_ms=%.1f fuzzy_ms=%.1f overlay_ms=%.1f total_search_ms=%.1f sample=%r",
            query,
            len(fuzzy_results),
            phrase_ms,
            fuzzy_ms,
            overlay_ms,
            total_search_ms,
            sample,
        )
        self.result_label.configure(text=f"{len(fuzzy_results)} matches")

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
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and self._is_valid_shortcut_target(hwnd):
            self._last_content_hwnd = hwnd
        if not self.running or not self.winfo_exists():
            return

        updated = self._drain_latest_index()
        if updated is not None:
            self.ocr_ready = True
            logger.info("Received OCR index update size=%s", len(updated))

        if self._is_recording and self.current_index:
            before = len(self._corpus)
            for item in self.current_index:
                phrase = item.get("original", "").strip()
                if phrase and phrase not in self._corpus_seen:
                    self._corpus.append(phrase)
                    self._corpus_seen.add(phrase)
            after = len(self._corpus)
            if after != before:
                self.result_label.configure(
                    text=f"⏺ Capturing... {after} phrases"
                )
        if updated is not None and self.visible and len(self.entry.get().strip()) >= MIN_QUERY_LENGTH:
            self._apply_search()
        elif self.ocr_refreshing and self.visible and len(self.entry.get().strip()) >= MIN_QUERY_LENGTH:
            # Do not clear existing highlights; just communicate that OCR is catching up.
            self.result_label.configure(text="Updating visible text...")
        self.index_poll_job = self.after(POLL_MS, self._poll_index_queue)

    def _poll_semantic_results(self):
        """Apply semantic reranking results when the worker thread finishes."""
        if not self.running or not self.winfo_exists():
            return

        latest = None
        while not self.semantic_result_queue.empty():
            latest = self.semantic_result_queue.get_nowait()

        if latest is not None and latest["token"] == self.search_token and self.ai_var.get():
            merge_started_at = time.perf_counter()
            merged = self._merge_results(self.latest_fuzzy_results, latest["results"])
            merged = self._filter_excluded_matches(merged)
            merge_ms = (time.perf_counter() - merge_started_at) * 1000.0
            self.result_label.configure(text=f"{len(merged)} matches")
            overlay_ms = self._set_matches(merged)
            logger.info(
                "Semantic merge applied token=%s matches=%s merge_ms=%.1f overlay_ms=%.1f",
                latest["token"],
                len(merged),
                merge_ms,
                overlay_ms,
            )

        self.search_poll_job = self.after(POLL_MS, self._poll_semantic_results)

    def _merge_results(self, fuzzy_results, semantic_results):
        """Combine fuzzy and semantic results into one ranked list."""
        merged = {}
        for item in fuzzy_results:
            merged[(item["x"], item["y"])] = {
                **item,
                "fuzzy_score": item.get("fuzzy_score", 0.0),
                "semantic_score": 0.0,
                "phrase_score": item.get("phrase_score", 0.0),
            }

        for item in semantic_results:
            key = (item["x"], item["y"])
            current = merged.setdefault(
                key,
                {
                    **item,
                    "fuzzy_score": 0.0,
                    "semantic_score": 0.0,
                    "phrase_score": item.get("phrase_score", 0.0),
                },
            )
            current["semantic_score"] = max(current["semantic_score"], item.get("semantic_score", 0.0))

        results = []
        for item in merged.values():
            item["final_score"] = (
                item.get("phrase_score", 0.0)
                +
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
    """Configure file logging.

    We keep logs on disk for debugging, but we must not let a single error loop
    create multi-GB logs (which also makes performance investigation painful).
    """
    import os
    from logging.handlers import RotatingFileHandler

    log_format = "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Replace any existing handlers (basicConfig(force=True) equivalent).
    for handler in list(root.handlers):
        root.removeHandler(handler)

    log_dir = os.path.abspath(".")
    os.makedirs(log_dir, exist_ok=True)

    # Main rolling log.
    main_handler = RotatingFileHandler(
        os.path.join(log_dir, "uniseba.log"),
        maxBytes=8_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    main_handler.setLevel(logging.DEBUG)
    main_handler.setFormatter(formatter)
    root.addHandler(main_handler)

    # Separate rolling error log for quick triage.
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "uniseba_errors.log"),
        maxBytes=3_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    # Keep noisy third-party libs from drowning our timings.
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("easyocr").setLevel(logging.WARNING)


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
        exclusion_rects=app._search_ui_exclusion_rects,
        preferred_hwnd=lambda: app.target_hwnd,
        locked_hwnd=lambda: app.locked_hwnd,
        lock_active=lambda: app.locked_hwnd is not None,
    )
    semantic_thread = SearchThread(semantic_request_queue, semantic_result_queue, stop_event)
    ocr_thread.start()
    semantic_thread.start()
    logger.info("OCR thread started")
    logger.info("Semantic thread started")
    tray.start()
    logger.info("Tray started")
    app.mainloop()


if __name__ == "__main__":
    main()
