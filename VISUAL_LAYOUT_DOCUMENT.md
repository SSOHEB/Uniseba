# Uniseba Visual Layout Document

## Purpose

This document explains how the major runtime components are arranged conceptually and how data moves between them.

It is not a pixel-perfect UI mockup. It is a structural map meant to answer:

- what sits upstream vs downstream
- which components produce data
- which components consume data
- where threads sit relative to the UI
- where the overlay sits relative to search

---

## Core Runtime Flow

The simplest system picture is:

```text
[Foreground Window]
        |
        v
[Capture]
        |
        v
[Change Detection]
        |
        v
[OCR]
        |
        v
[OCR Index Normalization]
        |
        v
[index_queue]
        |
        v
[UI / Searchbar]
   |            \
   |             \
   v              v
[Fuzzy Search]   [semantic_request_queue]
   |                    |
   |                    v
   |             [Semantic Thread]
   |                    |
   |                    v
   |             [Semantic Search]
   |                    |
   |                    v
   |             [semantic_result_queue]
   |                    |
   \____________________/
            |
            v
      [Merged Results]
            |
            v
        [Overlay]
```

---

## Runtime Ownership Map

The same flow grouped by ownership:

```text
USER / WINDOWS
--------------
[Target App Window]

WORKER THREAD SIDE
------------------
[threads/ocr_thread.py]
    -> capture target window
    -> detect changed regions
    -> OCR changed regions
    -> build normalized index
    -> publish index_queue

[threads/search_thread.py]
    -> receive semantic requests
    -> run semantic search
    -> publish semantic_result_queue

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

## Left-To-Right Pipeline View

If you want one straight pipeline for a refinery diagram, use this:

```text
[Target Window] -> [Capture] -> [Change Detection] -> [OCR] -> [Index]
                                                         |
                                                         v
                                                     [index_queue]
                                                         |
                                                         v
                                                  [UI / Searchbar]
                                                     /         \
                                                    v           v
                                           [Fuzzy Search]   [Semantic Request]
                                                    \           |
                                                     \          v
                                                      -> [Semantic Thread]
                                                             |
                                                             v
                                                      [Semantic Result]
                                                             |
                                                             v
                                                       [Result Merge]
                                                             |
                                                             v
                                                         [Overlay]
```

---

## Vertical Stack View

If you prefer a top-to-bottom diagram:

```text
TOP: USER'S REAL APP WINDOW
    [Chrome / VS Code / Notepad / etc.]

OCR LAYER
    [Target selection]
    [Window capture]
    [Change detection]
    [OCR]
    [Index normalization]

QUEUE LAYER
    [index_queue]
    [semantic_request_queue]
    [semantic_result_queue]

SEARCH/UI LAYER
    [Searchbar window]
    [Immediate fuzzy search]
    [Optional semantic rerank]
    [Result merge]

VISUAL OUTPUT LAYER
    [Fullscreen overlay rectangles]
```

---

## Spatial Relationship Of UI Components

There are three visible UI-adjacent pieces:

### 1. Target app window

This is the real application being searched.

- It exists outside Uniseba.
- OCR captures this window.
- Overlay rectangles are drawn over this window's content.

### 2. Searchbar window

This is the Uniseba control surface.

- created by `ui/searchbar.py`
- small floating window
- topmost
- contains:
  - text entry
  - result count label
  - AI toggle

It is conceptually above the target app in control terms, but not in the data pipeline.

### 3. Overlay window

This is the visual highlight layer.

- fullscreen
- transparent background
- topmost
- draws rectangles over the target app window

It is downstream from search, not upstream from OCR.

Simple view:

```text
[Searchbar]
    |
    | controls / queries
    v
[Search Logic] -----------------> [Overlay]
                                      |
                                      | draws on top of
                                      v
                               [Target App Window]
```

---

## Where Threads Sit

The OCR and semantic workers are not visually on screen, but architecturally they sit beside the UI, not inside it.

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

Meaning:

- OCR work happens off the UI thread
- semantic work happens off the UI thread
- queue polling and overlay drawing happen on the UI thread

---

## Physical Flow By File

This is the practical file-to-file layout:

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

## Practical Layout Summary

For a quick refinery or node graph, the best compressed version is:

```text
[Target Window]
      |
      v
[OCR Thread]
  Capture -> Change Detection -> OCR -> Index
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

If you need just one sentence:

Uniseba is laid out as a background OCR pipeline feeding a foreground search UI, which then drives a fullscreen overlay drawn over the user's real app window.
