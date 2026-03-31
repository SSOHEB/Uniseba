# Uniseba Problem And Update Report

## Current Status

Core OCR-search-overlay flow is working end-to-end with EasyOCR and queue-based background workers.

## Major Problems Addressed

## 1. Wrong or noisy OCR target

Implemented protections:

- Reject desktop shell windows (`Progman`, `WorkerW`).
- Reject blocked titles/prefixes and blocked console keywords.
- Normalize handles to top-level root window before capture.
- Track and lock preferred content window from global shortcut.

## 2. Overlay/search self-capture

Implemented protections:

- OCR-side masking of search UI overlap rectangles.
- Search-side filtering of known self-UI phrases.
- Exclusion padding around UI region.

## 3. Slow responsiveness on dynamic content

Implemented mitigations:

- Region change detection gate.
- Incremental OCR for merged changed regions.
- Scroll translation detection with strip-only OCR update.
- Full-window fallback retained for correctness.

## 4. Search quality and ranking drift

Implemented improvements:

- Fuzzy heuristics for containment, length mismatch, and stopword penalties.
- Phrase-aware clustering pass for multi-token queries.
- Duplicate result suppression when combining phrase + fuzzy + semantic outputs.

## 5. Runtime stability and observability

Implemented improvements:

- Rotating log files and separate error log.
- Queue payload typing (`refreshing`, `index`) to avoid stale UX confusion.
- UI signature checks to skip redundant redraw/search updates.

## Current Risks

- OCR latency is still the dominant bottleneck for dense views.
- Scroll translation estimate can occasionally drift before next refresh.
- Summary feature requires `GROQ_API_KEY` and external API access.
- `search/hybrid.py` duplicates logic that now primarily exists in `main.py`.

## Latest Test Results (2026-03-31)

Commands run with `venv311\Scripts\python.exe`:

1. `ocr_accuracy_test.py` -> PASS
   - 20/20 hit@1, 20/20 hit@5, 20/20 hit@10
2. `ocr_easyocr_test.py` -> PASS
   - 88 raw OCR detections written

Artifacts updated by tests:

- `ocr_accuracy_report.txt`
- `ocr_test_output.txt`
