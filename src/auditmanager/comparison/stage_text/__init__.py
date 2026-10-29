"""Pure deterministic Stage Text evidence; persistence is a separate slice."""

from .exact import ExactExclusion, SheetLink, prove_exact_exclusions
from .differences import RawDifference, RawTextPass, build_raw_differences
from .fragments import FragmentRefused, TextFragment, extract_fragments
from .hints import CrossSheetHint, find_cross_sheet_hints

__all__ = [
    "CrossSheetHint", "ExactExclusion", "FragmentRefused", "RawDifference",
    "RawTextPass", "SheetLink", "TextFragment", "build_raw_differences",
    "extract_fragments", "find_cross_sheet_hints", "prove_exact_exclusions",
]
