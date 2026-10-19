"""`R-137`: the degenerate blocks re-read in a session, judged by the unchanged rule.

The session route replaces only the source of the text. These cases hold it to that: the
same pages and crop custody, the same prompt, the same two-read rule, a version-2 ledger
with its sums, and a refusal for every way the answers could stop matching what the readers
were given.

Container-free; no connection can be opened (``conftest.py``).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from auditmanager.norms import __main__ as command
from auditmanager.norms import session_repair
from auditmanager.norms.__main__ import RunRefused, render_crop_png
from auditmanager.norms.corpus_source import degenerate_pages, snapshot_of
from auditmanager.norms.repair import RepairOutcome, repaired_snapshot
from auditmanager.norms.repair_journal import LEDGER_SUMS_FIELD, read_ledger_file
from auditmanager.norms.rerecognition import RECOGNITION_SYSTEM_PROMPT
from auditmanager.norms.session_repair import (
    SESSION_STOP_REASON,
    ReadsOutstanding,
    SessionRefused,
    prepare_session,
    session_ledger,
)
from tests.integration.norms.repair.support import CLEAN_PAGE, DEGENERATE_PAGE
from tests.integration.norms.repair.test_proxy_transport import minimal_pdf

SLUG = "СП_63_13330_2018"
FIRST = "blk_" + "a" * 32
SECOND = "blk_" + "b" * 32
MODEL = "claude-sonnet-5-5"
AT = "2026-10-19T09:00:00+00:00"


def _corpus(root: Path) -> Path:
    document = root / SLUG
    (document / "crops").mkdir(parents=True)
    body = "".join(
        f"""## Page {70 + number}

### BLOCK #{number + 1} [TEXT]: {block}

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://example.invalid/crop)

{DEGENERATE_PAGE}

"""
        for number, block in enumerate((FIRST, SECOND))
    )
    (document / "results.md").write_text(
        f"# Document: {SLUG}.pdf\n\nPath: normative/{SLUG}.pdf\n\n"
        f"Generated: 2026-08-25 09:47:54 UTC\n\n{body}",
        encoding="utf-8",
    )
    (document / "blocks.json").write_text(json.dumps({"document_id": "doc_1"}), encoding="utf-8")
    (document / "crops" / f"{FIRST}.pdf").write_bytes(minimal_pdf(200, 300))
    (document / "crops" / f"{SECOND}.pdf").write_bytes(minimal_pdf(300, 200))
    (root / "MANIFEST.json").write_text(
        json.dumps({"documents": [{"slug": SLUG, "document_id": "doc_1", "document_name": SLUG,
                                   "doc_type": "СП", "pdf_pages": 71, "blocks_count": 2}]},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    return root


def _sums(path: Path, root: Path) -> Path:
    lines = [
        f"{hashlib.sha256((root / SLUG / 'crops' / f'{block}.pdf').read_bytes()).hexdigest()}"
        f"  ./{SLUG}/crops/{block}.pdf\n"
        for block in (FIRST, SECOND)
    ]
    path.write_text("".join(lines), encoding="utf-8")
    return path


class Drop:
    def __init__(self, tmp_path: Path) -> None:
        self.root = _corpus(tmp_path / "corpus")
        self.sums = _sums(tmp_path / "SHA256SUMS", self.root)
        self.session = tmp_path / "session"
        self.pages = list(degenerate_pages(self.root))
        self.base = snapshot_of(self.root).snapshot_id
        self.sums_sha = hashlib.sha256(self.sums.read_bytes()).hexdigest()

    def prepare(self) -> dict[str, Any]:
        return prepare_session(
            self.pages, directory=self.session, base_snapshot=self.base,
            drop_sums_sha256=self.sums_sha, dpi=72,
            render=lambda crop: render_crop_png(crop, dpi=72), now=AT,
        )

    def answer(self, block: str, read: int, text: str) -> None:
        (self.session / "answers" / f"{block}.{read}.md").write_text(text, encoding="utf-8")

    def ledger(self, **overrides: Any):
        values: dict[str, Any] = {
            "directory": self.session, "base_snapshot": self.base,
            "drop_sums_sha256": self.sums_sha, "model": MODEL,
            "transcribed_at": AT, "generated_at": AT,
        }
        values.update(overrides)
        return session_ledger(self.pages, **values)


@pytest.fixture
def drop(tmp_path: Path) -> Drop:
    return Drop(tmp_path)


# --- prepare ------------------------------------------------------------------------------


def test_prepare_writes_one_image_per_page_and_the_exact_prompt(drop: Drop) -> None:
    document = drop.prepare()

    assert [entry["block_id"] for entry in document["pages"]] == [FIRST, SECOND]
    for entry in document["pages"]:
        png = (drop.session / entry["png"]).read_bytes()
        assert png.startswith(b"\x89PNG")
        assert hashlib.sha256(png).hexdigest() == entry["png_sha256"]
    assert (drop.session / "prompt.txt").read_bytes() == RECOGNITION_SYSTEM_PROMPT.encode("utf-8")
    recorded = json.loads((drop.session / "session.json").read_text(encoding="utf-8"))
    assert recorded["ruling"] == "R-137"
    assert recorded["base_snapshot"] == drop.base
    assert recorded["drop_sums_sha256"] == drop.sums_sha
    assert recorded["max_reads"] == 2


def test_prepare_never_rewrites_a_session(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)

    with pytest.raises(SessionRefused) as refused:
        drop.prepare()

    assert refused.value.reason == "session_exists"
    assert (drop.session / "answers" / f"{FIRST}.1.md").read_text(encoding="utf-8") == CLEAN_PAGE


# --- the ledger: the unchanged rule ---------------------------------------------------------


def test_clean_answers_become_applied_repairs_that_are_unpriced(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE + "\n")
    drop.answer(SECOND, 1, CLEAN_PAGE.replace("7.2.4", "7.2.5"))

    ledger = drop.ledger()

    assert [r.outcome for r in ledger.repairs] == [RepairOutcome.REPAIRED] * 2
    assert ledger.replacement_for(SLUG, FIRST) == CLEAN_PAGE
    attempt = ledger.repairs[0].attempts[0]
    assert (attempt.model, attempt.stop_reason, attempt.cost_usd) == (MODEL, SESSION_STOP_REASON, None)
    assert (attempt.input_tokens, attempt.output_tokens, attempt.recognised_at) == (0, 0, AT)
    assert ledger.unpriced_attempts == 2
    assert ledger.total_cost_usd == 0
    assert ledger.base_snapshot_id == drop.base


def test_the_repaired_snapshot_key_moves_by_the_applied_blocks(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE.replace("7.2.4", "7.2.5"))

    repaired = repaired_snapshot(snapshot_of(drop.root), drop.ledger())

    assert "+2r." in repaired.snapshot_id
    assert repaired.snapshot_id != drop.base


def test_a_degenerate_first_read_owes_a_second_and_the_rule_takes_it(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, DEGENERATE_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE)

    with pytest.raises(ReadsOutstanding) as owed:
        drop.ledger()
    assert owed.value.outstanding == ((SLUG, FIRST, 2),)

    drop.answer(FIRST, 2, CLEAN_PAGE.replace("7.2.4", "7.2.6"))
    first = drop.ledger().repairs[0]
    assert first.outcome is RepairOutcome.REPAIRED
    assert [a.ordinal for a in first.attempts] == [1, 2]
    assert not first.attempts[1].signals


def test_two_degenerate_reads_leave_the_block_unreliable_and_unapplied(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, DEGENERATE_PAGE)
    drop.answer(FIRST, 2, DEGENERATE_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE)

    ledger = drop.ledger()

    assert ledger.repairs[0].outcome is RepairOutcome.STILL_DEGENERATE
    assert ledger.repairs[0].replacement is None
    assert ledger.unreliable_count == 1
    assert "+1r+1u." in repaired_snapshot(snapshot_of(drop.root), ledger).snapshot_id


def test_an_empty_answer_is_unusable_not_a_deletion(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, "")
    drop.answer(SECOND, 1, CLEAN_PAGE)

    ledger = drop.ledger()

    assert ledger.repairs[0].outcome is RepairOutcome.UNUSABLE
    assert ledger.replacement_for(SLUG, FIRST) is None


# --- the ledger: refusals -------------------------------------------------------------------


def test_a_missing_first_read_refuses(drop: Drop) -> None:
    drop.prepare()
    drop.answer(SECOND, 1, CLEAN_PAGE)

    with pytest.raises(SessionRefused) as refused:
        drop.ledger()

    assert refused.value.reason == "first_read_missing"


def test_a_second_read_the_rule_did_not_need_refuses(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)
    drop.answer(FIRST, 2, CLEAN_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE)

    with pytest.raises(SessionRefused) as refused:
        drop.ledger()

    assert refused.value.reason == "answer_unconsumed"


@pytest.mark.parametrize("name", [f"blk_{'c' * 32}.1.md", f"{FIRST}.1.txt", "notes.md"])
def test_an_answer_to_no_block_of_the_session_refuses(drop: Drop, name: str) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE)
    (drop.session / "answers" / name).write_text(CLEAN_PAGE, encoding="utf-8")

    with pytest.raises(SessionRefused) as refused:
        drop.ledger()

    assert refused.value.reason == "answer_unexpected"


def test_an_answer_that_is_not_utf8_refuses(drop: Drop) -> None:
    drop.prepare()
    (drop.session / "answers" / f"{FIRST}.1.md").write_bytes("Страница".encode("cp1251"))
    drop.answer(SECOND, 1, CLEAN_PAGE)

    with pytest.raises(SessionRefused) as refused:
        drop.ledger()

    assert refused.value.reason == "answer_unreadable"


def test_a_page_image_changed_after_prepare_refuses(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE)
    image = drop.session / "pages" / f"{SECOND}.png"
    image.write_bytes(image.read_bytes() + b"\x00")

    with pytest.raises(SessionRefused) as refused:
        drop.ledger()

    assert refused.value.reason == "page_image_changed"


def test_a_changed_prompt_refuses(drop: Drop, monkeypatch: pytest.MonkeyPatch) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE)
    monkeypatch.setattr(session_repair, "RECOGNITION_SYSTEM_PROMPT", RECOGNITION_SYSTEM_PROMPT + " ")

    with pytest.raises(SessionRefused) as refused:
        drop.ledger()

    assert refused.value.reason == "session_mismatch"


def test_a_prompt_file_the_readers_saw_differently_refuses(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE)
    (drop.session / "prompt.txt").write_text("Опиши страницу.", encoding="utf-8")

    with pytest.raises(SessionRefused) as refused:
        drop.ledger()

    assert refused.value.reason == "session_mismatch"


def test_a_session_record_naming_another_prompt_refuses(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE)
    record = drop.session / "session.json"
    document = json.loads(record.read_text(encoding="utf-8"))
    document["prompt_sha256"] = "0" * 64
    record.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(SessionRefused) as refused:
        drop.ledger()

    assert refused.value.reason == "session_mismatch"


@pytest.mark.parametrize(
    "override",
    [{"base_snapshot": "2026-07-23..2026-08-20+17d.000000000000"}, {"drop_sums_sha256": "0" * 64}],
)
def test_another_drop_or_sums_refuses(drop: Drop, override: dict[str, str]) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)
    drop.answer(SECOND, 1, CLEAN_PAGE)

    with pytest.raises(SessionRefused) as refused:
        drop.ledger(**override)

    assert refused.value.reason == "session_mismatch"


def test_a_page_set_that_differs_from_the_session_refuses(drop: Drop) -> None:
    drop.prepare()
    drop.answer(FIRST, 1, CLEAN_PAGE)

    with pytest.raises(SessionRefused) as refused:
        session_ledger(
            drop.pages[:1], directory=drop.session, base_snapshot=drop.base,
            drop_sums_sha256=drop.sums_sha, model=MODEL, transcribed_at=AT, generated_at=AT,
        )

    assert refused.value.reason == "session_mismatch"


@pytest.mark.parametrize(
    ("override", "reason"),
    [({"model": ""}, "model_unnamed"), ({"model": "Sonnet"}, "model_unnamed"),
     ({"transcribed_at": "yesterday"}, "transcribed_at_invalid")],
)
def test_the_session_model_and_time_must_be_named_exactly(
    drop: Drop, override: dict[str, str], reason: str
) -> None:
    drop.prepare()

    with pytest.raises(SessionRefused) as refused:
        drop.ledger(**override)

    assert refused.value.reason == reason


# --- the commands -------------------------------------------------------------------------


def _run(drop: Drop, *arguments: str) -> int:
    return command.repair_main(
        [arguments[0], "--corpus", str(drop.root), "--sums", str(drop.sums),
         "--session-dir", str(drop.session), *arguments[1:]],
        environment={},
    )


def test_the_commands_write_a_ledger_the_bundle_export_can_read(
    drop: Drop, capsys: pytest.CaptureFixture[str]
) -> None:
    out = drop.session / "ledger.json"
    assert _run(drop, "session-prepare", "--dpi", "72") == 0
    drop.answer(FIRST, 1, CLEAN_PAGE)
    drop.answer(SECOND, 1, DEGENERATE_PAGE)
    capsys.readouterr()

    assert _run(drop, "session-ledger", "--model", MODEL, "--transcribed-at", AT,
                "--out", str(out)) == command.EXIT_STOPPED
    stopped = json.loads(capsys.readouterr().out)
    assert stopped["outstanding"] == [{"document_slug": SLUG, "block_id": SECOND, "read": 2}]
    assert not out.exists()

    drop.answer(SECOND, 2, CLEAN_PAGE)
    assert _run(drop, "session-ledger", "--model", MODEL, "--transcribed-at", AT,
                "--out", str(out)) == 0
    ledger, sums = read_ledger_file(out.read_bytes())
    assert sums == drop.sums_sha
    assert json.loads(out.read_text(encoding="utf-8"))[LEDGER_SUMS_FIELD] == drop.sums_sha
    assert len(ledger.applied) == 2


def test_the_commands_refuse_a_crop_that_differs_from_the_sums(drop: Drop) -> None:
    crop = drop.root / SLUG / "crops" / f"{FIRST}.pdf"
    crop.write_bytes(crop.read_bytes() + b"\n")

    with pytest.raises(RunRefused, match="differs from its SHA256SUMS"):
        _run(drop, "session-prepare", "--dpi", "72")
    assert not (drop.session / "session.json").exists()


def test_a_session_refusal_surfaces_as_a_run_refusal(drop: Drop) -> None:
    assert _run(drop, "session-prepare", "--dpi", "72") == 0

    with pytest.raises(RunRefused, match="first_read_missing"):
        _run(drop, "session-ledger", "--model", MODEL, "--transcribed-at", AT,
             "--out", str(drop.session / "ledger.json"))
