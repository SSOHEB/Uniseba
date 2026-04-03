# Quantified Proof (Slide-Ready)

## Latest Runtime Latency Metrics (Apr 4, 2026)
Source: `uniseba.log` filtered to `2026-04-04` entries using log parsing.

| Metric | Sample Size | Mean | P50 | P90 | P99 | Max |
|---|---:|---:|---:|---:|---:|---:|
| OCR end-to-end cycle (`total_cycle_ms`) | 143 OCR cycles | 2009.79 ms | 1413.00 ms | 4581.00 ms | 9583.80 ms | 11416.00 ms |
| OCR engine latency (`ocr_ms`) | 143 OCR cycles | 1870.30 ms | 1274.10 ms | 4393.40 ms | 9375.20 ms | 11186.40 ms |
| Search apply latency (`total_search_ms`) | 179 search events | 4.73 ms | 3.90 ms | 8.50 ms | 22.60 ms | 26.30 ms |
| Semantic merge (`merge_ms`) | 179 merge events | 0.07 ms | 0.10 ms | 0.10 ms | 0.20 ms | 1.00 ms |

### Latency Test Commands (Reproducible)
- `python analyze_ocr_log.py uniseba.log --tail 4000000`
- Parsed `Search applied ... total_search_ms` and `Semantic merge applied ... merge_ms` from `uniseba.log`

## Query Success (hit@k)
Source: `ocr_accuracy_test.py` against `test_crop.png` (20 benchmark queries).

| Aggregate | Score |
|---|---:|
| hit@1 | 20/20 (100%) |
| hit@5 | 20/20 (100%) |
| hit@10 | 20/20 (100%) |

### 10 Example Queries (for slide evidence)
| Query | hit@1 | hit@5 | hit@10 |
|---|---:|---:|---:|
| `contents` | True | True | True |
| `biography` | True | True | True |
| `early` | True | True | True |
| `education` | True | True | True |
| `movement` | True | True | True |
| `references` | True | True | True |
| `history` | True | True | True |
| `source` | True | True | True |
| `gandhi` | True | True | True |
| `nehru` | True | True | True |

## Suggested Pitch Line
"In our latest Apr 4 runtime logs, search response remained single-digit milliseconds on average (4.73 ms), and our controlled benchmark achieved 100% hit@1/hit@5 on 20 validation queries."

## Honest Limitation (say this if asked)
- Accuracy benchmark is currently single-image (`test_crop.png`) and should be expanded to a multi-scene benchmark for stronger external validity.
