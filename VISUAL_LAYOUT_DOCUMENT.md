# Uniseba Visual Layout Document

## Runtime Flow Diagram

```text
[Target Content Window]
         |
         v
 [Client-Area Capture]
         |
         v
 [Change Detection]
         |
         +-------------------------------+
         |                               |
         v                               v
 [Scroll Translation Path]      [Region Incremental Path]
         |                               |
         +---------------+---------------+
                         |
                         v
               [Full-Window Fallback OCR]
                         |
                         v
                 [OCR Normalized Index]
                         |
                         v
                     [index_queue]
                         |
                         v
               [IntegratedSearchbarApp]
                         |
          +--------------+---------------+
          |                              |
          v                              v
      [Fuzzy Search]          [semantic_request_queue]
          |                              |
          |                              v
          |                      [SearchThread]
          |                              |
          |                              v
          |                    [semantic_result_queue]
          |                              |
          +--------------+---------------+
                         |
                         v
                   [Result Merge]
                         |
                         v
                [Overlay Highlight Draw]
```

## UI Surfaces

- Floating search window (`ui/searchbar.py`): query input, match count, AI toggle, record, summarize.
- Summary panel (`ui/summary_panel.py`): async summary output.
- Transparent overlay (`ui/overlay.py`): highlight rectangles + click-to-copy.
- System tray (`ui/tray.py`): show/hide and quit controls.

## Thread Layout

```text
[Main/UI Thread]
  - Searchbar + Overlay + merge logic
  - Queue polling

[OCR Worker Thread]
  - Target selection
  - Capture + OCR mode routing
  - index_queue publish

[Semantic Worker Thread]
  - semantic_request_queue consume
  - embedding rerank
  - semantic_result_queue publish
```

## Latest Test Snapshot (2026-03-31)

- OCR benchmark script passed (100% across hit@1/5/10 on 20 queries).
- Raw EasyOCR extraction script passed (88 detections exported).
