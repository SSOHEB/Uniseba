"""Run OCR/search accuracy benchmarks on one or more images."""

import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PIL import Image

from ocr.engine import recognize_image
from ocr.index import build_ocr_index
from search.fuzzy import fuzzy_search


DEFAULT_IMAGE = Path("test_crop.png")
DEFAULT_REPORT_PATH = Path("ocr_accuracy_report.md")
logger = logging.getLogger("uniseba.tools.ocr_accuracy")

# Backward-compatible default single-image cases.
DEFAULT_CASES = [
    {"query": "contents", "expected": ("contents",)},
    {"query": "biography", "expected": ("biography",)},
    {"query": "early", "expected": ("early",)},
    {"query": "education", "expected": ("education",)},
    {"query": "movement", "expected": ("movement",)},
    {"query": "notes", "expected": ("notes",)},
    {"query": "references", "expected": ("references",)},
    {"query": "history", "expected": ("history",)},
    {"query": "source", "expected": ("source",)},
    {"query": "gandhi", "expected": ("gandhi",)},
    {"query": "nehru", "expected": ("nehru",)},
    {"query": "jamia", "expected": ("jamia",)},
    {"query": "legacy", "expected": ("legacy",)},
    {"query": "azad", "expected": ("azad",)},
    {"query": "abdul", "expected": ("abdul",)},
    {"query": "educ", "expected": ("education",)},
    {"query": "move", "expected": ("movement",)},
    {"query": "refer", "expected": ("references",)},
    {"query": "gand", "expected": ("gandhi",)},
    {"query": "nehr", "expected": ("nehru",)},
]


def _matches_expected(result, expected_substrings):
    original = str(result.get("original", "")).strip().lower()
    word = str(result.get("word", "")).strip().lower()
    for expected in expected_substrings:
        expected = expected.lower()
        if expected in original or expected in word:
            return True
    return False


def _format_result(result):
    return (
        f"{result.get('original', '')!r} "
        f"score={result.get('fuzzy_score', 0.0):.2f} "
        f"box=({result.get('x')},{result.get('y')},{result.get('w')},{result.get('h')})"
    )


def _load_cases_from_file(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    images = data.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("cases file must contain a non-empty 'images' list")

    parsed = []
    for image_item in images:
        image_path = Path(str(image_item.get("path", "")).strip())
        if not image_path:
            raise ValueError("each image entry must include 'path'")
        cases = image_item.get("cases", [])
        if not isinstance(cases, list) or not cases:
            raise ValueError(f"image '{image_path}' must include a non-empty 'cases' list")
        normalized_cases = []
        for case in cases:
            query = str(case.get("query", "")).strip()
            expected = case.get("expected", [])
            if not query:
                raise ValueError(f"image '{image_path}' has a case with empty query")
            if isinstance(expected, str):
                expected = [expected]
            if not isinstance(expected, list) or not expected:
                raise ValueError(f"image '{image_path}' query '{query}' must include expected strings")
            normalized_cases.append({"query": query, "expected": tuple(str(x) for x in expected)})
        parsed.append({"path": image_path, "cases": normalized_cases})
    return parsed


def _default_image_set():
    return [{"path": DEFAULT_IMAGE, "cases": DEFAULT_CASES}]


def _evaluate_image(image_path: Path, cases, limit: int):
    image = Image.open(image_path).convert("RGB")
    words = recognize_image(image, window_rect={"left": 0, "top": 0})
    index = build_ocr_index(words)

    hit_at_1 = 0
    hit_at_5 = 0
    hit_at_10 = 0
    case_rows = []

    for case in cases:
        query = case["query"]
        expected = case["expected"]
        results = fuzzy_search(query, index, limit=max(limit, 10))
        top_1 = results[:1]
        top_5 = results[:5]
        top_10 = results[:10]
        pass_1 = any(_matches_expected(result, expected) for result in top_1)
        pass_5 = any(_matches_expected(result, expected) for result in top_5)
        pass_10 = any(_matches_expected(result, expected) for result in top_10)
        hit_at_1 += int(pass_1)
        hit_at_5 += int(pass_5)
        hit_at_10 += int(pass_10)
        case_rows.append(
            {
                "query": query,
                "expected": expected,
                "hit_at_1": pass_1,
                "hit_at_5": pass_5,
                "hit_at_10": pass_10,
                "top_results": results[:5],
            }
        )

    return {
        "image": image_path,
        "ocr_words": len(words),
        "indexed_entries": len(index),
        "total_cases": len(cases),
        "hit_at_1": hit_at_1,
        "hit_at_5": hit_at_5,
        "hit_at_10": hit_at_10,
        "cases": case_rows,
    }


def _pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    return f"{(numerator / denominator):.0%}"


def _build_markdown_report(results):
    total_cases = sum(r["total_cases"] for r in results)
    total_hit_at_1 = sum(r["hit_at_1"] for r in results)
    total_hit_at_5 = sum(r["hit_at_5"] for r in results)
    total_hit_at_10 = sum(r["hit_at_10"] for r in results)

    lines = [
        "# OCR Accuracy Benchmark Report",
        "",
        f"- Images tested: **{len(results)}**",
        f"- Total queries: **{total_cases}**",
        f"- Aggregate hit@1: **{total_hit_at_1}/{total_cases} ({_pct(total_hit_at_1, total_cases)})**",
        f"- Aggregate hit@5: **{total_hit_at_5}/{total_cases} ({_pct(total_hit_at_5, total_cases)})**",
        f"- Aggregate hit@10: **{total_hit_at_10}/{total_cases} ({_pct(total_hit_at_10, total_cases)})**",
        "",
        "## Per-Image Summary",
        "",
        "| Image | OCR Words | Indexed Entries | Queries | hit@1 | hit@5 | hit@10 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for r in results:
        lines.append(
            "| {image} | {words} | {indexed} | {queries} | {h1}/{queries} ({h1p}) | {h5}/{queries} ({h5p}) | {h10}/{queries} ({h10p}) |".format(
                image=r["image"],
                words=r["ocr_words"],
                indexed=r["indexed_entries"],
                queries=r["total_cases"],
                h1=r["hit_at_1"],
                h5=r["hit_at_5"],
                h10=r["hit_at_10"],
                h1p=_pct(r["hit_at_1"], r["total_cases"]),
                h5p=_pct(r["hit_at_5"], r["total_cases"]),
                h10p=_pct(r["hit_at_10"], r["total_cases"]),
            )
        )

    lines.append("")
    lines.append("## Case Details")
    lines.append("")
    for r in results:
        lines.append(f"### {r['image']}")
        lines.append("")
        for case in r["cases"]:
            lines.append(
                "- query=`{query}` expected={expected} hit@1={h1} hit@5={h5} hit@10={h10}".format(
                    query=case["query"],
                    expected=case["expected"],
                    h1=case["hit_at_1"],
                    h5=case["hit_at_5"],
                    h10=case["hit_at_10"],
                )
            )
            if case["top_results"]:
                for result in case["top_results"]:
                    lines.append(f"  - {_format_result(result)}")
            else:
                lines.append("  - <no matches>")
        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="OCR accuracy benchmark for one or more images")
    parser.add_argument(
        "--cases-file",
        type=Path,
        default=None,
        help="JSON file describing images and test cases",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Output report path (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Fuzzy result limit used per query (default: 10)",
    )
    args = parser.parse_args()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)
    file_handler = RotatingFileHandler(
        "ocr_accuracy.log",
        maxBytes=1_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if args.cases_file:
        if not args.cases_file.exists():
            raise FileNotFoundError(f"Missing cases file: {args.cases_file}")
        image_sets = _load_cases_from_file(args.cases_file)
    else:
        if not DEFAULT_IMAGE.exists():
            raise FileNotFoundError(f"Missing benchmark image: {DEFAULT_IMAGE}")
        image_sets = _default_image_set()

    results = []
    for item in image_sets:
        image_path = item["path"]
        if not image_path.exists():
            raise FileNotFoundError(f"Missing benchmark image: {image_path}")
        results.append(_evaluate_image(image_path, item["cases"], args.limit))

    report = _build_markdown_report(results)
    args.report.write_text(report, encoding="utf-8")
    logger.info("Wrote OCR accuracy report to %s", args.report)


if __name__ == "__main__":
    main()
