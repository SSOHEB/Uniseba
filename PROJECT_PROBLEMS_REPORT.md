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
- full-window OCR
- no partial-region mapping
- no stabilization smoothing

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
- `threads/ocr_thread.py` currently runs in safe-mode full-window OCR
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
- using safe-mode full-window OCR to isolate geometry

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

The accurate baseline is currently less optimized because partial-region OCR is bypassed.

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

- keep safe mode as the baseline
- test it across multiple real windows
- avoid changing geometry and search simultaneously

### Later, reintroduce optimizations carefully

1. stabilization only
2. partial OCR only
3. region cache only

Each should be tested independently.

---

## Final Assessment

The project is in a much healthier place now than before this debugging pass.

The critical result is:

the app is no longer “theoretically promising but unstable.”

It now has a working, accurate, demo-ready baseline.
