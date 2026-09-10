"""The PC-01 input envelope, as an executable reference check.

`PROTOTYPE_PROFILE.md` section 7.1 states the envelope in prose: one unencrypted PDF, at
most 25 MiB and 30 pages, every page carrying extractable embedded text; scanned,
password-protected, mixed-file and companion-archive inputs fail explicitly and OCR is
never silently substituted. This module turns that prose into rules with stable ids, so
a negative fixture can be shown to violate *the specific rule it is named for* rather
than merely "failing".

This is fixture-side reference logic, not the product implementation. Ingest lives under
`src/`, which this session does not own. The value here is that every lane measures
rejection against the same enumerated rules.

The three-state result matters more than it looks. A rule that could not be evaluated
reports `NOT_EVALUATED`, never `PASS`: an encrypted file's page count is unknown, not
acceptable, and recording "unreadable" as "within the envelope" would let a document
through on a claim nobody checked.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import pdfextract

MAX_BYTES = 25 * 1024 * 1024
MAX_PAGES = 30

RULE_IS_PDF = "ENV-PDF"
RULE_NOT_ENCRYPTED = "ENV-ENCRYPTED"
RULE_MAX_BYTES = "ENV-SIZE"
RULE_MAX_PAGES = "ENV-PAGES"
RULE_TEXT_LAYER = "ENV-TEXT"

RULES = (RULE_IS_PDF, RULE_NOT_ENCRYPTED, RULE_MAX_BYTES, RULE_MAX_PAGES, RULE_TEXT_LAYER)

RULE_DESCRIPTIONS = {
    RULE_IS_PDF: "the input is a PDF file",
    RULE_NOT_ENCRYPTED: "the PDF is not encrypted or password-protected",
    RULE_MAX_BYTES: f"the file is at most {MAX_BYTES} bytes (25 MiB)",
    RULE_MAX_PAGES: f"the document has at most {MAX_PAGES} pages",
    RULE_TEXT_LAYER: "every page carries extractable embedded text",
}


class Status(str, Enum):
    PASS = "pass"
    VIOLATED = "violated"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True)
class RuleResult:
    rule: str
    status: Status
    detail: str


@dataclass(frozen=True)
class EnvelopeReport:
    results: tuple[RuleResult, ...]

    def by_rule(self, rule: str) -> RuleResult:
        for result in self.results:
            if result.rule == rule:
                return result
        raise KeyError(rule)

    @property
    def violations(self) -> tuple[str, ...]:
        return tuple(r.rule for r in self.results if r.status is Status.VIOLATED)

    @property
    def not_evaluated(self) -> tuple[str, ...]:
        return tuple(r.rule for r in self.results if r.status is Status.NOT_EVALUATED)

    @property
    def accepted(self) -> bool:
        """Accepted only when every rule was evaluated and every rule passed."""
        return all(r.status is Status.PASS for r in self.results)


def check(data: bytes) -> EnvelopeReport:
    """Evaluate every envelope rule against raw input bytes."""
    results: list[RuleResult] = []

    is_pdf = data[:5] == b"%PDF-"
    results.append(RuleResult(
        RULE_IS_PDF,
        Status.PASS if is_pdf else Status.VIOLATED,
        "header is %PDF-" if is_pdf else f"header is {data[:8]!r}, not %PDF-",
    ))

    size_ok = len(data) <= MAX_BYTES
    results.append(RuleResult(
        RULE_MAX_BYTES,
        Status.PASS if size_ok else Status.VIOLATED,
        f"{len(data)} bytes, limit {MAX_BYTES}",
    ))

    if not is_pdf:
        unknown = "not a PDF, so this rule could not be evaluated"
        results.append(RuleResult(RULE_NOT_ENCRYPTED, Status.NOT_EVALUATED, unknown))
        results.append(RuleResult(RULE_MAX_PAGES, Status.NOT_EVALUATED, unknown))
        results.append(RuleResult(RULE_TEXT_LAYER, Status.NOT_EVALUATED, unknown))
        return EnvelopeReport(tuple(results))

    try:
        doc = pdfextract.Document.load(data)
    except pdfextract.EncryptedPdfError as exc:
        results.append(RuleResult(RULE_NOT_ENCRYPTED, Status.VIOLATED, str(exc)))
        unknown = "the document is encrypted, so this rule could not be evaluated"
        results.append(RuleResult(RULE_MAX_PAGES, Status.NOT_EVALUATED, unknown))
        results.append(RuleResult(RULE_TEXT_LAYER, Status.NOT_EVALUATED, unknown))
        return EnvelopeReport(tuple(results))
    except pdfextract.PdfParseError as exc:
        results.append(RuleResult(
            RULE_NOT_ENCRYPTED, Status.NOT_EVALUATED, f"unreadable PDF: {exc}"
        ))
        unknown = f"unreadable PDF: {exc}"
        results.append(RuleResult(RULE_MAX_PAGES, Status.NOT_EVALUATED, unknown))
        results.append(RuleResult(RULE_TEXT_LAYER, Status.NOT_EVALUATED, unknown))
        return EnvelopeReport(tuple(results))

    results.append(RuleResult(RULE_NOT_ENCRYPTED, Status.PASS, "no /Encrypt in the trailer"))

    pages = doc.pages()
    pages_ok = len(pages) <= MAX_PAGES
    results.append(RuleResult(
        RULE_MAX_PAGES,
        Status.PASS if pages_ok else Status.VIOLATED,
        f"{len(pages)} pages, limit {MAX_PAGES}",
    ))

    blank: list[int] = []
    unreadable: str | None = None
    for index, page in enumerate(pages, start=1):
        try:
            text = pdfextract.page_text(doc, page)
        except pdfextract.PdfParseError as exc:
            unreadable = f"page {index}: {exc}"
            break
        if not text.strip():
            blank.append(index)
    if unreadable is not None:
        results.append(RuleResult(RULE_TEXT_LAYER, Status.VIOLATED, unreadable))
    elif blank:
        results.append(RuleResult(
            RULE_TEXT_LAYER,
            Status.VIOLATED,
            "no extractable text on page(s) " + ", ".join(str(p) for p in blank),
        ))
    else:
        results.append(RuleResult(
            RULE_TEXT_LAYER, Status.PASS, f"all {len(pages)} pages carry extractable text"
        ))

    return EnvelopeReport(tuple(results))
