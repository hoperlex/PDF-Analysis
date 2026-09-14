#!/usr/bin/env python3
"""Check that the PC-02 corpus is what its manifest says it is.

    .venv/bin/python tools/validation/corpus_check.py \
        fixtures/validation/PC-02/corpus_manifest.json
    .venv/bin/python tools/validation/corpus_check.py --self-test

This is deliberately not the generator's own verification pass. The generator checks the
thing in its hand; this checks the thing on disk, against the manifest a validation
session will actually read, with an extractor the writer does not share code with. A
corpus whose ground truth is wrong does not measure the model - it measures the ground
truth - and nobody downstream would be able to tell.

## Why `--self-test` exists

Ten tests in this programme have passed or failed without exercising what they named, and
the shape was identical every time: the test asserted a property of the fixture rather
than of the code. A checker that validates its own corpus is exactly where that goes
wrong - it is trivially green, and stays green if half of it is deleted.

So every assertion here carries a stable check id, and `--self-test` breaks the corpus in
one specific way per assertion and requires that assertion to fire. A mutation that
merely crashes proves nothing: the self-test asserts the *named check* reported the
failure, and it separately asserts the unmutated copy is clean, so "always red" fails
too. Both halves are reported.

Exit codes: 0 when the corpus matches the manifest (or, with `--self-test`, when every
assertion was shown both red and green); 1 otherwise; 2 on a usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Session A4's envelope rules and reference extractor, imported read-only. This task owns
# none of `tools/fixtures/**`; reusing them is what keeps one set of enumerated rules
# behind every lane's rejection.
sys.path.insert(0, str(REPO_ROOT / "tools" / "fixtures"))

from ar_corpus import envelope, pdfextract  # noqa: E402

MANIFEST_SCHEMA = "pc02-validation-corpus/1"

MIN_MEASURABLE = 12
MAX_MEASURABLE = 16
SEEDED_DOCUMENTS = 5
MIN_NEGATIVE = 2
MAX_NEGATIVE = 4

FINDING_LABELS = ["useful", "incorrect", "unclear"]
CATEGORIES = ["internal_contradiction", "explicit_placeholder"]
PROVENANCE_VALUES = ("synthetic", "anonymized")

_RULE_CHECK = {
    envelope.RULE_IS_PDF: "CHK-ENVELOPE-PDF",
    envelope.RULE_NOT_ENCRYPTED: "CHK-ENVELOPE-ENCRYPTED",
    envelope.RULE_MAX_BYTES: "CHK-ENVELOPE-SIZE",
    envelope.RULE_MAX_PAGES: "CHK-ENVELOPE-PAGES",
    envelope.RULE_TEXT_LAYER: "CHK-ENVELOPE-TEXT",
}

CHECKS = (
    "CHK-SCHEMA",
    "CHK-PROVENANCE",
    "CHK-ANONYMIZED-BYTES",
    "CHK-FILE-PRESENT",
    "CHK-SHA256",
    "CHK-BYTES",
    "CHK-PAGES-DECLARED",
    "CHK-PAGE-TEXT-SHA",
    "CHK-ENVELOPE-PDF",
    "CHK-ENVELOPE-ENCRYPTED",
    "CHK-ENVELOPE-SIZE",
    "CHK-ENVELOPE-PAGES",
    "CHK-ENVELOPE-TEXT",
    "CHK-QUOTATION-PAGE",
    "CHK-QUOTATION-OFFSET",
    "CHK-QUOTATION-INDEPENDENT",
    "CHK-CATEGORY",
    "CHK-LABELS",
    "CHK-CONTROL-CLEAN",
    "CHK-COMPOSITION",
    "CHK-NEGATIVE-RULE",
    "CHK-NEGATIVE-EVALUATED",
    "CHK-INDEPENDENT-AVAILABLE",
    "CHK-SESSION-SCHEMA",
)

SESSION_SCHEMA_ID = "https://pdf-analysis.invalid/schemas/pc02-session-record/1"
SESSION_RECORD_TYPES = (
    "finding_record",
    "document_record",
    "envelope_refusal_record",
    "post_session_record",
)


@dataclass(frozen=True)
class Problem:
    check: str
    message: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.message}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------------------
# Independent extraction
# --------------------------------------------------------------------------------------


class IndependentExtractor:
    """A reader that shares no code with the one that wrote the corpus.

    `ar_corpus.pdfextract` defines the offset semantics the manifest records, so it has
    to be the extractor the offsets are checked against. But it and `ar_corpus.pdfwrite`
    are one author's reading of one specification: if both were wrong in the same way,
    every quotation would verify and every downstream measurement would be contaminated
    without anyone noticing. `pdfplumber` is pinned in `docs/program/P02_LOCK.json` and
    is that second reader.
    """

    def __init__(self) -> None:
        self.name = ""
        self._plumber = None
        try:
            import pdfplumber  # noqa: PLC0415
        except ImportError:
            return
        self._plumber = pdfplumber
        self.name = f"pdfplumber {getattr(pdfplumber, '__version__', '?')}"

    @property
    def available(self) -> bool:
        return self._plumber is not None

    def pages(self, path: Path) -> list[str]:
        assert self._plumber is not None
        with self._plumber.open(str(path)) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]


# --------------------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------------------


def _check_manifest_shape(manifest: dict) -> list[Problem]:
    problems: list[Problem] = []
    if manifest.get("schema") != MANIFEST_SCHEMA:
        problems.append(Problem(
            "CHK-SCHEMA",
            f"manifest schema is {manifest.get('schema')!r}, expected "
            f"{MANIFEST_SCHEMA!r}",
        ))
    labels = manifest.get("finding_labels")
    if labels != FINDING_LABELS:
        problems.append(Problem(
            "CHK-LABELS",
            f"finding labels are {labels!r}; PROTOTYPE_PROFILE.md section 9 fixes "
            f"exactly {FINDING_LABELS!r} and a validation report cannot pool records "
            "carrying a label outside them",
        ))
    return problems


def _check_composition(manifest: dict) -> list[Problem]:
    problems: list[Problem] = []
    documents = manifest.get("documents", [])
    negatives = manifest.get("negative_envelope_documents", [])
    seeded = [d for d in documents if d.get("role") == "seeded"]
    controls = [d for d in documents if d.get("role") == "control"]

    if not MIN_MEASURABLE <= len(documents) <= MAX_MEASURABLE:
        problems.append(Problem(
            "CHK-COMPOSITION",
            f"{len(documents)} measurable documents; task P4-QA-01 fixes "
            f"{MIN_MEASURABLE}-{MAX_MEASURABLE}, and fewer than {MIN_MEASURABLE} is "
            "reported as BLOCKED rather than shipped",
        ))
    if len(seeded) != SEEDED_DOCUMENTS:
        problems.append(Problem(
            "CHK-COMPOSITION",
            f"{len(seeded)} seeded documents; the task fixes exactly "
            f"{SEEDED_DOCUMENTS}",
        ))
    if len(seeded) + len(controls) != len(documents):
        problems.append(Problem(
            "CHK-COMPOSITION",
            "a measurable document is neither seeded nor a control",
        ))
    if not MIN_NEGATIVE <= len(negatives) <= MAX_NEGATIVE:
        problems.append(Problem(
            "CHK-COMPOSITION",
            f"{len(negatives)} negative-envelope documents; the task fixes "
            f"{MIN_NEGATIVE}-{MAX_NEGATIVE}",
        ))

    declared = manifest.get("composition", {})
    if declared.get("measurable_documents") != len(documents):
        problems.append(Problem(
            "CHK-COMPOSITION",
            f"composition.measurable_documents is "
            f"{declared.get('measurable_documents')!r} but {len(documents)} documents "
            "are listed",
        ))
    seeded_issues = sum(len(d.get("seeded_issues", [])) for d in documents)
    if declared.get("seeded_issues") != seeded_issues:
        problems.append(Problem(
            "CHK-COMPOSITION",
            f"composition.seeded_issues is {declared.get('seeded_issues')!r} but "
            f"{seeded_issues} are listed",
        ))
    return problems


def _check_control_documents(manifest: dict) -> list[Problem]:
    """A control document's findings are all false positives by construction.

    A seeded issue hiding in one would silently turn true positives into false ones, and
    the precision figure the whole checkpoint reports would be wrong in the direction
    that flatters nobody and misleads everybody.
    """
    problems: list[Problem] = []
    for record in manifest.get("documents", []):
        if record.get("role") != "control":
            continue
        if record.get("seeded_issues"):
            problems.append(Problem(
                "CHK-CONTROL-CLEAN",
                f"{record.get('label')} is declared a control document but carries "
                f"{len(record['seeded_issues'])} seeded issue(s)",
            ))
        if not record.get("controls"):
            problems.append(Problem(
                "CHK-CONTROL-CLEAN",
                f"{record.get('label')} is a control document with no control "
                "statements, so it applies no false-positive pressure",
            ))
    return problems


def _check_document(record: dict, root: Path,
                    extractor: IndependentExtractor) -> list[Problem]:
    problems: list[Problem] = []
    label = record.get("label", "<unlabelled>")
    provenance = record.get("provenance")
    path = root / str(record.get("path", ""))

    if provenance not in PROVENANCE_VALUES:
        problems.append(Problem(
            "CHK-PROVENANCE",
            f"{label}: provenance is {provenance!r}, expected one of "
            f"{list(PROVENANCE_VALUES)}",
        ))

    if provenance == "anonymized":
        # OD-17 rules this corpus synthetic-only. The rule is enforced anyway: an
        # anonymized record carries anchors and hashes and never document bytes, so a
        # future record that did carry bytes is a leak, not a fixture.
        if path.is_file():
            problems.append(Problem(
                "CHK-ANONYMIZED-BYTES",
                f"{label}: provenance is 'anonymized' but document bytes are committed "
                f"at {record.get('path')}; an anonymized record carries anchors and "
                "hashes only",
            ))
        return problems

    if not path.is_file():
        problems.append(Problem(
            "CHK-FILE-PRESENT", f"{label}: {record.get('path')} is missing"
        ))
        return problems

    data = path.read_bytes()

    if sha256(data) != record.get("sha256"):
        problems.append(Problem(
            "CHK-SHA256",
            f"{label}: declared sha256 {record.get('sha256')}, file is {sha256(data)}",
        ))
    if len(data) != record.get("bytes"):
        problems.append(Problem(
            "CHK-BYTES",
            f"{label}: declared {record.get('bytes')} bytes, file is {len(data)}",
        ))

    report = envelope.check(data)
    for result in report.results:
        if result.status is envelope.Status.PASS:
            continue
        problems.append(Problem(
            _RULE_CHECK[result.rule],
            f"{label}: {result.rule} is {result.status.value} - {result.detail}",
        ))
    if not report.accepted:
        # Nothing below can be trusted if the document is outside the envelope or
        # unreadable, and a traceback here would tell a caller far less than this line.
        return problems

    pages = pdfextract.extract_pages(data)
    if len(pages) != record.get("pages"):
        problems.append(Problem(
            "CHK-PAGES-DECLARED",
            f"{label}: declared {record.get('pages')} pages, file has {len(pages)}",
        ))

    declared_hashes = record.get("page_text_sha256", [])
    actual_hashes = [sha256(text.encode("utf-8")) for text in pages]
    if declared_hashes != actual_hashes:
        for index, (declared, actual) in enumerate(
            zip(declared_hashes, actual_hashes), start=1
        ):
            if declared != actual:
                problems.append(Problem(
                    "CHK-PAGE-TEXT-SHA",
                    f"{label} page {index}: declared page-text sha256 {declared}, "
                    f"extracted text hashes to {actual}",
                ))
        if len(declared_hashes) != len(actual_hashes):
            problems.append(Problem(
                "CHK-PAGE-TEXT-SHA",
                f"{label}: {len(declared_hashes)} page-text hashes declared for "
                f"{len(actual_hashes)} pages",
            ))

    independent = extractor.pages(path) if extractor.available else None

    for issue in record.get("seeded_issues", []):
        if issue.get("category") not in CATEGORIES:
            problems.append(Problem(
                "CHK-CATEGORY",
                f"{label}/{issue.get('id')}: category {issue.get('category')!r} is not "
                f"one of {CATEGORIES}, fixed by PROTOTYPE_PROFILE.md section 7.1",
            ))
        for anchor in issue.get("evidence", []):
            problems += _check_anchor(
                label, issue.get("id"), anchor, pages, independent, extractor
            )

    for control in record.get("controls", []):
        for anchor in control.get("anchors", []):
            problems += _check_anchor(
                label, control.get("id"), anchor, pages, independent, extractor
            )

    return problems


def _check_anchor(label: str, owner: str, anchor: dict, pages: list[str],
                  independent: list[str] | None,
                  extractor: IndependentExtractor) -> list[Problem]:
    """One ground-truth anchor: the quotation is where the manifest says it is.

    Three separate claims, three separate check ids, because they fail for different
    reasons and a session needs to know which. The quotation is on exactly the declared
    page and no other; it starts at the declared character offset; and a second reader
    finds it too.
    """
    problems: list[Problem] = []
    quotation = anchor.get("quotation", "")
    page_number = anchor.get("page")

    if not isinstance(page_number, int) or not 1 <= page_number <= len(pages):
        problems.append(Problem(
            "CHK-QUOTATION-PAGE",
            f"{label}/{owner}: declared page {page_number!r} is outside the document's "
            f"{len(pages)} pages",
        ))
        return problems

    found = {n for n, text in enumerate(pages, start=1) if quotation in text}
    if page_number not in found:
        problems.append(Problem(
            "CHK-QUOTATION-PAGE",
            f"{label}/{owner}: quotation {quotation!r} is not present on its declared "
            f"page {page_number}; it resolves on pages {sorted(found)}",
        ))
        return problems

    text = pages[page_number - 1]
    offset = anchor.get("char_offset_in_page_text")
    if text[offset:offset + len(quotation)] != quotation:
        problems.append(Problem(
            "CHK-QUOTATION-OFFSET",
            f"{label}/{owner}: quotation does not start at declared offset {offset!r} "
            f"on page {page_number}; the text there is "
            f"{text[offset:offset + len(quotation)]!r}",
        ))

    line_index = anchor.get("line_index_in_page_text")
    lines = text.split("\n")
    if not isinstance(line_index, int) or not 0 <= line_index < len(lines):
        problems.append(Problem(
            "CHK-QUOTATION-OFFSET",
            f"{label}/{owner}: declared line index {line_index!r} is outside the "
            f"{len(lines)} lines of page {page_number}",
        ))
    elif lines[line_index] != anchor.get("line_text"):
        problems.append(Problem(
            "CHK-QUOTATION-OFFSET",
            f"{label}/{owner}: declared line text does not match line {line_index} of "
            f"page {page_number}",
        ))

    if independent is not None:
        if page_number > len(independent) or quotation not in independent[page_number - 1]:
            problems.append(Problem(
                "CHK-QUOTATION-INDEPENDENT",
                f"{label}/{owner}: quotation {quotation!r} resolves with the reference "
                f"extractor but not with {extractor.name} on page {page_number}. A "
                "quotation only one reader can see is not grounded.",
            ))
    return problems


def _check_session_schema(manifest: dict, root: Path) -> list[Problem]:
    """The recording schema exists and still fixes the same three labels as the corpus.

    The corpus and the protocol have to agree about what a label is, and they live in
    different files that different people edit. If the schema grew a fourth label while
    the manifest kept three, two moderators could record data that validates and still
    cannot be pooled - which is the exact failure this whole protocol is built to
    prevent, arriving through the back door.

    This is a structural check, not a JSON Schema meta-validation: `jsonschema` is not in
    `docs/program/P02_LOCK.json` and this task does not take the root lock to add it.
    """
    problems: list[Problem] = []
    declared = manifest.get("session_record_schema")
    if not declared:
        problems.append(Problem(
            "CHK-SESSION-SCHEMA",
            "the manifest names no session_record_schema, so nothing ties the corpus's "
            "labels to the ones a session will record",
        ))
        return problems

    path = root / str(declared)
    if not path.is_file():
        problems.append(Problem(
            "CHK-SESSION-SCHEMA", f"session record schema {declared} is missing"
        ))
        return problems

    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        problems.append(Problem(
            "CHK-SESSION-SCHEMA", f"{declared} is not valid JSON: {exc}"
        ))
        return problems

    if schema.get("$id") != SESSION_SCHEMA_ID:
        problems.append(Problem(
            "CHK-SESSION-SCHEMA",
            f"{declared}: $id is {schema.get('$id')!r}, expected {SESSION_SCHEMA_ID!r}",
        ))

    defs = schema.get("$defs", {})
    label_enum = defs.get("label", {}).get("enum")
    if label_enum != FINDING_LABELS:
        problems.append(Problem(
            "CHK-SESSION-SCHEMA",
            f"{declared}: the label enum is {label_enum!r}, but the corpus and "
            f"PROTOTYPE_PROFILE.md section 9 fix exactly {FINDING_LABELS!r}",
        ))
    if label_enum != manifest.get("finding_labels"):
        problems.append(Problem(
            "CHK-SESSION-SCHEMA",
            f"{declared}: the schema's labels {label_enum!r} do not match the "
            f"manifest's {manifest.get('finding_labels')!r}",
        ))

    for record_type in SESSION_RECORD_TYPES:
        if record_type not in defs:
            problems.append(Problem(
                "CHK-SESSION-SCHEMA",
                f"{declared}: no definition for {record_type!r}; the protocol requires "
                "a per-finding, per-document, envelope-refusal and post-session record",
            ))

    category_enum = (
        defs.get("finding_record", {}).get("properties", {})
        .get("category", {}).get("enum")
    )
    if category_enum is not None and sorted(category_enum) != sorted(CATEGORIES):
        problems.append(Problem(
            "CHK-SESSION-SCHEMA",
            f"{declared}: finding categories {category_enum!r} do not match the two "
            f"fixed by the profile, {CATEGORIES!r}",
        ))
    return problems


def _check_negatives(manifest: dict, root: Path) -> list[Problem]:
    """Each negative-envelope document is refused by the specific rule it names."""
    problems: list[Problem] = []
    for record in manifest.get("negative_envelope_documents", []):
        label = record.get("label", "<unlabelled>")
        path = root / str(record.get("path", ""))
        if not path.is_file():
            problems.append(Problem(
                "CHK-FILE-PRESENT", f"{label}: {record.get('path')} is missing"
            ))
            continue
        data = path.read_bytes()
        if sha256(data) != record.get("sha256"):
            problems.append(Problem(
                "CHK-SHA256",
                f"{label}: declared sha256 {record.get('sha256')}, file is "
                f"{sha256(data)}",
            ))
        if len(data) != record.get("bytes"):
            problems.append(Problem(
                "CHK-BYTES",
                f"{label}: declared {record.get('bytes')} bytes, file is {len(data)}",
            ))

        rule = record.get("violates_rule")
        report = envelope.check(data)
        if report.violations != (rule,):
            problems.append(Problem(
                "CHK-NEGATIVE-RULE",
                f"{label}: declared to violate exactly {rule!r}, violates "
                f"{list(report.violations)}. A fixture that breaks two rules proves "
                "nothing about which one fired.",
            ))
        if rule in report.not_evaluated:
            problems.append(Problem(
                "CHK-NEGATIVE-EVALUATED",
                f"{label}: {rule} was not evaluated at all, so the fixture proves "
                "nothing about it; a rule that could not be checked is not a rule "
                "that passed",
            ))
    return problems


def check_corpus(manifest_path: Path, root: Path | None = None,
                 require_independent: bool = True) -> list[Problem]:
    """Every assertion, against the files on disk. Returns every problem, not the first."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if root is None:
        # <root>/fixtures/validation/PC-02/corpus_manifest.json
        root = manifest_path.resolve().parents[3]

    extractor = IndependentExtractor()
    problems: list[Problem] = []
    if require_independent and not extractor.available:
        problems.append(Problem(
            "CHK-INDEPENDENT-AVAILABLE",
            "pdfplumber is not importable, so no extractor independent of the corpus "
            "writer is available. Every quotation would be verified only by the reader "
            "its own author wrote, which is not verification. pdfplumber is pinned in "
            "docs/program/P02_LOCK.json; run this under .venv/bin/python.",
        ))

    problems += _check_manifest_shape(manifest)
    problems += _check_composition(manifest)
    problems += _check_control_documents(manifest)
    problems += _check_session_schema(manifest, root)
    for record in manifest.get("documents", []):
        problems += _check_document(record, root, extractor)
    problems += _check_negatives(manifest, root)
    return problems


# --------------------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Mutation:
    name: str
    expects: str
    describe: str
    apply: object  # Callable[[Path, dict], None]
    # "manifest" mutations break the corpus or its manifest. "reader" mutations break the
    # *answer the second extractor gives*, which is the only way to exercise a check
    # whose whole subject is two readers disagreeing: both readers read the same bytes,
    # so no edit to those bytes can make one of them alone go blind. The distinction is
    # printed, so nobody reads more into that case than it proves.
    kind: str = "manifest"


def _seeded_record(manifest: dict) -> dict:
    return next(d for d in manifest["documents"] if d["role"] == "seeded")


def _control_record(manifest: dict) -> dict:
    return next(d for d in manifest["documents"] if d["role"] == "control")


def _rebase_record_onto(record: dict, root: Path, new_path: str) -> None:
    """Point a measurable record at a different committed file, honestly.

    The sha256, byte count and page count are recomputed from the substituted file, so
    the *only* thing wrong with the mutated corpus is the one property under test. A
    mutation that trips three checks at once would not show that the check it names can
    fire on its own.
    """
    data = (root / new_path).read_bytes()
    record["path"] = new_path
    record["sha256"] = sha256(data)
    record["bytes"] = len(data)
    record["seeded_issues"] = []
    record["controls"] = []
    try:
        pages = pdfextract.extract_pages(data)
    except pdfextract.PdfParseError:
        pages = []
    record["pages"] = len(pages)
    record["page_text_sha256"] = [sha256(t.encode("utf-8")) for t in pages]


def _mutations(root: Path) -> list[Mutation]:
    def flip_declared_sha(_root: Path, manifest: dict) -> None:
        record = _seeded_record(manifest)
        digest = record["sha256"]
        record["sha256"] = ("0" if digest[0] != "0" else "1") + digest[1:]

    def append_byte_to_file(work: Path, manifest: dict) -> None:
        record = _seeded_record(manifest)
        target = work / record["path"]
        # Appended after %%EOF: every xref offset still resolves, so the file still
        # parses and the failure is attributable to the digest rather than to a crash.
        target.write_bytes(target.read_bytes() + b"\n")

    def wrong_declared_bytes(_root: Path, manifest: dict) -> None:
        _seeded_record(manifest)["bytes"] += 1

    def wrong_declared_pages(_root: Path, manifest: dict) -> None:
        _seeded_record(manifest)["pages"] += 1

    def wrong_page_text_sha(_root: Path, manifest: dict) -> None:
        record = _seeded_record(manifest)
        digest = record["page_text_sha256"][1]
        record["page_text_sha256"][1] = ("0" if digest[0] != "0" else "1") + digest[1:]

    def flip_quotation_character(_root: Path, manifest: dict) -> None:
        anchor = _seeded_record(manifest)["seeded_issues"][0]["evidence"][0]
        quotation = anchor["quotation"]
        cut = len(quotation) // 2
        anchor["quotation"] = (
            quotation[:cut] + ("X" if quotation[cut] != "X" else "Y") + quotation[cut + 1:]
        )

    def shift_offset(_root: Path, manifest: dict) -> None:
        anchor = _seeded_record(manifest)["seeded_issues"][0]["evidence"][0]
        anchor["char_offset_in_page_text"] += 1

    def move_to_another_page(_root: Path, manifest: dict) -> None:
        record = _seeded_record(manifest)
        anchor = record["seeded_issues"][0]["evidence"][0]
        anchor["page"] = 1 if anchor["page"] != 1 else record["pages"]

    def wrong_line_text(_root: Path, manifest: dict) -> None:
        anchor = _seeded_record(manifest)["seeded_issues"][0]["evidence"][0]
        anchor["line_text"] = anchor["line_text"] + " "

    def drop_provenance(_root: Path, manifest: dict) -> None:
        _seeded_record(manifest).pop("provenance", None)

    def claim_anonymized(_root: Path, manifest: dict) -> None:
        _seeded_record(manifest)["provenance"] = "anonymized"

    def bad_category(_root: Path, manifest: dict) -> None:
        _seeded_record(manifest)["seeded_issues"][0]["category"] = "norm_violation"

    def extra_label(_root: Path, manifest: dict) -> None:
        manifest["finding_labels"] = FINDING_LABELS + ["partially_useful"]

    def seed_a_control(_root: Path, manifest: dict) -> None:
        seeded = _seeded_record(manifest)
        _control_record(manifest)["seeded_issues"] = [seeded["seeded_issues"][0]]

    def drop_a_document(_root: Path, manifest: dict) -> None:
        manifest["documents"] = manifest["documents"][:-1]

    def wrong_negative_rule(_root: Path, manifest: dict) -> None:
        record = manifest["negative_envelope_documents"][0]
        record["violates_rule"] = next(
            r for r in envelope.RULES if r != record["violates_rule"]
        )

    def measurable_is_oversize(_root: Path, manifest: dict) -> None:
        _rebase_record_onto(
            _seeded_record(manifest), root,
            "fixtures/validation/PC-02/negative/PC02-N03-oversize.pdf",
        )

    def measurable_is_too_long(_root: Path, manifest: dict) -> None:
        _rebase_record_onto(
            _seeded_record(manifest), root,
            "fixtures/validation/PC-02/negative/PC02-N04-too-many-pages.pdf",
        )

    def measurable_has_no_text(_root: Path, manifest: dict) -> None:
        _rebase_record_onto(
            _seeded_record(manifest), root,
            "fixtures/validation/PC-02/negative/PC02-N02-image-only.pdf",
        )

    def measurable_is_encrypted(_root: Path, manifest: dict) -> None:
        _rebase_record_onto(
            _seeded_record(manifest), root,
            "fixtures/validation/PC-02/negative/PC02-N01-encrypted.pdf",
        )

    def bad_schema(_root: Path, manifest: dict) -> None:
        manifest["schema"] = "pc02-validation-corpus/0"

    def delete_a_document_file(work: Path, manifest: dict) -> None:
        (work / _seeded_record(manifest)["path"]).unlink()

    def measurable_is_not_a_pdf(work: Path, manifest: dict) -> None:
        record = _seeded_record(manifest)
        stray = "fixtures/validation/PC-02/documents/not-a-pdf.bin"
        (work / stray).write_bytes(
            "Синтетический файл без заголовка %PDF-.\n".encode("utf-8")
        )
        data = (work / stray).read_bytes()
        record["path"] = stray
        record["sha256"] = sha256(data)
        record["bytes"] = len(data)
        record["pages"] = 0
        record["page_text_sha256"] = []
        record["seeded_issues"] = []
        record["controls"] = []

    def negative_names_an_unevaluable_rule(_root: Path, manifest: dict) -> None:
        # The encrypted fixture's page count and text layer cannot be evaluated at all,
        # because the document cannot be opened. Naming ENV-TEXT as the rule it violates
        # is the exact mistake the three-state result exists to catch: "unreadable" is
        # not "within the envelope", and a rule that could not be checked is not a rule
        # that passed.
        record = next(
            r for r in manifest["negative_envelope_documents"]
            if r["violates_rule"] == envelope.RULE_NOT_ENCRYPTED
        )
        record["violates_rule"] = envelope.RULE_TEXT_LAYER

    def second_reader_goes_blind(_root: Path, _manifest: dict) -> None:
        pass  # applied by the self-test harness, see Mutation.kind

    def schema_grows_a_fourth_label(work: Path, manifest: dict) -> None:
        path = work / manifest["session_record_schema"]
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["$defs"]["label"]["enum"] = FINDING_LABELS + ["partially_useful"]
        path.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return [
        Mutation("declared-sha256-wrong", "CHK-SHA256",
                 "flip one hex digit of a document's declared SHA-256",
                 flip_declared_sha),
        Mutation("file-bytes-changed", "CHK-SHA256",
                 "append one byte to a committed PDF, after %%EOF so it still parses",
                 append_byte_to_file),
        Mutation("declared-bytes-wrong", "CHK-BYTES",
                 "declare one byte more than the file holds", wrong_declared_bytes),
        Mutation("declared-pages-wrong", "CHK-PAGES-DECLARED",
                 "declare one page more than the document has", wrong_declared_pages),
        Mutation("page-text-hash-wrong", "CHK-PAGE-TEXT-SHA",
                 "flip one hex digit of a page's declared text hash",
                 wrong_page_text_sha),
        Mutation("quotation-character-flipped", "CHK-QUOTATION-PAGE",
                 "flip one character in the middle of a seeded quotation",
                 flip_quotation_character),
        Mutation("quotation-offset-shifted", "CHK-QUOTATION-OFFSET",
                 "shift a seeded quotation's character offset by one", shift_offset),
        Mutation("quotation-page-moved", "CHK-QUOTATION-PAGE",
                 "declare a seeded quotation on a page it is not on",
                 move_to_another_page),
        Mutation("anchor-line-text-wrong", "CHK-QUOTATION-OFFSET",
                 "add a trailing space to a declared line text", wrong_line_text),
        Mutation("provenance-missing", "CHK-PROVENANCE",
                 "remove a document's provenance field", drop_provenance),
        Mutation("anonymized-with-bytes", "CHK-ANONYMIZED-BYTES",
                 "mark a record anonymized while its bytes stay committed",
                 claim_anonymized),
        Mutation("category-outside-the-two", "CHK-CATEGORY",
                 "give a seeded issue a category outside the two fixed by the profile",
                 bad_category),
        Mutation("fourth-finding-label", "CHK-LABELS",
                 "add a fourth finding label beside useful/incorrect/unclear",
                 extra_label),
        Mutation("seeded-issue-in-a-control", "CHK-CONTROL-CLEAN",
                 "plant a seeded issue in a document declared to be a control",
                 seed_a_control),
        Mutation("document-dropped", "CHK-COMPOSITION",
                 "drop a document so the corpus falls to 13 with a stale count",
                 drop_a_document),
        Mutation("negative-names-wrong-rule", "CHK-NEGATIVE-RULE",
                 "claim a negative fixture violates a rule it does not",
                 wrong_negative_rule),
        Mutation("measurable-over-25-mib", "CHK-ENVELOPE-SIZE",
                 "put a file over 25 MiB into the measurable set", measurable_is_oversize),
        Mutation("measurable-over-30-pages", "CHK-ENVELOPE-PAGES",
                 "put a 31-page file into the measurable set", measurable_is_too_long),
        Mutation("measurable-has-no-text-layer", "CHK-ENVELOPE-TEXT",
                 "put a scanned, text-free file into the measurable set",
                 measurable_has_no_text),
        Mutation("measurable-is-encrypted", "CHK-ENVELOPE-ENCRYPTED",
                 "put a password-protected file into the measurable set",
                 measurable_is_encrypted),
        Mutation("schema-version-wrong", "CHK-SCHEMA",
                 "declare a manifest schema version nothing reads", bad_schema),
        Mutation("document-file-deleted", "CHK-FILE-PRESENT",
                 "delete a committed document the manifest still lists",
                 delete_a_document_file),
        Mutation("measurable-is-not-a-pdf", "CHK-ENVELOPE-PDF",
                 "put a file with no %PDF- header into the measurable set",
                 measurable_is_not_a_pdf),
        Mutation("negative-names-an-unevaluable-rule", "CHK-NEGATIVE-EVALUATED",
                 "claim the encrypted fixture violates ENV-TEXT, a rule that cannot be "
                 "evaluated on a document nothing can open",
                 negative_names_an_unevaluable_rule),
        Mutation("schema-grows-a-fourth-label", "CHK-SESSION-SCHEMA",
                 "add a fourth label to the session record schema while the manifest "
                 "still fixes three, so records would validate and still not pool",
                 schema_grows_a_fourth_label),
        Mutation("second-reader-goes-blind", "CHK-QUOTATION-INDEPENDENT",
                 "make the independent extractor return page text with a seeded "
                 "quotation removed, so the two readers disagree",
                 second_reader_goes_blind, kind="reader"),
    ]


def _check_with_blinded_reader(manifest_path: Path, work: Path,
                               manifest: dict) -> list[Problem]:
    """Run the whole check with the independent extractor made blind to one quotation.

    `CHK-QUOTATION-INDEPENDENT` is the assertion that two readers agree, and it is the
    one assertion no edit to the corpus bytes can exercise: both readers read the same
    file, so breaking the file blinds both of them at once and some other check fires
    first. The honest way to show this guard can go red is to make the disagreement it
    watches for actually happen - so the second reader's answer, and nothing else, is
    replaced by one with a seeded quotation deleted from it.

    This proves the check fires on a real disagreement. It does not prove pdfplumber
    would ever produce one, and it is not evidence about pdfplumber at all.
    """
    quotation = manifest["documents"][0]["seeded_issues"][0]["evidence"][0]["quotation"]
    original = IndependentExtractor.pages

    def blinded(self: IndependentExtractor, path: Path) -> list[str]:
        return [text.replace(quotation, "") for text in original(self, path)]

    IndependentExtractor.pages = blinded  # type: ignore[method-assign]
    try:
        return check_corpus(manifest_path, root=work)
    finally:
        IndependentExtractor.pages = original  # type: ignore[method-assign]


def _restore_tree(work_base: Path, root_base: Path) -> None:
    """Put the working copy back exactly as the committed tree is.

    A self-test that leaves damage behind makes every later case unattributable, so this
    removes files a mutation added, restores files it deleted and rewrites files it
    changed - and the harness proves it worked by re-running the whole check green at
    the end.
    """
    expected = {p.relative_to(root_base) for p in root_base.rglob("*") if p.is_file()}
    actual = {p.relative_to(work_base) for p in work_base.rglob("*") if p.is_file()}
    for extra in actual - expected:
        (work_base / extra).unlink()
    for relative in expected:
        target = work_base / relative
        source = root_base / relative
        if (not target.is_file()
                or target.stat().st_size != source.stat().st_size
                or target.read_bytes() != source.read_bytes()):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


def self_test(manifest_path: Path, verbose: bool = True) -> int:
    """Break the corpus one way per assertion and require that assertion to fire."""
    root = manifest_path.resolve().parents[3]
    relative = manifest_path.resolve().relative_to(root)

    with tempfile.TemporaryDirectory(prefix="pc02-selftest-") as tmp:
        work = Path(tmp)
        shutil.copytree(
            root / "fixtures" / "validation" / "PC-02",
            work / "fixtures" / "validation" / "PC-02",
        )
        work_manifest = work / relative
        pristine = work_manifest.read_bytes()

        baseline = check_corpus(work_manifest, root=work)
        if baseline:
            print("FAIL: the unmutated copy is not clean, so nothing below would mean "
                  "anything:", file=sys.stderr)
            for problem in baseline:
                print(f"  {problem}", file=sys.stderr)
            return 1
        if verbose:
            print(f"green  unmutated copy: 0 problems over "
                  f"{len(json.loads(pristine)['documents'])} measurable documents")

        failures: list[str] = []
        covered: set[str] = set()
        for mutation in _mutations(root):
            work_manifest.write_bytes(pristine)
            manifest = json.loads(pristine.decode("utf-8"))
            mutation.apply(work, manifest)  # type: ignore[operator]
            work_manifest.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            if mutation.kind == "reader":
                problems = _check_with_blinded_reader(
                    work_manifest, work, json.loads(pristine.decode("utf-8"))
                )
            else:
                problems = check_corpus(work_manifest, root=work)
            fired = sorted({p.check for p in problems})

            if not problems:
                failures.append(
                    f"{mutation.name}: the corpus was broken ({mutation.describe}) and "
                    f"no check fired. {mutation.expects} does not guard what it names."
                )
            elif mutation.expects not in fired:
                failures.append(
                    f"{mutation.name}: expected {mutation.expects} to fire; the checks "
                    f"that fired were {fired}. A mutation that trips some other "
                    "assertion has not shown this one can go red."
                )
            else:
                covered.add(mutation.expects)
                if verbose:
                    marker = "" if mutation.kind == "manifest" else " [reader-side]"
                    print(f"red    {mutation.name}{marker}: {mutation.expects} fired "
                          f"({len(problems)} problem(s), checks {fired}) - "
                          f"{mutation.describe}")

            # Restore any file-level damage before the next case.
            _restore_tree(
                work / "fixtures" / "validation" / "PC-02",
                root / "fixtures" / "validation" / "PC-02",
            )
            work_manifest.write_bytes(pristine)

        green = check_corpus(work_manifest, root=work)
        if green:
            failures.append(
                "after reverting every mutation the corpus is still red, so the "
                "self-test did not restore what it broke and its red results are not "
                "attributable"
            )

    unexercised = sorted(set(CHECKS) - covered - {"CHK-INDEPENDENT-AVAILABLE"})
    if verbose:
        print(f"green  reverted copy: 0 problems")
        print(f"\n{len(covered)} of {len(CHECKS)} checks shown both red and green.")
        print("CHK-INDEPENDENT-AVAILABLE is an environment assertion, not a corpus "
              "one: it fires when pdfplumber is absent, which no mutation of the "
              "corpus can arrange.")
        if unexercised:
            print("not exercised by a mutation (each is reported here rather than "
                  "quietly assumed):")
            for check in unexercised:
                print(f"  {check}")

    if failures:
        print("\nFAIL: a guard did not go red when what it protects was broken:",
              file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the PC-02 validation corpus against its manifest.",
    )
    parser.add_argument(
        "manifest", nargs="?",
        default=str(REPO_ROOT / "fixtures/validation/PC-02/corpus_manifest.json"),
        help="path to corpus_manifest.json",
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="break the corpus one way per assertion and require that assertion to fire",
    )
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"usage error: no manifest at {manifest_path}", file=sys.stderr)
        return 2

    if args.self_test:
        return self_test(manifest_path, verbose=not args.quiet)

    problems = check_corpus(manifest_path)
    if problems:
        print(f"FAIL: {len(problems)} problem(s) in {manifest_path}:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    composition = manifest.get("composition", {})
    if not args.quiet:
        extractor = IndependentExtractor()
        anchors = sum(
            len(i["evidence"]) for d in manifest["documents"] for i in d["seeded_issues"]
        ) + sum(len(c["anchors"]) for d in manifest["documents"] for c in d["controls"])
        print(
            f"OK  {composition.get('measurable_documents')} measurable documents "
            f"({composition.get('seeded_documents')} seeded, "
            f"{composition.get('control_documents')} control), "
            f"{composition.get('seeded_issues')} seeded issues, "
            f"{composition.get('control_statements')} control statements, "
            f"{composition.get('negative_envelope_documents')} negative-envelope "
            f"documents counted separately"
        )
        print(f"OK  {anchors} ground-truth quotations resolved at their declared page "
              f"and offset, each also confirmed by {extractor.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
