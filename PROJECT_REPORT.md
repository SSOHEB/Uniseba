# Uniseba Project Report

## Overview

Uniseba is a Windows desktop OCR overlay that lets users search text visible in another app window and highlight matches in place.

Current runtime behavior:

1. `Ctrl+Shift+U` opens the floating search UI.
2. OCR thread tracks a valid target window (excluding Uniseba/desktop/blocked consoles).
3. Client area is captured and change-detected.
4. OCR thread selects one mode:
   - scroll translation + strip OCR,
   - incremental merged-region OCR, or
   - full-window fallback OCR.
5. OCR words are normalized to a shared index schema.
6. UI runs fuzzy search immediately; semantic rerank is optional.
7. Overlay draws final absolute coordinate boxes.

## What Is Newly Implemented

- Phrase-aware fuzzy pre-pass for multi-word queries in `main.py`.
- Scroll-specialized OCR update path in `threads/ocr_thread.py`.
- Incremental OCR with merged changed regions and full fallback.
- Self-UI exclusion masking/filtering to avoid searching overlay/searchbar text.
- Search de-dup guards in UI (`last_search_*` signatures, overlay draw signature).
- Record + summarize flow (corpus capture + Groq summary) in `main.py` and `ai/gemini.py`.
- Rotating logs (`uniseba.log`, `uniseba_errors.log`) configured in `main.py`.

## Architecture Snapshot

- Entry: `main.py`
- Config source of truth: `config.py`
- OCR engine: `ocr/engine.py` (EasyOCR)
- OCR worker: `threads/ocr_thread.py`
- Search modules: `search/fuzzy.py`, `search/semantic.py`
- Semantic worker: `threads/search_thread.py`
- UI: `ui/searchbar.py`, `ui/overlay.py`, `ui/summary_panel.py`, `ui/tray.py`

## Latest Test Results (2026-03-31)

Environment used:

- Interpreter: `venv311\Scripts\python.exe` (Python 3.11.9)
- Platform: Windows (workspace `C:\Users\ssohe\Desktop\uniseba`)

Executed commands:

1. `venv311\Scripts\python.exe ocr_accuracy_test.py`
2. `venv311\Scripts\python.exe ocr_easyocr_test.py`

Results:

- `ocr_accuracy_test.py`: PASS, wrote `ocr_accuracy_report.txt`
  - OCR words: 86
  - Indexed entries: 338
  - hit@1: 20/20 (100%)
  - hit@5: 20/20 (100%)
  - hit@10: 20/20 (100%)
- `ocr_easyocr_test.py`: PASS, wrote `ocr_test_output.txt`
  - Raw OCR lines written: 88

## Known Gaps

- `ocr_thread._build_full_index()` currently uses hardcoded `DOWNSCALE = 0.75` instead of config constant.
- `search/hybrid.py` is now mostly alternate/legacy path; main merge logic lives in `main.py`.
- Semantic rerank depends on local availability of `all-MiniLM-L6-v2` (`SEMANTIC_LOCAL_FILES_ONLY=True`).
