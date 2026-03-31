# Uniseba System Deep Dive

## End-to-End Flow

1. Global shortcut toggles search UI.
2. OCR worker chooses/maintains target content window.
3. Target client area is captured via `mss`.
4. Frame change detection decides whether OCR refresh is needed.
5. OCR worker picks mode:
   - scroll translation + strip OCR,
   - merged-region incremental OCR,
   - full-window fallback OCR.
6. OCR output is normalized into index entries.
7. UI thread consumes newest index and runs fuzzy search.
8. Optional semantic worker reranks asynchronously.
9. UI merges scores and draws overlay highlights.

## Coordinate Ownership

- Capture rect is client-area absolute screen coordinates.
- OCR boxes are converted to absolute coordinates before indexing.
- Overlay draws those coordinates directly without extra transforms.

This is the core alignment rule that keeps highlights stable.

## Active Search Strategy

- Fuzzy search runs immediately for responsiveness.
- Phrase-aware clustering improves multi-word queries.
- Semantic rerank is optional and token-based (latest request wins).
- Final score combines `phrase_score`, `fuzzy_score`, and `semantic_score`.

## Summarization Path

- User can record observed OCR words while navigating content.
- On summarize, corpus text is sent to Groq model `llama-3.3-70b-versatile`.
- Output is shown in `ui/summary_panel.py`.
- If API key is missing, UI shows failure string returned by helper.

## Operational Safeguards

- Excludes own windows from OCR target selection.
- Masks search UI area from OCR capture.
- Filters self-UI phrases before search/overlay display.
- Uses rotating logs to limit runaway file growth.

## Latest Test Results (2026-03-31)

Commands:

1. `venv311\Scripts\python.exe ocr_accuracy_test.py`
2. `venv311\Scripts\python.exe ocr_easyocr_test.py`

Observed:

- OCR benchmark: 20/20 pass at hit@1, hit@5, hit@10.
- Raw EasyOCR extraction test: 88 detections emitted to output file.
