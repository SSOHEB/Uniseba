import logging
from tkinter import Canvas

logger = logging.getLogger("uniseba.selection_box")


class SelectionBox:
    """
    Draws a selection rectangle on an existing
    tkinter Canvas for recording region selection.
    User clicks and drags to define the region.
    Calls on_complete(x, y, w, h) with absolute
    screen coordinates when drag is released.
    Minimum box size 50x50 enforced.
    """

    MIN_SIZE = 50

    def __init__(self, canvas, on_complete):
        self._canvas = canvas
        self._on_complete = on_complete
        self._start_x = None
        self._start_y = None
        self._rect_id = None
        self._active = False
        self._bindings = []
        self._stored_rect = None

    def activate(self):
        """Enable drawing mode on the canvas."""
        if self._active:
            return
        self._active = True
        self._bind("<ButtonPress-1>", self._on_press)
        self._bind("<B1-Motion>", self._on_drag)
        self._bind("<ButtonRelease-1>", self._on_release)
        self._canvas.configure(cursor="crosshair")
        logger.debug("SelectionBox activated")

    def deactivate(self):
        """Remove all bindings and clean canvas state."""
        self._active = False
        for seq, bid in self._bindings:
            try:
                self._canvas.unbind(seq, bid)
            except Exception:
                pass
        self._bindings = []
        if self._rect_id is not None:
            try:
                self._canvas.delete(self._rect_id)
            except Exception:
                pass
            self._rect_id = None
        self._start_x = None
        self._start_y = None
        try:
            self._canvas.configure(cursor="")
        except Exception:
            pass
        logger.debug("SelectionBox deactivated")

    def get_rect(self):
        """Return stored (x, y, w, h) or None."""
        return self._stored_rect

    def clear_rect(self):
        """Clear stored rect - call on recording stop."""
        self._stored_rect = None

    def _bind(self, sequence, handler):
        bid = self._canvas.bind(sequence, handler, add=True)
        self._bindings.append((sequence, bid))

    def _on_press(self, event):
        self._start_x = event.x_root
        self._start_y = event.y_root
        if self._rect_id is not None:
            try:
                self._canvas.delete(self._rect_id)
            except Exception:
                pass
        self._rect_id = self._canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="#3b82f6",
            width=2,
            fill="",
            tags="selection_box"
        )

    def _on_drag(self, event):
        if self._rect_id is None:
            return
        try:
            self._canvas.coords(
                self._rect_id,
                self._canvas.winfo_rootx() -
                self._canvas.winfo_rootx() +
                (self._start_x -
                 self._canvas.winfo_rootx()),
                self._start_y -
                self._canvas.winfo_rooty(),
                event.x_root -
                self._canvas.winfo_rootx(),
                event.y_root -
                self._canvas.winfo_rooty()
            )
        except Exception:
            pass

    def _on_release(self, event):
        if self._start_x is None:
            return
        x = min(self._start_x, event.x_root)
        y = min(self._start_y, event.y_root)
        w = abs(event.x_root - self._start_x)
        h = abs(event.y_root - self._start_y)

        if w < self.MIN_SIZE or h < self.MIN_SIZE:
            logger.debug(
                "SelectionBox too small (%dx%d) "
                "-- resetting for redraw", w, h
            )
            if self._rect_id is not None:
                try:
                    self._canvas.delete(self._rect_id)
                except Exception:
                    pass
                self._rect_id = None
            self._start_x = None
            self._start_y = None
            return

        # Clamp to screen dimensions
        try:
            import ctypes
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
            x = max(0, min(x, sw))
            y = max(0, min(y, sh))
            w = min(w, sw - x)
            h = min(h, sh - y)
        except Exception as e:
            logger.warning(
                "Screen dimension clamp failed: %s", e
            )

        self._stored_rect = (x, y, w, h)
        logger.info(
            "SelectionBox region set: "
            "x=%s y=%s w=%s h=%s", x, y, w, h
        )
        self.deactivate()
        try:
            self._on_complete(x, y, w, h)
        except Exception as e:
            logger.warning(
                "SelectionBox on_complete failed: %s", e
            )
