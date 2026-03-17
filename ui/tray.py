"""System tray integration for the Uniseba desktop app."""

import threading

from PIL import Image, ImageDraw
import pystray


class TrayController:
    """Manage the tray icon and its simple show/hide + quit menu."""

    def __init__(self, on_toggle, on_quit):
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self.icon = pystray.Icon(
            "uniseba",
            self._build_icon(),
            "Uniseba",
            menu=pystray.Menu(
                pystray.MenuItem("Show/Hide Overlay", self._handle_toggle),
                pystray.MenuItem("Quit", self._handle_quit),
            ),
        )

    def start(self):
        """Run the tray icon on a background thread."""
        threading.Thread(target=self.icon.run, daemon=True, name="UnisebaTray").start()

    def stop(self):
        """Remove the tray icon if it is running."""
        self.icon.stop()

    def _handle_toggle(self, _icon, _item):
        """Relay the show/hide action back to the main application."""
        self.on_toggle()

    def _handle_quit(self, _icon, _item):
        """Relay quit back to the main application."""
        self.on_quit()

    def _build_icon(self):
        """Create a small tray icon image in memory."""
        image = Image.new("RGBA", (64, 64), (17, 24, 39, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill=(59, 130, 246, 255))
        draw.rectangle((20, 18, 44, 46), fill=(255, 215, 0, 255))
        return image
