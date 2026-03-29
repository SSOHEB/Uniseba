# Uniseba Codebase Detailed Reference

## Purpose

This document is the current codebase reference for Uniseba.

It describes:

- what the app actually runs today
- which files are active
- which subsystems are trusted
- which parts are legacy or temporarily bypassed

---

## Current Truth

- OCR backend: EasyOCR
- OCR mode: hybrid (full-window fallback + incremental OCR)
- capture origin: client area only
- partial-region OCR: enabled (merged changed regions)
- scroll-specialized OCR: enabled (translation estimate + strip OCR)
- stabilization smoothing: bypassed
- search path: fuzzy first, optional semantic rerank
- overlay path: draws final absolute coordinates directly

Known-good launch command:

```powershell
python main.py
```

---

## Repository Snapshot

- `main.py`
  Integrated application coordinator.
- `config.py`
  Centralized runtime config.
- `capture/`
  Capture and change-detection helpers.
- `ocr/`
  EasyOCR backend wrapper and index normalization.
- `search/`
  Fuzzy, semantic, and hybrid ranking logic.
- `threads/`
  OCR worker and semantic worker.
- `ui/`
  Searchbar base UI, overlay, and tray.

Markdown files in this repo are now synchronized to the current runtime baseline.

---

## Active Runtime Path

## `main.py`

Current responsibilities:

- set DPI awareness
- configure logging
- create queues
- start OCR thread
- start semantic thread
- start tray
- run integrated UI
- run fuzzy-first search flow
- request semantic rerank
- merge and draw final matches

## `threads/ocr_thread.py`

Current active responsibilities:

- choose target window
- capture client area
- use change detection as a gating signal
- run incremental OCR where safe, otherwise full-window OCR
- build OCR index
- publish index to UI

Important current mode:

- `_build_full_index()` remains the correctness fallback
- incremental path is enabled (merged regions + scroll translation)
- `_stabilize_index()` currently returns `new_index`

## `ocr/engine.py`

Current responsibilities:

- initialize EasyOCR reader
- use CUDA when available
- run OCR synchronously
- convert EasyOCR boxes into the project schema
- reject OCR confidence below `0.15`

## `ocr/index.py`

Current responsibilities:

- normalize OCR output into shared search entries
- apply OCR noise filtering
- compute search-layer confidence proxy field

## `search/fuzzy.py`

Current responsibilities:

- immediate query search
- OCR candidate filtering
- partial-ratio-based fuzzy search

Current important settings:

- `FUZZY_THRESHOLD = 85`
- `MIN_CONFIDENCE = 0.15`

## `search/semantic.py`

Current responsibilities:

- optional semantic rerank backend
- lazy local embedding model load

## `threads/search_thread.py`

Current responsibilities:

- receive semantic requests
- run semantic search
- return semantic results by queue

## `ui/searchbar.py`

Current responsibilities:

- pure UI base class
- entry, result label, AI toggle
- visibility, overlay ownership, shutdown

## `ui/overlay.py`

Current responsibilities:

- draw rectangles from final `x`, `y`, `w`, `h`
- no coordinate transformations

## `ui/tray.py`

Current responsibilities:

- tray icon
- show/hide callback
- quit callback

---

## Configuration Reality

`config.py` is now populated and centralized.

Current important values include:

- `DEBOUNCE_MS = 250`
- `POLL_MS = 100`
- `MAX_RESULTS = 50`
- `FUZZY_THRESHOLD = 85`
- `MIN_CONFIDENCE = 0.15`
- `SCAN_INTERVAL_MS = 300`
- `CHANGE_GRID = (6, 6)`
- `CHANGE_THRESHOLD = 2.5`
- `OCR_UPDATE_DEBOUNCE_MS = 100`
- `OCR_STABILITY_COUNT_THRESHOLD = 40`
- `FORCED_OCR_INTERVAL_MS = 30000`

These values are no longer scattered through `getattr(config, ...)` fallbacks.

---

## Dependency Reality

Current OCR reality:

- code uses EasyOCR
- environment needs EasyOCR + torch + compatible NumPy
- CUDA support depends on the installed torch build and NVIDIA setup

Important practical note:

The code has moved ahead of the original `requirements.txt` assumptions. The runtime now depends on the EasyOCR stack being healthy, so dependency cleanup is still an active maintenance task.

---

## Coordinate Ownership

This remains the most important concept in the project.

Current trusted chain:

1. OCR thread captures client-area image in screen coordinates.
2. OCR engine runs on the full image.
3. OCR engine returns screen-space coordinates when given `window_rect`.
4. OCR index stores those coordinates.
5. Overlay draws them directly.

This direct path (full-window OCR with absolute coordinates) is why the correctness fallback aligns correctly.

---

## Why The Current Baseline Works

The recent debugging session established that:

- the fundamental full-window OCR pipeline works
- the overlay path works
- the main geometry corruption came from optimization layers

The most important debugging outcome was:

Full-window fallback proved the system can work accurately before incremental optimizations were reintroduced.

---

## Current Risks

### 1. Optimization Debt

Incremental OCR is back, but correctness and fallback behavior must be continuously validated (especially scroll translation and region merging).

### 2. Search Merge Duplication

`main.py` and `search/hybrid.py` still overlap conceptually.

### 3. Dependency Drift

The OCR backend changed faster than the package/documentation story.

---

## Best Reading Order

1. `main.py`
2. `threads/ocr_thread.py`
3. `ocr/engine.py`
4. `ocr/index.py`
5. `search/fuzzy.py`
6. `search/semantic.py`
7. `ui/searchbar.py`
8. `ui/overlay.py`
9. `threads/search_thread.py`
10. `config.py`

---

## Final Assessment

Uniseba now has a working, accurate baseline:

- client-area capture
- full-window EasyOCR
- searchable OCR index
- background worker orchestration
- aligned overlay highlights

The project’s current strength is not maximum optimization. Its strength is that the baseline path is now trustworthy.
