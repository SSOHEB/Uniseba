# Uniseba Data Schema Document

## Purpose

This document defines the active runtime data shapes currently used by Uniseba.

## 1. Capture Rect

```python
{
    "left": int,
    "top": int,
    "width": int,
    "height": int,
}
```

Meaning: target window client area in absolute screen coordinates.

## 2. Raw OCR Word (`ocr/engine.py`)

```python
{
    "text": str,
    "x": int,
    "y": int,
    "w": int,
    "h": int,
}
```

Notes:

- EasyOCR confidence is filtered internally (`confidence >= 0.15`) before emitting.
- Coordinates are absolute when a window offset is supplied.

## 3. Normalized OCR Index Entry (`ocr/index.py`)

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

## 4. `index_queue` Payload (`threads/ocr_thread.py`)

Refresh notification:

```python
{
    "type": "refreshing",
    "changed_regions": int,
    "total_regions": int,
}
```

Index publication:

```python
{
    "type": "index",
    "index": list[NormalizedOCRIndexEntry],
}
```

## 5. Fuzzy Result (`search/fuzzy.py`)

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
    "_rank_score": float,
}
```

## 6. Phrase-Enriched Result (`main.py`)

```python
{
    ...base entry fields...,
    "phrase_match": bool,
    "phrase_score": float,
}
```

## 7. Semantic Request Packet

```python
{
    "token": int,
    "query": str,
    "index": list[NormalizedOCRIndexEntry],
    "limit": int,
}
```

## 8. Semantic Result Packet

```python
{
    "token": int,
    "results": list[dict],  # each includes semantic_score
}
```

## 9. Final Merged Result (`main.py`)

```python
{
    ...base entry fields...,
    "fuzzy_score": float,
    "semantic_score": float,
    "phrase_score": float,
    "final_score": float,
}
```

## 10. Overlay Consumption (`ui/overlay.py`)

Required:

```python
{"x": int, "y": int, "w": int, "h": int}
```

Optional used fields:

- `original` (for clipboard copy text)
- score fields (not required for drawing)

## Latest Test Reference (2026-03-31)

Current schema exercised successfully by:

- `ocr_accuracy_test.py` (PASS)
- `ocr_easyocr_test.py` (PASS)
