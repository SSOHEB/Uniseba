# Uniseba Visual Layout Document

## Purpose

This document shows where the current runtime components sit relative to each other.

It reflects the current codebase:

- EasyOCR backend
- full-window OCR safe mode
- fuzzy-first search
- overlay rendering from final coordinates

---

## Core Runtime Flow

```text
[Foreground Content Window]
           |
           v
[Client-Area Capture]
           |
           v
[Full-Window EasyOCR]
           |
           v
[OCR Index Normalization]
           |
           v
[index_queue]
           |
           v
[UI / Searchbar]
   |                 \
   |                  \
   v                   v
[Fuzzy Search]   [semantic_request_queue]
   |                      |
   |                      v
   |               [Semantic Thread]
   |                      |
   |                      v
   |               [Semantic Search]
   |                      |
   |                      v
   |               [semantic_result_queue]
   |                      |
   \______________________/
              |
              v
        [Merged Results]
              |
              v
          [Overlay]
```

---

## Ownership View

```text
WINDOWS / USER
--------------
[Target App Window]

WORKER SIDE
-----------
[threads/ocr_thread.py]
  -> select target
  -> capture client area
  -> run full-window OCR
  -> build OCR index
  -> publish index_queue

[threads/search_thread.py]
  -> receive semantic requests
  -> run semantic search
  -> publish semantic results

UI / MAIN THREAD SIDE
---------------------
[main.py + IntegratedSearchbarApp]
  -> poll OCR index
  -> run fuzzy search
  -> request semantic rerank
  -> merge results
  -> draw overlay

DISPLAY SIDE
------------
[ui/overlay.py]
  -> draw rectangles in final screen coordinates
```

---

## Spatial UI Relationship

```text
[Searchbar]
    |
    | query / control
    v
[Search Logic] -----------------> [Overlay]
                                      |
                                      | drawn on top of
                                      v
                               [Target App Window]
```

Meaning:

- the target app window is the thing being searched
- the searchbar is the control surface
- the overlay is the downstream visual layer

---

## Thread Placement

```text
                  [Main UI Thread]
                         |
        -----------------------------------------
        |                                       |
        v                                       v
[OCR Worker Thread]                    [Semantic Worker Thread]
        |                                       |
        v                                       v
 [index_queue]                         [semantic_result_queue]
        \                                       /
         \                                     /
          \___________[UI / Searchbar]________/
                          |
                          v
                      [Overlay]
```

---

## File Flow

```text
[main.py]
    |
    +--> [threads/ocr_thread.py]
    |         |
    |         +--> [capture/change.py]
    |         +--> [ocr/engine.py]
    |         +--> [ocr/index.py]
    |
    +--> [threads/search_thread.py]
    |         |
    |         +--> [search/semantic.py]
    |
    +--> [ui/searchbar.py]
    |         |
    |         +--> [search/fuzzy.py]
    |         +--> [ui/overlay.py]
    |
    +--> [ui/tray.py]
```

---

## Current Practical Summary

```text
[Target Window]
      |
      v
[OCR Thread]
  Target -> Client Capture -> Full OCR -> Index
      |
      v
[index_queue]
      |
      v
[UI/Searchbar]
  Fuzzy Search + Semantic Request
      |
      +--> [Semantic Thread] -> [semantic_result_queue]
      |
      v
[Merged Results]
      |
      v
[Overlay]
```
