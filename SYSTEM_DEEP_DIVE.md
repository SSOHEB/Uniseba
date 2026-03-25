# Uniseba System Deep Dive

## Purpose

This document explains the current Uniseba system end to end by analyzing the actual source files in the repository.

It is meant to answer:

- what each file does
- which path is actually used at runtime
- how data moves through the system
- where coordinates are produced and consumed
- how OCR, search, and UI depend on each other

---

## High-Level Architecture

The system is split into five main layers:

1. Capture
2. OCR
3. Search
4. Threads / orchestration
5. UI

These are wired together by `main.py`.

Runtime flow:

1. User activates the app.
2. OCR thread chooses a target window.
3. OCR thread captures the full target window.
4. Change detection decides which regions changed.
5. OCR runs on changed regions.
6. OCR words are converted into an index.
7. The index is pushed into a queue.
8. UI polls the queue and stores the newest index.
9. User types a query.
10. Search runs on the OCR index.
11. Overlay draws rectangles at matching coordinates.

---

## File-By-File Analysis

## `main.py`

This is the real application entry point.

Key responsibilities:

- sets DPI awareness before UI creation
- creates queues and stop event
- creates the integrated search bar app
- starts the OCR thread
- starts the semantic search thread
- starts the tray icon

Important class:

- `IntegratedSearchbarApp(SearchbarApp)`

This subclass is important because it changes Phase 4 behavior into Phase 5 behavior.

What it changes:

- disables the old local OCR refresh loop from `ui/searchbar.py`
- polls OCR results from a background queue
- applies fuzzy search immediately
- optionally asks the semantic thread for reranking
- redraws overlay only when match signatures change

Important note:

`main.py` still stores `locked_hwnd`, but current OCR target selection is primarily foreground-driven in `threads/ocr_thread.py`. So there is some mismatch between stored UI intent and current OCR thread behavior.

---

## `capture/screen.py`

This is the original Phase 2 helper for active-window capture.

It:

- gets the foreground HWND
- calls `GetWindowRect`
- builds a rect dict
- uses `mss` to capture it
- returns both image and absolute rect

This file is simple and still useful conceptually, but in the integrated app the main runtime capture path is inside `threads/ocr_thread.py`, not here.

---

## `capture/change.py`

This is the current change-detection module.

Key function:

- `get_changed_regions(previous_image, current_image, grid, threshold, thumb_size)`

How it works:

- splits the captured image into a grid, currently default `4x4`
- crops each region
- converts each region to grayscale thumbnail
- compares previous vs current mean absolute pixel difference
- returns only the regions whose diff exceeds threshold

Special behavior:

- if there is no previous image, all grid regions are considered changed

Why it matters:

- it is the gatekeeper for OCR cost
- it controls whether OCR is skipped, partial, or forced

---

## `ocr/engine.py`

This is the OCR engine wrapper.

It is not a scheduler. It is a thin conversion layer around Windows OCR.

Main responsibilities:

- lazy-import WinRT namespaces
- create English OCR engine
- convert PIL image to `SoftwareBitmap`
- preprocess image before OCR
- run `recognize_async`
- return words with boxes

Important implementation details:

- it upscales input image `2x`
- it autocontrasts grayscale text
- it drops tiny OCR boxes below `min_height`

Important note:

`recognize_image(image, window_rect=None)` can return:

- absolute coordinates if `window_rect` is provided
- local image coordinates if `window_rect` is `None`

In the current integrated partial-region path, `threads/ocr_thread.py` calls:

- `recognize_image(region_image, None)`

then maps region-local OCR output into final screen coordinates itself.

This makes `ocr_thread.py` the true owner of final coordinate mapping.

---

## `ocr/index.py`

This converts raw OCR words into the search index format.

Each index item looks like:

```python
{
    "word": lowercased_text,
    "original": original_text,
    "x": absolute_screen_x,
    "y": absolute_screen_y,
    "w": width,
    "h": height,
    "confidence": proxy_score,
}
```

Filtering rules:

- empty text is rejected
- height below `8` is rejected
- one-character non-digit noise is rejected

Confidence:

- there is no real OCR confidence from WinRT here
- the code uses a proxy based on bounding-box height

Why that matters:

- search logic is partly making decisions based on a confidence estimate, not true OCR confidence

---

## `threads/ocr_thread.py`

This is the core of the current system.

It is doing many jobs:

- target selection
- capture
- change detection
- partial OCR orchestration
- coordinate mapping
- OCR stabilization
- queue publishing

### Target Selection

`_update_target_window()` currently:

- normalizes foreground HWND to top-level root window
- prefers the current foreground app
- rejects bad targets like:
  - `Program Manager`
  - `Uniseba Search`
  - console/debug windows
  - small windows
  - minimized windows

The thread used to rely more heavily on lock/fallback behavior. Right now it is more foreground-driven.

### Full Window Capture

`_capture_target_window()`:

- normalizes the stored target HWND
- validates it
- obtains full bounds from `_get_full_window_rect()`
- logs `[OCR REGION] width=... height=...`
- captures that exact rect using `mss`

This means capture itself is supposed to be full-window, not bottom-strip.

### Partial OCR

`_build_partial_index()`:

- takes changed regions only
- crops each changed region from the captured image
- downscales region by `OCR_DOWNSCALE`
- runs OCR on region
- maps OCR coordinates back to screen-space
- stores OCR results per region in `region_index_cache`
- merges all region caches into one deduplicated full index

This is the most subtle part of the system.

Coordinate formula:

```python
screen_x = rect["left"] + region["left"] + (word["x"] * scale_back)
screen_y = rect["top"] + region["top"] + (word["y"] * scale_back)
```

This is why overlay drawing should use final `x/y` directly.

### Stabilization

The thread also keeps:

- `last_stable_index`
- `last_update_at`
- `last_forced_ocr_at`

It rejects unstable OCR frames if the word count changes too much and smooths repeated word positions by averaging old and new coordinates.

### Why This File Is So Important

If there is a bug in this file, symptoms can appear as:

- “bad OCR”
- “bad search”
- “wrong rectangles”
- “wrong window”
- “slow scrolling”

even when the rest of the system is fine.

---

## `search/fuzzy.py`

This is the primary immediate search engine.

Key behavior:

- lowercases query
- filters obvious OCR junk
- runs RapidFuzz `WRatio`
- returns OCR entries with a `fuzzy_score`

It rejects:

- very short OCR words
- very low confidence entries
- pure symbol strings

It prints:

- accepted candidate count
- rejected candidate count
- final match count

This file is important because it often defines the perceived quality of search much more than hybrid/semantic layers do.

---

## `search/semantic.py`

This is the optional embedding-based search backend.

Key behavior:

- lazy-loads `all-MiniLM-L6-v2`
- uses local files only by default
- caches OCR index embeddings
- computes cosine similarity between query and OCR words

Important limitation:

- if the model is not available locally, semantic search returns empty results and hybrid search effectively becomes fuzzy-only

---

## `search/hybrid.py`

This merges fuzzy and semantic scores.

Key behavior:

- collects fuzzy matches first
- merges semantic matches by `(x, y)` key
- computes weighted final score
- suppresses overlapping boxes

Important point:

The hybrid layer assumes OCR coordinates are already correct. It does not transform geometry.

---

## `threads/search_thread.py`

This is a simple background worker.

It:

- reads semantic requests from a queue
- runs `semantic_search()`
- writes results back to another queue

It does not own search ranking overall. It only assists reranking when AI toggle is enabled.

---

## `ui/searchbar.py`

This file contains the original Phase 4 standalone UI logic.

It still includes:

- its own hotkey
- its own local OCR refresh path
- sample OCR index data
- direct search calls

Important reality:

In integrated mode, `main.py` overrides `_refresh_loop()` and `_register_hotkey()`, so a lot of this file becomes a base UI shell rather than the active OCR driver.

It still provides:

- the actual search window
- entry field
- result label
- AI toggle
- target window remembering behavior

This file therefore acts partly as UI base class and partly as legacy standalone app.

---

## `ui/overlay.py`

This is the final draw surface.

Responsibilities:

- create fullscreen transparent top-level window
- keep a canvas covering the screen
- clear old highlight rectangles
- draw new highlight rectangles

Critical contract:

- it draws exactly where `x/y/w/h` tell it
- it does not re-map coordinates

Current debug behavior:

- it prints `[DRAW CHECK] using x=..., y=...`

This is useful because it shows the last stage before visible rendering.

---

## `ui/tray.py`

Simple tray controller.

Responsibilities:

- create tray icon
- provide `Show/Hide Overlay`
- provide `Quit`

This is peripheral to OCR/search logic but important for the desktop app experience.

---

## `config.py`

Currently empty.

That means many values come from per-file defaults, for example:

- OCR loop timing
- search thresholds
- grid size
- debounce values
- semantic model config

This matters because configuration is currently decentralized.

---

## End-To-End Data Flow

### Step 1. User Action

The user activates the app through the global shortcut registered in `main.py`.

### Step 2. Window Choice

The integrated UI stores the current target intent in `target_hwnd` and `locked_hwnd`.

### Step 3. OCR Thread Selects Target

`threads/ocr_thread.py` decides which HWND to capture, usually based on normalized foreground window plus validity rules.

### Step 4. Capture

The OCR thread captures the full target window with `mss`.

### Step 5. Change Detection

`capture/change.py` decides whether OCR should run and which regions changed.

### Step 6. OCR

`ocr/engine.py` converts images into WinRT OCR output.

### Step 7. Indexing

`ocr/index.py` turns OCR words into a searchable coordinate-aware index.

### Step 8. Queue Transfer

The OCR thread pushes the current index into the UI queue.

### Step 9. UI Poll

`main.py` polls the queue and stores the latest OCR index.

### Step 10. Search

The user types in the search bar.

`main.py` runs fuzzy search immediately and optionally semantic rerank in background.

### Step 11. Overlay Draw

The resulting matches are sent to `ui/overlay.py`, which draws highlight rectangles on the screen.

---

## Coordinate System Ownership

This is one of the most important conceptual points in the project.

### Capture Space

`mss` captures a window image in screen pixel space.

### OCR Space

OCR runs on:

- full window images in some test paths
- cropped and downscaled regions in the integrated OCR thread

So OCR output is not automatically safe to draw.

### Mapping Space

`threads/ocr_thread.py` is the place where OCR region-local coordinates are converted into absolute screen coordinates.

### Draw Space

`ui/overlay.py` assumes coordinates are already final.

That means:

- if rectangles are misplaced, the first place to inspect is usually `threads/ocr_thread.py`
- if rectangles are not visible, inspect `ui/overlay.py`

---

## What Is Active vs Legacy

### Active In Integrated Runtime

- `main.py`
- `threads/ocr_thread.py`
- `threads/search_thread.py`
- `capture/change.py`
- `ocr/engine.py`
- `ocr/index.py`
- `search/fuzzy.py`
- `search/hybrid.py`
- `ui/overlay.py`
- `ui/tray.py`

### Legacy Or Partially Overridden

- parts of `ui/searchbar.py`
- standalone OCR refresh logic in `ui/searchbar.py`
- sample OCR index in `ui/searchbar.py`

---

## Main Technical Risks Still Present

### 1. OCR Engine Availability

If WinRT modules are unavailable, the whole pipeline breaks at the OCR stage.

### 2. Target Selection Ambiguity

The project has changed target-selection behavior many times. The current version is more foreground-based, but UI state still keeps lock-related fields.

### 3. Partial OCR Complexity

Partial OCR improves responsiveness but creates more opportunities for:

- coordinate mismatch
- stale region caches
- inconsistent OCR across regions

### 4. Configuration Drift

Because `config.py` is empty, behavior is spread across module-local defaults, making tuning harder.

---

## Best Mental Model For This Codebase

If you want the shortest correct model of the system, use this:

Uniseba is a queue-based Windows desktop OCR overlay.

- `threads/ocr_thread.py` is the live sensor
- `ocr/engine.py` is the OCR backend
- `ocr/index.py` is the normalizer
- `search/*.py` are ranking layers
- `main.py` is the coordinator
- `ui/searchbar.py` is the control surface
- `ui/overlay.py` is the renderer

And the most important invariant is:

OCR thread must produce correct absolute coordinates for the same window the user believes is being searched.

If that invariant breaks, everything else appears wrong.

