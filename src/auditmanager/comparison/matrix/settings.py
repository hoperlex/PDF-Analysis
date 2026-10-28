"""The numbers and the rule set of the algorithmic matrix, each with the line of the original it is copied from.

`CMP-MATRIX-01` (ADR-0025 decision 3, plan section 4 wave C1). The original is the product whose «Сравнение версий»
this module reproduces; its source at commit ``23f379fd`` is cited as ``settings.py:N``, ``lineage.py:N``,
``resolve.py:N`` and ``parts.py:N`` (``backend/app/services/version_comparison/``) and
``document_matching.py:N`` (``backend/app/services/stage_comparison/``). A number below is **copied**, never
chosen: changing one is a new ``ALGO_VERSION`` (the stored builds keep the version that made them).
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "ALGO_VERSION",
    "ANCHOR",
    "COVER_WORDS",
    "MATCH_CANDIDATE_FLOOR",
    "MATCH_HIGH",
    "MATCH_MARGIN",
    "MATCH_MEDIUM",
    "MATCH_TEXT_MIN_TOKENS",
    "MAX_CANDIDATES",
    "MAX_EDITS_PER_BATCH",
    "RESOLVE_BLOCK_COVER",
    "RESOLVE_BLOCK_EDGE",
    "RESOLVE_DUP_IMAGE",
    "RESOLVE_FOOTER_BAND",
    "RESOLVE_FRAC",
    "RESOLVE_FRAC_ROBUST",
    "RESOLVE_IMAGE_FRAC",
    "RESOLVE_MAX_AGAINST",
    "RESOLVE_MIN_IMAGE_AREA",
    "RESOLVE_MIN_W",
    "RESOLVE_NEIGHBOR_SPAN",
    "RESOLVE_PACKAGE_MIN",
    "RESOLVE_PACKAGE_SHARE",
    "RESOLVE_TABLE_COVER",
    "RESOLVE_TEMPLATE_SIM",
    "RESOLVE_TITLE_MIN_LEN",
    "RESOLVE_COUNT_FRAC",
    "RESOLVE_W_MARK",
    "RESOLVE_W_NUMBER",
    "RESOLVE_W_WORD",
    "RULES",
    "RULES_VERSION",
    "STRUCTURE_REVISION",
]

#: Names this implementation. The unique key of ``comparison_matrix`` includes it, so a change to any rule or
#: weight below is a new value and the old builds stay as they are (at most 64 characters, ``ck_..._algo_version``).
ALGO_VERSION: Final[str] = "cmp-matrix/1"
#: The original's ``LINEAGE_REVISION`` (``lineage.py:394``): the "diverged copies" handling of duplicates is part of
#: the structure and of the signature.
STRUCTURE_REVISION: Final[str] = "copies1"
#: The rule set. ``settings.py:172`` ``MATCH_RULES_DEFAULT = "v1.2"``.
RULES_VERSION: Final[str] = "v1.2"

# -- thresholds (settings.py:92-94) ---------------------------------------------------------------------------
#: A pair at or above this score is linked with confidence ``high``.
MATCH_HIGH: Final[float] = 0.55
#: A pair at or above this score is linked with confidence ``medium`` (the assignment's acceptance threshold).
MATCH_MEDIUM: Final[float] = 0.35
#: A pair below this score is no candidate at all (its weight is zero in the assignment).
MATCH_CANDIDATE_FLOOR: Final[float] = 0.20

#: ``MATCH_RULES_V12`` (settings.py:125): ``v1.1`` (order, text, kind, shx, margin, chain, stale) plus resolve,
#: package, direct, permit, pageno, group. ``shx`` (the stamp read from hidden SHX text) is **not** carried: the page
#: profile holds no such text (report, limits). ``chain`` (a non-adjacent pair only through the chain of adjacent
#: links) and ``stale`` (pair fingerprints inside a run) belong to the series, not to the matrix.
RULES: Final[frozenset[str]] = frozenset(
    {"order", "text", "kind", "margin", "resolve", "package", "direct", "permit", "pageno", "group"}
)

# -- the page score (settings.py:127-129, lineage.py:196-257) ---------------------------------------------------
#: Pair is accepted only if it beats its nearest competitor by this (``MATCH_MARGIN``, settings.py:133).
MATCH_MARGIN: Final[float] = 0.05
#: A page carries content text if it has at least this many words outside the service zones
#: (``MATCH_TEXT_MIN_TOKENS``, settings.py:135).
MATCH_TEXT_MIN_TOKENS: Final[int] = 10
#: Cover words that make an unstamped page a title page (``COVER_WORDS``, lineage.py:45).
COVER_WORDS: Final[tuple[str, ...]] = ("рабочая документация", "проектная документация", "том ", "книга ")
#: The most candidates an unmatched cell lists. The original lists three (``lineage.py:634``); the contract allows 8.
MAX_CANDIDATES: Final[int] = 3

# -- resolve (settings.py:137-175) --------------------------------------------------------------------------------
RESOLVE_W_MARK: Final[float] = 1.0
RESOLVE_W_WORD: Final[float] = 0.5
RESOLVE_W_NUMBER: Final[float] = 0.15
RESOLVE_FRAC: Final[float] = 0.85
RESOLVE_MIN_W: Final[float] = 3.0
RESOLVE_FRAC_ROBUST: Final[float] = 0.7
RESOLVE_MAX_AGAINST: Final[int] = 2
RESOLVE_COUNT_FRAC: Final[float] = 0.85
RESOLVE_IMAGE_FRAC: Final[float] = 0.8
RESOLVE_MIN_IMAGE_AREA: Final[int] = 150
RESOLVE_DUP_IMAGE: Final[float] = 0.97
RESOLVE_BLOCK_EDGE: Final[float] = 0.25
RESOLVE_BLOCK_COVER: Final[float] = 0.8
RESOLVE_TABLE_COVER: Final[float] = 0.6
RESOLVE_TITLE_MIN_LEN: Final[int] = 4
RESOLVE_FOOTER_BAND: Final[float] = 0.92
RESOLVE_TEMPLATE_SIM: Final[float] = 0.8
RESOLVE_NEIGHBOR_SPAN: Final[int] = 3
RESOLVE_PACKAGE_MIN: Final[int] = 2
RESOLVE_PACKAGE_SHARE: Final[float] = 0.8

#: Where a rule of this module is anchored in the original, for the report and for a reader of the code.
ANCHOR: Final[dict[str, str]] = {
    "thresholds": "settings.py:92-94",
    "rules": "settings.py:120-129, 172",
    "assignment": "lineage.py:343-392; document_matching.py:73-133",
    "features": "lineage.py:71-172",
    "score": "lineage.py:190-282",
    "content_evidence": "lineage.py:284-287",
    "duplicates": "lineage.py:290-317",
    "build": "lineage.py:397-498",
    "bridge": "lineage.py:459-476",
    "candidates": "lineage.py:612-640",
    "resolve": "resolve.py:484-573",
    "package": "resolve.py:452-482",
    "group": "resolve.py:397-450",
    "blocks": "resolve.py:351-395",
    "permit": "resolve.py:279-288",
    "pageno": "resolve.py:127-148; lineage.py:121-132",
    "direct": "lineage.py:501-508; resolve.py:307-330",
    "parts": "parts.py:27-75",
    "edits": "lineage.py:511-576; jobs.py:298-334",
    "signature": "lineage.py:694-699; jobs.py:173-175",
}

#: The most edits one batch carries (the contract's ``maxItems`` of ``ApplyComparisonMatrixEditsRequest.edits``).
MAX_EDITS_PER_BATCH: Final[int] = 500
