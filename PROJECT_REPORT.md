# Uniseba Project Report

## 1. Project Overview

`uniseba` is a Windows desktop OCR-and-search project built in phases.

The high-level idea is:

1. Capture the currently active window on screen.
2. Run OCR on that captured image.
3. Convert OCR results into a searchable in-memory index.
4. Search that index using both typo-tolerant matching and semantic similarity.
5. Later phases can connect this backend to UI, background threads, overlays, shortcuts, and tray behavior.

At the current point in the repo, the implemented work covers:

- Phase 1: environment setup and foreground window screenshot test
- Phase 2: capture + OCR backend
- Phase 3: hybrid search backend

The UI, thread orchestration, tray integration, overlay rendering, and higher-level app behavior are not implemented yet in this workspace.

## 2. Current Folder Purpose

- `capture/`
  Stores image acquisition logic and frame-change detection logic.
- `ocr/`
  Stores OCR execution and OCR result normalization/indexing.
- `search/`
  Stores fuzzy, semantic, and hybrid search logic.
- `threads/`
  Reserved for later background worker logic.
- `ui/`
  Reserved for later interface components.
- `assets/`
  Reserved for static resources.
- `main.py`
  A simple Phase 1 test script for foreground-window capture.
- `config.py`
  Present but currently empty in this repo snapshot.
- `requirements.txt`
  Lists Python packages required by the project.
- `.gitignore`
  Excludes virtual environments, cache files, logs, IDE files, and build artifacts.

## 3. Environment and Dependency Choices

The working environment you described is:

- Windows
- Python `3.11.9` in `venv311`

The major installed packages and why they matter:

- `mss`
  Used for fast screen capture.
- `winrt-Windows.Media.Ocr`
  Used to access Windows OCR APIs.
- `rapidfuzz`
  Used for typo-tolerant fuzzy search.
- `sentence-transformers`
  Used for embedding-based semantic search.
- `numpy`
  Used here for pixel-diff calculation and numerical operations.
- `Pillow`
  Used for image conversion, resizing, and saving.
- `pywin32`
  Used for active-window detection through `win32gui`.
- `torch`
  Backend dependency used by `sentence-transformers`.
- `transformers`
  Supports the semantic model stack.
- `nuitka`
  Planned later for packaging/building.

Some dependencies such as `customtkinter`, `keyboard`, `pystray`, and `psutil` are installed but are mainly for later phases, not the currently implemented backend flow.

## 4. Phase 1: Foreground Window Capture Test

### Goal

Prove that the app can correctly capture only the active window, not the full screen.

### File

- `main.py`

### What it does

`main.py`:

1. Sets Windows DPI awareness immediately.
2. Reads the foreground window handle using `win32gui.GetForegroundWindow()`.
3. Reads the active window rectangle using `win32gui.GetWindowRect()`.
4. Captures that exact rectangle using `mss`.
5. Converts the raw capture to a PIL image.
6. Saves the result as `test_capture.png`.
7. Prints the rectangle and a success/failure message.

### Why DPI awareness matters

Without DPI awareness, Windows can report scaled coordinates that do not match actual screen pixels. That would cause the capture region to be offset or incorrectly sized. Setting DPI awareness first ensures the bounding box used by `mss` matches the real screen coordinates.

### How Phase 1 relates to later phases

Everything else depends on correct capture. If the image is wrong, OCR will be wrong, and search results will be wrong. So Phase 1 establishes the foundation for the entire project.

## 5. Phase 2: OCR Pipeline Backend

Phase 2 takes the capture idea from `main.py` and turns it into reusable backend modules.

### 5.1 `capture/screen.py`

Purpose:

- reusable foreground-window screenshot function

What it does:

- sets DPI awareness
- gets the foreground window
- gets its absolute screen rectangle
- captures just that rectangle with `mss`
- converts the image to PIL
- returns:
  - the image
  - the absolute rectangle dict

Why it exists:

`main.py` is just a test script. `capture/screen.py` makes the same logic reusable by OCR and later background processing.

### 5.2 `capture/change.py`

Purpose:

- basic frame-change detection

What it does:

1. Accepts a previous image and current image.
2. Converts both to grayscale.
3. Shrinks both to small thumbnails.
4. Converts them to NumPy arrays.
5. Computes mean absolute pixel difference.
6. Returns `True` if the difference crosses a threshold.

Why thumbnails are used:

Comparing full-resolution frames is more expensive and unnecessary for simple change detection. Small grayscale thumbnails are enough to detect whether the scene changed meaningfully.

Why this matters:

Later, if the app captures the screen repeatedly, it should avoid rerunning OCR when nothing important changed. This module is the first step toward that optimization.

### 5.3 `ocr/engine.py`

Purpose:

- wrap Windows OCR
- return OCR words with bounding boxes

What it does:

1. Lazily imports WinRT OCR-related modules.
2. Converts a PIL image into a `SoftwareBitmap`, which the Windows OCR engine expects.
3. Creates an English OCR engine using `Language("en-US")`.
4. Runs `recognize_async()` on the bitmap.
5. Iterates through recognized lines and words.
6. Filters tiny bounding boxes using `min_height=8`.
7. Converts relative OCR boxes into absolute screen coordinates by adding the window’s `left` and `top`.
8. Returns a list of word dictionaries:
   - `text`
   - `x`
   - `y`
   - `w`
   - `h`

It also contains a direct test entry point:

- capture active window
- run OCR
- build index
- print recognized words and their boxes

Why async is involved:

Windows OCR uses async WinRT APIs. `asyncio.run()` is used so the test script can still be launched simply from the command line.

### 5.4 `ocr/index.py`

Purpose:

- normalize OCR output into a simple in-memory search index

What it does:

It transforms raw OCR word items into a list of dictionaries with consistent keys:

- `word`
  lowercase version used for searching
- `original`
  original text as recognized
- `x`, `y`, `w`, `h`
  absolute box coordinates and size
- `confidence`
  a simple proxy score currently derived from box height

Why normalization matters:

Search code should not need to know OCR engine internals. By converting OCR output into one stable schema, the search layer can stay simple and independent.

## 6. Phase 3: Hybrid Search Backend

Phase 3 adds search over the OCR index.

The idea is to combine:

- fuzzy string matching for typos and near-exact word matches
- semantic similarity for meaning-based matching

### 6.1 `search/fuzzy.py`

Purpose:

- typo-tolerant OCR word search

What it does:

1. Normalizes the query to lowercase.
2. Rejects very short queries below the minimum length.
3. Extracts candidate words from the OCR index.
4. Uses `rapidfuzz.process.extract()` with `fuzz.WRatio`.
5. Applies score cutoff and result limit.
6. Returns matching index entries with a `fuzzy_score`.

Why fuzzy search matters:

OCR is imperfect and users also mistype. Fuzzy matching helps recover useful results when exact matching would fail.

### 6.2 `search/semantic.py`

Purpose:

- embedding-based similarity search

What it does:

1. Lazily loads the `sentence-transformers` model `all-MiniLM-L6-v2`.
2. Encodes OCR words into embeddings.
3. Caches embeddings for the current OCR index.
4. Encodes the query.
5. Computes cosine similarity.
6. Returns ranked entries with `semantic_score`.

Why lazy loading matters:

Semantic models are heavier than fuzzy matching. Delaying model load avoids slow startup when the feature is not used yet.

### Important current behavior

In this repo snapshot, `semantic.py` uses `local_files_only=True` by default through:

- `SEMANTIC_LOCAL_FILES_ONLY = getattr(config, "SEMANTIC_LOCAL_FILES_ONLY", True)`

This was done so the search test can run even when the environment cannot access Hugging Face to download the model. In that case:

- model loading fails quietly
- semantic results become an empty list
- hybrid search still works using fuzzy results only

So the semantic layer is coded, but whether it actively contributes scores depends on whether the model is already cached locally.

### 6.3 `search/hybrid.py`

Purpose:

- combine fuzzy and semantic results into one ranked output

What it does:

1. Normalizes the query.
2. Runs fuzzy search.
3. Runs semantic search.
4. Deduplicates matches by `(x, y)` coordinate pair.
5. Merges both scores into one entry.
6. Computes:

`final_score = fuzzy_score * 0.4 + semantic_score * 0.6`

7. Sorts by final score descending.
8. Returns the top results.

It also contains a simple sample test index and test queries such as:

- `soheb`
- `succes`
- `name`
- `phase`

### Why deduplicate by coordinates

The same on-screen word can appear in both fuzzy and semantic result sets. Deduplicating by absolute position ensures one screen word becomes one final result entry.

## 7. How the Pieces Connect

This is the backend flow implemented so far:

1. `capture/screen.py`
   captures the foreground window image
2. `capture/change.py`
   can decide whether the frame changed enough to justify rerunning OCR
3. `ocr/engine.py`
   extracts words and bounding boxes from the image
4. `ocr/index.py`
   converts OCR words into a normalized index
5. `search/fuzzy.py`
   searches the index by string similarity
6. `search/semantic.py`
   searches the index by embedding similarity
7. `search/hybrid.py`
   merges the search signals into final ranked results

So the logic chain is:

`screen capture -> OCR -> normalized index -> search results`

That is the core backend pipeline of the project.

## 8. Why Certain Fixes Were Needed During Development

### Replacing `winrt`

The OCR dependency was adjusted to:

- `winrt-Windows.Media.Ocr>=2.0.0`

This aligns the dependency with the Windows OCR API actually needed for the project instead of a generic older `winrt` entry.

### Python version compatibility

An earlier install issue happened because some packages, especially older pinned versions like `numpy==1.26.4`, were not compatible with Python `3.14`. The project moved to Python `3.11.9` in `venv311`, which fits the dependency set much better.

### RapidFuzz API correction

The original search code used `process.extractBests`, but the installed `rapidfuzz==3.6.1` exposes `process.extract`. That was corrected so fuzzy search runs properly.

### Semantic model download fallback

The environment blocked outbound access to Hugging Face, so semantic model loading would fail. A local-only fallback was added so the project can still run tests and keep fuzzy search working in offline or restricted environments.

## 9. What Is Working Right Now

Based on the repo state and the testing you described:

- active window capture works
- coordinates are DPI-correct
- OCR extracts English words with absolute bounding boxes
- OCR index generation works
- fuzzy search works
- hybrid search works
- semantic search code exists
- semantic scoring only becomes active when the MiniLM model is available locally

## 10. What Is Not Implemented Yet

These parts are still placeholders or future-phase work:

- UI
- overlay drawing
- tray behavior
- keyboard shortcuts
- background threads
- full app orchestration
- populated `config.py` constants
- packaging/distribution flow

The current repo is therefore best understood as:

- a tested backend foundation
- not yet a complete end-user application

## 11. Important Files Summary

- `main.py`
  One-file Phase 1 test for saving the active window as `test_capture.png`.
- `capture/screen.py`
  Reusable active-window capture helper.
- `capture/change.py`
  Lightweight frame-difference detector.
- `ocr/engine.py`
  Windows OCR wrapper and console OCR test.
- `ocr/index.py`
  OCR result normalization into searchable dictionaries.
- `search/fuzzy.py`
  RapidFuzz typo-tolerant search.
- `search/semantic.py`
  Sentence-transformers semantic search with local-only fallback.
- `search/hybrid.py`
  Combined search ranking and test harness.
- `requirements.txt`
  Declares the backend/runtime dependencies.
- `.gitignore`
  Prevents noisy, generated, or sensitive files from being committed.

## 12. Simple Mental Model of the Project

If someone asks, “What is Uniseba right now?”, the simplest correct answer is:

Uniseba is currently a Windows-only OCR backend prototype that can capture the active window, extract visible text with bounding boxes, convert that text into a searchable index, and search it using fuzzy and hybrid ranking logic.

## 13. Suggested Reading Order for Understanding the Repo

If you want to understand the code step by step, read it in this order:

1. `main.py`
2. `capture/screen.py`
3. `ocr/engine.py`
4. `ocr/index.py`
5. `search/fuzzy.py`
6. `search/semantic.py`
7. `search/hybrid.py`
8. `capture/change.py`

This order follows the actual data flow from screen pixels to search results.

## 14. Final Notes

This report reflects the current workspace state plus the progress notes you provided during development. If you want, a next step could be a second document focused only on:

- architecture
- data flow diagrams
- file-by-file explanation
- beginner-friendly explanation
- GitHub README format

This file is meant to be the broad “what this project is and how everything relates” reference.
