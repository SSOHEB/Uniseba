"""Centralized runtime configuration for Uniseba.

This file is the single source of truth for the tunable defaults used by the
integrated OCR/search runtime. Modules should import the constants they need
directly from here instead of calling getattr(config, ...) with local fallbacks.
"""

# UI / search loop settings

# Delay, in milliseconds, before a typed query is applied.
DEBOUNCE_MS = 250

# Poll interval, in milliseconds, for OCR queue updates and semantic results.
POLL_MS = 100

# Global shortcut used to show or hide the Uniseba search UI.
GLOBAL_SHORTCUT = "ctrl+shift+u"

# Maximum number of matches returned by fuzzy, semantic, or merged search.
MAX_RESULTS = 50


# Search scoring settings

# Minimum query length required before search runs.
MIN_QUERY_LENGTH = 2

# Minimum accepted fuzzy score. The previous code effectively clamped this to 90.
FUZZY_THRESHOLD = 82

# Weight of fuzzy matching when fuzzy and semantic scores are merged.
FUZZY_WEIGHT = 0.4

# Weight of semantic matching when fuzzy and semantic scores are merged.
SEMANTIC_WEIGHT = 0.6

# Reject OCR words shorter than this before fuzzy matching.
MIN_WORD_LENGTH = 2

# Minimum proxy confidence required for fuzzy search candidates.
MIN_CONFIDENCE = 0.15


# Semantic search settings

# Sentence-transformers model used for semantic reranking.
SEMANTIC_MODEL_NAME = "all-MiniLM-L6-v2"

# When True, only load a model that already exists locally.
SEMANTIC_LOCAL_FILES_ONLY = True


# OCR thread timing and capture settings

# Background OCR scan interval in milliseconds.
SCAN_INTERVAL_MS = 150

# Smallest top-level window width allowed for normal OCR targeting.
MIN_TARGET_WIDTH = 300

# Smallest top-level window height allowed for normal OCR targeting.
MIN_TARGET_HEIGHT = 200

# Minimum length for a window title to be considered a valid normal target.
MIN_TARGET_TITLE_LENGTH = 2

# Region grid used for change detection.
CHANGE_GRID = (6, 6)

# Mean grayscale thumbnail diff required to mark a region as changed.
CHANGE_THRESHOLD = 2.5

# Thumbnail size used during region diffing.
CHANGE_THUMB_SIZE = (32, 32)

# Downscale factor applied to OCR regions before they are sent into the OCR engine.
OCR_DOWNSCALE = 0.75

# Minimum time between published OCR updates, in milliseconds.
OCR_UPDATE_DEBOUNCE_MS = 100

# Maximum allowed OCR word-count jump before a frame is treated as unstable.
OCR_STABILITY_COUNT_THRESHOLD = 40

# Force a refresh even when no region changed after this many milliseconds.
FORCED_OCR_INTERVAL_MS = 200


# OCR target filtering settings

# Exact lowercase window titles that should never be selected as OCR targets.
BLOCKED_WINDOW_TITLES = frozenset({"windows powershell", "uniseba search"})

# Lowercase prefixes that should be rejected as OCR targets.
BLOCKED_WINDOW_PREFIXES = ("uniseba",)

# Console keywords that cause console windows to be rejected during OCR targeting.
BLOCKED_CONSOLE_KEYWORDS = ("powershell", "python")

# Desktop shell text that identifies the Windows desktop pseudo-window.
DESKTOP_WINDOW_KEYWORD = "program manager"
