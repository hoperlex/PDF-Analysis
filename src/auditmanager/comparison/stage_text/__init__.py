"""Pure deterministic Stage Text evidence; persistence is a separate slice."""

from .exact import ExactExclusion, SheetLink, prove_exact_exclusions
from .fragments import FragmentRefused, TextFragment, extract_fragments

__all__ = [
    "ExactExclusion", "FragmentRefused", "SheetLink", "TextFragment",
    "extract_fragments", "prove_exact_exclusions",
]
