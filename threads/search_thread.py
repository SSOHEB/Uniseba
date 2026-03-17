"""Optional background semantic reranking worker."""

import logging
import threading
from queue import Empty, Queue

from search.semantic import semantic_search


class SearchThread(threading.Thread):
    """Run semantic search in the background when AI reranking is enabled."""

    def __init__(self, request_queue: Queue, result_queue: Queue, stop_event: threading.Event):
        super().__init__(daemon=True, name="UnisebaSemantic")
        self.request_queue = request_queue
        self.result_queue = result_queue
        self.stop_event = stop_event
        self.logger = logging.getLogger("uniseba")

    def run(self):
        """Process semantic rerank requests until the app shuts down."""
        while not self.stop_event.is_set():
            try:
                request = self.request_queue.get(timeout=0.2)
            except Empty:
                continue

            if request is None:
                continue

            try:
                results = semantic_search(request["query"], request["index"], limit=request["limit"])
                self.result_queue.put({"token": request["token"], "results": results})
            except Exception:
                self.logger.exception("Semantic search thread failed.")
