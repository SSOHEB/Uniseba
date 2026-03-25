# Uniseba Failure Modes Document

## Purpose

This document describes what system failures look like when they happen.

The goal is to make failures legible for:

- diagnostics
- node coloring in a refinery/system map
- demo explanations
- user-visible symptom tracing

It focuses on the current codebase behavior.

---

## Quick Failure Table

| Component / Area | Failure Mode | User Symptom | Visible To User? | Misleading? | Likely File |
| --- | --- | --- | --- | --- | --- |
| Target selection | Wrong window chosen | Search results belong to a different app than expected | Yes | Yes | `threads/ocr_thread.py` |
| Capture | Invalid or empty window rect | Searchbar says waiting or stops updating | Yes | Sometimes | `threads/ocr_thread.py`, `capture/screen.py` |
| Change detection | Real visual changes not detected | Old OCR results remain on screen after scrolling or editing | Yes | Yes | `capture/change.py`, `threads/ocr_thread.py` |
| Forced refresh | Forced OCR not happening often enough | OCR appears stale even though the target changed | Yes | Yes | `threads/ocr_thread.py` |
| OCR WinRT availability | OCR engine import/load failure | No useful OCR results ever arrive | Yes | No | `ocr/engine.py` |
| OCR quality | Text not recognized or recognized badly | Missing matches or weird matches | Yes | Yes | `ocr/engine.py` |
| OCR coordinate mapping | Region-local coordinates mapped incorrectly | Rectangles appear offset from the real text | Yes | Yes | `threads/ocr_thread.py` |
| OCR stabilization | Frame rejected as unstable | OCR appears frozen briefly on older content | Yes | Yes | `threads/ocr_thread.py` |
| OCR smoothing | Same word matched to wrong old position | Rectangles jitter or drift slightly | Yes | Yes | `threads/ocr_thread.py` |
| OCR region cache | Stale region reused | Only part of the screen updates while another part stays old | Yes | Yes | `threads/ocr_thread.py` |
| OCR index cleanup | Legitimate text filtered out | Some visible words are never searchable | Yes | Yes | `ocr/index.py` |
| Fuzzy search threshold | Threshold too strict | Search misses words that seem "close enough" | Yes | Yes | `search/fuzzy.py` |
| Fuzzy search filtering | OCR entries rejected before matching | Search feels sparse or incomplete | Yes | Yes | `search/fuzzy.py` |
| Semantic model missing | Model unavailable locally | AI toggle appears to do nothing | Yes | Yes | `search/semantic.py` |
| Semantic thread error | Background rerank fails | Fuzzy search still works, AI effect disappears | Partly | Yes | `threads/search_thread.py` |
| Result merge | Fuzzy and semantic merge differently than expected | Ranking seems odd or inconsistent | Yes | Yes | `main.py`, `search/hybrid.py` |
| Overlay draw | Rectangles fail to appear | Search count changes but no boxes are visible | Yes | Yes | `ui/overlay.py` |
| Overlay layering | Overlay behind or awkwardly above windows | Highlights seem inconsistent or intrusive | Yes | Yes | `ui/overlay.py` |
| Overlay click-through | Overlay intercepts user interaction awkwardly | Screen feels blocked or difficult to click through | Yes | No | `ui/overlay.py` |
| Queue timing | UI consumes stale/newest-only updates | Results jump ahead and intermediate states disappear | Usually | Sometimes | `main.py` |
| Shutdown/thread lifecycle | Worker exits or app closes mid-update | App stops updating or closes abruptly | Yes | No | `main.py`, `threads/*` |

---

## Failure Modes By Component

## 1. Target Selection Failures

### Failure

The OCR thread selects the wrong target window.

### What it looks like

- You search for text visible in App A.
- Results come from App B.
- Overlay boxes may still look "correct" for the wrong app, which makes the failure deceptive.

### User-visible symptom

- "Search is wrong."
- "OCR is reading the wrong thing."
- "Highlights are appearing on unexpected content."

### Why it is misleading

The OCR and overlay can both be technically functioning correctly, but on the wrong source window.

### Primary source

- `threads/ocr_thread.py`

---

## 2. Capture Failures

### Failure

The window cannot be captured or produces an invalid rectangle.

### What it looks like

- OCR updates never arrive.
- Search remains stuck on old data.
- The app may appear idle even though the UI is still open.

### User-visible symptom

- "Waiting for OCR..."
- no live refresh
- no new searchable content

### Primary sources

- `threads/ocr_thread.py`
- `capture/screen.py`

---

## 3. Change Detection Failures

### Failure

A real visual change happens, but the diff logic does not mark the region as changed.

### What it looks like

- scrolling occurs but old words remain searchable
- edited text does not update quickly
- only some screen regions refresh

### User-visible symptom

- stale search results
- stale overlay rectangles
- delayed refresh after visible content changes

### Why it matters

The OCR thread may reuse cached region OCR instead of recomputing the changed content.

### Primary sources

- `capture/change.py`
- `threads/ocr_thread.py`

---

## 4. OCR Engine Availability Failures

### Failure

WinRT OCR dependencies are unavailable or fail to load.

### What it looks like

- OCR pipeline never produces useful words
- downstream search has nothing meaningful to search

### User-visible symptom

- app never becomes useful for live text search
- search stays empty or stuck waiting

### Primary source

- `ocr/engine.py`

---

## 5. OCR Quality Failures

### Failure

OCR runs, but recognition quality is poor.

### What it looks like

- visible words are missing from search
- wrong words appear in search results
- short words disappear
- noisy OCR artifacts show up

### User-visible symptom

- "Search is bad"
- "The word is on screen but cannot be found"
- "The result count makes no sense"

### Why it is misleading

Search can only rank what OCR extracted. A search complaint may actually be an OCR quality problem.

### Primary sources

- `ocr/engine.py`
- `ocr/index.py`

---

## 6. Coordinate Mapping Failures

### Failure

OCR word boxes are mapped incorrectly from region-local space into screen space.

### What it looks like

- rectangles are shifted left/right/up/down
- rectangles appear over nearby but wrong words
- highlights drift more when the screen changes

### User-visible symptom

- "The boxes are offset"
- "The right word is found, but the rectangle is not on it"

### Visible to user?

Yes, very clearly.

### Primary source

- `threads/ocr_thread.py`

---

## 7. OCR Stabilization Failures

### Failure

The stabilization step rejects a frame or smooths positions too aggressively.

### What it looks like

- OCR appears to freeze on an older state
- highlight positions lag slightly behind content
- repeated words can inherit the wrong older position

### User-visible symptom

- delayed updates
- strange but small box drift
- occasional "sticky" rectangles

### Primary source

- `threads/ocr_thread.py`

---

## 8. OCR Region Cache Failures

### Failure

Cached OCR for unchanged regions remains even though that region really changed.

### What it looks like

- one part of the app updates correctly
- another part remains old
- search mixes old and new content

### User-visible symptom

- partial stale search state
- inconsistent screen understanding

### Primary source

- `threads/ocr_thread.py`

---

## 9. OCR Index Cleanup Failures

### Failure

Valid OCR words are filtered out as noise.

### What it looks like

- single-character words disappear
- small but meaningful labels never appear in search
- numbers survive more often than short letters

### User-visible symptom

- "Certain visible words are impossible to find"

### Primary source

- `ocr/index.py`

---

## 10. Fuzzy Search Failures

### Failure

Fuzzy matching is too strict or candidate filtering removes too much input.

### What it looks like

- near matches do not appear
- minor typos fail unexpectedly
- result counts stay low

### User-visible symptom

- "Search feels too strict"
- "It should have matched that"

### Primary source

- `search/fuzzy.py`

---

## 11. Semantic Search Failures

### Failure

The semantic model is missing, cannot load, or background rerank fails.

### What it looks like

- AI toggle changes nothing visible
- fuzzy search still works
- there is no obvious crash

### User-visible symptom

- "AI mode doesn't seem different"

### Why it is misleading

This failure is intentionally graceful, so it can look like the feature is simply weak rather than unavailable.

### Primary sources

- `search/semantic.py`
- `threads/search_thread.py`

---

## 12. Result Merge Failures

### Failure

Merged ranking or deduping behaves unexpectedly.

### What it looks like

- results rank oddly
- duplicate-like boxes remain
- integrated mode and standalone mode behave differently

### User-visible symptom

- "The ordering feels wrong"
- "Too many similar highlights"

### Primary sources

- `main.py`
- `search/hybrid.py`

---

## 13. Overlay Rendering Failures

### Failure

Overlay draws incorrectly, draws behind something, or does not appear.

### What it looks like

- result count updates but no visible rectangles
- rectangles flash inconsistently
- overlay feels intrusive or blocks interaction

### User-visible symptom

- "Search found matches, but nothing is highlighted"
- "The overlay is awkward to use"

### Primary source

- `ui/overlay.py`

---

## 14. Queue And Timing Failures

### Failure

Queue handoff timing causes stale or skipped intermediate states.

### What it looks like

- OCR updates jump from old to new without showing intermediate changes
- semantic updates arrive after the user already typed something newer
- visible result changes feel non-linear

### User-visible symptom

- inconsistent or jumping results

### Why it is usually acceptable

The app intentionally drains queues and keeps the newest item, favoring freshness over preserving every intermediate state.

### Primary sources

- `main.py`
- `threads/search_thread.py`
- `threads/ocr_thread.py`

---

## Best Symptom-To-File Map

| Symptom | First File To Inspect |
| --- | --- |
| Wrong app content searched | `threads/ocr_thread.py` |
| Rectangles offset from words | `threads/ocr_thread.py` |
| Search count changes but no boxes visible | `ui/overlay.py` |
| AI toggle appears ineffective | `search/semantic.py` |
| Search misses visible text | `ocr/engine.py`, then `ocr/index.py`, then `search/fuzzy.py` |
| Screen updates only partly | `threads/ocr_thread.py` |
| Results feel stale after scrolling | `capture/change.py`, then `threads/ocr_thread.py` |

---

## Refinery Coloring Suggestion

If you want a simple severity coloring model:

- Red
  wrong target selection, OCR unavailable, coordinate mapping failure, overlay not drawing
- Orange
  stale region cache, poor OCR quality, stabilization drift, strict fuzzy filtering
- Yellow
  semantic unavailable, queue timing oddities, result merge quirks
- Green
  component healthy and producing expected output

---

## One-Sentence Summary

Most visible Uniseba failures are misleading because the user often experiences them as "bad search" even when the root cause is actually upstream in target selection, OCR extraction, or coordinate mapping.
