# Uniseba Codebase Detailed Reference

## Purpose

This document is a code-driven map of the current Uniseba repository.

It is written to answer:

- what the app actually does today
- which files are active at runtime
- how each subsystem behaves in detail
- which defaults control behavior
- where subtle implementation decisions live
- what is still legacy, experimental, or fragile

This document is based on the current repository contents, not on earlier phase plans.

---

## Repository Snapshot

Top-level structure:

- `main.py`
  Integrated application entry point.
- `capture/`
  Window capture and frame-change detection helpers.
- `ocr/`
  OCR engine wrapper and OCR result normalization.
- `search/`
  Fuzzy, semantic, and hybrid ranking logic.
- `threads/`
  Background OCR worker and semantic rerank worker.
- `ui/`
  Floating search bar, fullscreen overlay, and tray integration.
- `assets/`
  Present but unused by the current Python runtime.
- `config.py`
  Empty right now, so runtime behavior falls back to per-module defaults.
- `PROJECT_REPORT.md`
  Older project summary; parts of it are now outdated.
- `SYSTEM_DEEP_DIVE.md`
  Good high-level explanation, but not exhaustive.
- `PROJECT_PROBLEMS_REPORT.md`
  Useful historical context and risk summary.
- `requirements.txt`
  Python dependency pins.

Empty modules:

- `config.py`
- `capture/__init__.py`
- `ocr/__init__.py`
- `search/__init__.py`
- `threads/__init__.py`
- `ui/__init__.py`

---

## Executive Summary

Uniseba is a Windows-only desktop OCR search overlay.

Its live integrated runtime works like this:

1. `main.py` creates the UI, tray, OCR worker, semantic worker, and shared queues.
2. `threads/ocr_thread.py` continuously chooses a target window, captures it, detects changed regions, OCRs only those regions, and publishes a searchable index.
3. `main.py` polls that OCR index into the UI state.
4. When the user types into the search bar, fuzzy search runs immediately.
5. If the AI toggle is enabled, semantic search runs on a background thread and returns reranked matches.
6. `ui/overlay.py` draws highlight rectangles using final absolute screen coordinates.

The most important design fact in the whole codebase is this:

`threads/ocr_thread.py` owns the conversion from OCR-local coordinates into final screen coordinates.

If that mapping is wrong, search can still be correct while the overlay looks wrong.

---

## What Is Actually Active Today

Files definitely active in the integrated runtime:

- `main.py`
- `threads/ocr_thread.py`
- `threads/search_thread.py`
- `capture/change.py`
- `ocr/engine.py`
- `ocr/index.py`
- `search/fuzzy.py`
- `search/semantic.py`
- `ui/searchbar.py`
- `ui/overlay.py`
- `ui/tray.py`

Files that exist but are not the main runtime path:

- `capture/screen.py`
  Still useful as a standalone helper and for OCR testing, but the integrated app captures in `threads/ocr_thread.py`.
- `search/hybrid.py`
  Still used by the standalone `ui/searchbar.py` path, but not by `main.py` integrated mode, which reimplements result merging locally.

Files that serve as historical or planning docs rather than code:

- `PROJECT_REPORT.md`
- `PROJECT_PROBLEMS_REPORT.md`
- `SYSTEM_DEEP_DIVE.md`

---

## Dependency Picture

From `requirements.txt`:

- `mss==9.0.1`
  Screen capture backend.
- `winrt-Windows.Media.Ocr>=2.0.0`
  Windows OCR APIs.
- `rapidfuzz==3.6.1`
  Typo-tolerant fuzzy matching.
- `sentence-transformers==2.7.0`
  Embedding model interface.
- `numpy==1.26.4`
  Fast diff math for change detection.
- `Pillow==10.3.0`
  Image conversion, resize, crop, preprocessing, icon drawing.
- `customtkinter==5.2.2`
  Search bar UI.
- `keyboard==0.13.5`
  Global hotkey registration.
- `pywin32==306`
  Window discovery and Win32 APIs.
- `pystray==0.19.5`
  Tray icon.
- `psutil==5.9.8`
  Currently listed but not imported by the code.
- `torch==2.2.2`
  Backend for transformer embeddings.
- `transformers==4.40.1`
  Transformer dependency chain.
- `nuitka==4.0.5`
  Packaging/build ambitions; not used at runtime.

Important practical note:

The semantic path is optional in practice because `search/semantic.py` uses local-only model loading by default. If the MiniLM model is not already cached locally, semantic search silently becomes unavailable and the app still runs.

---

## Configuration Reality

`config.py` is empty.

That means the app relies on `getattr(config, "...", default)` in multiple files. Current effective defaults are spread across the codebase:

### `main.py`

- `DEBOUNCE_MS = 250`
- `MAX_RESULTS = 50`
- `FUZZY_WEIGHT = 0.4`
- `SEMANTIC_WEIGHT = 0.6`
- `POLL_MS = 100`

### `search/fuzzy.py`

- `MIN_QUERY_LENGTH = 2`
- `FUZZY_THRESHOLD = max(90, config default 75)`
- `MAX_RESULTS = 50`
- `MIN_WORD_LENGTH = 2`
- `MIN_CONFIDENCE = 0.2`

Important subtlety:

Even if `config.FUZZY_THRESHOLD` is lower than `90`, the code clamps it upward with `max(90, ...)`. So the effective minimum threshold is always `90`.

### `search/semantic.py`

- `MIN_QUERY_LENGTH = 2`
- `MAX_RESULTS = 50`
- `SEMANTIC_MODEL_NAME = "all-MiniLM-L6-v2"`
- `SEMANTIC_LOCAL_FILES_ONLY = True`

### `search/hybrid.py`

- `FUZZY_WEIGHT = 0.4`
- `SEMANTIC_WEIGHT = 0.6`
- `MAX_RESULTS = 50`
- `MIN_QUERY_LENGTH = 2`

### `threads/ocr_thread.py`

- `SCAN_INTERVAL_MS = 150`
- `MIN_TARGET_WIDTH = 300`
- `MIN_TARGET_HEIGHT = 200`
- `CHANGE_GRID = (4, 4)`
- `CHANGE_THRESHOLD = 3.0`
- `CHANGE_THUMB_SIZE = (32, 32)`
- `OCR_DOWNSCALE = 0.75`
- `OCR_UPDATE_DEBOUNCE_MS = 120`
- `OCR_STABILITY_COUNT_THRESHOLD = 20`
- `FORCED_OCR_INTERVAL_MS = 500`

This decentralized configuration is one of the main maintainability constraints in the repo.

---

## End-To-End Runtime Walkthrough

### 1. Process startup

`main.py` starts by calling:

- `ctypes.windll.user32.SetProcessDPIAware()`

This happens before UI modules are instantiated so Win32 window rectangles match actual capture pixels.

Then it creates:

- `stop_event`
- `index_queue`
- `semantic_request_queue`
- `semantic_result_queue`

These queues are the handoff boundaries between UI and worker threads.

### 2. UI creation

`IntegratedSearchbarApp` subclasses `ui.searchbar.SearchbarApp` and reuses its base window construction.

The subclass immediately changes behavior:

- disables the legacy local hotkey registration
- disables the old local OCR refresh loop
- polls OCR data from `index_queue`
- polls semantic results from `semantic_result_queue`
- keeps its own merged search state

### 3. Tray and hotkey wiring

`main.py` creates `TrayController` with two callbacks:

- toggle overlay
- quit app

It also explicitly registers the global hotkey in `IntegratedSearchbarApp.register_global_shortcut()`.

The hotkey is:

- `ctrl+shift+u`

### 4. Target capture intent

When the hotkey is pressed, `IntegratedSearchbarApp._handle_global_shortcut()`:

- reads the current foreground window with `win32gui.GetForegroundWindow()`
- ignores it if it belongs to Uniseba itself
- stores it in:
  - `target_hwnd`
  - `locked_hwnd`

This is the UI-side target intent.

### 5. Background OCR loop

`threads/ocr_thread.py` runs continuously until `stop_event` is set.

Its loop performs:

1. update target window
2. capture target window
3. detect changed regions
4. decide whether to skip OCR
5. OCR changed regions
6. normalize words into index entries
7. stabilize the new index
8. push the final index to `index_queue`

### 6. UI queue polling

`IntegratedSearchbarApp._poll_index_queue()` drains the latest OCR index and stores it as `current_index`.

If the overlay is visible and the user already typed at least 2 characters, it reruns search immediately against the new OCR data.

### 7. Search behavior

When the query changes:

- fuzzy search runs immediately in the UI thread
- overlay updates immediately from fuzzy results
- if AI is enabled, a semantic request is queued in the background

This gives fast first results with optional reranking later.

### 8. Semantic rerank

`threads/search_thread.py` receives queued requests and calls `search.semantic.semantic_search()`.

When results come back, `IntegratedSearchbarApp._poll_semantic_results()` checks the request token and only applies the newest matching semantic response.

### 9. Overlay draw

`ui.overlay.OverlayWindow.draw_matches()`:

- clears old rectangles
- draws new rectangles directly from `x`, `y`, `w`, `h`
- does not transform coordinates

This means coordinate correctness must already be guaranteed upstream.

---

## File-By-File Detailed Analysis

## `main.py`

### Role

This is the integrated application entry point and coordinator.

### Main responsibilities

- sets process DPI awareness
- configures file logging
- creates shared queues and stop event
- instantiates the integrated UI
- creates and starts the OCR and semantic threads
- starts the tray icon
- runs the Tk event loop

### `IntegratedSearchbarApp`

This subclass is the most important integration layer in the project.

It bridges:

- base UI from `ui/searchbar.py`
- OCR worker from `threads/ocr_thread.py`
- semantic worker from `threads/search_thread.py`

### Important state fields

- `external_index_queue`
  Queue owned externally by `main()`, used for OCR indexes.
- `semantic_request_queue`
  Queue of semantic rerank jobs.
- `semantic_result_queue`
  Queue of semantic rerank results.
- `stop_event`
  Shared shutdown signal for worker threads.
- `global_hotkey`
  Registered keyboard hotkey handle.
- `tray`
  `TrayController` instance.
- `search_poll_job`
  Tk `after()` handle for semantic polling.
- `index_poll_job`
  Tk `after()` handle for OCR polling.
- `search_token`
  Monotonic token used to discard stale semantic responses.
- `latest_query`
  Last query issued.
- `latest_fuzzy_results`
  Used as the base set before semantic merging.
- `last_draw_signature`
  Used to suppress redundant overlay redraws.
- `ocr_ready`
  Prevents search until at least one OCR index arrives.
- `locked_hwnd`
  UI-side remembered target lock while searching.

### Lifecycle overrides from the base class

- `_register_hotkey()`
  Disabled in subclass so the app can wire hotkeys explicitly later.
- `_refresh_loop()`
  Disabled in subclass because integrated mode relies on the OCR worker thread instead of self-driven OCR in the UI.

### Search flow in integrated mode

`_apply_search()`:

1. reads the entry text
2. refuses to search until OCR is ready
3. clears results for queries shorter than 2 characters
4. drains the newest OCR index if available
5. runs `fuzzy_search()`
6. immediately draws fuzzy results
7. if AI is enabled, sends semantic rerank request

Important behavior:

- semantic search does not replace fuzzy search; it augments it later
- fuzzy results are visible first, so the UI feels responsive even if semantic search is slow

### Local result merging

`_merge_results()` combines fuzzy and semantic matches keyed by `(x, y)`.

For each result it stores:

- `fuzzy_score`
- `semantic_score`
- `final_score`

Then it sorts by:

- `fuzzy_score * 0.4 + semantic_score * 0.6`

Important discrepancy:

`main.py` does its own merging instead of calling `search.hybrid.hybrid_search()`. This means there are effectively two hybrid strategies in the repo:

- `search/hybrid.py`
- `main.py` local merge logic

They are similar, but not identical:

- `search/hybrid.py` suppresses overlapping boxes
- `main.py` does not call `_stabilize_results()`

So integrated runtime behavior is not exactly the same as standalone hybrid behavior.

### Overlay redraw suppression

`_set_matches()` creates a tuple signature from:

- `x`
- `y`
- `w`
- `h`
- `original`

If the signature matches the previous one, redraw is skipped.

This helps prevent needless overlay churn.

### Shutdown path

`shutdown()`:

- sets `stop_event`
- cancels Tk poll jobs
- removes hotkey
- stops tray
- delegates remaining UI cleanup to `SearchbarApp.shutdown()`

It does not explicitly join worker threads; they are daemons and will exit once the process ends.

---

## `capture/screen.py`

### Role

Standalone active-window capture helper.

### Behavior

- sets DPI awareness at module import
- gets foreground window handle
- calls `GetWindowRect()`
- captures that rect with `mss`
- converts raw bytes to PIL `Image`
- returns `(image, rect)`

### Notes

- Not the primary integrated capture path.
- Still useful for quick standalone tests and OCR experiments.

---

## `capture/change.py`

### Role

Region-based change detection for captured frames.

### Core idea

Instead of comparing the whole image at full resolution, the file:

- splits the image into a fixed grid
- reduces each cell to a grayscale thumbnail
- computes the mean absolute difference per cell

### Main functions

`_grayscale_array(image, size)`

- converts to grayscale
- resizes to `size`
- returns `numpy.int16` array

`_region_bounds(width, height, rows, cols)`

- yields region boundaries for the grid
- computes pixel bounds using proportional integer splits

`get_changed_regions(previous_image, current_image, grid, threshold, thumb_size)`

- returns all changed grid cells as dictionaries:
  - `left`
  - `top`
  - `width`
  - `height`

Important details:

- if `current_image` is `None`, returns `[]`
- if `previous_image` is `None`, every region is marked changed
- default threshold is `6.0`, but integrated runtime overrides it to `3.0`

`has_significant_change(...)`

- convenience wrapper returning boolean only
- used in the legacy standalone UI path

### Subtle implementation fact

The integrated OCR worker and the standalone UI use the same change logic, but not with the same sensitivity:

- standalone path uses default threshold `6.0`
- integrated OCR worker uses `CHANGE_THRESHOLD = 3.0`

So integrated mode is intentionally more sensitive to small visual changes.

---

## `ocr/engine.py`

### Role

Thin Windows OCR wrapper around WinRT APIs.

### WinRT loading strategy

`_load_winrt_modules()` imports:

- `Language`
- `BitmapDecoder`
- `OcrEngine`
- `DataWriter`
- `InMemoryRandomAccessStream`

These imports are delayed until OCR is actually needed.

If import fails, the file raises:

- `RuntimeError("Required WinRT OCR namespaces are not available in this environment.")`

### Image conversion pipeline

`_image_to_software_bitmap(image)`:

1. converts PIL image to BMP in memory
2. writes bytes into `InMemoryRandomAccessStream`
3. decodes stream with `BitmapDecoder`
4. returns `SoftwareBitmap`

### OCR preprocessing

`_prepare_image_for_ocr(image, scale_factor=2)`:

- enlarges the image 2x using `LANCZOS`
- converts to grayscale
- applies `ImageOps.autocontrast`
- converts back to RGB

This means OCR always sees a modified image, not the original capture.

### Recognition behavior

`recognize_image(image, window_rect=None, min_height=8)`:

- creates English OCR engine with `Language("en-US")`
- preprocesses the image
- converts it to `SoftwareBitmap`
- runs `engine.recognize_async(bitmap)`
- iterates lines and words
- rejects small boxes by scaled height

Return fields:

- `text`
- `x`
- `y`
- `w`
- `h`

### Coordinate behavior

If `window_rect` is provided:

- output coordinates are offset into absolute screen space

If `window_rect` is `None`:

- output coordinates are local to the image passed to OCR

This distinction is critical.

Integrated OCR uses:

- `recognize_image(region_image, None)`

So region-local coordinates are returned and later transformed by `threads/ocr_thread.py`.

### Included test path

The file can run directly:

- captures the active window with `capture_active_window()`
- OCRs it
- normalizes it with `build_ocr_index()`
- prints each recognized item

---

## `ocr/index.py`

### Role

Normalize raw OCR word output into the repository's standard index schema.

### Filtering

`_is_meaningful_word(text, height)` rejects:

- empty strings after strip
- words with height under `8`
- one-character non-digit values

Allowed examples:

- `7`
- `A1`
- `Name`

Rejected examples:

- `""`
- `"a"` if single non-digit
- tiny punctuation artifacts

### Index schema

`build_ocr_index(words)` returns entries shaped like:

```python
{
    "word": text.lower(),
    "original": text,
    "x": int(...),
    "y": int(...),
    "w": int(...),
    "h": int(...),
    "confidence": float,
}
```

### Confidence meaning

The app does not receive true OCR confidence from WinRT here.

Instead it computes:

- `confidence = round(min(1.0, max(height, 8) / 32.0), 2)`

So confidence is really a height proxy, not a recognition certainty metric.

Implication:

Any downstream logic that filters by confidence is indirectly filtering by text box height.

### Logging

The function prints:

- `[OCR CLEANUP] filtered OCR word count: ...`

---

## `search/fuzzy.py`

### Role

Primary fast search engine used for immediate results.

### Effective thresholds

- query length must be at least `2`
- OCR word length must be at least `2`
- confidence must be at least `0.2`
- effective fuzzy score cutoff is at least `90`

### Candidate filtering

`is_viable_search_word(query, entry)` currently ignores the `query` argument and decides only from `entry`.

It rejects entries when:

- word length is below `2`
- confidence is below `0.2`
- the word contains no alphanumeric characters

This means the same OCR entry viability decision is reused across different queries.

### Search algorithm

`fuzzy_search(query, index, limit, threshold)`:

1. normalizes query to lowercase
2. returns `[]` if query is too short
3. filters the OCR index through `is_viable_search_word()`
4. extracts candidate strings
5. calls `rapidfuzz.process.extract()` with `fuzz.WRatio`
6. converts matched entries to result dictionaries
7. stores `fuzzy_score` as `score / 100.0`

### Subtle detail

Inside the result loop, the code contains:

- `substring_match = normalized_query in normalized_word`
- `if not substring_match and float(score) < threshold: continue`

Because `process.extract(..., score_cutoff=threshold)` already applied the same cutoff, this condition mostly matters as a safeguard rather than a normal branch.

### Logging

It prints:

- accepted candidate count
- rejected candidate count
- final match count

This is useful when debugging why search feels too narrow or too noisy.

---

## `search/semantic.py`

### Role

Optional semantic search backend using embeddings.

### Model loading behavior

The module keeps global state:

- `_MODEL`
- `_INDEX_CACHE`
- `_MODEL_LOAD_FAILED`

`_get_model()` lazily loads:

- `SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)`

If model load fails once, `_MODEL_LOAD_FAILED` becomes `True`, and future calls return `None` immediately.

This avoids repeated failed load attempts.

### Index caching

`_index_key(index)` builds a tuple from:

- `(entry["word"], entry["x"], entry["y"])`

This key is used to cache embeddings for the current OCR index.

Important subtlety:

The cache key ignores:

- `w`
- `h`
- `confidence`

So two indexes with same words at same coordinates but different sizes/confidences will reuse embeddings.

### Search algorithm

`semantic_search(query, index, limit)`:

1. lowercases the query
2. rejects short queries and empty indexes
3. gets or loads the embedding model
4. encodes the query
5. gets cached index embeddings
6. computes cosine similarity with `util.cos_sim`
7. returns top `k` matches with `semantic_score`

### Important operational reality

If the model is not present locally:

- semantic search returns `[]`
- no exception is surfaced to the UI
- the app behaves like fuzzy-only search

That makes the feature graceful, but it can also make AI reranking appear silently inactive.

---

## `search/hybrid.py`

### Role

Standalone hybrid result merger.

### Why it matters

Even though integrated runtime merges results in `main.py`, this file still captures the intended hybrid scoring policy and is still used by the standalone `ui/searchbar.py` mode.

### Result merging

It:

- runs `fuzzy_search()`
- runs `semantic_search()`
- merges items by `(x, y)`
- stores `fuzzy_score`, `semantic_score`, and `final_score`

Final score:

- `fuzzy * 0.4 + semantic * 0.6`

### Overlap suppression

`_boxes_overlap(a, b)` checks rectangle intersection.

`_stabilize_results(results)` keeps the first result in ranked order and drops later overlapping ones.

This is a display-oriented cleanup step to reduce redundant highlight clutter.

### Important difference from integrated mode

Integrated mode in `main.py` does not use this overlap suppression.

So highlight density can differ between:

- standalone `SearchbarApp`
- integrated `IntegratedSearchbarApp`

### Test harness

The file contains a sample index and demo queries when run directly.

---

## `threads/ocr_thread.py`

### Role

This is the most complex and operationally important file in the repository.

It combines:

- target selection
- capture
- change detection
- region OCR orchestration
- coordinate mapping
- OCR result reuse
- stabilization
- queue publishing

### Thread identity

The thread is created as:

- daemon thread
- name `"UnisebaOCR"`

### Constructor state

Key fields:

- `index_queue`
  Output queue for OCR indexes.
- `stop_event`
  Shared shutdown signal.
- `excluded_hwnds`
  Callback returning current Uniseba-owned windows.
- `preferred_hwnd`
  Callback returning UI's preferred target.
- `locked_hwnd`
  Callback supplied but not actively used in selection logic.
- `lock_active`
  Callback supplied but not actively used in selection logic.
- `current_image`
  Last captured full window image used for diffing.
- `target_hwnd`
  Currently selected OCR target.
- `has_found_valid_target`
  Changes selection rules after first valid OCR target.
- `blocked_exact_titles`
  Exact lowercase titles:
  - `windows powershell`
  - `uniseba search`
- `region_index_cache`
  Cached OCR results per region box.
- `last_stable_index`
  Previous stabilized full index.
- `last_update_at`
  Time of last published OCR update.
- `last_forced_ocr_at`
  Time of last forced full refresh behavior.

### Main loop

`run()` does the following every cycle:

1. `_update_target_window()`
2. `_capture_target_window()`
3. if no image, sleep and continue
4. run region change detection
5. decide whether to force OCR
6. skip OCR entirely if nothing changed and force interval not reached
7. apply debounce to avoid overly frequent OCR updates
8. build partial index for changed regions
9. stabilize the new index
10. publish it to `index_queue`

### Target selection strategy

The logic is more foreground-driven than lock-driven.

#### Bootstrap phase

Before any valid target is found:

- the foreground window is preferred if it passes `_is_bootstrap_target()`
- otherwise `preferred_hwnd()` is tried

Bootstrap target rules are permissive:

- must be a real window
- must not be minimized
- must not be a Uniseba-owned window
- must not be desktop / Program Manager
- must not have blocked exact title
- must have a valid rectangle

Notably, bootstrap mode does not enforce minimum width/height.

#### Normal phase

After a valid target has been found:

- current foreground window is preferred if `_is_valid_target()`
- otherwise `preferred_hwnd()` is tried

#### Valid target rejection rules

The target is rejected when:

- not a real window
- minimized
- owned by Uniseba
- title too short
- title contains `program manager`
- exact title is blocked
- title starts with `uniseba`
- class is `ConsoleWindowClass` and title includes `powershell` or `python`
- width < `300`
- height < `200`

### Window normalization

`_normalize_hwnd(hwnd)` maps child or owned windows to top-level root using:

- `win32gui.GetAncestor(hwnd, win32con.GA_ROOT)`

This reduces capture mistakes caused by focusing child controls.

### Capture behavior

`_capture_target_window()`:

- validates the current normalized target
- gets full bounds with `_get_full_window_rect()`
- captures that rectangle with `mss`
- converts it to PIL `Image`

Returned `rect` format:

```python
{
    "left": ...,
    "top": ...,
    "width": ...,
    "height": ...,
}
```

### Change detection integration

The file calls:

- `get_changed_regions(self.current_image, image, grid=CHANGE_GRID, threshold=CHANGE_THRESHOLD, thumb_size=CHANGE_THUMB_SIZE)`

With current defaults that means:

- a `4 x 4` region grid
- threshold `3.0`

If no region changed and the forced OCR interval has not elapsed, OCR is skipped.

### Forced OCR refresh

If enough time passed since the last forced refresh:

- `FORCED_OCR_INTERVAL_MS = 500`

and no region changed, the file forces a single full-window OCR region:

```python
{
    "left": 0,
    "top": 0,
    "width": image.width,
    "height": image.height,
}
```

This is a safety valve against missed visual changes.

### Debounce behavior

Even if change is detected, OCR update is skipped when:

- less than `120 ms` passed since the last update

So the loop has two pacing gates:

- scan interval
- update debounce

### Partial OCR strategy

`_build_partial_index(image, rect, changed_regions)` is the heart of the OCR worker.

For each changed region:

1. create a region key from image-space box
2. crop the region from the full image
3. optionally downscale it using `_prepare_region_image()`
4. run OCR on the region with `recognize_image(region_image, None)`
5. map OCR-local coordinates back into screen coordinates
6. normalize them with `build_ocr_index()`
7. store them in `region_index_cache[key]`

Then:

- all region caches are merged
- duplicates are removed
- the final list is returned

### Coordinate mapping formula

Because OCR runs on the region image without `window_rect`, the file performs its own coordinate mapping:

```python
screen_x = rect["left"] + region["left"] + (word["x"] * scale_back)
screen_y = rect["top"] + region["top"] + (word["y"] * scale_back)
```

Where:

- `scale_back = 1.0 / OCR_DOWNSCALE`
- current default `OCR_DOWNSCALE = 0.75`
- so `scale_back` is approximately `1.3333`

Widths and heights are also scaled back:

```python
w = word["w"] * scale_back
h = word["h"] * scale_back
```

This is the single most important geometry transformation in the repo.

### Region cache behavior

`region_index_cache` persists OCR results for unchanged regions.

Implication:

- if only one grid region changes, all others reuse their previous OCR words
- this improves speed
- but stale data can persist if the change detector misses a region that visually changed

### Deduplication key

When region caches are merged, dedupe key is:

- `(word, x, y, w, h)`

That means two identical words at different positions are preserved, but exact duplicates collapse.

### Region image preparation

`_prepare_region_image()` downsizes the region to `75%` of original by default.

This improves speed, but it also means OCR input is first:

- downscaled in `ocr_thread.py`
- then upscaled 2x in `ocr/engine.py`

So the OCR image pipeline is:

1. capture full window
2. crop region
3. downscale region to `0.75x`
4. inside OCR engine, upscale to `2x`
5. autocontrast grayscale

This is one of the more subtle image-processing choices in the codebase.

### Stabilization logic

`_stabilize_index(new_index)` has two jobs:

1. reject wildly different OCR frames
2. smooth positions for same-word matches

#### Frame rejection

If:

- `abs(len(new_index) - len(old_index)) > 20`

then the frame is treated as unstable and discarded.

This prevents sudden OCR explosions or collapses from immediately replacing the previous stable index.

#### Position smoothing

For each new item:

- it looks up previous items with the same normalized word
- chooses the closest old match by Manhattan distance
- averages old and new `x` and `y`

This reduces highlight jitter for repeated OCR updates.

### Subtle limitation in stabilization

Matching previous words only by normalized text can misassociate repeated words like:

- `the`
- `name`
- `code`

if several copies appear on screen. The closest-position rule helps, but repeated common words can still cross-associate.

### Logging/debug output

This file prints many operational messages, including:

- target selection
- region size
- change count
- debounce skips
- unstable frame skips
- OCR totals

It also logs exceptions through the `uniseba` logger.

### Architectural significance

If the app behaves strangely, this is the file most likely responsible because it influences:

- what window is searched
- how often OCR runs
- which parts of the screen get OCR'd
- where matches appear on screen
- how stable the visible results feel

---

## `threads/search_thread.py`

### Role

Background semantic rerank worker.

### Behavior

The thread:

- waits up to `0.2s` for a request
- ignores `None` requests
- runs `semantic_search(query, index, limit)`
- pushes `{"token": ..., "results": ...}` to `result_queue`

### Notes

- It is a daemon thread named `"UnisebaSemantic"`.
- It catches exceptions and logs them.
- It does not do merging; it only produces semantic results.

---

## `ui/searchbar.py`

### Role

Original standalone floating search bar application.

### Current status

This file is both:

- the base UI class reused by integrated mode
- a still-runnable standalone OCR/search overlay app

That dual role makes it partly active and partly legacy.

### Base window setup

The class `SearchbarApp(ctk.CTk)` creates:

- title `"Uniseba Search"`
- geometry `420x110+80+80`
- topmost non-resizable window
- companion overlay via `OverlayWindow(self)`

It starts hidden:

- `self.withdraw()`

### Initial sample index

`current_index` begins as `SAMPLE_INDEX`.

This means the standalone UI can still display and test search behavior even before live OCR data arrives.

### UI elements

Created in `_build_ui()`:

- `CTkEntry` for search input
- `CTkLabel` showing match count
- `CTkSwitch` labeled `AI`

Appearance mode is set to:

- `dark`

### Hotkey behavior

By default, `_register_hotkey()` registers:

- `ctrl+shift+u`

Integrated mode overrides this registration so the subclass can manage it itself.

### Visibility behavior

`toggle_visibility()`:

- hides both search window and overlay if already visible
- otherwise remembers the target window
- shows the search bar
- shows the overlay
- focuses the entry after a short delay
- immediately applies search

### Query handling

`_on_query_changed()`:

- prints debug query text
- cancels prior debounce
- schedules `_apply_search()` after `250 ms`

### Search behavior in standalone mode

`_apply_search()`:

- ignores short queries
- drains newest OCR index
- if AI toggle is on, uses `hybrid_search()`
- otherwise uses `fuzzy_search()`
- updates label
- redraws overlay

This differs from integrated mode:

- standalone mode calls `search/hybrid.py`
- integrated mode does fuzzy first plus background semantic rerank

### Legacy local OCR refresh path

`_refresh_loop()` and `_refresh_worker()` implement an older OCR model where the UI drives OCR itself.

This path:

- captures target window
- checks for significant change
- runs OCR in a worker thread
- builds OCR index
- pushes it into `index_queue`

Integrated mode disables this by overriding `_refresh_loop()` to do nothing.

### Target remembering

`_remember_target_window()` stores the foreground window active before Uniseba takes focus.

It does not normalize to root window here, unlike the OCR thread.

### Standalone capture behavior

`_capture_target_window()`:

- uses `self.target_hwnd`
- gets its window rect
- captures the full rect with `mss`

### Shutdown path

`shutdown()`:

- flips `running` false
- cancels scheduled jobs
- removes hotkey
- clears/hides overlay
- destroys overlay window if it still exists
- destroys the main window

### Architectural note

This file still contains substantial operational code that integrated mode no longer relies on directly. It is the main source of "old path vs new path" complexity in the UI layer.

---

## `ui/overlay.py`

### Role

Transparent fullscreen overlay that renders highlight rectangles.

### Window setup

The overlay:

- is a `tk.Toplevel`
- starts hidden
- is borderless via `overrideredirect(True)`
- is always-on-top
- uses alpha `0.9`
- uses background color `#010101`
- sets the same color as transparent key

It creates a fullscreen `Canvas` covering the screen.

### Click-through support

There is an `_apply_click_through()` helper that sets:

- `WS_EX_LAYERED`
- `WS_EX_TRANSPARENT`
- `WS_EX_TOOLWINDOW`

But the constructor currently does not call it because the call is commented out:

- `# self._apply_click_through()`

That means current overlay behavior depends only on Tk topmost/transparent-color handling, not true Win32 click-through styling.

### Display methods

`exists()`

- returns true only if both window and canvas exist

`show()`

- deiconifies
- lifts
- refreshes idletasks

`hide()`

- withdraws the window

`clear()`

- deletes all canvas items tagged `"highlight"`

`draw_matches(matches)`

- clears previous highlights
- converts each match into rectangle coordinates
- draws gold outline with width `4`
- raises the highlight tag
- lifts the window

### Visual contract

The overlay expects each match to already contain final absolute screen coordinates.

It does not know:

- which window was OCR'd
- whether OCR was region-based
- whether any scaling occurred earlier

### Debugging support

Each draw prints:

- `[DRAW CHECK] using x=..., y=..., word=...`

This is the last observable stage before the user sees rectangles.

---

## `ui/tray.py`

### Role

System tray wrapper.

### Behavior

The tray icon:

- uses `pystray.Icon`
- displays title `Uniseba`
- has two menu items:
  - `Show/Hide Overlay`
  - `Quit`

The callbacks simply relay control back to the main app.

### Threading

`start()` runs the tray icon on a separate daemon thread named:

- `"UnisebaTray"`

### Icon construction

The icon is created in memory:

- dark background
- blue rounded rectangle
- gold inner rectangle

No file assets are required.

---

## Cross-Cutting System Details

## Coordinate System Ownership

There are several coordinate spaces in the app:

### 1. Window/screen capture space

Full-window capture rectangles from Win32/mss are in absolute screen pixels.

### 2. Region-local image space

When the OCR thread crops a changed region, that region image starts at `(0, 0)` relative to its crop.

### 3. Downscaled region space

The OCR thread may shrink the region to `75%` before OCR.

### 4. OCR-preprocessed space

The OCR engine then enlarges that downscaled image `2x` before OCR.

### 5. OCR output space

`recognize_image(..., None)` returns coordinates relative to the OCR input image after internal scale compensation, but still local to the cropped region, not the screen.

### 6. Final screen space

`threads/ocr_thread.py` maps region-local OCR boxes back to absolute screen coordinates.

### 7. Overlay draw space

`ui/overlay.py` uses final screen-space coordinates directly.

This is why the OCR thread is the coordinate owner.

---

## Search Strategy Comparison

There are two search execution patterns in the repo:

### Standalone path

Used by `ui/searchbar.py` when run directly:

- query
- maybe OCR locally
- `hybrid_search()`
- overlay draw

### Integrated path

Used by `main.py`:

- background OCR thread keeps index fresh
- fuzzy search runs immediately
- semantic rerank runs asynchronously
- local merge in `main.py`
- overlay draw

Integrated mode prioritizes responsiveness more explicitly.

---

## Queue Boundaries

Current queues:

- `index_queue`
  OCR thread -> UI
- `semantic_request_queue`
  UI -> semantic thread
- `semantic_result_queue`
  semantic thread -> UI

These are all unbounded standard `queue.Queue()` instances.

Important consequence:

Backpressure is not explicitly managed. Instead, the UI resolves queue buildup by draining and keeping only the newest item when polling.

---

## Logging And Debuggability

The app uses two debugging channels:

### 1. `print()`

Used heavily across:

- `main.py`
- `ocr/index.py`
- `search/fuzzy.py`
- `search/hybrid.py`
- `threads/ocr_thread.py`
- `ui/searchbar.py`
- `ui/overlay.py`

### 2. `logging`

Configured in `main.py` to write to:

- `uniseba.log`

Used mainly for exception logging in worker threads.

This means the codebase is debug-friendly during development, but logging style is mixed.

---

## Behavioral Invariants

These are the practical invariants the code expects:

1. DPI awareness must be enabled before capture/UI coordinate logic matters.
2. OCR must output words that can be normalized into the expected schema.
3. OCR thread must publish final absolute coordinates, not region-local coordinates.
4. UI overlay draws whatever coordinates it receives without correction.
5. Search requires at least 2 query characters.
6. Fuzzy search filters out low-height OCR noise indirectly through `confidence`.
7. Semantic search may legitimately produce no results without breaking the app.
8. Uniseba should avoid OCRing its own windows.

If any of these invariants break, symptoms spread across multiple layers.

---

## Current Technical Risks

## 1. Dual Runtime Paths

There are two partially overlapping app models:

- standalone UI-driven OCR in `ui/searchbar.py`
- integrated thread-driven OCR in `main.py`

This increases maintenance cost and can cause behavioral drift.

## 2. Two Hybrid Implementations

Both `search/hybrid.py` and `main.py` merge fuzzy and semantic results.

They are similar but not identical, so search behavior is not fully centralized.

## 3. Silent Semantic Disablement

If the embedding model is not cached locally, semantic reranking disappears quietly.

That is graceful operationally, but easy to misunderstand during testing.

## 4. Stale Region Cache Possibility

The OCR thread caches per-region OCR results. If a real visual change is missed by region diff, stale OCR data can remain in the merged index.

## 5. Stabilization Heuristics

The stabilization step uses word text and nearest position, which can mis-handle repeated same-word content.

## 6. Configuration Drift

Behavior is scattered across defaults in several modules because `config.py` is empty.

## 7. Overlay Click-Through Not Fully Active

The helper exists, but true click-through styles are not applied because `_apply_click_through()` is currently commented out.

## 8. Bootstrap vs Normal Target Rules

The first valid target is chosen under looser rules than later targets, which is intentional but adds complexity when debugging startup behavior.

---

## Where To Look For Specific Problems

If the problem is "wrong app content is being searched":

- inspect `threads/ocr_thread.py`
- especially `_update_target_window()`, `_is_bootstrap_target()`, `_is_valid_target()`

If the problem is "highlights are offset":

- inspect `threads/ocr_thread.py`
- especially `_build_partial_index()`
- then inspect `ocr/engine.py` preprocessing assumptions

If the problem is "search finds weird junk":

- inspect `ocr/index.py`
- inspect `search/fuzzy.py`

If the problem is "AI toggle seems to do nothing":

- inspect `search/semantic.py`
- confirm the MiniLM model exists locally

If the problem is "overlay is visible but awkward":

- inspect `ui/overlay.py`
- especially the click-through helper and alpha/transparent-color behavior

If the problem is "UI feels laggy or too eager":

- inspect:
  - `threads/ocr_thread.py` scan interval
  - OCR debounce
  - change threshold
  - forced OCR interval
  - `main.py` polling interval

---

## Best Reading Order For The Whole Codebase

If you want to understand the real runtime in the best order, read:

1. `main.py`
2. `threads/ocr_thread.py`
3. `ocr/engine.py`
4. `ocr/index.py`
5. `capture/change.py`
6. `search/fuzzy.py`
7. `search/semantic.py`
8. `ui/searchbar.py`
9. `ui/overlay.py`
10. `threads/search_thread.py`
11. `ui/tray.py`
12. `capture/screen.py`
13. `search/hybrid.py`

That order follows the integrated runtime first, then the older/auxiliary paths.

---

## Final Assessment

Uniseba is not just a prototype sketch. It is a working Windows OCR overlay system with:

- active window capture
- OCR extraction
- searchable normalized text index
- background worker orchestration
- fuzzy search
- optional semantic reranking
- overlay-based result highlighting
- tray and hotkey integration

Its strongest engineering idea is the separation between:

- OCR production in a worker thread
- UI-driven search and display

Its most fragile engineering area is the OCR worker, because that file mixes:

- target policy
- capture policy
- change policy
- coordinate mapping
- cache reuse
- stabilization heuristics

If you want one sentence that best describes the codebase today, it is this:

Uniseba is a queue-driven Windows OCR search overlay whose correctness depends primarily on `threads/ocr_thread.py` producing stable, accurate absolute coordinates for the intended target window.
