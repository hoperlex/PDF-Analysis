"""Deterministic builder for the synthetic Russian AR acceptance corpus (P2-BHV-01).

Everything in this package is pure standard library. The repository's root lock
(`pyproject.toml` / `uv.lock`) carries no PDF library and is a single-owner hotspot that
this session does not own, so the PDF writer, the TrueType subsetter and the text
extractor are all implemented here from the file-format specifications.

Nothing here reads customer, production or real project bytes. Owner decision OD-17 rules
the PC-01 corpus synthetic-only.
"""

__all__ = [
    "content",
    "envelope",
    "negatives",
    "pdfextract",
    "pdfwrite",
    "ttfsubset",
]
