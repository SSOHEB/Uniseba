# Quantified Proof (Slide-Ready)

## Runtime Latency Metrics
Source: `uniseba.log` (analyzed on 2026-04-03) using `analyze_ocr_log.py` and log parsing.

| Metric | Sample Size | Mean | P50 | P90 | P99 |
|---|---:|---:|---:|---:|---:|
| OCR engine latency (`ocr_ms`) | 174 OCR cycles | 3014.2 ms | 1347.2 ms | 9022.5 ms | 18745.1 ms |
| OCR end-to-end cycle (`total_cycle_ms`) | 174 OCR cycles | 3145.8 ms | 1491.1 ms | 9165.0 ms | 18952.6 ms |
| Search apply latency (`total_search_ms`) | 85 search events | 6.78 ms | 5.50 ms | 11.70 ms | 37.00 ms |

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
"In our current benchmark run, search response stays in single-digit milliseconds on average (6.78 ms), and keyword retrieval achieved 100% hit@1/hit@5 across 20 validation queries."

## Honest Limitation (say this if asked)
- Accuracy benchmark is currently single-image (`test_crop.png`) and should be expanded to a multi-scene benchmark for stronger external validity.
