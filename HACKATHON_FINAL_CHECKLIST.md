# Hackathon Final Checklist (Apr 4, 2026)

## Submission Artifacts Ready
- `README.md` - project overview, stack, and benchmark snapshot
- `QUANTIFIED_PROOF.md` - slide-ready latency + retrieval numbers
- `PITCH_ARCHITECTURE_HLD_LLD.md` - HLD/LLD and jury Q&A prep
- `TECHNICAL_DEEP_DIVE.md` - detailed system walkthrough
- `TEST_STATUS_MATRIX.md` - done/partial/pending validation matrix
- `ocr_accuracy_report.dataset_real.md` - multi-image benchmark details (14 images)
- `ocr_accuracy_report.md` - controlled baseline benchmark details (`test_crop.png`)
- `ocr_accuracy_report.txt` - compact benchmark summary

## Primary Numbers to Use in Pitch
- Search latency (`total_search_ms`, Apr 4 logs): mean `4.73 ms`, p90 `8.50 ms`, n=`179`
- OCR cycle (`total_cycle_ms`, Apr 4 logs): mean `2009.79 ms`, p50 `1413.00 ms`, p90 `4581.00 ms`, n=`143`
- Multi-image retrieval benchmark: `42/42` hit@1, `42/42` hit@5, `42/42` hit@10 (14 images, 42 queries)
- Controlled baseline: `20/20` hit@1, `20/20` hit@5, `20/20` hit@10

## Exact Safe Claim Lines
- "Uniseba is validated with runtime logs and controlled benchmark scripts."
- "Search interaction is low-latency; OCR inference is the main performance bottleneck."
- "The current multi-image benchmark is retrieval-oriented and not a CER ground-truth study."

## Do Not Overclaim
- Do not claim "100% OCR accuracy overall."
- Do not claim CER/word-accuracy validation unless you add labeled ground truth.
- Do not claim full production packaging if installer is not completed.

## 2-Minute Demo Flow
1. Open a non-copyable text scene (image/PDF-like/remote UI).
2. Press `Ctrl+Shift+U` and show instant highlight search.
3. Start `Record`, scroll for content capture, then `Stop`.
4. Click `Summarize`, then `Graph`.
5. Close with benchmark slide (`QUANTIFIED_PROOF.md` table).

## Last-Minute Dry Run (10 minutes)
1. Launch app once and verify hotkey + overlay.
2. Verify `Record -> Summarize -> Graph` flow.
3. Keep `QUANTIFIED_PROOF.md` and `TEST_STATUS_MATRIX.md` open for Q&A.
4. Keep one fallback line ready: "Prototype scope is honest; packaging hardening is next."
