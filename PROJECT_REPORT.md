# Uniseba Project Report

## 1. Project Overview

Uniseba is a Windows desktop OCR search overlay.

Current user flow:

1. Pick the current foreground content window.
2. Capture the client area of that window.
3. Run OCR on the full captured image.
4. Normalize OCR words into a searchable in-memory index.
5. Search that index with fuzzy matching and optional semantic reranking.
6. Draw highlight rectangles over matching words on a transparent overlay.

The codebase is now beyond a backend prototype. It includes:

- integrated UI
- tray icon
- background OCR worker
- background semantic worker
- overlay rendering
- centralized config
- structured logging

Current baseline mode:

- OCR backend: EasyOCR
- capture area: client area only
- OCR mode: hybrid (full-window fallback + incremental OCR)
- partial-region OCR: enabled (merged changed regions)
- scroll-specialized OCR: enabled (translation estimate + strip OCR)
- stabilization smoothing: bypassed (newest index wins)

---

## 2. Current Folder Purpose

- `capture/`
  Screen capture and frame-change detection helpers.
- `ocr/`
  OCR backend wrapper and OCR index normalization.
- `search/`
  Fuzzy, semantic, and hybrid search logic.
- `threads/`
  Background OCR and semantic worker threads.
- `ui/`
  Searchbar base UI, overlay, and tray.
- `main.py`
  Integrated application entry point.
- `config.py`
  Centralized runtime configuration.
- `requirements.txt`
  Dependency list, though it still needs cleanup to fully reflect the current EasyOCR-based runtime.

---

## 3. Current Runtime Architecture

Runtime flow:

`target window -> client-area capture -> (incremental OCR or full OCR) -> OCR index -> index_queue -> UI search -> overlay`

More explicitly:

1. `main.py` creates the UI, tray, queues, and worker threads.
2. `threads/ocr_thread.py` selects a valid target window and captures its client area.
3. The OCR thread chooses between:
   - scroll-translation update (shift prior index + OCR only the newly revealed strip), or
   - incremental region OCR (OCR merged changed regions), or
   - full-window OCR fallback.
4. `ocr/index.py` filters and normalizes OCR results.
5. The OCR thread publishes the index to the UI queue.
6. `main.py` runs fuzzy search immediately.
7. If AI is enabled, semantic search runs in a background thread.
8. `ui/overlay.py` draws rectangles using final screen coordinates.

---

## 4. OCR Backend

### Current OCR Engine

The project now uses EasyOCR instead of WinRT OCR.

Current `ocr/engine.py` behavior:

- creates a module-level EasyOCR reader
- uses CUDA when `torch.cuda.is_available()` is true
- logs whether EasyOCR initialized on GPU or CPU
- converts PIL image to NumPy array
- calls `reader.readtext(...)`
- converts EasyOCR polygon boxes into:
  - `text`
  - `x`
  - `y`
  - `w`
  - `h`
- applies a real OCR confidence filter:
  - reject if OCR confidence < `0.15`
- applies `window_rect` offset if absolute coordinates are needed

### Why This Matters

This backend change was the major step that made OCR work better on:

- browser content
- editor content
- dark themes
- desktop labels
- mixed visual backgrounds

---

## 5. Current OCR Thread Behavior

`threads/ocr_thread.py` is still the most important operational file.

It currently owns:

- target selection
- client-area capture
- change detection gating
- incremental OCR and full-window OCR fallback
- queue publishing

Important current behavior:

- capture uses client area, not full decorated window bounds
- OCR may run on full window or smaller regions depending on change/scroll detection
- `_build_full_index()` remains the correctness fallback
- `_stabilize_index()` currently returns `new_index` directly

Correctness note:
Partial OCR must not downscale crops unless OCR coordinates are scaled back up. The current implementation avoids this by keeping region crops at native scale.

---

## 6. Search Layer

### Fuzzy Search

`search/fuzzy.py` now:

- uses `fuzz.partial_ratio` for candidate scoring
- uses `FUZZY_THRESHOLD = 85`
- keeps strong substring-style matches
- filters out weak OCR entries using the normalized index schema

### Semantic Search

`search/semantic.py` still provides optional embedding reranking using sentence-transformers.

Important note:

- semantic reranking is optional
- if the model is unavailable locally, fuzzy search still works

---

## 7. UI and Overlay

### Searchbar

`ui/searchbar.py` is now a pure UI base class.

It owns:

- the floating search window
- the entry
- result label
- AI toggle
- show/hide behavior
- overlay ownership

It no longer owns OCR orchestration.

### Overlay

`ui/overlay.py`:

- creates the transparent fullscreen draw layer
- assumes incoming coordinates are already final
- draws rectangles directly from `x`, `y`, `w`, `h`

---

## 8. What Is Working Right Now

Current confirmed baseline:

- client-area capture works
- full-window OCR works
- EasyOCR imports successfully
- CUDA-capable torch is installed and available
- fuzzy search works
- semantic thread exists
- overlay alignment is good in the correctness fallback path (full-window OCR)
- scrolling updates are working in the current baseline

This baseline has already worked on:

- Notepad/editor text
- browser pages
- desktop labels
- mixed screen content

---

## 9. What Is Intentionally Disabled Right Now

These are not gone forever, but they are not the current trusted path:

- partial-region OCR mapping
- region OCR cache reuse
- stabilization smoothing

Reason:

These optimizations previously introduced coordinate corruption and visual misalignment.

---

## 10. Current Risks

### 1. Dependency Drift

The code now uses EasyOCR, but `requirements.txt` still needs cleanup to fully reflect the live OCR stack.

### 2. Dual Search Merge Paths

The project still has:

- local merge logic in `main.py`
- hybrid merge logic in `search/hybrid.py`

These should eventually be consolidated.

### 3. Full-Window Fallback Is Correct But Less Optimized

The current baseline is accurate and demo-friendly, but it is intentionally less optimized than the earlier partial-region design.

---

## 11. Best Mental Model

The best short description of the project today is:

Uniseba is a Windows OCR overlay app that uses client-area capture plus a hybrid OCR strategy (incremental when safe, full-window fallback when needed) to produce searchable screen text and highlight matches.

---

## 12. Recommended Reading Order

Read the current code in this order:

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

## 13. Final Assessment

The project now has a working, demo-ready baseline.

The major breakthrough of the recent session was not a small tuning fix. It was the realization that:

- the fundamental full-window OCR pipeline was correct
- the geometry bugs came from the optimization path

That means the project now has a trustworthy base to build on.
