"""Windows OCR wrapper for Phase 2."""

import asyncio
import io

from PIL import Image

from capture.screen import capture_active_window
from ocr.index import build_ocr_index


def _load_winrt_modules():
    """Import WinRT OCR modules only when needed so failures stay explicit."""
    try:
        from winrt.windows.globalization import Language
        from winrt.windows.graphics.imaging import BitmapDecoder
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
    except ImportError as exc:
        raise RuntimeError(
            "Required WinRT OCR namespaces are not available in this environment."
        ) from exc
    return Language, BitmapDecoder, DataWriter, InMemoryRandomAccessStream, OcrEngine


async def _image_to_software_bitmap(image):
    """Encode a PIL image to BMP bytes, then decode it into a SoftwareBitmap."""
    Language, BitmapDecoder, DataWriter, InMemoryRandomAccessStream, _ = _load_winrt_modules()
    _ = Language  # Keep the import grouped in one place for the OCR pipeline.

    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="BMP")
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(buffer.getvalue())
    await writer.store_async()
    writer.detach_stream()
    stream.seek(0)

    decoder = await BitmapDecoder.create_async(stream)
    return await decoder.get_software_bitmap_async()


async def recognize_image(image, window_rect=None, min_height=8):
    """Run OCR on a PIL image and return filtered words with absolute boxes."""
    Language, _, _, _, OcrEngine = _load_winrt_modules()
    engine = OcrEngine.try_create_from_language(Language("en-US"))
    if engine is None:
        raise RuntimeError("English OCR engine is not available.")

    bitmap = await _image_to_software_bitmap(image)
    result = await engine.recognize_async(bitmap)
    offset_x = 0 if window_rect is None else window_rect["left"]
    offset_y = 0 if window_rect is None else window_rect["top"]
    words = []

    for line in result.lines:
        for word in line.words:
            box = word.bounding_rect
            if box.height < min_height:
                continue
            words.append(
                {
                    "text": word.text,
                    "x": int(offset_x + box.x),
                    "y": int(offset_y + box.y),
                    "w": int(box.width),
                    "h": int(box.height),
                }
            )

    return words


async def _run_test():
    """Capture the active window, run OCR, and print word boxes."""
    image, rect = capture_active_window()
    if image is None:
        print("No active window found.")
        return

    words = await recognize_image(image, rect)
    index = build_ocr_index(words)
    for item in index:
        print(f"{item['original']}: ({item['x']}, {item['y']}, {item['w']}, {item['h']})")


if __name__ == "__main__":
    asyncio.run(_run_test())
