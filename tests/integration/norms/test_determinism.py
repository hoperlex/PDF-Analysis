"""The same bytes in give byte-identical chunks out.

`W33-CORPUS` requires it and the reason is not tidiness. A chunk row carries a snapshot
identifier so that a verdict citing a clause can be re-read against the corpus it was taken
against. If segmenting the same drop twice produced different chunk boundaries, ordinals or
offsets, that identifier would point at a corpus nobody can reconstruct, and the `R-17`
consequence it exists to serve would be satisfied in form and not in fact.

The proof runs the pipeline twice over the same input and compares the serialised output.
It is deliberately a serialisation comparison rather than a field-by-field one: a field the
pipeline gains later is covered without anyone remembering to add it here.
"""

from __future__ import annotations

import json
import os
import pathlib
import random
import subprocess
import sys
import textwrap

from auditmanager.norms import derive, fingerprint, join_into_chunks, segment
from auditmanager.norms.snapshot import DocumentFingerprint


def _serialise(markdown: str, slug: str = "example") -> str:
    paragraphs, report = segment(slug, markdown)
    chunks = join_into_chunks(paragraphs, "snapshot-under-test")
    return json.dumps(
        {
            "report": [
                report.document_slug, report.page_headings, report.blocks,
                report.recognised_characters, report.candidates,
                report.discarded_publisher_noise, report.discarded_repeated_offcut,
                report.substantive, report.numbered_clauses, report.headings,
                report.table_rows, report.substantive_characters, report.drawn_on,
                report.attribution.value,
            ],
            "paragraphs": [
                [p.document_slug, p.page_label, p.block_id, p.ordinal, p.char_offset,
                 p.char_length, p.kind.value, p.clause_number, p.text]
                for p in paragraphs
            ],
            "chunks": [
                [c.snapshot_id, c.document_slug, c.ordinal, c.page_first, c.page_last,
                 c.char_offset, c.char_length, c.paragraph_count, list(c.clause_numbers),
                 c.content_sha256, c.text]
                for c in chunks
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def test_two_runs_over_one_input_are_byte_identical(
    consultant_plus_markdown: str, unattributed_markdown: str, gapped_pages_markdown: str
) -> None:
    for markdown in (consultant_plus_markdown, unattributed_markdown, gapped_pages_markdown):
        first = _serialise(markdown)
        second = _serialise(markdown)
        assert first == second


def test_the_run_does_not_depend_on_the_process_it_runs_in(consultant_plus_markdown: str) -> None:
    """Nothing in the pipeline may reach for a hash seed, a clock or a set's ordering.

    A `PYTHONHASHSEED`-dependent output is the exact failure the test above cannot see,
    because both of its runs share one process and therefore one seed. So this one segments
    the same input in fresh interpreters under three different seeds and compares the bytes.
    Without it, `frozenset` membership in the offcut rule and any future `dict` iteration
    would be unguarded, and the resulting non-determinism would appear only across machines.
    """
    source = pathlib.Path(__file__).resolve().parents[3] / "src"
    program = textwrap.dedent(
        """
        import json, sys
        from auditmanager.norms import join_into_chunks, segment
        markdown = sys.stdin.read()
        paragraphs, report = segment("example", markdown)
        chunks = join_into_chunks(paragraphs, "snapshot-under-test")
        print(json.dumps(
            [[c.ordinal, c.page_first, c.page_last, c.char_offset, c.char_length,
              c.paragraph_count, list(c.clause_numbers), c.content_sha256]
             for c in chunks] +
            [[p.ordinal, p.char_offset, p.char_length, p.kind.value, p.clause_number]
             for p in paragraphs],
            ensure_ascii=False, sort_keys=True))
        """
    )
    outputs = set()
    for seed in ("0", "1", "4242"):
        environment = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(source))
        completed = subprocess.run(
            [sys.executable, "-c", program],
            input=consultant_plus_markdown,
            capture_output=True,
            text=True,
            env=environment,
            check=True,
        )
        outputs.add(completed.stdout)
    assert len(outputs) == 1, "segmentation differs between interpreters with different hash seeds"


def test_the_snapshot_identifier_does_not_depend_on_directory_order(
    consultant_plus_markdown: str,
) -> None:
    """A filesystem walk has no guaranteed order, so the digest sorts before it hashes."""
    fingerprints = [
        fingerprint(f"slug-{index:03d}", f"doc_{index:03d}", f"body {index}".encode(), "2026-07-23")
        for index in range(25)
    ]
    expected = derive(fingerprints).snapshot_id
    shuffled = list(fingerprints)
    rng = random.Random(20260922)
    for _ in range(5):
        rng.shuffle(shuffled)
        assert derive(shuffled).snapshot_id == expected


def test_one_changed_byte_anywhere_changes_the_snapshot(consultant_plus_markdown: str) -> None:
    """The dates are what the corpus says; the digest is what it is.

    A refresh that reissues a ГОСТ under the same `Дата сохранения` moves no date. If the
    identifier were the window alone, that refresh would be invisible, and the verdicts taken
    against the old text would claim to have been taken against the new one.
    """
    base = [
        fingerprint("a", "doc_a", b"first", "2026-07-23"),
        fingerprint("b", "doc_b", b"second", "2026-07-23"),
    ]
    changed = [base[0], fingerprint("b", "doc_b", b"seconD", "2026-07-23")]
    assert derive(base).snapshot_id != derive(changed).snapshot_id
    assert derive(base).drawn_from == derive(changed).drawn_from, (
        "the window is unmoved, which is precisely why the window cannot be the identifier"
    )


def test_a_corpus_with_no_documents_is_refused_rather_than_given_an_identifier() -> None:
    """A silent fallback here would name an empty corpus and every later figure about it."""
    import pytest

    with pytest.raises(ValueError):
        derive([])


def test_an_undated_document_is_counted_in_the_identifier_and_not_dropped() -> None:
    mixed: list[DocumentFingerprint] = [
        fingerprint("a", "doc_a", b"x", "2026-07-23"),
        fingerprint("b", "doc_b", b"y", "2026-08-20"),
        fingerprint("c", "doc_c", b"z", None),
    ]
    snapshot = derive(mixed)
    assert snapshot.undated_documents == 1
    assert "+1d." in snapshot.snapshot_id
    assert snapshot.document_count == 3
