# Uniseba Failure Modes Document

## Failure Matrix

| Area | Failure Mode | User Symptom | Primary File |
| --- | --- | --- | --- |
| Target selection | Wrong window locked/captured | Search highlights unrelated app | `threads/ocr_thread.py`, `main.py` |
| Capture geometry | Client origin mismatch | Systematic highlight offset | `threads/ocr_thread.py` |
| OCR engine | EasyOCR init or runtime failure | No/low OCR index updates | `ocr/engine.py` |
| Incremental OCR | Bad region merge or scroll estimate | Temporary ghost/misaligned boxes | `threads/ocr_thread.py` |
| Self-UI filtering | Exclusion gaps | Search matches include Uniseba UI text | `threads/ocr_thread.py`, `main.py` |
| Fuzzy ranking | Threshold/heuristic imbalance | Missing good matches or noisy top results | `search/fuzzy.py` |
| Semantic rerank | Local model unavailable | AI toggle has little/no visible effect | `search/semantic.py` |
| Queue sync | Stale token/index races | Older semantic results appear briefly | `main.py`, `threads/search_thread.py` |
| Summarize API | Missing key or API error | Summary panel shows failure text | `ai/gemini.py` |
| Logging | Oversized noisy logs | Disk growth, harder triage | `main.py` |

## Current High-Risk Zones

1. OCR performance under dense or rapidly changing content.
2. Scroll translation estimation edge cases.
3. Split merge logic (`main.py` vs `search/hybrid.py`) increasing maintenance drift.

## Current Safeguards

- Full-window OCR fallback for correctness.
- Typed queue messages for refresh/index state.
- Query/index signatures to avoid redundant reruns.
- Self-window exclusion and phrase-based noise filtering.
- Rotating log handlers with capped file sizes.

## Latest Validation (2026-03-31)

- `venv311\Scripts\python.exe ocr_accuracy_test.py` -> PASS (20/20 across hit@1/5/10)
- `venv311\Scripts\python.exe ocr_easyocr_test.py` -> PASS (88 OCR rows written)
