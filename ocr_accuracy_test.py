"""Run a lightweight OCR/search accuracy benchmark against the saved crop."""

from pathlib import Path

from PIL import Image

from ocr.engine import recognize_image
from ocr.index import build_ocr_index
from search.fuzzy import fuzzy_search


TEST_IMAGE = Path("test_crop.png")
REPORT_PATH = Path("ocr_accuracy_report.txt")

# These cases are intentionally simple and visible in test_crop.png.
# They measure whether the current OCR + fuzzy pipeline can surface an
# obviously relevant result near the top for both exact and partial queries.
TEST_CASES = [
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


def main():
    if not TEST_IMAGE.exists():
        raise FileNotFoundError(f"Missing benchmark image: {TEST_IMAGE}")

    image = Image.open(TEST_IMAGE).convert("RGB")
    words = recognize_image(image, window_rect={"left": 0, "top": 0})
    index = build_ocr_index(words)

    hit_at_1 = 0
    hit_at_5 = 0
    hit_at_10 = 0
    lines = [
        f"Image: {TEST_IMAGE}",
        f"OCR words: {len(words)}",
        f"Indexed entries: {len(index)}",
        "",
    ]

    for case in TEST_CASES:
        query = case["query"]
        expected = case["expected"]
        results = fuzzy_search(query, index, limit=10)
        top_1 = results[:1]
        top_5 = results[:5]
        top_10 = results[:10]
        pass_1 = any(_matches_expected(result, expected) for result in top_1)
        pass_5 = any(_matches_expected(result, expected) for result in top_5)
        pass_10 = any(_matches_expected(result, expected) for result in top_10)
        hit_at_1 += int(pass_1)
        hit_at_5 += int(pass_5)
        hit_at_10 += int(pass_10)

        lines.append(
            f"query={query!r} expected={expected} hit@1={pass_1} hit@5={pass_5} hit@10={pass_10}"
        )
        for result in top_5:
            lines.append(f"  - {_format_result(result)}")
        if not results:
            lines.append("  - <no matches>")
        lines.append("")

    total = len(TEST_CASES)
    lines.insert(
        4,
        (
            f"Summary: hit@1={hit_at_1}/{total} ({hit_at_1 / total:.0%}), "
            f"hit@5={hit_at_5}/{total} ({hit_at_5 / total:.0%}), "
            f"hit@10={hit_at_10}/{total} ({hit_at_10 / total:.0%})"
        ),
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote OCR accuracy report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
