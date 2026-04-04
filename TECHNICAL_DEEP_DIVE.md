# TECHNICAL_DEEP_DIVE

## 1. What Uniseba Is
Uniseba is a Windows desktop “search what you see” tool that continuously OCRs the currently selected content window, lets the user query visible text with instant on-screen highlights, and layers optional AI features (summary and knowledge graph) on top of captured reading context. It differs from static screenshot OCR tools because it runs as a live overlay with partial/incremental OCR, scroll-aware updates, and optional semantic reranking, so the experience feels like searching inside the active screen rather than exporting content elsewhere. It is built for students, analysts, and demo/hackathon users who need fast recall of on-screen information without switching applications, and it exists to reduce context-switch friction while reading, scrolling, and cross-referencing dense material.

## 2. System Architecture Overview
When the user presses `Ctrl+Shift+U`, `keyboard` triggers `IntegratedSearchbarApp._handle_global_shortcut` in `main.py`, which locks the last valid foreground content window handle and toggles visibility of the `SearchbarApp` window plus the fullscreen `OverlayWindow`. In parallel, the `OCRThread` is already running: it tracks the target HWND, captures the target client area with `mss`, computes changed regions with `capture.change.get_changed_regions`, chooses an OCR mode (scroll-strip, incremental regions, or full-window fallback), runs OCR through `ocr.engine.recognize_image`, normalizes tokens through `ocr.index.build_ocr_index`, filters self-UI noise, and publishes a fresh index message into `index_queue`. The UI thread polls `index_queue` every `POLL_MS`, updates `current_index`, and when the query length reaches `MIN_QUERY_LENGTH`, runs fuzzy search immediately (`search.fuzzy.fuzzy_search`), optionally builds phrase clusters, filters out self-UI overlap, and draws highlight rectangles at absolute coordinates through `ui.overlay.OverlayWindow.draw_matches`. If AI reranking is enabled, the same query and index are posted into `semantic_request_queue`, `SearchThread` computes embedding similarity with `search.semantic.semantic_search`, and merged results are pulled from `semantic_result_queue` and redrawn. The visible result is a non-blocking cycle where OCR, ranking, and highlighting happen asynchronously while the Tk mainloop stays responsive.

## 3. Every File Explained

### `main.py`
This file owns runtime orchestration: app lifecycle, hotkey behavior, queue polling, record/summarize/graph actions, fuzzy+phrase+semantic search flow, and worker startup/shutdown. It does not own low-level OCR extraction, fuzzy scoring internals, semantic embedding math, or UI widget base definitions; those belong to other modules. It talks to `ui/searchbar.py` by subclassing `SearchbarApp`, to `ui/summary_panel.py` and `ui/graph_panel.py` for AI outputs, to `threads/ocr_thread.py` and `threads/search_thread.py` via queues/events, and to `ai/gemini.py` for LLM calls. Key design choices include queue-driven non-blocking UI, deduplicated ordered corpus capture, phrase-aware matching before full-query fuzzy ranking, and explicit self-UI exclusion before draw. Technical debt includes growing class size, mixed concerns (UI control + search policy + AI control), and some encoding artifacts in status strings.

### `config.py`
This file owns all tunable constants for timing, thresholds, weights, target filtering, and UI-exclusion behavior. It does not own execution logic. It is imported by almost every runtime file as the single source of defaults. The main design decision is centralized explicit constants rather than local fallbacks. Technical debt: some constants are currently unused in live paths (`OCR_DOWNSCALE`, `OCR_STABILITY_COUNT_THRESHOLD`) and can confuse new maintainers unless documented.

### `ai/gemini.py`
This file owns Groq client lifecycle and LLM prompt calls for `summarize_screen_text` and `build_knowledge_graph`. It does not own threading, UI updates, or graph rendering. It talks to `main.py` through pure function calls and depends on `.env` (`GROQ_API_KEY`) plus `python-dotenv` and `groq`. Design decisions: singleton client reuse for lower overhead, explicit JSON-only graph prompt, short timeout (`with_options(timeout=25)`) for graph generation, and preprocessing that removes short uppercase status tokens before graph extraction. Limitations: API key is loaded once per process, network timeouts surface as user text errors, and JSON parsing is strict (model formatting drift can fail).

### `capture/change.py`
This file owns region-based frame-diff detection by dividing frames into a fixed grid and comparing grayscale thumbnails. It does not own capture, OCR, or indexing. It is used by `threads/ocr_thread.py` to decide when/where OCR should run. The design favors cheap mean absolute grayscale diff over expensive pixel-perfect diff. Limitation: grid granularity can miss tiny isolated changes or over-trigger on animated areas.

### `capture/screen.py`
This file owns a simple active-window capture helper used by OCR test paths. It does not own target filtering or incremental capture policy. It talks to `mss`, PIL, and Win32 APIs. Design choice: minimal utility for standalone tests. Limitation: captures full window bounds in this helper, while production OCR thread uses client-area capture logic, so behavior differs from live pipeline.

### `capture/__init__.py`
This package file is empty and owns no runtime behavior. It only marks the package namespace.

### `ocr/engine.py`
This file owns EasyOCR integration and conversion from OCR polygons to axis-aligned word boxes in absolute coordinates. It does not own change detection, index merging, or search. It talks to `easyocr`, `torch`, PIL/NumPy, and `ocr/index.py` for its local test runner. Design choices include lazy reader initialization on first OCR call, GPU auto-detection, local model cache directory (`models/easyocr`), and selective upscale only for genuinely small images. Limitations: first OCR call may incur one-time model load delay, and confidence filtering is basic.

### `ocr/index.py`
This file owns text normalization and heuristics that convert raw OCR words into searchable entries (`word`, `original`, coordinates, proxy confidence). It does not own OCR itself or ranking. It is called by `ocr/engine.py` and `threads/ocr_thread.py`. Design choices include filtering obvious OCR/UI noise, dropping low-value one-character tokens, and splitting long multi-word detections into per-word entries. Limitation: proxy confidence is geometric (height-based), not OCR-native probability.

### `ocr/__init__.py`
This package file is empty and owns no runtime behavior.

### `search/fuzzy.py`
This file owns fuzzy matching with RapidFuzz plus ranking heuristics and noise filtering. It does not own OCR index creation or overlay rendering. It is called from `main.py`. Design decisions include `fuzz.partial_ratio`, stopword down-ranking, length mismatch penalties, and containment checks to reduce false positives. Limitation: heuristics are hand-tuned and may need domain-specific retuning.

### `search/semantic.py`
This file owns optional embedding-based semantic reranking with sentence-transformers (`all-MiniLM-L6-v2`) and index embedding caching. It does not own UI toggles or score fusion policy. It is called by `threads/search_thread.py`. Design choices: lazy model load, local-files-only mode by default, and graceful degradation (return empty if model unavailable). Limitations: cache can grow with many unique OCR indexes and no eviction policy is implemented.

### `search/hybrid.py`
This file owns an older direct hybrid helper combining fuzzy + semantic in one function. It does not own the active runtime path anymore. It talks to `search.fuzzy` and `search.semantic`. Design choice: keep a simple utility composition. Limitation: currently dead for live flow (main flow now merges in `main.py`), so it can drift.

### `search/__init__.py`
This package file is empty and owns no runtime behavior.

### `threads/ocr_thread.py`
This file owns continuous capture, target selection, change detection, OCR mode selection, index publish timing, and OCR-side self-UI filtering. It does not own query handling or overlay drawing. It talks to `capture/change.py`, `ocr/engine.py`, `ocr/index.py`, and `main.py` via `index_queue`. Important design decisions include client-area capture, partial OCR by changed regions, scroll translation estimation by phase correlation, full fallback with downscale + coordinate remap, and queue messages for “refreshing” vs “index.” Limitations include heuristic thresholds, one large class, and currently bypassed stabilization logic.

### `threads/search_thread.py`
This file owns asynchronous semantic reranking requests. It does not own fuzzy search, result merge policy, or UI. It consumes `semantic_request_queue` and produces `semantic_result_queue`. Design choice: keep semantic computation off UI thread with short blocking queue reads (`timeout=0.2`). Limitation: no backpressure/coalescing beyond token overwrite behavior in UI.

### `threads/__init__.py`
This package file is empty and owns no runtime behavior.

### `ui/searchbar.py`
This file owns the base floating search window and control widgets (entry, labels, AI switch, Record/Summarize/Graph buttons), plus show/hide coordination with overlay. It does not own OCR/search orchestration or AI logic; subclass hooks handle that. It talks to `ui/overlay.py` and is subclassed by `main.py`. Design choices include `customtkinter`, debounced key handling, and fixed geometry. Limitation: debug `print` statements remain in `_on_query_changed`.

### `ui/overlay.py`
This file owns the transparent fullscreen highlight layer, hit-testing, click-to-copy, and flash feedback. It does not own search ranking or OCR. It receives match rectangles from `main.py`. Design choices: transparent-color fullscreen top-level, canvas rectangles at absolute coordinates, and clipboard copy on click. Limitation: behavior is Windows-specific due transparency and clipboard APIs.

### `ui/summary_panel.py`
This file owns the summary/intelligence toplevel UI panel and text display lifecycle (`show_loading`, `show_summary`, `set_text`). It does not own summarization/graph generation logic itself. It is used by `main.py`. Design choices: plain Tk `Toplevel` (not CTk), centered fixed-size dark panel, topmost + withdraw/deiconify workflow. Limitation: if widget lifecycle and callback ordering drift, stale widget references can trigger Tk command errors.

### `ui/tray.py`
This file owns tray icon setup and show/hide/quit callbacks via `pystray`. It does not own app shutdown internals. It talks to `main.py` through injected callbacks. Design choice: run tray event loop on its own daemon thread. Limitation: tray behavior can vary by Windows shell/session.

### `ui/graph_panel.py`
This file owns knowledge-graph HTML generation and pywebview launch mechanics. It does not own graph extraction quality or corpus capture. It is called by `main.py`. Design choices: self-contained temp HTML, vis.js from CDN, immediate window open, and pywebview started in a separate Python subprocess to satisfy main-thread constraints. Limitations: depends on `webview` package availability and external CDN reachability.

### `ui/__init__.py`
This package file is empty and owns no runtime behavior.

### `ocr_accuracy_test.py`
This file owns OCR/search benchmark execution and report generation. It supports a default single-image run (`test_crop.png`) and multi-image runs via a JSON cases file (`--cases-file`) with per-image query expectations, then emits markdown reports (for example `ocr_accuracy_report.md` and `ocr_accuracy_report.dataset_real.md`). It does not own runtime UI logic. It talks to `ocr.engine`, `ocr.index`, and `search.fuzzy`. Design choice: practical retrieval benchmark (hit@1/5/10) that is easy to extend quickly for hackathon validation across real screenshots. Limitation: when cases are auto-generated from OCR-visible tokens, results are retrieval-oriented and not equivalent to full ground-truth CER/word-accuracy validation.

### `ocr_easyocr_test.py`
This file owns direct EasyOCR smoke testing and raw dump generation to `ocr_test_output.txt`. It does not own indexing/ranking behavior. It talks directly to `easyocr`. Design choice: isolate OCR engine behavior from app logic. Limitation: hardcoded GPU=True and single input path.

### `analyze_ocr_log.py`
This file owns log parsing and performance summarization for OCR cycles and scroll estimates. It does not own runtime capture/search. It talks only to log files. Design choices: regex extraction + percentile stats with simple CLI flags (`--tail`). Limitation: parser is format-coupled to specific log line templates.

### `ai/__init__.py`
There is no `ai/__init__.py` in this codebase. The package still resolves because Python namespace package rules allow it in this layout.

## 4. The OCR Pipeline In Depth
The production OCR pipeline is centered in `threads/ocr_thread.py`. Each cycle starts with target tracking (`_update_target_window`) and client-area capture (`_capture_target_window`), not full outer window bounds. The captured frame is optionally masked where Uniseba’s own floating UI overlaps content, preventing recursive OCR contamination. Change detection (`capture.change.get_changed_regions`) compares previous and current frames on a `CHANGE_GRID` and returns coarse changed rectangles. If nothing changed and forced-refresh interval has not elapsed, OCR is skipped entirely.

Mode selection has three paths. The first path is scroll-strip mode (`_maybe_build_scroll_index` → `_build_scroll_index`), activated when changes look large, phase-correlation confidence is acceptable, horizontal drift is small, and vertical shift is meaningful. In that mode, the previous stable index is translated by `(dx, dy)`, and only the newly revealed top/bottom strip is OCRed and merged. The second path is incremental region mode (`_build_incremental_index`), used when partial OCR is enabled, changes are not major, and a previous stable index exists; changed rectangles are merged/padded, only those crops are OCRed, and overlapping stale entries are replaced. The third path is full-window fallback (`_build_full_index`) used when partial criteria are not met, when changed-area coverage is too large, or when no stable baseline exists.

The coordinate ownership chain is strict: `mss` captures pixels for a client-area rect in absolute screen coordinates; OCR runs either on full downscaled image or local crops; OCR output boxes are normalized in `ocr.engine.recognize_image` and offset by crop/window origin; full-window mode rescales boxes back from `0.75x` to original size and then offsets by rect origin; merged index entries are absolute screen-space boxes; `main.py` passes those unchanged to `ui.overlay.OverlayWindow`, which draws rectangles directly on a fullscreen transparent canvas. Earlier bugs came from violating this chain (downscaling crops without coordinate compensation), causing shrunken/misaligned highlight boxes. The current code explicitly warns against downscaling partial crops unless coordinates are remapped.

The `0.75x` downscale decision is a throughput tradeoff in full-window fallback: fewer pixels means lower OCR latency and better responsiveness during large updates, but tiny text can lose fidelity. The code accepts that tradeoff and compensates coordinates back to full resolution so overlays remain correctly positioned.

## 5. The Search Pipeline In Depth
Search starts in `main.py::_apply_search`. Query strings shorter than `MIN_QUERY_LENGTH` are ignored. For fuzzy ranking, `search.fuzzy.fuzzy_search` uses RapidFuzz `fuzz.partial_ratio`, where `FUZZY_THRESHOLD=85` means candidates below 85/100 similarity are excluded before ranking. In practice, this keeps approximate substring matches while dropping weaker noise; the module then applies heuristics (exact-match bonus, containment behavior, stopword penalties, length penalties) to improve ordering.

Multi-word queries are handled by phrase clustering in `main.py::_build_phrase_results`. The query is tokenized, each token is searched independently, and seed matches are expanded by spatial proximity (`PHRASE_VERTICAL_THRESHOLD`, `PHRASE_HORIZONTAL_THRESHOLD`) so terms likely belonging to the same local phrase cluster are grouped. Phrase hits are tagged with `phrase_score=1.0` and merged before regular full-query fuzzy results to surface coherent multi-word context first.

Semantic reranking is optional behind the AI toggle. `threads/search_thread.py` calls `search.semantic.semantic_search`, which embeds the query and OCR tokens using `all-MiniLM-L6-v2` and cosine similarity. If the model is unavailable locally (`SEMANTIC_LOCAL_FILES_ONLY=True`), semantic returns empty and fuzzy-only behavior continues. In `main.py::_merge_results`, each entry gets `final_score = phrase_score + fuzzy_score*FUZZY_WEIGHT + semantic_score*SEMANTIC_WEIGHT`, then top results are redrawn.

There are two skip gates to reduce redundant work: one prevents rerunning search when query and index version are unchanged, and another avoids redraw when query/signature/index version are unchanged. This avoids repeated fuzzy/overlay churn during high-frequency polling.

## 6. The Recording And AI Features
Recording is managed in `main.py` with `self._is_recording`, `self._corpus` (ordered list), and `self._corpus_seen` (dedupe set). During each OCR poll, each new phrase (`item["original"]`) is appended once in insertion order. This preserves readable phrase chronology while preventing duplicates. Summarization joins corpus phrases in order, shows loading, then calls `ai.gemini.summarize_screen_text` on a background thread, with UI updates marshaled back via `self.after`.

The capture stability indicator uses `_stable_poll_count` and `_last_corpus_size`. If corpus size stays unchanged for consecutive polls, stability count rises; at count `>=3`, the UI reports “captured, scroll now,” signaling the current viewport has likely been fully absorbed and user should move onward. If corpus is still growing, the label remains in capturing mode with phrase count. This prevents users from scrolling before capture settles and missing content.

Knowledge graph generation now uses captured corpus text, not the search query as input text. `build_knowledge_graph` preprocesses text by dropping short uppercase status-like tokens, applies a stricter prompt demanding JSON-only graph output with a central concept and descriptive edge labels, and parses the result into a Python dict. `main.py::_on_graph_clicked` opens a quick placeholder graph window immediately for responsiveness, then asynchronously replaces it with the generated graph when the model returns. `ui/graph_panel.py` renders the graph via vis.js inside temp-file HTML displayed in pywebview.

## 7. The Overlay System
The overlay is a fullscreen transparent Tk `Toplevel` (`ui/overlay.py`) configured as topmost, borderless, and keyed to a transparent background color. OCR results are already in absolute screen coordinates, so drawing is direct: each match maps to a rectangle on the canvas. This simplicity is intentional; if any upstream coordinate conversion is wrong, highlights visibly drift or resize incorrectly.

Self-UI exclusion exists to prevent Uniseba from OCRing and highlighting its own controls. On the OCR side, overlapping regions are blacked out before recognition and filtered again post-index; on the search/display side, results overlapping search UI rects or containing known self phrases are dropped. Click-to-copy behavior is implemented by hit-testing clicked rectangles, copying `original` text into the Windows clipboard, and flashing the border for feedback.

## 8. Threading Model
Uniseba has three long-lived threads. The main UI thread runs Tk (`SearchbarApp` + `OverlayWindow` + `SummaryPanel`), processes user events, polls queues with `after`, and performs drawing. The OCR worker thread (`OCRThread`) captures frames, computes OCR indexes, and publishes messages to `index_queue`. The semantic worker thread (`SearchThread`) consumes semantic requests and publishes rerank results.

`index_queue` carries OCR-side messages. Producer: OCR thread. Consumer: UI thread (`_poll_index_queue`). Message shapes: `{"type":"refreshing","changed_regions":...,"total_regions":...}` and `{"type":"index","index":[...]}` (plus backward-compatible raw list handling). `semantic_request_queue` carries `{"token","query","index","limit"}` from UI thread to semantic thread. `semantic_result_queue` carries `{"token","results"}` from semantic thread back to UI thread. Tokening ensures stale semantic results are ignored. UI non-blocking behavior is preserved because long work (OCR, embeddings, network LLM calls) never runs on the Tk event loop.

## 9. Configuration System
`config.py` controls runtime behavior globally. `DEBOUNCE_MS` governs keypress wait before search; lowering makes typing more reactive but noisier. `POLL_MS` sets queue poll cadence; lower values feel faster but increase CPU wakeups. `GLOBAL_SHORTCUT` defines activation hotkey. `MAX_RESULTS` caps result set size and draw cost.

Search sensitivity is driven by `MIN_QUERY_LENGTH`, `FUZZY_THRESHOLD`, `MIN_WORD_LENGTH`, and `MIN_CONFIDENCE`. Lower thresholds increase recall but add noise. `FUZZY_WEIGHT` and `SEMANTIC_WEIGHT` tune merged ranking influence. Semantic model options are `SEMANTIC_MODEL_NAME` and `SEMANTIC_LOCAL_FILES_ONLY`; enabling remote fetch (by setting local-files-only false) improves first-run availability but adds network dependency.

OCR cadence and scope are controlled by `SCAN_INTERVAL_MS`, `OCR_UPDATE_DEBOUNCE_MS`, and `FORCED_OCR_INTERVAL_MS`. Change detection sensitivity is set by `CHANGE_GRID`, `CHANGE_THRESHOLD`, and `CHANGE_THUMB_SIZE`. Partial OCR behavior depends on `PARTIAL_OCR_ENABLED`, `PARTIAL_OCR_PADDING_PX`, `PARTIAL_OCR_MAX_RECTS`, and `PARTIAL_OCR_MAX_AREA_RATIO`; stricter caps trigger full fallback sooner. `MAJOR_CHANGE_REGION_COUNT` and `MAJOR_CHANGE_REGION_RATIO` decide when UI should show refreshing state. Window targeting and self-filtering depend on minimum target geometry/title constants, blocked window sets/prefixes, console keywords, and self-UI exclusion constants (`SEARCH_UI_EXCLUSION_PADDING`, `SELF_UI_PHRASES`). `OCR_DOWNSCALE` exists as config intent but full fallback currently uses a local `DOWNSCALE = 0.75` constant in `ocr_thread.py`.

## 10. Key Engineering Decisions And Why
EasyOCR was chosen over WinRT OCR because the runtime environment repeatedly failed on missing WinRT namespaces (`winrt.windows.globalization`), while EasyOCR is cross-environment and already integrated in Python. Client-area capture was chosen instead of full window bounds to avoid title bars/chrome and keep coordinates aligned with visible content where highlights should appear. A 0.75 full-frame downscale was chosen to keep worst-case OCR latency manageable; it sacrifices some tiny-text accuracy but preserves interactivity.

Stabilization smoothing is currently bypassed (`_stabilize_index` returns newest frame) because previous smoothing logic risked hiding fresh updates and harming perceived responsiveness; correctness now favors latest frame. The early skip gate in search was added to prevent redundant fuzzy/overlay recomputation under high-frequency polls where query/index content did not materially change. Corpus storage uses ordered list plus dedupe set instead of a set alone so summaries/graphs preserve reading order while still avoiding repeated phrases.

Pywebview was selected instead of opening a browser tab to keep graph visualization in an app-owned desktop window with predictable size and topmost behavior. Because pywebview requires main-thread startup in a process, the implementation launches a separate Python subprocess for reliability. Groq is used instead of Gemini in current code despite module naming; the stack uses Groq’s chat completions with `llama-3.3-70b-versatile` for both summarization and graph extraction.

## 11. Known Limitations And Technical Debt
The project is functional but not production-hardened. The central orchestrator class in `main.py` is large and mixes concerns. Some modules retain dead or legacy paths (`search/hybrid.py`, unused helper methods/fields in OCR thread). Dependency versions may drift between local environments and pinned `requirements.txt`, which can affect strict reproducibility across machines.

LLM outputs are parsed optimistically; malformed JSON returns a user error string but no repair pass is attempted. Semantic embedding cache has no eviction and can grow over long sessions with many unique OCR indexes. OCR heuristics are tuned for responsiveness and can miss very small text or noisy regions. There are no formal unit/integration test suites; validation is primarily script-based and manual. UI status strings show encoding artifacts in some consoles/log contexts. CDN dependency for vis.js introduces network fragility for graph rendering in offline-restricted environments.

## 12. How To Run And Test
Create and use the Python 3.11 virtual environment in this repo:

```powershell
cd C:\Users\ssohe\Desktop\uniseba
.\venv311\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the app:

```powershell
python main.py
```

Key manual flow to verify:
1. Press `Ctrl+Shift+U` to open overlay/search.
2. Click `Record`, scroll content, wait for capture indicator.
3. Click `Summarize` and verify summary panel updates.
4. Click `Graph` and verify graph window opens and updates.
5. Type search terms and verify highlights/click-to-copy.

Run OCR and analysis scripts:

```powershell
python ocr_easyocr_test.py
python ocr_accuracy_test.py --report ocr_accuracy_report.md
python ocr_accuracy_test.py --cases-file ocr_accuracy_cases.sample.json --report ocr_accuracy_report.md
python analyze_ocr_log.py uniseba.log
python analyze_ocr_log.py uniseba.log --tail 2000000
```

## 13. Glossary
OCR: Optical Character Recognition, converting image pixels into text boxes. Fuzzy matching: approximate string matching tolerant of typos/partials. `fuzz.partial_ratio`: RapidFuzz scorer that compares best-matching substring overlap as a 0–100 score. Semantic reranking: embedding-based similarity scoring that complements lexical fuzzy matching. Embedding model: neural model mapping text to vectors (`all-MiniLM-L6-v2`). Incremental OCR: OCR only changed regions and merge into prior index. Scroll-strip OCR: special incremental mode that estimates scroll translation and OCRs only newly revealed strip. Full-window fallback: OCR whole captured frame when partial/scroll paths are not reliable.

Corpus: collected recorded phrases from OCR during a user session. Deduplication set: companion structure used to prevent repeated corpus entries while preserving list order. Overlay: transparent fullscreen canvas used to draw match highlights. HWND: Windows handle identifying a window. Client area: drawable content area of a window excluding title bar and frame. Phase correlation: frequency-domain method to estimate translational shift between two images, used here for scroll detection. Queue polling: periodic UI-thread checks of worker-produced messages without blocking event handling. Debounce: delaying action briefly after input to avoid running logic on every keystroke. Topmost window: window flag keeping a panel above normal windows. Self-UI exclusion: filtering/masking to stop Uniseba from OCRing or matching its own controls.
