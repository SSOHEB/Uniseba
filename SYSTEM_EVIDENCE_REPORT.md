# Uniseba System Evidence Report

## Purpose

This document captures the current system truth from the logs we retrieved during the latest validation pass.

It is meant to preserve context before the next refinement cycle, so future decisions are based on evidence instead of memory.

---

## Evidence Sources

The findings below are based on these extracted logs:

- `timing_only.log`
- `target_selected.log`
- `ocr_index_quality.log`
- `errors_only.log`
- overlay/search timing slices from `uniseba.log` (e.g., `"Search applied"` lines with `overlay_ms`)
 - performance summaries from `analyze_ocr_log.py`

Tested surfaces discussed in this pass:

- Visual Studio Code
- Wikipedia / browser text
- image / Photos

Scrolling and dynamic-content behavior has been exercised (scroll translation detection + incremental publishing are present in logs).

---

## Current Trusted Baseline

Current system baseline:

- EasyOCR backend
- client-area capture
- hybrid OCR
  - full-window OCR fallback
  - merged-region incremental OCR
  - scroll-translation incremental OCR (strip OCR)
- no smoothing-based coordinate stabilization in the active trusted path
- fuzzy search over OCR-derived index
- optional semantic rerank
- transparent overlay drawing absolute screen-space highlights

This baseline is currently functioning end-to-end.

---

## Executive Summary

The current system is real and functional, and the logs show a clear structure to its strengths and weaknesses.

Main conclusions:

1. Search is fast.
2. Overlay draw cost is acceptable.
3. OCR inference is the dominant bottleneck by far.
4. Target selection works across real apps, but the hotkey path sometimes captures the wrong window.
5. OCR output and indexing are stable, but the index expansion strategy can introduce noisy tokens.
6. Redundant search and redraw passes are happening even when the visible result set does not materially change.
7. The current EasyOCR pipeline does not show an active crash pattern in the recent logs.

---

## 1. Timing Findings

### Capture and change detection

Capture and change detection are not the main problem.

Observed ranges:

- `capture_ms`: roughly `56` to `94 ms`
- `change_ms`: roughly `19` to `36 ms`

Interpretation:

- screen acquisition is acceptable for a prototype
- change detection is not dominating end-to-end latency

### OCR cost

OCR is the main performance bottleneck.

Observed (from `analyze_ocr_log.py` over a recent slice of `uniseba.log`):

- full-window cycles (`full_window=1`): p50 OCR around `~9.1s`
- incremental cycles (`full_window=0`): p50 OCR around `~4.3s`
- best-case scroll-strip updates can reach sub-second total cycles when the newly revealed strip is small (examples in logs show `total_cycle_ms` under `~1s`)

Interpretation:

- the system is OCR-bound, not search-bound
- stable screens feel usable because search on an existing OCR index is fast
- dynamic screens will feel stale because OCR refresh takes seconds on dense content

However, scroll can feel responsive when translation is detected and only a strip is OCR'd.

### Index build cost

Observed ranges:

- `index_ms`: usually under `3 ms`

Interpretation:

- index building itself is cheap compared to OCR inference

### Search and overlay timing

Observed ranges:

- `fuzzy_ms`: usually `0.5` to `2.9 ms`
- occasional spikes: `15` to `24 ms`
- `phrase_ms`: almost always `0.0 ms`
- `overlay_ms`: usually `2` to `9 ms`
- larger redraw cases: around `12` to `21 ms`
- `total_search_ms`: usually around `0.6` to `6 ms`, occasionally higher when many matches redraw

Interpretation:

- search is fast enough for interactive use
- overlay rendering is not the primary bottleneck

---

## 2. Search Behavior Findings

### What is working

The search layer is behaving well overall:

- queries resolve quickly
- fuzzy matching is responsive
- phrase clustering is cheap
- exact and partial phrase cases are being found across real app surfaces

Examples seen in logs:

- `postmodernism`
- `methods`
- `annales`
- `marxism`
- `history`
- `research`

### Redundant search reruns

A clear inefficiency is present:

- the same query is applied multiple times
- the same result sample appears repeatedly
- `overlay_ms=0.0` in many repeated cases

This means the system is re-running search even when:

- query is unchanged
- visible results are effectively unchanged
- no actual redraw is needed

Examples observed:

- `iit`
- `me`
- `meh`
- `madhu`
- `remar`

Interpretation:

- this is a low-risk smoothness optimization target
- reducing redundant search passes should improve feel without touching OCR geometry

### Search quality noise

Some search results still show OCR/index noise.

Examples observed:

- `~for example, whether its`
- `project_proble_`
- `rem`
- `an`

Interpretation:

- search quality is limited more by OCR/index token quality than by fuzzy matching speed

---

## 3. Target Selection Findings

### What is working

Target selection is functioning across multiple real apps:

- VS Code
- Chrome / Edge
- PowerPoint
- Photos

Examples seen:

- `main.py - uniseba - Visual Studio Code`
- `History - Wikipedia ... - Microsoft Edge`
- `Opening - PowerPoint`
- `Photos`

### Real issue found

The hotkey capture path sometimes locks onto the wrong foreground window.

Examples seen:

- `Shortcut captured foreground window ... title='Uniseba Search'`
- `Shortcut captured foreground window ... title='Windows PowerShell'`

Interpretation:

- target selection loop is generally fine
- hotkey intent capture is not yet fully hardened
- this is a real demo-risk because the user may accidentally anchor the app or terminal instead of the intended content window

### Secondary note

Target selection logs are noisy and repetitive.

Interpretation:

- not a correctness blocker
- but evidence that target-selection chatter could be reduced later

---

## 4. OCR And Index Quality Findings

### OCR output stability

OCR output is stable for the same surface type.

Examples:

- dense page runs often stayed around `words_found=108` to `113`
- lighter surfaces stayed around `words_found=34` to `36`

Interpretation:

- OCR output is not fluctuating wildly on steady content
- this is a good sign for system consistency

### Index expansion behavior

The index layer is aggressively expanding OCR output into many searchable entries.

Examples:

- `words_found=108`, `kept=311`
- `words_found=103`, `kept=296`
- `words_found=108`, `kept=349`

Interpretation:

- OCR often produces larger spans / lines
- the index layer is splitting those spans into more searchable units
- this is likely a major reason browser-text search improved

### Filtering behavior

Filtering is light and controlled.

Common patterns:

- `filtered=3` to `11`

Interpretation:

- the filter is not overly destructive
- it trims some junk but preserves most text candidates

### Quality tradeoff

The same expansion that improves searchability can also add noise.

Likely consequences:

- more short weak tokens
- more fuzzy false positives
- larger candidate sets
- noisier overlays on dense pages

Interpretation:

- the OCR/index strategy is coherent and useful
- but it likely needs later tightening once the more urgent smoothness issues are handled

---

## 5. Overlay Findings

### What is working

Overlay rendering works across real content:

- browser text
- code/editor text
- image / photo content
- presentation-like content

The renderer is alive and integrated correctly.

### Upstream noise is visible in the overlay

Older logs show self-capture and diagnostic artifacts such as:

- `Uniseba Search`
- `query typed:`
- `candidates-101 rejected`
- `[searchbar`

More recent logs show meaningful user-facing phrases such as:

- `Maulana Azad`
- `civil disobedience`
- `young man`
- `Union Minister of Education`

Interpretation:

- overlay is faithfully drawing what upstream OCR/index/search provides
- the renderer is not the core quality problem

### Redraw churn

Repeated near-identical draws are visible in the logs.

Interpretation:

- overlay is being asked to redraw too often
- this matches the repeated search-application pattern found earlier

### Phrase grouping

There are clear signs that phrase grouping sometimes works well.

Examples:

- `As a young man`
- `civil disobedience`
- `Union Minister of Education`

Interpretation:

- phrase-level results are a real strength, not just a theoretical feature

---

## 6. Error Findings

### Historical errors

The only real `ERROR` entries in the retrieved log slice are old WinRT OCR failures:

- `ModuleNotFoundError: No module named 'winrt.windows.globalization'`
- `RuntimeError: Required WinRT OCR namespaces are not available in this environment.`

These belong to the older OCR backend and are historical.

### Non-critical debug noise

The repeated PIL lines about `olefile` are debug-level plugin import messages:

- `failed to import FpxImagePlugin`
- `failed to import MicImagePlugin`

Interpretation:

- these do not indicate current OCR/search pipeline failure
- they are not the cause of current runtime behavior

### Current crash status

The current EasyOCR-based system does not show an active crash pattern in the recent validation logs.

Interpretation:

- present issues are performance and smoothness issues, not current fatal stability issues

---

## 7. What The System Is Good At Right Now

Current strengths:

- works across multiple real desktop applications
- search layer is fast
- overlay layer works
- OCR/index pipeline is stable enough for repeated demo use
- browser-text search improved due to span splitting and phrase grouping
- no active current crash signature seen in recent evidence

This means the project is already past the "concept only" stage and into "real but rough prototype" territory.

---

## 8. What The System Is Weak At Right Now

Current weaknesses:

- OCR refresh is slow on dense content
- dynamic content responsiveness is likely the weakest real-world behavior
- hotkey capture can select the wrong foreground window
- redundant search/rerender passes create avoidable churn
- index expansion improves coverage but also introduces token noise

---

## 9. Recommended Next-Step Priority

These are the most evidence-supported next steps.

### Priority 1: Harden hotkey target capture

Reason:

- directly improves target correctness
- low risk
- visible demo benefit

Goal:

- prevent locking onto `Uniseba Search`
- prevent locking onto blocked console windows like `Windows PowerShell`

### Priority 2: Skip redundant search/rerender passes

Reason:

- clear evidence of repeated identical query/result applications
- low risk
- likely improves smoothness immediately

Goal:

- if query is unchanged and result signature is unchanged, skip the full apply path

### Priority 3: Run a dedicated scrolling / dynamic-content test

Reason:

- this is the biggest remaining unmeasured behavior
- now that system truth is documented, this test will answer a focused question

Goal:

- measure how quickly new visible text becomes searchable after scroll/change
- confirm how stale the index feels under motion

### Priority 4: Later quality tightening

After the first two fixes and the dynamic-content test:

- reduce noisy token expansion
- possibly tighten filtering for weak split tokens
- consider further OCR acquisition improvements only after low-risk wins are exhausted

---

## 10. Final Current Assessment

Based on the retrieved evidence:

- the overlay is not the main problem
- search is not the main problem
- the OCR engine is the main latency bottleneck
- the hotkey target path has a real correctness issue
- redundant search/redraw passes are the clearest low-risk smoothness issue

So the next refinement phase should focus on:

1. target-capture correctness
2. redundant rerun elimination
3. dynamic-content measurement

That is the most disciplined path forward from the evidence we now have.
