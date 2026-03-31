# Uniseba System Evidence Report

## Evidence Scope

This report summarizes evidence verified from the current codebase and fresh local test runs on 2026-03-31.

## Code Evidence Highlights

Observed in source:

- OCR mode routing includes scroll translation, region incremental OCR, and full fallback (`threads/ocr_thread.py`).
- Queue payloads now include typed packets (`refreshing`, `index`) rather than raw list only.
- Phrase-aware query clustering is active before normal fuzzy merge (`main.py`).
- Semantic rerank worker is asynchronous and optional (`threads/search_thread.py`, `search/semantic.py`).
- Summarization feature is active via Groq API (`ai/gemini.py`, `ui/summary_panel.py`).
- Overlay supports click-to-copy feedback flash (`ui/overlay.py`).
- Logging uses rotating file handlers and split error log (`main.py`).

## Test Evidence (Executed 2026-03-31)

Interpreter:

- `venv311\Scripts\python.exe` (Python 3.11.9)

Executed commands:

1. `ocr_accuracy_test.py`
2. `ocr_easyocr_test.py`

Results:

- `ocr_accuracy_test.py`: PASS
  - OCR words: 86
  - Indexed entries: 338
  - hit@1: 20/20 (100%)
  - hit@5: 20/20 (100%)
  - hit@10: 20/20 (100%)
- `ocr_easyocr_test.py`: PASS
  - Output lines written: 88

Generated artifacts:

- `ocr_accuracy_report.txt`
- `ocr_test_output.txt`

## Evidence-Based Risks

- Performance risk remains OCR latency on dense windows; search/overlay are comparatively light.
- Semantic rerank can silently become fuzzy-only if local model is unavailable.
- Full-index downscale constant in OCR thread is hardcoded and can drift from config intent.

## Conclusion

The system is functionally integrated and test scripts pass in the project runtime environment, with remaining risk concentrated in OCR performance and maintainability consistency.
