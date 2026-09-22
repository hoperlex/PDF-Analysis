"""`R-17`'s corpus-snapshot identifier, and why it is not a date.

The ruling states provenance as a footnote naming a source and a date, with documents not
pinned to versions. The integrator recorded the consequence: the snapshot date becomes the
only anchor of provenance, so it has to be a field on chunk rows or the first refresh makes
every past verdict uninterpretable.

Measured over all 674 documents, the `Дата сохранения` field reads 23.07.2026 for 395,
24.07.2026 for 256, 20.08.2026 for 6, and is absent from 17. These tests hold the identifier
to that shape rather than to a day.
"""

from __future__ import annotations

from auditmanager.norms import SourceAttribution, attribution, derive, drawn_on, fingerprint


def test_the_identifier_is_a_window_and_not_a_day() -> None:
    corpus = [
        fingerprint(f"july-{index}", f"doc_j{index}", f"{index}".encode(), "2026-07-23")
        for index in range(395)
    ] + [
        fingerprint(f"august-{index}", f"doc_a{index}", f"{index}".encode(), "2026-08-20")
        for index in range(6)
    ]
    snapshot = derive(corpus)
    assert snapshot.drawn_from == "2026-07-23"
    assert snapshot.drawn_to == "2026-08-20"
    assert snapshot.footnote_window == "2026-07-23..2026-08-20"
    assert "2026-07-23..2026-08-20" in snapshot.snapshot_id


def test_the_window_stays_a_window_when_a_corpus_is_drawn_in_one_sitting() -> None:
    """Otherwise the footnote quietly becomes a single date the next time it can."""
    snapshot = derive([fingerprint("a", "doc_a", b"x", "2026-07-23")])
    assert snapshot.footnote_window == "2026-07-23..2026-07-23"


def test_an_entirely_undated_corpus_is_not_given_a_date_it_does_not_have() -> None:
    snapshot = derive([fingerprint("a", "doc_a", b"x", None)])
    assert snapshot.drawn_from is None
    assert snapshot.footnote_window == "date not stated by the corpus"
    assert snapshot.snapshot_id.startswith("undated+1d.")


def test_attribution_is_a_field_because_the_footnote_names_one_source(
    consultant_plus_markdown: str, unattributed_markdown: str
) -> None:
    """`R-17`'s footnote names ConsultantPlus. It is accurate for 657 documents and not for 17.

    Those 17 carry no ConsultantPlus marker in any form — not the stamp, not the URL, not
    the save date — and one of them, `ГОСТ_Р_72509-2026`, prints a different publisher's line
    49 times. If attribution is not a field, nothing downstream can tell the 657 from the 17,
    and the appendix's single sentence is inaccurate for the ones it cannot name.
    """
    assert attribution(consultant_plus_markdown) is SourceAttribution.CONSULTANT_PLUS
    assert attribution(unattributed_markdown) is SourceAttribution.UNATTRIBUTED


def test_the_draw_date_is_read_as_iso_and_absence_is_none(
    consultant_plus_markdown: str, unattributed_markdown: str
) -> None:
    assert drawn_on(consultant_plus_markdown) == "2026-07-23"
    assert drawn_on(unattributed_markdown) is None


def test_the_identifier_states_how_many_documents_the_window_does_not_cover() -> None:
    """A reader who sees `+17d` asks what those are. A reader who sees a window does not."""
    corpus = [fingerprint("a", "doc_a", b"x", "2026-07-23")] + [
        fingerprint(f"u{index}", f"doc_u{index}", f"{index}".encode(), None) for index in range(17)
    ]
    assert "+17d." in derive(corpus).snapshot_id


def test_the_full_digest_is_kept_so_nothing_depends_on_the_truncation() -> None:
    snapshot = derive([fingerprint("a", "doc_a", b"x", "2026-07-23")])
    assert len(snapshot.content_digest) == 64
    assert snapshot.content_digest.startswith(snapshot.snapshot_id.rsplit(".", 1)[-1])
