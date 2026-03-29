# Uniseba Failure Modes Document

## Purpose

This document describes what failures look like in the current Uniseba runtime.

It reflects the current baseline:

- EasyOCR backend
- client-area capture
- hybrid OCR (incremental + full-window fallback)

---

## Quick Failure Table

| Component | Failure | User Symptom | Visible? | Likely File |
| --- | --- | --- | --- | --- |
| Target selection | Wrong window chosen | Search is reading the wrong app | Yes | `threads/ocr_thread.py` |
| Client-area capture | Wrong origin or bad rect | Boxes shifted consistently | Yes | `threads/ocr_thread.py` |
| OCR backend | EasyOCR import/runtime failure | No OCR results arrive | Yes | `ocr/engine.py` |
| OCR quality | OCR noise or missed words | Missing or garbage matches | Yes | `ocr/engine.py`, `ocr/index.py` |
| OCR noise filter | Valid text filtered out | Some words never searchable | Yes | `ocr/index.py` |
| Fuzzy search | Matching too loose or too strict | Too many matches or missed matches | Yes | `search/fuzzy.py` |
| Semantic rerank | Model unavailable | AI toggle has little visible effect | Partly | `search/semantic.py` |
| Overlay draw | Rectangles missing or awkward | Search count changes but no visible highlights | Yes | `ui/overlay.py` |
| Optimization path | Partial OCR/stabilization reintroduced badly | Offset, jitter, clipped words | Yes | `threads/ocr_thread.py` |
| Scroll mode | Bad translation estimate | Ghost hits or boxes briefly drift during scroll | Yes | `threads/ocr_thread.py` |

---

## Current Important Failure Interpretations

### Wrong content searched

Most likely:

- target selection issue

First file:

- `threads/ocr_thread.py`

### Boxes offset from words

Most likely:

- capture origin mismatch
- geometry mapping bug

First file:

- `threads/ocr_thread.py`

### Search noisy even though OCR works

Most likely:

- OCR noise
- fuzzy threshold/scorer tuning

First files:

- `ocr/index.py`
- `search/fuzzy.py`

### AI toggle seems weak

Most likely:

- semantic reranker unavailable or not contributing much

First file:

- `search/semantic.py`

---

## Important Historical Lesson

The biggest misleading failure pattern in this project was:

“bad search” that was actually caused by geometry corruption in the optimization path.

That is why the current safe-mode baseline matters.

---

## Current Highest-Risk Area

The highest current risk is not the base OCR loop.

It is the incremental paths:

- region OCR correctness (crop boundaries + coordinate integrity)
- scroll translation correctness (dx/dy estimate confidence)

Those are the parts most likely to create "looks fast but wrong" behavior.
