# Uniseba Data Schema Document

## Purpose

This document records the exact data shapes passed between major components in the current codebase.

It focuses on connection points:

- capture output
- OCR output
- normalized index entries
- queue payloads
- semantic request/result packets
- overlay input shape

All schemas below reflect the current code.

---

## Schema Overview

The most important runtime handoffs are:

```text
capture -> OCR words -> normalized OCR index -> index_queue
index + query -> fuzzy results
index + query -> semantic_request_queue -> semantic results -> semantic_result_queue
fuzzy results + semantic results -> merged results -> overlay
```

---

## 1. Capture Rectangle Schema

Used by:

- `capture/screen.py`
- `threads/ocr_thread.py`
- `ui/searchbar.py`

Shape:

```python
{
    "left": int,
    "top": int,
    "width": int,
    "height": int,
}
```

Meaning:

- `left`
  Absolute screen X of the top-left corner.
- `top`
  Absolute screen Y of the top-left corner.
- `width`
  Captured window width in screen pixels.
- `height`
  Captured window height in screen pixels.

Example:

```python
{
    "left": 120,
    "top": 80,
    "width": 1440,
    "height": 900,
}
```

---

## 2. Changed Region Schema

Produced by:

- `capture/change.py:get_changed_regions()`

Consumed by:

- `threads/ocr_thread.py:_build_partial_index()`

Shape:

```python
{
    "left": int,
    "top": int,
    "width": int,
    "height": int,
}
```

Important note:

These coordinates are image-local to the captured window image, not absolute screen coordinates.

Example:

```python
{
    "left": 360,
    "top": 225,
    "width": 360,
    "height": 225,
}
```

---

## 3. Raw OCR Word Schema

Produced by:

- `ocr/engine.py:recognize_image()`

Shape:

```python
{
    "text": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
}
```

Meaning:

- `text`
  OCR-recognized text.
- `x`, `y`
  Top-left coordinate.
- `w`, `h`
  Bounding box width and height.

Coordinate meaning depends on call site:

- if `window_rect` is provided:
  coordinates are absolute screen coordinates
- if `window_rect` is `None`:
  coordinates are local to the image passed to OCR

Example:

```python
{
    "text": "Search",
    "x": 412,
    "y": 196,
    "w": 68,
    "h": 18,
}
```

---

## 4. Transformed OCR Word Schema

Produced inside:

- `threads/ocr_thread.py:_build_partial_index()`

This is an intermediate shape created after region-local OCR output is mapped back into screen coordinates, but before cleanup/index normalization.

Shape:

```python
{
    "text": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
}
```

Difference from raw OCR words:

- same field names
- now intended to be in final absolute screen coordinates

---

## 5. Normalized OCR Index Entry Schema

Produced by:

- `ocr/index.py:build_ocr_index()`

Consumed by:

- `search/fuzzy.py`
- `search/semantic.py`
- `search/hybrid.py`
- `main.py`
- `ui/searchbar.py`
- `ui/overlay.py` indirectly through search results

Shape:

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

Field meanings:

- `word`
  Lowercased search key.
- `original`
  Original OCR text.
- `x`, `y`, `w`, `h`
  Final absolute screen-space geometry.
- `confidence`
  Height-derived proxy score, not true OCR confidence.

Example:

```python
{
    "word": "search",
    "original": "Search",
    "x": 412,
    "y": 196,
    "w": 68,
    "h": 18,
    "confidence": 0.56,
}
```

---

## 6. `index_queue` Payload Schema

Produced by:

- `threads/ocr_thread.py`
- standalone legacy path in `ui/searchbar.py:_refresh_worker()`

Consumed by:

- `main.py:IntegratedSearchbarApp._poll_index_queue()`
- `ui/searchbar.py:_drain_latest_index()`

Shape:

```python
list[NormalizedOCRIndexEntry]
```

More explicitly:

```python
[
    {
        "word": str,
        "original": str,
        "x": int,
        "y": int,
        "w": int,
        "h": int,
        "confidence": float,
    },
    ...
]
```

Important note:

There is no outer wrapper object for OCR queue updates right now. The queue contains the raw list directly.

Example:

```python
[
    {
        "word": "phase",
        "original": "Phase",
        "x": 120,
        "y": 220,
        "w": 78,
        "h": 26,
        "confidence": 0.81,
    },
    {
        "word": "search",
        "original": "Search",
        "x": 412,
        "y": 196,
        "w": 68,
        "h": 18,
        "confidence": 0.56,
    },
]
```

---

## 7. Fuzzy Search Result Schema

Produced by:

- `search/fuzzy.py:fuzzy_search()`

Consumed by:

- `main.py`
- `search/hybrid.py`
- `ui/searchbar.py` when AI is disabled
- `ui/overlay.py` indirectly

Shape:

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

Example:

```python
{
    "word": "search",
    "original": "Search",
    "x": 412,
    "y": 196,
    "w": 68,
    "h": 18,
    "confidence": 0.56,
    "fuzzy_score": 0.96,
}
```

---

## 8. Semantic Search Result Schema

Produced by:

- `search/semantic.py:semantic_search()`

Consumed by:

- `main.py`
- `search/hybrid.py`

Shape:

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

Example:

```python
{
    "word": "search",
    "original": "Search",
    "x": 412,
    "y": 196,
    "w": 68,
    "h": 18,
    "confidence": 0.56,
    "semantic_score": 0.73,
}
```

---

## 9. Semantic Request Queue Packet

Produced by:

- `main.py:IntegratedSearchbarApp._apply_search()`

Consumed by:

- `threads/search_thread.py`

Queue:

- `semantic_request_queue`

Shape:

```python
{
    "token": int,
    "query": str,
    "index": list[NormalizedOCRIndexEntry],
    "limit": int,
}
```

Field meanings:

- `token`
  Monotonic request id used to discard stale responses.
- `query`
  Lower-level search input as typed by the user.
- `index`
  Current OCR index snapshot to search semantically.
- `limit`
  Max result count requested.

Example:

```python
{
    "token": 14,
    "query": "phase",
    "index": [
        {
            "word": "phase",
            "original": "Phase",
            "x": 120,
            "y": 220,
            "w": 78,
            "h": 26,
            "confidence": 0.81,
        }
    ],
    "limit": 50,
}
```

---

## 10. Semantic Result Queue Packet

Produced by:

- `threads/search_thread.py`

Consumed by:

- `main.py:IntegratedSearchbarApp._poll_semantic_results()`

Queue:

- `semantic_result_queue`

Shape:

```python
{
    "token": int,
    "results": list[SemanticSearchResult],
}
```

Example:

```python
{
    "token": 14,
    "results": [
        {
            "word": "phase",
            "original": "Phase",
            "x": 120,
            "y": 220,
            "w": 78,
            "h": 26,
            "confidence": 0.81,
            "semantic_score": 0.88,
        }
    ],
}
```

---

## 11. Merged Result Schema In `main.py`

Produced by:

- `main.py:IntegratedSearchbarApp._merge_results()`

Consumed by:

- `ui/overlay.py`

Shape:

```python
{
    "word": str,
    "original": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
    "confidence": float,      # if present from source item
    "fuzzy_score": float,
    "semantic_score": float,
    "final_score": float,
}
```

Important notes:

- The merged result keeps the geometry fields used for drawing.
- `confidence` survives if present on the original entry.
- `final_score` is computed as:
  - `fuzzy_score * FUZZY_WEIGHT + semantic_score * SEMANTIC_WEIGHT`

Example:

```python
{
    "word": "phase",
    "original": "Phase",
    "x": 120,
    "y": 220,
    "w": 78,
    "h": 26,
    "confidence": 0.81,
    "fuzzy_score": 0.94,
    "semantic_score": 0.88,
    "final_score": 0.904,
}
```

---

## 12. Hybrid Result Schema In `search/hybrid.py`

Produced by:

- `search/hybrid.py:hybrid_search()`

Consumed by:

- standalone `ui/searchbar.py`

Shape:

```python
{
    "word": str,
    "original": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
    "confidence": float,      # if present on source entry
    "fuzzy_score": float,
    "semantic_score": float,
    "final_score": float,
}
```

This shape is very close to the merged shape in `main.py`, but the selection/stabilization policy differs.

---

## 13. Overlay Input Schema

Consumed by:

- `ui/overlay.py:draw_matches()`

Required fields:

```python
{
    "x": int,
    "y": int,
    "w": int,
    "h": int,
}
```

Optional but commonly present:

```python
{
    "original": str,
    "word": str,
    "confidence": float,
    "fuzzy_score": float,
    "semantic_score": float,
    "final_score": float,
}
```

Important note:

The overlay only truly requires the geometry fields. Everything else is metadata.

---

## 14. Searchbar Internal Match Signature Schema

Used by:

- `main.py:IntegratedSearchbarApp._set_matches()`

Shape of each tuple element:

```python
(
    item["x"],
    item["y"],
    item["w"],
    item["h"],
    item.get("original", ""),
)
```

This is not a public packet, but it matters because it is the redraw-suppression identity used by the integrated UI.

---

## 15. Queue Summary Cheat Sheet

### `index_queue`

Payload:

```python
list[NormalizedOCRIndexEntry]
```

### `semantic_request_queue`

Payload:

```python
{
    "token": int,
    "query": str,
    "index": list[NormalizedOCRIndexEntry],
    "limit": int,
}
```

### `semantic_result_queue`

Payload:

```python
{
    "token": int,
    "results": list[SemanticSearchResult],
}
```

---

## 16. Data Ownership Summary

If you want to know which layer "owns" each schema:

| Schema | Owner |
| --- | --- |
| capture rect | capture / OCR thread |
| changed region | change detection |
| raw OCR word | OCR engine |
| normalized OCR index entry | OCR index normalizer |
| index queue payload | OCR thread |
| fuzzy result | fuzzy search |
| semantic request packet | integrated UI |
| semantic result packet | semantic thread |
| merged result | integrated UI |
| overlay input | search/UI result layer |

---

## One-Sentence Summary

The three most important handoffs in Uniseba are: `index_queue` carries a raw list of normalized OCR entries, `semantic_request_queue` carries `{token, query, index, limit}`, and `semantic_result_queue` carries `{token, results}`.
