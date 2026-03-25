# Uniseba Problem And Update Report

## Purpose

This document records what was built, what changed across the project, what problems repeatedly appeared, which fixes helped, which fixes did not help enough, and what the current codebase reality is.

It is intentionally honest. It describes the implementation as it exists in the repository now, not only the intended design.

---

## Project Summary

Uniseba is a desktop OCR overlay search tool for Windows.

The intended user flow is:

1. Choose a visible app window.
2. Capture that window.
3. OCR its visible text.
4. Index OCR words with screen coordinates.
5. Search those words.
6. Draw highlight rectangles over matching words on a transparent overlay.

Current implementation files are organized into:

- `capture/`
- `ocr/`
- `search/`
- `threads/`
- `ui/`
- `main.py`

---

## Phase-Level Progress

### Phase 1: Environment And Screenshot

What was done:

- Python environment and dependencies were prepared.
- Active-window capture logic was added.
- DPI awareness was set early.
- Capturing the foreground window worked.

What worked:

- `mss` capture path worked.
- `win32gui.GetForegroundWindow()` plus `GetWindowRect()` worked.
- Screenshot saving and basic rect logging worked.

Main files:

- `main.py`
- `capture/screen.py`

### Phase 2: OCR Backend

What was done:

- WinRT OCR wrapper was added.
- OCR word extraction with bounding boxes was added.
- OCR words were converted into an in-memory index format.
- Thumbnail-based change detection was introduced first in a simple form.

What worked:

- OCR could detect visible words in simple windows.
- Bounding boxes could be extracted and normalized.

What caused trouble:

- WinRT namespace availability was inconsistent.
- OCR quality on dark editors and small text was unstable.
- OCR frequently missed short words.

Main files:

- `ocr/engine.py`
- `ocr/index.py`
- `capture/change.py`

### Phase 3: Hybrid Search

What was done:

- Fuzzy search was added with RapidFuzz.
- Semantic search was added with `sentence-transformers`.
- Hybrid reranking logic was added.

What worked:

- Typo-tolerant fuzzy search worked.
- Hybrid scoring returned ranked results with coordinates.

What caused trouble:

- RapidFuzz API mismatch had to be corrected.
- Semantic model availability depended on local Hugging Face cache.
- Search quality was extremely sensitive to OCR quality.

Main files:

- `search/fuzzy.py`
- `search/semantic.py`
- `search/hybrid.py`

### Phase 4: Overlay UI

What was done:

- Floating search bar UI was added.
- Transparent overlay was added.
- Highlight rectangles were drawn on a fullscreen canvas.

What worked:

- The search UI could open and accept input.
- The overlay could draw rectangles after multiple fixes.

What caused trouble:

- Click-through and transparency behavior was fragile.
- Tkinter canvas/window lifecycle produced errors during close.
- Overlay rendering was visible only after several debugging passes.
- Initial UI responsiveness problems made the screen feel frozen.

Main files:

- `ui/searchbar.py`
- `ui/overlay.py`

### Phase 5: Integration

What was done:

- Background OCR thread was introduced.
- Background semantic rerank thread was introduced.
- Queue-based UI integration was added.
- Tray icon support was added.

What worked:

- OCR thread can feed the UI through a queue.
- Search bar can consume live OCR indexes.
- Overlay can draw result rectangles using absolute coordinates.

What caused trouble:

- OCR target selection repeatedly drifted to the wrong window.
- Window locking and fallback logic became inconsistent.
- Partial OCR introduced coordinate-mapping complexity.
- OCR stabilization, debounce, and change detection all interacted in subtle ways.

Main files:

- `main.py`
- `threads/ocr_thread.py`
- `threads/search_thread.py`
- `ui/tray.py`

---

## Main Problem Clusters

### 1. OCR Environment Problems

Observed problems:

- `winrt.windows.globalization` and related namespaces were not always available.
- OCR backend could fail before the UI ever received an index.

Why this mattered:

- If `ocr/engine.py` fails, all downstream systems appear “broken” even when UI and search logic are fine.

Current status:

- The OCR pipeline still depends on WinRT import availability in `ocr/engine.py`.
- This remains an environmental risk.

### 2. Wrong Window Selection

Observed problems:

- OCR locked onto:
  - `Uniseba Search`
  - `Windows PowerShell`
  - `Program Manager`
  - stale previous windows

Why this mattered:

- Search looked inaccurate even when it was actually searching the wrong window correctly.
- Overlay highlights looked “bad” because OCR was indexing the wrong content.

What was changed:

- Added foreground-window targeting.
- Added exclusions for Uniseba windows.
- Added rejection for desktop (`Program Manager`).
- Added root-window normalization through `GetAncestor(..., GA_ROOT)`.

What still feels fragile:

- `main.py` still stores `locked_hwnd`, but current `threads/ocr_thread.py` now mainly follows foreground-first selection.
- The code contains remnants of multiple target-selection strategies from previous debugging rounds.

### 3. Overlay Rendering Problems

Observed problems:

- Fullscreen overlay froze the desktop.
- Tkinter threw canvas destruction errors.
- `canvas.lift()` was used incorrectly.
- Rectangles were not visible for a while even when matches existed.

What was changed:

- Overlay drawing logic was simplified.
- Invalid `canvas.lift()` usage was removed.
- Drawing was shifted to final absolute coordinates only.
- Debug drawing and dots were added, then removed/refined.

Current status:

- `ui/overlay.py` now draws rectangles directly from `x`, `y`, `w`, `h`.
- Overlay rendering is currently much more stable than earlier iterations.

### 4. Coordinate Mapping Problems

Observed problems:

- OCR region crops plus downscaling caused coordinate drift.
- Raw OCR coordinates were confused with final screen coordinates.
- Highlight boxes appeared offset.

What was changed:

- Partial OCR results are transformed in `threads/ocr_thread.py` into absolute screen coordinates.
- `ui/overlay.py` now uses final coordinates only.
- `ocr/index.py` stores only final mapped values.

Current status:

- Coordinate mapping is cleaner now, but it is still a delicate part of the pipeline because partial OCR and region downscaling are both active.

### 5. Change Detection Problems

Observed problems:

- Full-frame diff was too coarse.
- Scroll updates were missed.
- OCR either ran too often or not often enough.

What was changed:

- Change detection was replaced by region-based diff in `capture/change.py`.
- Thresholds were lowered.
- Forced OCR refresh every 500 ms was added.
- OCR debounce was reduced.

Current status:

- The system is more responsive to scroll than earlier.
- However, region diff, forced refresh, OCR debounce, and stabilization all now interact, so tuning remains sensitive.

### 6. Search Quality Problems

Observed problems:

- Search results were noisy.
- Tiny OCR artifacts matched unexpectedly.
- Short queries produced visually messy highlights.

What was changed:

- Search filtering was tuned several times.
- OCR noise filtering was tightened in `ocr/index.py`.
- Fuzzy score thresholding was raised in `search/fuzzy.py`.
- Overlapping results were suppressed in `search/hybrid.py`.

Current status:

- Search is usable, but still heavily depends on OCR quality.
- “Bad search” symptoms often originate upstream in OCR or target selection.

---

## What Definitely Helped

- Setting DPI awareness before UI creation.
- Moving OCR off the UI thread.
- Using queue-based OCR updates instead of direct UI OCR.
- Rejecting desktop and Uniseba windows as OCR targets.
- Switching to region-based change detection.
- Mapping OCR boxes into final screen coordinates before overlay draw.
- Drawing overlay rectangles directly from final coordinates.
- Using top-level root HWND normalization.

---

## What Helped Partially

- Temporal OCR stabilization.
- OCR debounce.
- Forced OCR refresh.
- Target locking.
- Partial OCR per changed region.

These helped some symptoms, but also increased complexity and made debugging harder.

---

## What Did Not Work Well Or Created New Problems

- Over-aggressive target locking.
- Falling back to stale `last_valid_hwnd`.
- Treating document titles containing words like `PowerShell` as blocked.
- Overlay debug states that changed transparency/click-through behavior too much.
- Downscaled region OCR without careful coordinate remapping.
- Very strict filtering rules in search that rejected valid OCR words.

---

## Current Code Reality

These points matter when reading the repository today:

- `main.py` is the integrated app entry point.
- `ui/searchbar.py` still contains an older standalone OCR path, but `main.py` disables that refresh loop in integrated mode.
- `threads/ocr_thread.py` is the real OCR engine driver for the integrated app.
- `ocr/engine.py` is a thin WinRT wrapper, not a full OCR orchestration layer.
- `ui/overlay.py` assumes incoming coordinates are already final screen-space values.
- `config.py` is currently empty, so many runtime values are using hardcoded `getattr(..., default)` fallbacks.

---

## Current Risks

### Architectural Risk

The code now contains traces of many debugging rounds, so there is some overlap between:

- old standalone Phase 4 behavior
- current integrated Phase 5 behavior
- abandoned target-lock ideas

### Runtime Risk

- WinRT OCR availability may still break the entire pipeline in some environments.
- Foreground-based selection can still be wrong if the user is not focused on the intended app.
- Region-based partial OCR can still produce inconsistency if OCR output shifts between frames.

### Maintainability Risk

- A lot of behavior is now controlled by defaults inside each module because `config.py` is empty.
- The OCR thread has become the most complex part of the codebase and carries many responsibilities at once.

---

## Recommended Reading Order

If someone wants to understand the current project state fast, read files in this order:

1. `main.py`
2. `threads/ocr_thread.py`
3. `ocr/engine.py`
4. `ocr/index.py`
5. `capture/change.py`
6. `search/fuzzy.py`
7. `search/hybrid.py`
8. `ui/searchbar.py`
9. `ui/overlay.py`
10. `threads/search_thread.py`
11. `ui/tray.py`

---

## Final Assessment

Uniseba is no longer just a concept. It is a real working prototype with:

- window capture
- OCR
- search
- overlay rendering
- thread-based background updates

But it is still in a heavy iteration stage.

The biggest reason the app can feel inaccurate is not only search quality. It is the combination of:

- wrong target window
- unstable OCR
- changing region maps
- coordinate transformations
- UI overlay expectations

In short:

- the project has working foundations
- the OCR/search/highlight loop is real
- the main remaining challenge is stability and consistency, not basic feasibility

