# Uniseba Codebase Detailed Reference

## Runtime Truth

- Platform focus: Windows desktop.
- OCR backend: EasyOCR (`ocr/engine.py`).
- Capture origin: target window client area.
- OCR modes: scroll-strip incremental, merged-region incremental, full fallback.
- Search path: fuzzy first, optional semantic rerank.
- Overlay input coordinates: absolute screen space.

## Key Files

- `main.py`: app wiring, phrase search flow, semantic merge, summarize actions.
- `config.py`: centralized tunables.
- `threads/ocr_thread.py`: target selection, capture, OCR mode routing, queue publish.
- `threads/search_thread.py`: semantic worker.
- `ocr/index.py`: OCR normalization + filters.
- `search/fuzzy.py`: fuzzy matching and ranking heuristics.
- `search/semantic.py`: lazy model load + cosine similarity search.
- `ui/searchbar.py`: floating UI base.
- `ui/overlay.py`: transparent highlight layer with click-to-copy.
- `ui/summary_panel.py`: summary modal.
- `ai/gemini.py`: Groq-backed summarization helper.

## Queue Contracts

### `index_queue` payloads from OCR thread

- Refresh signal:

```python
{"type": "refreshing", "changed_regions": int, "total_regions": int}
```

- Index update:

```python
{"type": "index", "index": list[dict]}
```

### `semantic_request_queue` payload

```python
{"token": int, "query": str, "index": list[dict], "limit": int}
```

### `semantic_result_queue` payload

```python
{"token": int, "results": list[dict]}
```

## Notable Current Behaviors

- UI preserves last good highlights while OCR is refreshing.
- Query/index signatures avoid unnecessary redraws.
- Phrase results are merged ahead of plain fuzzy results.
- Overlay clicks copy matched text to clipboard.
- Record mode accumulates seen OCR words into a corpus for summarization.

## Latest Test Results (2026-03-31)

Executed with `venv311\Scripts\python.exe`:

1. `ocr_accuracy_test.py`: PASS (100% on hit@1/hit@5/hit@10 over 20 cases)
2. `ocr_easyocr_test.py`: PASS (88 OCR rows written)

Updated artifacts:

- `ocr_accuracy_report.txt`
- `ocr_test_output.txt`
