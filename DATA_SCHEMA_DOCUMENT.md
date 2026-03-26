# Uniseba Data Schema Document

## Purpose

This document records the current data shapes passed between the active runtime components.

It reflects the current codebase:

- EasyOCR backend
- full-window OCR safe mode

---

## Core Active Handoffs

```text
capture rect -> OCR words -> normalized OCR index -> index_queue
query + index -> fuzzy results
query + index -> semantic request -> semantic results
fuzzy + semantic -> merged results -> overlay
```

---

## 1. Capture Rect

```python
{
    "left": int,
    "top": int,
    "width": int,
    "height": int,
}
```

Meaning:

- client-area screen coordinates

---

## 2. Raw OCR Word

Produced by `ocr/engine.py`.

```python
{
    "text": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
}
```

Current source:

- EasyOCR polygon bbox converted into rectangle form

If `window_rect` is provided:

- coordinates are absolute screen coordinates

---

## 3. Normalized OCR Index Entry

Produced by `ocr/index.py`.

```python
{
    "word": str,
    "original": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
    "confidence": float,
}
```

Important note:

- `confidence` here is still the project’s normalized proxy field used by later search filtering
- EasyOCR’s own OCR confidence is filtered earlier in `ocr/engine.py`

---

## 4. `index_queue` Payload

Produced by `threads/ocr_thread.py`.

```python
list[NormalizedOCRIndexEntry]
```

There is no outer wrapper object.

---

## 5. Fuzzy Search Result

Produced by `search/fuzzy.py`.

```python
{
    "word": str,
    "original": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
    "confidence": float,
    "fuzzy_score": float,
}
```

---

## 6. Semantic Request Packet

Produced by `main.py`.

```python
{
    "token": int,
    "query": str,
    "index": list[NormalizedOCRIndexEntry],
    "limit": int,
}
```

---

## 7. Semantic Result Packet

Produced by `threads/search_thread.py`.

```python
{
    "token": int,
    "results": list[SemanticSearchResult],
}
```

Where each semantic result looks like:

```python
{
    "word": str,
    "original": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
    "confidence": float,
    "semantic_score": float,
}
```

---

## 8. Merged Result

Produced by `main.py`.

```python
{
    "word": str,
    "original": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
    "confidence": float,
    "fuzzy_score": float,
    "semantic_score": float,
    "final_score": float,
}
```

---

## 9. Overlay Input

Consumed by `ui/overlay.py`.

Required fields:

```python
{
    "x": int,
    "y": int,
    "w": int,
    "h": int,
}
```

Metadata fields like `original`, `fuzzy_score`, and `final_score` may also be present.

---

## 10. Current Important Schema Fact

Because safe mode is active, there is currently no trusted active schema for partial-region OCR mapping. The trusted active path is:

- full-window OCR words
- normalized OCR index
- queue to UI
- overlay draw
