"""Oracles and figures for the finding to portal block relation, on real stored artifacts (D-353, D-354). Not a test module.

The rule under proof (``analysis.geometry.finding_blocks``) *estimates* where an evidence quote lies on its page from the
extractor's line boxes (a cut proportional to characters within a line). Two independent witnesses are held against it here:

* **the glyphs** -- :class:`PdfOracle` asks the PDF itself where the quote's characters are (``pdfplumber`` ``Page.search`` with
  the extraction options the text layer was built with, one box per line of the quote), and which portal blocks cover that
  place. A linked block that does not even touch the quote's glyph boxes is a **wrong** link; a block that covers at least
  half of a glyph box but is not linked is a **missed** one;
* **the portal's own words** -- :func:`text_verdict` compares the quote with the block's recognised text (normalised: case,
  ``ё``, spaces, punctuation, line-end hyphenation), the precision proxy the portal's reading gives.

Nothing here imports the rule's private helpers: the coverage arithmetic is restated (three lines) so that a defect in the rule's
version cannot hide in the oracle's.
"""

from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pdfplumber

from auditmanager.analysis.geometry.finding_blocks import (
    COVERAGE,
    WITNESS_MIN_CHARACTERS,
    EvidenceSpan,
    PortalBox,
    link_evidence,
)
from auditmanager.analysis.stages.extraction import TEXT_OPTIONS

Box = tuple[float, float, float, float]

#: A quote's words found in a block's words at least this share: "most of its words" (the precision proxy's lenient reading).
MOST_OF_THE_WORDS = 0.5


# -- the text oracle -------------------------------------------------------------------------


def normalise_text(text: str) -> str:
    """Case, ``ё``, soft hyphens, end-of-line hyphenation, punctuation and runs of spaces folded away."""
    text = unicodedata.normalize("NFKC", text).casefold().replace("ё", "е").replace("­", "")
    text = re.sub(r"-[ \t]*\n[ \t]*", "", text)
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def text_verdict(quote: str, block_text: str) -> tuple[str, float]:
    """``("contains" | "most" | "some" | "none", share of the quote's words found in the block)``."""
    wanted, held = normalise_text(quote), normalise_text(block_text)
    words, vocabulary = wanted.split(), set(held.split())
    if not words:
        return "none", 0.0
    share = sum(1 for word in words if word in vocabulary) / len(words)
    if f" {wanted} " in f" {held} ":
        return "contains", 1.0
    if share >= MOST_OF_THE_WORDS:
        return "most", share
    return ("some" if share > 0 else "none"), share


# -- the glyph oracle ------------------------------------------------------------------------


def covered_share(box: Box, block: Box) -> float:
    """The share of ``box``'s area that ``block`` covers (both normalised, top-left origin)."""
    across = min(box[2], block[2]) - max(box[0], block[0])
    down = min(box[3], block[3]) - max(box[1], block[1])
    if across <= 0 or down <= 0:
        return 0.0
    return across * down / ((box[2] - box[0]) * (box[3] - box[1]))


@dataclass(frozen=True, slots=True)
class LayerPage:
    page_number: int
    char_start: int
    char_end: int
    text: str
    width_pt: float
    height_pt: float


class PdfOracle:
    """The PDF's own answer to "where on its page is this quotation"."""

    def __init__(self, pdf: bytes) -> None:
        self._pdf = pdfplumber.open(io.BytesIO(pdf))
        self._textmaps: dict[int, Any] = {}
        self.layer: list[LayerPage] = []
        cursor = 0
        for number, page in enumerate(self._pdf.pages, start=1):
            text = unicodedata.normalize("NFC", page.extract_text(**TEXT_OPTIONS) or "")
            self.layer.append(LayerPage(number, cursor, cursor + len(text), text, float(page.width), float(page.height)))
            cursor += len(text)

    def close(self) -> None:
        self._pdf.close()

    @property
    def text(self) -> str:
        return "".join(page.text for page in self.layer)

    def quote_boxes(self, page_number: int, char_start: int, quote: str) -> list[Box] | None:
        """One box per line of the quote at global offset ``char_start``, normalised to the page; ``None`` when not found.

        ``None`` is never an empty list: a quote the oracle cannot place is *unplaced*, not "nowhere".
        """
        entry = self.layer[page_number - 1]
        local = char_start - entry.char_start
        if entry.text[local:local + len(quote)] != quote:
            return None
        positions = [match.start() for match in re.finditer(re.escape(quote), entry.text)]
        if local not in positions:
            return None
        if page_number not in self._textmaps:
            self._textmaps[page_number] = self._pdf.pages[page_number - 1].get_textmap(**TEXT_OPTIONS)
        found = self._textmaps[page_number].search(quote, regex=False, case=True)
        if len(found) != len(positions):
            return None
        chars = [char for char in found[positions.index(local)]["chars"] if char.get("text", "").strip()]
        if not chars:
            return None
        lines: list[list[dict[str, Any]]] = []
        for char in chars:
            if lines and char["top"] < lines[-1][-1]["bottom"] - 0.5 * (char["bottom"] - char["top"]):
                lines[-1].append(char)
            else:
                lines.append([char])
        return [
            (
                min(c["x0"] for c in line) / entry.width_pt, min(c["top"] for c in line) / entry.height_pt,
                max(c["x1"] for c in line) / entry.width_pt, max(c["bottom"] for c in line) / entry.height_pt,
            )
            for line in lines
        ]


def holders(boxes: Sequence[Box], blocks: Mapping[str, Box]) -> tuple[set[str], set[str]]:
    """``(blocks covering at least COVERAGE of some line box, blocks touching some line box)`` of one quotation."""
    holding: set[str] = set()
    touching: set[str] = set()
    for identifier, block in blocks.items():
        shares = [covered_share(box, block) for box in boxes]
        if any(share > 0 for share in shares):
            touching.add(identifier)
        if any(share >= COVERAGE for share in shares):
            holding.add(identifier)
    return holding, touching


# -- the rule with the second witness (D-450) ------------------------------------------------

#: Cyrillic letters a reading writes with their Latin look-alikes.
HOMOGLYPHS = str.maketrans("аеорсхАЕОРСХ", "aeopcxAEOPCX")
NOISE_RATES = (0.1, 0.3)


def degrade(block_id: str, text: str, rate: float) -> str:
    """The recognised text as a damaging reading gives it: a deterministic ``rate`` of its words with a look-alike Latin letter
    (or, with none to swap, a letter short; a one-letter word becomes a bar). Nothing is added to the text: damage makes a word
    stop matching the quotation's."""
    pieces = []
    for number, piece in enumerate(re.split(r"(\s+)", text)):
        if piece.strip():
            draw = int(hashlib.sha256(f"{block_id}:{number}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
            if draw < rate:
                swapped = piece.translate(HOMOGLYPHS)
                piece = swapped if swapped != piece else (piece[:-1] or "|")
        pieces.append(piece)
    return "".join(pieces)


class MemoOracle:
    """``PdfOracle`` that answers a placement it has given before from memory: the same quotations are held against several rules."""

    def __init__(self, oracle: PdfOracle) -> None:
        self._oracle = oracle
        self._memo: dict[tuple[int, int, str], Any] = {}

    def quote_boxes(self, page_number: int, char_start: int, quote: str) -> Any:
        key = (page_number, char_start, quote)
        if key not in self._memo:
            self._memo[key] = self._oracle.quote_boxes(page_number, char_start, quote)
        return self._memo[key]


def rule_links(
    evidence: Sequence[EvidenceFact], lines: Sequence[Any], sizes: Mapping[int, tuple[float, float]], blocks: Sequence[BlockFact],
    unlinked: set[int], texts: Mapping[str, str] | None, min_characters: int = WITNESS_MIN_CHARACTERS,
) -> list[str]:
    """``finding_blocks.link_evidence`` over the stored documents: the shipped rule, called as the adapter calls it, with the
    recognised text (the second witness) when ``texts`` is given. ``unlinked`` are the adapter's ``unlinked_pages``."""
    by_page: dict[int, list[Any]] = {}
    for line in lines:
        by_page.setdefault(line.page_number, []).append(line)
    boxes = [PortalBox(b.portal_block_id, b.page_number, *b.bbox_norm) for b in blocks]
    spans = [EvidenceSpan(f.page_number, f.char_start, f.char_end, f.quote) for f in evidence if f.page_number not in unlinked]
    pages = {n: size for n, size in sizes.items() if n not in unlinked}
    return list(link_evidence(
        spans, lines=by_page, pages=pages, blocks=boxes, block_texts=texts, witness_min_characters=min_characters,
    ))


def require_same_links(reproduced: Mapping[str, Sequence[str]], shipped: Mapping[str, Sequence[str]]) -> None:
    """The guard of the reproduction: the rule called without the text must give the shipped adapter's answer for every finding
    (and for no other), or what is measured with the text is not the shipped rule's second witness."""
    differing = sorted(uid for uid in set(reproduced) | set(shipped) if list(reproduced.get(uid, ())) != list(shipped.get(uid, ())))
    if differing:
        raise AssertionError(
            f"the reproduction of the adapter's rule differs for {len(differing)} of {len(shipped)} findings, e.g. {differing[:3]}"
        )


# -- one run's links against the witnesses ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvidenceFact:
    page_number: int
    char_start: int
    char_end: int
    quote: str


@dataclass(frozen=True, slots=True)
class BlockFact:
    portal_block_id: str
    page_number: int
    block_type: str
    bbox_norm: Box
    text: str | None


def analyse(
    *,
    items: Sequence[tuple[str, Sequence[str], str]],
    evidence: Mapping[str, Sequence[EvidenceFact]],
    blocks: Sequence[BlockFact],
    unlinked_pages: Sequence[int],
    oracle: PdfOracle,
) -> dict[str, Any]:
    """Hold the links against the glyphs and the recognised text.

    ``items`` are ``(finding_uid, linked portal block ids, label)``; ``evidence`` the canonical observation's evidence by
    finding uid; ``label`` is carried to the report (a sweep's unit kind, a finding's title).
    """
    by_id = {block.portal_block_id: block for block in blocks}
    boxes = {block.portal_block_id: block.bbox_norm for block in blocks}
    unlinked = set(unlinked_pages)
    findings: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    for uid, linked, label in items:
        facts = list(evidence.get(uid, ()))
        record: dict[str, Any] = {"finding_uid": uid, "label": label, "linked": list(linked), "evidence": []}
        truth: set[str] = set()
        touched: set[str] = set()
        placeable = False
        for fact in facts:
            placed = oracle.quote_boxes(fact.page_number, fact.char_start, fact.quote)
            on_page = {key: box for key, box in boxes.items() if by_id[key].page_number == fact.page_number}
            entry: dict[str, Any] = {
                "page": fact.page_number, "quote": fact.quote, "unlinked_page": fact.page_number in unlinked,
                "glyph_boxes": None if placed is None else [[round(v, 4) for v in box] for box in placed],
            }
            if placed is not None and fact.page_number not in unlinked:
                hold, touch = holders(placed, on_page)
                entry["glyph_holders"], truth, touched = sorted(hold), truth | hold, touched | touch
                placeable = placeable or bool(hold)
            record["evidence"].append(entry)
        record["has_truth"] = placeable
        record["truth_blocks"] = sorted(truth)
        record["unlinked_only"] = bool(facts) and all(e["unlinked_page"] for e in record["evidence"])
        findings.append(record)
        for identifier in linked:
            block = by_id[identifier]
            same_page = [f for f in facts if f.page_number == block.page_number]
            verdicts = [(f, text_verdict(f.quote, block.text)) for f in same_page] if block.text is not None else []
            best = max(verdicts, key=lambda pair: pair[1][1], default=None)
            judged = [e for e in record["evidence"] if e["page"] == block.page_number and e["glyph_boxes"] is not None]
            if not judged:
                geometry = "unplaced"
            elif identifier in truth:
                geometry = "holds"
            elif identifier in touched:
                geometry = "marginal"
            else:
                geometry = "WRONG"
            pair = {
                "finding_uid": uid, "label": label, "portal_block_id": identifier, "page": block.page_number,
                "block_type": block.block_type, "bbox_norm": list(block.bbox_norm), "geometry": geometry,
                "text": None if best is None else best[1][0], "word_share": None if best is None else round(best[1][1], 3),
                "quote": None if best is None else best[0].quote,
                "block_text": block.text,
            }
            pairs.append(pair)
        for identifier in sorted(truth - set(linked)):
            misses.append({
                "finding_uid": uid, "label": label, "portal_block_id": identifier, "page": by_id[identifier].page_number,
                "block_type": by_id[identifier].block_type, "bbox_norm": list(by_id[identifier].bbox_norm),
                "quotes": [e["quote"] for e in record["evidence"] if identifier in e.get("glyph_holders", ())],
            })
    return {"findings": findings, "pairs": pairs, "misses": misses, "unlinked_pages": sorted(unlinked)}


def figures(analysis: Mapping[str, Any], *, label_of: Any = None) -> dict[str, Any]:
    """The counts and shares of one :func:`analyse` result, overall and by label kind."""
    findings, pairs, misses = analysis["findings"], analysis["pairs"], analysis["misses"]
    on_linkable = [f for f in findings if not f["unlinked_only"]]
    linked = [f for f in on_linkable if f["linked"]]
    with_truth = [f for f in on_linkable if f["has_truth"]]
    truth_pairs = sum(len(f["truth_blocks"]) for f in on_linkable)
    texted = [p for p in pairs if p["text"] is not None]
    geometry = Counter(p["geometry"] for p in pairs)

    def share(numerator: int, denominator: int) -> float | None:
        return None if denominator == 0 else round(numerator / denominator, 4)

    judged = [p for p in pairs if p["geometry"] != "unplaced"]
    result: dict[str, Any] = {
        "findings": len(findings),
        "findings_on_unlinked_pages_only": len(findings) - len(on_linkable),
        "findings_with_a_block": len(linked),
        "coverage": share(len(linked), len(on_linkable)),
        "findings_whose_glyphs_a_block_holds": len(with_truth),
        "coverage_ceiling_by_glyphs": share(len(with_truth), len(on_linkable)),
        "links": len(pairs),
        "links_by_geometry": dict(geometry),
        "link_precision_by_glyphs": share(geometry["holds"] + geometry["marginal"], len(judged)),
        "link_precision_strict_by_glyphs": share(geometry["holds"], len(judged)),
        "links_with_recognised_text": len(texted),
        "text_contains": sum(1 for p in texted if p["text"] == "contains"),
        "text_most_words": sum(1 for p in texted if p["text"] in ("contains", "most")),
        "precision_text_contains": share(sum(1 for p in texted if p["text"] == "contains"), len(texted)),
        "precision_text_most_words": share(sum(1 for p in texted if p["text"] in ("contains", "most")), len(texted)),
        "links_to_blocks_without_text": len(pairs) - len(texted),
        "wrong": geometry["WRONG"],
        "missed_links": len(misses),
        "recall_by_glyphs": share(truth_pairs - len(misses), truth_pairs) if truth_pairs else None,
    }
    if label_of is not None:
        kinds: dict[str, dict[str, Any]] = {}
        for kind in sorted({label_of(f["label"]) for f in findings}):
            subset = [f for f in on_linkable if label_of(f["label"]) == kind]
            subset_pairs = [p for p in pairs if label_of(p["label"]) == kind]
            kind_texted = [p for p in subset_pairs if p["text"] is not None]
            kinds[kind] = {
                "text_contains": share(sum(1 for p in kind_texted if p["text"] == "contains"), len(kind_texted)),
                "text_most_words": share(sum(1 for p in kind_texted if p["text"] in ("contains", "most")), len(kind_texted)),
                "findings": len(subset),
                "with_a_block": sum(1 for f in subset if f["linked"]),
                "coverage": share(sum(1 for f in subset if f["linked"]), len(subset)),
                "links": len(subset_pairs),
                "wrong": sum(1 for p in subset_pairs if p["geometry"] == "WRONG"),
                "marginal": sum(1 for p in subset_pairs if p["geometry"] == "marginal"),
                "missed": sum(1 for m in misses if label_of(m["label"]) == kind),
            }
        result["by_kind"] = kinds
    return result
