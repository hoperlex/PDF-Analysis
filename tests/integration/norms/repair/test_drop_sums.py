"""`W54-JUDGE-Y` F3: one ``SHA256SUMS`` parser, and the sums a repair checked on record.

Before the fix the repair parser (``norms/__main__.py``) accepted lowercase only and kept the
last of two lines for one path, while the export parser folded uppercase and refused
duplicates; and nothing recorded which sums file a repair run checked its crops against.
Now both read through ``corpus_source.read_drop_sums``, the journal header records the
file's SHA-256, and the ledger file carries it for the export to compare.

Container-free; no connection can be opened (``conftest.py``).
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from auditmanager.norms import __main__ as command
from auditmanager.norms.__main__ import RunRefused, verify_crops_against_sums
from auditmanager.norms.corpus_source import DropSumsInvalid, read_drop_sums
from auditmanager.norms.repair_journal import (
    LEDGER_SUMS_FIELD,
    JournalRefused,
    LocalJournal,
    file_journal,
    read_ledger_file,
)
from tests.integration.norms.repair.support import BASE, CLEAN_PAGE, MODEL, SUMS, MemoryStore, openai_body
from tests.integration.norms.repair.test_proxy_transport import (
    ENVIRONMENT,
    StubOpener,
    _args,
    _corpus,
    _factory,
    _sums,
    minimal_pdf,
)

A = "a" * 64
B = "b" * 64


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# --- the one parser ----------------------------------------------------------------------


def test_the_parser_reads_sha256sum_text_in_both_modes(tmp_path: Path) -> None:
    path = _write(tmp_path / "SHA256SUMS", f"{A}  ./x/document.pdf\n{B} *y/crops/blk_1.pdf\n\n")
    parsed = read_drop_sums(path)
    assert dict(parsed.entries) == {"x/document.pdf": A, "y/crops/blk_1.pdf": B}
    assert parsed.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("text", "words"),
    [
        (f"{A.upper()}  ./x.pdf\n", "not '<64 lowercase hex>"),
        (f"{A}  ./x.pdf\n{B}  ./x.pdf\n", "names x.pdf twice"),
        (f"{A}  ./x.pdf\n{B}  x.pdf\n", "names x.pdf twice"),
        (f"\\{A}  ./x\\npdf\n", "not '<64 lowercase hex>"),
        (f"{A} ./x.pdf\n", "not '<64 lowercase hex>"),
        (f"{A}  ./\n", "names no path"),
        ("\n", "is empty"),
    ],
    ids=["uppercase", "duplicate", "duplicate-after-dot-slash", "escaped", "one-space", "no-path", "empty"],
)
def test_the_parser_refuses_anything_but_one_canonical_listing(tmp_path: Path, text: str, words: str) -> None:
    with pytest.raises(DropSumsInvalid, match=words) as refused:
        read_drop_sums(_write(tmp_path / "SHA256SUMS", text))
    assert refused.value.reason == "drop_sums_malformed"


def test_the_parser_names_an_absent_file(tmp_path: Path) -> None:
    with pytest.raises(DropSumsInvalid) as refused:
        read_drop_sums(tmp_path / "absent")
    assert refused.value.reason == "drop_sums_absent"


def test_the_repair_step_zero_uses_the_one_parser(tmp_path: Path) -> None:
    """The judge's case: the repair kept the last of two lines; now two lines refuse."""
    root = _corpus(tmp_path / "corpus", minimal_pdf())
    sums = _sums(tmp_path / "SHA256SUMS", root)
    line = sums.read_text(encoding="utf-8")
    pages = command._pages(root)
    assert verify_crops_against_sums(root, pages, sums).sha256 == hashlib.sha256(sums.read_bytes()).hexdigest()
    sums.write_text(("0" * 64) + line[64:] + line, encoding="utf-8")
    with pytest.raises(RunRefused, match="drop_sums_malformed: .* twice"):
        verify_crops_against_sums(root, pages, sums)
    sums.write_text(line[:64].upper() + line[64:], encoding="utf-8")
    with pytest.raises(RunRefused, match="drop_sums_malformed"):
        verify_crops_against_sums(root, pages, sums)


# --- the journal header and the ledger record the sums ----------------------------------


def _legacy_journal(directory: Path, base: str = BASE) -> None:
    """A journal whose header predates the sums digest, chained exactly as the file writes."""
    directory.mkdir(parents=True)
    line = {
        "seq": 1, "kind": "header", "at": "t0", "prev": file_journal.GENESIS,
        "body": {"format": file_journal.FORMAT, "base_snapshot": base, "model": MODEL, "ceiling_usd": "10"},
    }
    digest = hashlib.sha256(file_journal._canonical(line)).hexdigest()
    (directory / file_journal.JOURNAL_FILENAME).write_bytes(file_journal._canonical(dict(line, digest=digest)) + b"\n")


def test_a_new_journal_records_the_sums_and_needs_them(tmp_path: Path) -> None:
    with pytest.raises(JournalRefused, match="SHA256SUMS"):
        LocalJournal(tmp_path / "none").open(base_snapshot=BASE, model=MODEL, ceiling_usd=Decimal(10), now="t")
    journal = LocalJournal(tmp_path / "j").open(
        base_snapshot=BASE, model=MODEL, ceiling_usd=Decimal(10), drop_sums_sha256=SUMS, now="t"
    )
    assert journal.header is not None and journal.header["drop_sums_sha256"] == SUMS
    journal.close()
    with pytest.raises(JournalRefused, match="bound to one base snapshot, model, ceiling and SHA256SUMS"):
        LocalJournal(tmp_path / "j").open(
            base_snapshot=BASE, model=MODEL, ceiling_usd=Decimal(10), drop_sums_sha256="6" * 64, now="t"
        )


def test_a_journal_header_without_the_sums_refuses_a_writer(tmp_path: Path) -> None:
    """Backward reading is explicit: refused, named, nothing appended."""
    _legacy_journal(tmp_path / "old")
    before = (tmp_path / "old" / file_journal.JOURNAL_FILENAME).read_bytes()
    with pytest.raises(JournalRefused, match="journal_sums_unrecorded"):
        LocalJournal(tmp_path / "old").open(
            base_snapshot=BASE, model=MODEL, ceiling_usd=Decimal(10), drop_sums_sha256=SUMS, now="t"
        )
    assert (tmp_path / "old" / file_journal.JOURNAL_FILENAME).read_bytes() == before


def test_the_run_records_the_sums_in_the_header_and_the_ledger(tmp_path: Path, capsys) -> None:
    root = _corpus(tmp_path / "corpus", minimal_pdf())
    sums = _sums(tmp_path / "SHA256SUMS", root)
    expected = hashlib.sha256(sums.read_bytes()).hexdigest()
    store = MemoryStore()
    opener = StubOpener((200, openai_body(CLEAN_PAGE, cost=0.03)))
    for stage in ("sample", "full"):
        assert command._command_run(_args(tmp_path, stage=stage), ENVIRONMENT,
                                    transport_factory=_factory(opener), store_factory=lambda _env: store) == 0
    capsys.readouterr()
    journal = LocalJournal(tmp_path / "repairs").open(read_only=True)
    assert journal.header is not None and journal.header["drop_sums_sha256"] == expected
    journal.close()
    data = (tmp_path / "repairs" / "ledger.json").read_bytes()
    assert json.loads(data)[LEDGER_SUMS_FIELD] == expected
    ledger, recorded = read_ledger_file(data)
    assert recorded == expected and len(ledger.applied) == 1

    out = tmp_path / "export" / "ledger.json"
    assert command.repair_main(["ledger", "--corpus", str(root), "--journal-dir", str(tmp_path / "repairs"),
                                "--out", str(out)], environment={}) == 0
    assert read_ledger_file(out.read_bytes())[1] == expected


def test_the_ledger_command_refuses_a_journal_without_the_sums(tmp_path: Path) -> None:
    root = _corpus(tmp_path / "corpus", minimal_pdf())
    _legacy_journal(tmp_path / "old", command.snapshot_of(root).snapshot_id)
    with pytest.raises(RunRefused, match="journal_sums_unrecorded"):
        command.repair_main(["ledger", "--corpus", str(root), "--journal-dir", str(tmp_path / "old"),
                             "--out", str(tmp_path / "ledger.json")], environment={})
    assert not (tmp_path / "ledger.json").exists()


def test_a_ledger_file_without_the_field_reads_back_as_unrecorded() -> None:
    from auditmanager.norms.repair import ledger_of

    document = ledger_of(BASE, "t", ()).as_document()
    assert read_ledger_file(json.dumps(document).encode())[1] is None
    with pytest.raises(ValueError, match="64 lowercase hex"):
        read_ledger_file(json.dumps(dict(document, drop_sums_sha256="X")).encode())
