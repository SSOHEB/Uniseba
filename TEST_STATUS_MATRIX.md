# Test Status Matrix (Submission Readiness)

## Scope
Status of requested validation items based on latest available artifacts in this repo.

- Runtime logs: `uniseba.log` (Apr 4 slice)
- Latency summary: `QUANTIFIED_PROOF.md`
- Accuracy reports: `ocr_accuracy_report.md`, `ocr_accuracy_report.dataset_real.md`
- Architecture/Q&A pack: `PITCH_ARCHITECTURE_HLD_LLD.md`

---

## 1) Must-Have Tests

| Test Item | Status | Evidence | Result Summary | Jury-safe Note |
|---|---|---|---|---|
| OCR Accuracy Benchmark (controlled) | `DONE` | `ocr_accuracy_report.md` | 1 image, 20 queries, hit@1/hit@5/hit@10 = 20/20 | Controlled single-scene benchmark only |
| OCR Accuracy Benchmark (dataset real) | `PARTIAL` | `ocr_accuracy_report.dataset_real.md`, `ocr_accuracy_cases.dataset_real.json` | 14 images, 42 queries, hit@1/hit@5/hit@10 = 42/42 | Queries were auto-generated from OCR-visible tokens (self-retrieval style), not strict ground-truth CER |
| End-to-End Latency / Performance | `DONE` | `QUANTIFIED_PROOF.md`, Apr 4 log parsing | OCR cycle: n=143 mean 2009.79ms p50 1413ms p90 4581ms; Search: n=179 mean 4.73ms p90 8.50ms | Hotkey->first-search has low sample confidence; excluded from headline claims |
| UI Responsiveness / Thread Safety (no crash during stress) | `DONE` | Apr 4 log parse from `uniseba.log` | 11.86 min window, OCR publishes=143 (~12.05/min), received updates=139, error-like lines=0 | Queue backlog metric is inferred/proxy (no explicit backlog counter in current logs) |
| Cross-Scenario Reliability | `PARTIAL` | `uniseba.log` target titles + dataset report | 11 unique target titles observed in Apr 4 logs; dataset coverage includes docs/photos/vscode-like scenes | Requires explicit scenario success/fail checklist table for stronger claim |

---

## 2) Nice-to-Have / High-Impact Tests

| Test Item | Status | Evidence | Gap to Close |
|---|---|---|---|
| Scalability simulation (100+ phrases / 500+ indexed items) | `PARTIAL` | Apr 4 logs include `total_words` peaks up to 321 | Need controlled load-step experiment and latency-vs-size curve |
| Offline mode fallback behavior | `PENDING` | Not explicitly benchmarked | Run with AI disabled/network unavailable and document fallback output quality |
| Resource usage (CPU/RAM) | `PENDING` | No `psutil` report yet | Add lightweight resource profiler run (idle vs OCR-active vs summary) |
| Ground-truth OCR quality (CER / Word Accuracy %) | `PENDING` | Not computed in current scripts | Need human-annotated truth text per image and CER calculator |

---

## 3) Key Numbers for Pitch (Use These)

- Search latency (`total_search_ms`, Apr 4): `n=179`, mean `4.73 ms`, p50 `3.90 ms`, p90 `8.50 ms`, p99 `22.60 ms`
- OCR cycle latency (`total_cycle_ms`, Apr 4): `n=143`, mean `2009.79 ms`, p50 `1413.00 ms`, p90 `4581.00 ms`, p99 `9583.80 ms`
- Controlled benchmark: `20/20` hit@1/hit@5/hit@10 on `test_crop.png`
- Multi-image dataset-real run: `14 images`, `42 queries`, `42/42` hit@1/hit@5/hit@10 (self-retrieval benchmark)

---

## 4) Strict Claim Guidance

Safe claims:
- "Prototype is log-validated for latency and stability under asynchronous OCR/search flow."
- "Search response path is consistently low-latency in latest Apr 4 runs."
- "Controlled benchmark and multi-image retrieval benchmark both show strong query surfacing."

Avoid:
- "100% OCR accuracy overall."
- "CER validated on diverse ground-truth dataset."
- "Production-hardened deployment is complete."

