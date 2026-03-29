# Uniseba Problem And Update Report

## Purpose

This document records the main problems encountered so far, what changed, what actually helped, and what the current code reality is after the recent EasyOCR and safe-mode debugging pass.

---

## Project Summary

Uniseba is a Windows OCR overlay search tool that:

1. captures the current content window
2. OCRs visible text
3. indexes OCR words with screen coordinates
4. searches those words
5. draws highlight rectangles over the matches

Current trusted baseline:

- EasyOCR backend
- client-area capture
- hybrid OCR:
  - full-window OCR fallback
  - incremental OCR on merged changed regions
  - scroll-specialized OCR using translation + strip OCR
- stabilization smoothing bypassed (newest index wins)

---

## Main Problem Clusters

## 1. OCR Backend Limitations

### Earlier problem

The older WinRT OCR path struggled on:

- browser pages
- dark themes
- visually complex layouts

### What changed

- OCR backend was replaced with EasyOCR
- CUDA-capable torch was installed and verified

### Current state

The project now uses EasyOCR successfully, but the dependency stack needs to stay aligned:

- `numpy 1.26.4`
- `torch 2.2.2+cu121`
- EasyOCR import must remain healthy

---

## 2. Wrong Window Selection

### Problem

OCR sometimes targeted:

- Uniseba itself
- console windows
- desktop shell windows
- wrong foreground windows

### Fixes that helped

- root HWND normalization
- rejecting `Progman` and `WorkerW`
- rejecting empty-title windows
- rejecting blocked titles and console windows
- preserving target intent in the integrated UI

### Current state

Target selection is much better, though still worth watching in demos involving rapid focus changes.

---

## 3. Systematic Box Offset

### Problem

Boxes appeared consistently above the actual word.

### Root cause

Capture and draw were not using the same geometry origin:

- full decorated window bounds included title bar and borders
- OCR was supposed to align to content

### Fix that helped

Using client-area bounds through:

- `GetClientRect()`
- `ClientToScreen()`

### Current state

This was a major geometry fix and remains part of the current known-good baseline.

---

## 4. Region Mapping Corruption

### Problem

Partial-region OCR repeatedly caused:

- offset boxes
- clipped words like `"ocument"`
- wrong words being highlighted
- box jitter

### Root causes

- coordinate remapping complexity
- crop boundary issues
- scale conversions
- stale region cache interactions
- stabilization interacting with incorrect positions

### Important outcome

The optimization path was the problem, not the fundamental OCR/search loop.

### Current state (after fixes)

Incremental OCR is back, but with two guardrails:

- region crops are kept at native scale (no silent downscale without coordinate compensation)
- scroll can be handled via translation estimation + strip OCR, avoiding lots of large crops

---

## 5. Stabilization And Jitter

### Problem

The stabilization layer caused:

- frozen-looking OCR
- lagging positions
- jitter from mixing old and new coordinates

### What changed

Safe mode bypassed stabilization entirely:

- `_stabilize_index()` currently returns `new_index`

### Current state

This is intentionally simple right now because it keeps geometry honest.

---

## 6. Search Noise

### Problem

Search sometimes surfaced:

- partial garbage
- OCR of log lines
- overly long line-like text blocks

### Fixes that helped

- OCR noise filtering in `ocr/index.py`
- rejecting very long OCR strings
- rejecting OCR strings with too many spaces
- rejecting OCR that looks like app debug/log output
- tuning fuzzy threshold to a more usable middle ground

### Current state

Search quality is improved, though this is still an actively tuned area.

---

## Biggest Breakthrough

The biggest breakthrough of the session was the safe-mode debugging step.

Safe mode did three things:

1. used full-window OCR only
2. removed partial-region coordinate remapping
3. removed stabilization smoothing

Result:

- boxes aligned correctly
- scroll updates worked
- OCR became trustworthy on multiple screen types

This proved the main bug was in the optimization layers, not the base OCR pipeline.

---

## Current Code Reality

These points are the current truth:

- `main.py` is the integrated app entry point
- `ui/searchbar.py` is now a pure UI base class
- `threads/ocr_thread.py` uses incremental OCR when safe, and falls back to full-window OCR
- `ocr/engine.py` now uses EasyOCR, not WinRT
- `config.py` is centralized and populated
- structured logging is active across the runtime

---

## What Definitely Helped

- centralizing config
- making the searchbar a pure UI base
- moving to structured logging
- switching capture to client-area bounds
- replacing WinRT OCR with EasyOCR
- rejecting desktop shell windows explicitly
- using full-window OCR as a correctness baseline to isolate geometry (historical lesson)

---

## What Helped Partially

- search threshold tuning
- OCR preprocessing changes
- target locking
- change-detection tuning

These can improve behavior, but they were not the primary breakthrough.

---

## What Created Problems

- partial-region OCR mapping
- region crop boundary tricks
- overly aggressive stabilization
- chasing GPU utilization visually in Task Manager
- making multiple tuning changes before validating geometry

---

## Current Risks

### 1. Optimization Debt

The system is now using incremental OCR again, which improves scroll and minor-change responsiveness.

The risk is correctness drift:

- bad scroll translation estimates can create ghost hits or temporary misalignment
- large merged regions can still be expensive (multi-second) if the screen is very dynamic

### 2. Dependency Maintenance

The EasyOCR stack now matters:

- EasyOCR
- torch CUDA build
- NumPy compatibility

### 3. Search Merge Duplication

There are still two hybrid-style merge paths:

- `main.py`
- `search/hybrid.py`

---

## Recommended Next Steps

### Before further optimization

- keep full-window OCR as the correctness fallback
- validate scroll mode across multiple apps (browser, editor, PDF viewer)
- avoid changing geometry + search heuristics in the same pass

### Next optimization target (low-risk)

- reduce how often we are forced into full-window OCR when incremental would be sufficient
- add better metrics around how much area each incremental pass is OCRing (to explain slow "full_window=0" cycles)

---

## Final Assessment

The project is in a much healthier place now than before this debugging pass.

The critical result is:

the app is no longer "theoretically promising but unstable."

It now has a working, accurate, demo-ready baseline.
