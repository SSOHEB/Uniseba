# Uniseba System Deep Dive

## Purpose

This document explains the current Uniseba system end to end using the code as it exists now.

It focuses on:

- current runtime ownership
- actual OCR backend
- actual coordinate ownership
- what is active
- what is intentionally bypassed

---

## Current High-Level Architecture

The live architecture is:

1. Capture
2. OCR
3. Index normalization
4. Search
5. Overlay rendering

Runtime flow:

1. User triggers the app.
2. OCR thread chooses a valid target window.
3. OCR thread captures the client area of that window.
4. OCR thread chooses between:
   - scroll-translation update (shift previous index + OCR the newly revealed strip),
   - incremental region OCR (OCR merged changed regions), or
   - full-window EasyOCR fallback.
5. OCR words are normalized into a searchable index.
6. The index is pushed into a queue.
7. The UI polls the queue and stores the newest index.
8. Fuzzy search runs immediately on user query.
9. Optional semantic reranking runs in a background thread.
10. Overlay draws rectangles using final coordinates.

---

## Current Active Runtime Path

### `main.py`

Current responsibilities:

- DPI awareness
- queue creation
- worker thread startup
- tray startup
- integrated UI wiring
- fuzzy-first search flow
- semantic rerank request flow
- final overlay update

### `threads/ocr_thread.py`

This is still the most important operational file.

Current active behavior:

- foreground-oriented target selection
- client-area capture
- change detection gating
- incremental OCR plus full-window OCR fallback
- queue publishing

Important current note:
The optimization path is back, but only in ways that preserve coordinate correctness:

- scroll-specialized mode: estimate translation and OCR only the new strip
- region mode: merge changed regions and OCR those crops at native scale
- full-window OCR remains the fallback when the above are not safe

### `ocr/engine.py`

Current OCR backend:

- EasyOCR
- synchronous OCR call
- module-level reader
- CUDA-aware initialization

It is no longer a WinRT wrapper.

### `ocr/index.py`

Current role:

- normalize OCR output
- remove obvious OCR noise
- build the shared search index schema

### `threads/search_thread.py`

Current role:

- background semantic rerank worker
- leaves overall ranking ownership to `main.py`

### `ui/searchbar.py`

Current role:

- pure UI base class
- owns widgets, overlay ownership, visibility, and shutdown

It no longer owns OCR orchestration.

### `ui/overlay.py`

Current role:

- draw final rectangles at final coordinates
- no geometry transformation

---

## Capture Geometry Ownership

This was one of the biggest bug sources, so it is worth stating clearly.

### Current capture rectangle

The OCR thread now captures the client area only.

It uses:

- `GetClientRect()`
- `ClientToScreen()`

This excludes:

- title bar
- borders
- other window chrome

That change fixed the earlier consistent vertical offset.

---

## OCR Backend Behavior

Current `recognize_image(image, window_rect=None, min_height=8)`:

- converts PIL image to NumPy
- runs EasyOCR `readtext(...)`
- receives `(bbox, text, confidence)` tuples
- filters out OCR confidence below `0.15`
- converts polygon boxes into `x`, `y`, `w`, `h`
- applies `window_rect` offset if provided

This means the OCR backend now uses real OCR confidence, not just geometry-derived proxy behavior.

---

## Coordinate Ownership

Current safest coordinate story:

1. OCR thread captures client-area image in screen pixel coordinates.
2. OCR engine returns screen-space coordinates when `window_rect` is passed.
3. OCR index stores those absolute coordinates.
4. Overlay draws them directly.

This direct path is why safe mode aligned correctly.

---

## Why Safe Mode Matters

The recent debugging session proved something important:

- the base OCR pipeline was correct
- the optimization path was corrupting geometry

The key "safe mode" lesson still applies:

- avoid transformations that break coordinate integrity (especially downscaling crops without scaling boxes back up)
- avoid smoothing/stabilization that mixes old and new coordinates incorrectly

The current trusted architecture is hybrid:

- incremental OCR is allowed when it preserves coordinates
- full-window OCR remains the correctness fallback

---

## Search Layer

### Fuzzy Search

Current fuzzy behavior:

- `fuzz.partial_ratio`
- `FUZZY_THRESHOLD = 85`
- candidate confidence gate through the normalized index
- additional substring-style acceptance behavior

### Semantic Search

Current semantic behavior:

- optional
- background worker
- local model fallback behavior still applies

---

## Current Risks

### 1. Translation / Incremental OCR Can Be Wrong

If scroll translation is mis-estimated, the shifted index can produce ghost hits or temporarily misaligned boxes until the next full-window refresh.

### 2. Dependency Stack Needs Maintenance

The code now depends on the EasyOCR / torch / NumPy compatibility story remaining healthy.

### 3. Search Merge Logic Is Still Split

There is still overlap between:

- `main.py` merge logic
- `search/hybrid.py`

---

## Best Mental Model

The current best mental model of the codebase is:

Uniseba is a queue-based Windows OCR overlay whose trusted runtime uses client-area capture plus a hybrid OCR strategy (incremental when safe, full-window fallback when needed) to produce final absolute coordinates for search and drawing.
