# Uniseba Pitch Architecture Pack (HLD + LLD + Jury Q&A)

## 1) Elevator Technical Positioning
Uniseba is a Windows desktop "screen intelligence" system that turns any visible screen text into a live searchable layer, then adds AI summarization and knowledge-graph understanding on top of captured reading context.  
Its primary differentiation is not static document OCR, but real-time overlay search across arbitrary app surfaces (legacy UI, VM/remote screens, image-heavy panes, non-copyable content).

---

## 2) High-Level Design (HLD)

### 2.1 System Goal
- Input: Pixels from currently targeted foreground window.
- Core output: On-screen highlight matches for query in near-real time.
- Extended outputs: Summary and knowledge graph from recorded corpus.

### 2.2 HLD Components
- UI Layer (`main.py`, `ui/*`)
  - Floating search bar, overlay, summary panel, graph panel, tray.
- OCR Runtime Layer (`threads/ocr_thread.py`, `ocr/*`, `capture/*`)
  - Captures target window client area, detects change regions, runs OCR, builds index.
- Search Layer (`search/fuzzy.py`, `search/semantic.py`, `threads/search_thread.py`)
  - Immediate fuzzy retrieval + optional semantic reranking.
- AI Layer (`services/ai_controller.py`, `ai/gemini.py`)
  - Recording orchestration, summarization, knowledge graph generation.
- Messaging Layer (`runtime/messages.py`)
  - Typed message contracts over queues between threads.

### 2.3 Concurrency Model (3 long-lived threads)
- Main UI thread:
  - Tk event loop, queue polling, highlight rendering.
- OCR thread:
  - Capture -> change detect -> OCR mode select -> index publish.
- Semantic thread:
  - Embedding-based rerank request/response.

### 2.4 Data Flow (end-to-end)
1. User presses `Ctrl+Shift+U`.
2. Target HWND locked; overlay shown.
3. OCR thread captures client area and updates index asynchronously.
4. UI thread consumes latest index and runs fuzzy search immediately.
5. Overlay draws absolute-coordinate rectangles.
6. Optional semantic thread returns rerank results; UI merges and redraws.
7. If recording is enabled, corpus accumulates deduplicated phrases.
8. Summary/graph requests run in background and update panels asynchronously.

---

## 3) Low-Level Design (LLD)

### 3.1 Core runtime class
- `IntegratedSearchbarApp` (`main.py`)
  - Responsibilities:
    - App lifecycle, hotkey registration, queue polling cadence.
    - Query application path (phrase clustering, fuzzy search, semantic merge).
    - Overlay redraw de-dup using signatures.
    - OCR target validation and self-window filtering.
  - Key methods:
    - `_handle_global_shortcut`, `_poll_index_queue`, `_apply_search`, `_poll_semantic_results`, `_merge_results`.

### 3.2 AI control extraction
- `AIController` (`services/ai_controller.py`)
  - Responsibilities:
    - Record toggle state, corpus ingestion, summary request, graph request.
    - Summary panel lifecycle ownership.
  - Why extracted:
    - Keeps `main.py` as orchestrator; reduces mixed-concern risk.

### 3.3 OCR LLD details
- `OCRThread` modes:
  - Scroll-strip mode:
    - Estimate translation via phase correlation; shift existing index; OCR only new strip.
  - Incremental region mode:
    - OCR only merged changed rectangles and replace overlapping stale entries.
  - Full-window fallback:
    - OCR full frame with downscale + coordinate remap.
- Change detection:
  - Grid thumbnail diff (`capture/change.py`) with thresholded region activation.
- Coordinate contract:
  - All index boxes normalized to absolute screen coordinates before overlay draw.

### 3.4 Search LLD details
- Fuzzy:
  - RapidFuzz `partial_ratio` + hand-tuned ranking heuristics.
- Phrase clustering:
  - Multi-token spatial clustering before full-query fuzzy fallback.
- Semantic rerank:
  - Sentence-transformers (`all-MiniLM-L6-v2`) on separate thread.
- Merge scoring:
  - `final = phrase_score + fuzzy*FUZZY_WEIGHT + semantic*SEMANTIC_WEIGHT`.

### 3.5 Queue message contracts
- `index_queue`:
  - `OCRRefreshing`, `OCRIndexUpdate`.
- `semantic_request_queue`:
  - `SemanticRequest`.
- `semantic_result_queue`:
  - `SemanticResult`.
- Benefit:
  - Strong decoupling, easier backward compatibility and stale result rejection.

---

## 4) Technology Stack and Versions

## 4.1 Pinned in `requirements.txt`
- `mss==9.0.1`
- `easyocr==1.7.2`
- `groq==0.26.0`
- `python-dotenv==1.1.1`
- `pywebview==5.4`
- `rapidfuzz==3.6.1`
- `sentence-transformers==2.7.0`
- `numpy==1.26.4`
- `opencv-python-headless==4.10.0.84`
- `Pillow==10.3.0`
- `customtkinter==5.2.2`
- `keyboard==0.13.5`
- `pywin32==306`
- `pystray==0.19.5`
- `torch==2.2.2+cu121`
- `torchvision==0.17.2+cu121`
- `transformers==4.40.1`

## 4.2 Currently observed in active `venv311` (important for Q&A honesty)
- `easyocr 1.7.2`
- `rapidfuzz 3.6.1`
- `sentence-transformers 2.7.0`
- `torch 2.2.2+cu121`
- `numpy 1.26.4`
- `mss 9.0.1`
- `pywin32 306`
- `customtkinter 5.2.2`
- `keyboard 0.13.5`
- `pystray 0.19.5`
- `groq 1.1.2`
- `python-dotenv 1.2.2`
- `pywebview 6.1`
- `Pillow 12.1.1`

Note:
- A few runtime package versions are newer than pinned requirement versions in this environment (`groq`, `python-dotenv`, `pywebview`, `Pillow`). This is acceptable for demo, but should be normalized for strict reproducibility.

---

## 5) Performance Snapshot (Latest Apr 4 Log Slice)
- OCR cycle (`total_cycle_ms`): `n=143`, mean `2009.79`, p50 `1413.00`, p90 `4581.00`, p99 `9583.80`.
- OCR core (`ocr_ms`): `n=143`, mean `1870.30`, p50 `1274.10`, p90 `4393.40`.
- Search (`total_search_ms`): `n=179`, mean `4.73`, p50 `3.90`, p90 `8.50`, p99 `22.60`.
- Semantic merge (`merge_ms`): `n=179`, mean `0.07`, p90 `0.10`.

Interpretation for jury:
- Retrieval interaction path (query -> highlight) is low-latency.
- OCR is the dominant latency stage; variable by scene complexity and text density.

---

## 6) Design Tradeoffs (Explicit)

### 6.1 EasyOCR over WinRT OCR
- Why:
  - WinRT namespace/runtime issues blocked reliable cross-environment startup.
  - EasyOCR gave controllable Python-first integration.
- Tradeoff:
  - Heavier ML runtime footprint.
  - More dependency management burden.

### 6.2 Partial/incremental OCR over full-frame-only OCR
- Why:
  - Better interactivity by avoiding full-page OCR on every frame.
- Tradeoff:
  - More heuristics/edge cases (scroll estimation, merge correctness).

### 6.3 Queue-driven async pipeline over synchronous flow
- Why:
  - Prevent UI freeze under OCR/semantic load.
- Tradeoff:
  - Requires stale-result handling and message contract discipline.

### 6.4 Semantic rerank optional toggle
- Why:
  - Fuzzy is fast and robust baseline; semantic improves intent matching.
- Tradeoff:
  - Embedding model availability and cache growth concerns.

### 6.5 Full-window fallback downscale (`~0.75x`)
- Why:
  - Throughput control on dense frames.
- Tradeoff:
  - Can lose very tiny-text fidelity; coordinate remap complexity.

---

## 7) Challenge History and Solutions (Pitch-Relevant)

### 7.1 Initial OCR backend instability (WinRT path)
- Problem:
  - Runtime import/environment mismatch and inconsistent portability.
- Solution:
  - Migrated to EasyOCR-based pipeline with explicit model/runtime control.

### 7.2 Overlay misalignment bugs
- Problem:
  - Coordinate mismatch under partial/full modes (especially with scaling).
- Solution:
  - Enforced absolute coordinate chain and explicit remap in full fallback path.

### 7.3 UI responsiveness under heavy OCR
- Problem:
  - Potential stutter when OCR + search + render compete.
- Solution:
  - Queue decoupling, debounce, deduplicated redraw signatures, background semantic thread.

### 7.4 Self-OCR contamination
- Problem:
  - System OCRing its own search panel created noisy matches.
- Solution:
  - Pre-OCR masking + post-filtering + known self-phrase exclusion.

### 7.5 Large orchestrator complexity
- Problem:
  - `main.py` had mixed concerns.
- Solution:
  - Extracted `AIController` for recording/summarize/graph responsibilities.

---

## 8) Reliability and Known Limits (Answer honestly)
- Current benchmark accuracy claims are controlled-case, not universal.
- OCR quality varies by font size, contrast, motion, and render quality.
- Semantic cache has no explicit eviction policy yet.
- Graph rendering depends on `pywebview` + CDN vis.js availability.
- Packaging/installer hardening is pending for no-Python distribution path.

---

## 9) Likely Jury Questions and Strong Answers

## 9.1 Easy level
Q: What makes this different from Ctrl+F?  
A: Ctrl+F only works inside one document model. Uniseba works on live screen pixels across apps, including text that is not natively searchable.

Q: Why not just use Snipping Tool + OCR?  
A: That is manual and one-off. Uniseba is continuous, searchable in-place, and connected to summary/knowledge graph context.

Q: What are your main metrics?  
A: Latest Apr 4 logs: search mean 4.73 ms (p90 8.50 ms), OCR cycle p50 1413 ms, semantic merge mean 0.07 ms.

## 9.2 Medium level
Q: Why 3-thread architecture?  
A: UI must remain responsive while OCR and semantic work run asynchronously; queues isolate heavy work from Tk event loop.

Q: How do you avoid stale semantic results?  
A: Tokened request/response (`search_token`) and latest-result-only application in UI poller.

Q: How do you handle scroll updates efficiently?  
A: Change-region detection + scroll translation mode + incremental region OCR before full fallback.

## 9.3 Hard level
Q: Why is OCR p90 high while search is low?  
A: Search runs on already-indexed text and is lightweight; OCR is image-model inference and scene-dependent. We optimize perceived responsiveness via incremental updates and async pipelines.

Q: How do you validate correctness beyond demo?  
A: Controlled hit@k benchmark script, log-derived latency analysis, and multi-image cases support for expanded test coverage.

Q: What failure modes are most critical?  
A: Dense/tiny-text scenes, fast visual changes, and model availability edge cases. Mitigations include fallback modes, exclusions, and explicit known limitations.

Q: Why Groq LLM integration and not local-only?  
A: It balances quality and implementation speed for hackathon scope. Core OCR/search remains local; AI outputs are optional enhancement layer.

---

## 10) Strict Pitch Claim Boundaries (Do/Don't)

Do say:
- "Prototype validated with runtime logs and controlled benchmark scripts."
- "Search path is low-latency; OCR remains primary bottleneck and optimization focus."
- "Works on many non-copyable scenarios where native search fails."

Do not say:
- "100% OCR accuracy overall."
- "Production-ready deployment solved."
- "Fully scalable enterprise platform today."

---

## 11) Demo Defense Script (30 seconds)
"Uniseba uses a queue-based 3-thread architecture so UI stays responsive while OCR and semantic reranking run asynchronously. We process screen changes incrementally to reduce OCR workload, keep coordinates in absolute screen space for accurate overlay rendering, and apply fuzzy search immediately with optional semantic rerank. In our latest Apr 4 logs, search response averaged 4.73 ms, while OCR cycle p50 was 1.41 seconds. Our current benchmark is controlled and honest about scope, and we have a clear path to broaden accuracy coverage and packaging hardening."

