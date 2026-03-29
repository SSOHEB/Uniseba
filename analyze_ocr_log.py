import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean


@dataclass(frozen=True)
class OcrCycle:
    ts: datetime
    full_window: bool
    changed_regions: int
    total_words: int
    capture_ms: float
    change_ms: float
    ocr_ms: float
    index_ms: float
    total_cycle_ms: float


@dataclass(frozen=True)
class ScrollEstimate:
    ts: datetime
    dx: int
    dy: int
    response: float


_OCR_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*?"
    r"Published OCR index full_window=(?P<full_window>[01]|True|False)\s+"
    r"changed_regions=(?P<changed_regions>\d+)\s+"
    r"total_words=(?P<total_words>\d+)\s+"
    r"capture_ms=(?P<capture_ms>[\d.]+)\s+"
    r"change_ms=(?P<change_ms>[\d.]+)\s+"
    r"ocr_ms=(?P<ocr_ms>[\d.]+)\s+"
    r"index_ms=(?P<index_ms>[\d.]+)\s+"
    r"total_cycle_ms=(?P<total_cycle_ms>[\d.]+)\s*$"
)

_SCROLL_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*?"
    r"Detected scroll-like translation dx=(?P<dx>-?\d+)\s+"
    r"dy=(?P<dy>-?\d+)\s+response=(?P<response>[\d.]+)\s*$"
)


def _parse_ts(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f")


def _pct(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    # Nearest-rank percentile (good enough for logs).
    idx = max(0, min(len(values) - 1, int(round(p * (len(values) - 1)))))
    return float(values[idx])


def _fmt_ms(x: float) -> str:
    if x != x:  # NaN
        return "n/a"
    return f"{x:.1f}ms"


def _fmt_int(x: float) -> str:
    if x != x:
        return "n/a"
    return f"{int(round(x))}"


def _summarize_cycles(label: str, cycles: list[OcrCycle]) -> None:
    ocr = [c.ocr_ms for c in cycles]
    total = [c.total_cycle_ms for c in cycles]
    words = [c.total_words for c in cycles]
    changed = [c.changed_regions for c in cycles]

    print(f"{label}: n={len(cycles)}")
    if not cycles:
        return
    print(
        "  ocr_ms:   mean=%s p50=%s p90=%s p99=%s"
        % (_fmt_ms(mean(ocr)), _fmt_ms(_pct(ocr, 0.50)), _fmt_ms(_pct(ocr, 0.90)), _fmt_ms(_pct(ocr, 0.99)))
    )
    print(
        "  total_ms: mean=%s p50=%s p90=%s p99=%s"
        % (
            _fmt_ms(mean(total)),
            _fmt_ms(_pct(total, 0.50)),
            _fmt_ms(_pct(total, 0.90)),
            _fmt_ms(_pct(total, 0.99)),
        )
    )
    print(
        "  words:    mean=%s p50=%s p90=%s"
        % (_fmt_int(mean(words)), _fmt_int(_pct(words, 0.50)), _fmt_int(_pct(words, 0.90)))
    )
    print(
        "  changed:  mean=%s p50=%s p90=%s"
        % (_fmt_int(mean(changed)), _fmt_int(_pct(changed, 0.50)), _fmt_int(_pct(changed, 0.90)))
    )


def _summarize_scroll(estimates: list[ScrollEstimate]) -> None:
    print(f"scroll-like estimates: n={len(estimates)}")
    if not estimates:
        return
    responses = [e.response for e in estimates]
    dys = [abs(e.dy) for e in estimates]
    dxs = [abs(e.dx) for e in estimates]
    print("  response: mean=%.3f p50=%.3f p90=%.3f" % (mean(responses), _pct(responses, 0.50), _pct(responses, 0.90)))
    print("  |dy|:     mean=%s p50=%s p90=%s" % (_fmt_int(mean(dys)), _fmt_int(_pct(dys, 0.50)), _fmt_int(_pct(dys, 0.90))))
    print("  |dx|:     mean=%s p50=%s p90=%s" % (_fmt_int(mean(dxs)), _fmt_int(_pct(dxs, 0.50)), _fmt_int(_pct(dxs, 0.90))))


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze Uniseba OCR performance from uniseba.log")
    ap.add_argument("log", nargs="?", default="uniseba.log", help="Path to uniseba.log (default: ./uniseba.log)")
    ap.add_argument("--tail", type=int, default=0, help="Only analyze the last N bytes (0 = full file)")
    args = ap.parse_args()

    path = Path(args.log)
    if not path.exists():
        raise SystemExit(f"Log file not found: {path}")

    data = path.read_bytes()
    if args.tail and args.tail > 0 and len(data) > args.tail:
        data = data[-args.tail :]
    text = data.decode("utf-8", errors="replace").splitlines()

    cycles: list[OcrCycle] = []
    scroll: list[ScrollEstimate] = []

    for line in text:
        m = _OCR_RE.match(line)
        if m:
            full_raw = m.group("full_window")
            full_window = full_raw in ("1", "True")
            cycles.append(
                OcrCycle(
                    ts=_parse_ts(m.group("ts")),
                    full_window=full_window,
                    changed_regions=int(m.group("changed_regions")),
                    total_words=int(m.group("total_words")),
                    capture_ms=float(m.group("capture_ms")),
                    change_ms=float(m.group("change_ms")),
                    ocr_ms=float(m.group("ocr_ms")),
                    index_ms=float(m.group("index_ms")),
                    total_cycle_ms=float(m.group("total_cycle_ms")),
                )
            )
            continue

        m = _SCROLL_RE.match(line)
        if m:
            scroll.append(
                ScrollEstimate(
                    ts=_parse_ts(m.group("ts")),
                    dx=int(m.group("dx")),
                    dy=int(m.group("dy")),
                    response=float(m.group("response")),
                )
            )

    print(f"log: {path}  cycles={len(cycles)}  scroll_estimates={len(scroll)}")
    if cycles:
        print(f"time range: {min(c.ts for c in cycles)} .. {max(c.ts for c in cycles)}")
    print()

    _summarize_cycles("all cycles", cycles)
    print()
    _summarize_cycles("full_window=0 (incremental/scroll)", [c for c in cycles if not c.full_window])
    print()
    _summarize_cycles("full_window=1 (full OCR)", [c for c in cycles if c.full_window])
    print()
    _summarize_scroll(scroll)
    print()

    if cycles:
        slow = sorted(cycles, key=lambda c: c.total_cycle_ms, reverse=True)[:10]
        print("top 10 slowest cycles:")
        for c in slow:
            print(
                f"  {c.ts} full_window={int(c.full_window)} total_cycle_ms={c.total_cycle_ms:.1f} ocr_ms={c.ocr_ms:.1f} changed_regions={c.changed_regions} words={c.total_words}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

