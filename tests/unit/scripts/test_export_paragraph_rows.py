"""`AR-V3-BETA-SPANS-MEASURE-01`: the read-only paragraph-row exporter.

Everything runs on a fake corpus, so the unit tests need no database. They prove the output is
the exact ``paragraphs`` input ``map_pack`` accepts (the last test of the first group runs the
real ``build_scope_maps`` and ``validate_scope_maps`` on it) and that every refusal fires with
its own code and leaves no file behind. One class at the end runs against a real database
and is skipped unless ``EXPORT_PARAGRAPH_ROWS_TEST_DATABASE_URL`` names one.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.profiles.ar_v3.norm_map import map_pack
from auditmanager.analysis.profiles.ar_v3.norm_map.beta_sources import load_beta_source_policy
from auditmanager.shared.errors import DomainError, ErrorCode

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "export_paragraph_rows", ROOT / "scripts/norms/export_paragraph_rows.py")
assert SPEC and SPEC.loader
exporter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = exporter
SPEC.loader.exec_module(exporter)

SNAPSHOT = "ns_0000000000000000000000000A"
OTHER_SNAPSHOT = "ns_0000000000000000000000000B"
DOC_A = "ndoc_0000000000000000000000000A"
DOC_B = "ndoc_0000000000000000000000000B"
UNKNOWN_DOC = "ndoc_0000000000000000000000000C"
DESIGNATION = "SYNTH-A"


def paragraph_id(document: str, ordinal: int) -> str:
    return f"npar_{document[-1]}{'0' * 21}{ordinal:04d}"


def make_paragraph(
    document: str, ordinal: int, *, reliable: bool = True, text: str | None = None,
    clause: str | None = "1.1",
) -> Any:
    return exporter.ParagraphFacts(
        norm_paragraph_id=paragraph_id(document, ordinal), ordinal=ordinal,
        page_label=ordinal // 10 + 1, clause_number=clause,
        text=f"fixture text {document[-1]} {ordinal}" if text is None else text,
        reliable=reliable,
    )


class FakeSource:
    def __init__(self) -> None:
        self.documents: dict[str, Any] = {}
        self.rows: dict[str, list[Any]] = {}
        self.calls: list[tuple[str, int]] = []

    def add_document(
        self, document: str, count: int, *, snapshot: str = SNAPSHOT,
        designation: str = DESIGNATION, title: str = "Synthetic title",
    ) -> "FakeSource":
        self.documents[document] = exporter.DocumentFacts(
            document, snapshot, designation, title)
        self.rows[document] = [make_paragraph(document, o) for o in range(count)]
        return self

    def replace(self, document: str, ordinal: int, **changes: Any) -> None:
        rows = self.rows[document]
        index = next(i for i, row in enumerate(rows) if row.ordinal == ordinal)
        rows[index] = make_paragraph(document, ordinal, **changes)

    def drop(self, document: str, ordinal: int) -> None:
        self.rows[document] = [r for r in self.rows[document] if r.ordinal != ordinal]

    def document(self, norm_document_id: str) -> Any:
        return self.documents.get(norm_document_id)

    def paragraphs(self, norm_document_id: str, *, through_ordinal: int) -> Sequence[Any]:
        self.calls.append((norm_document_id, through_ordinal))
        return [r for r in self.rows[norm_document_id] if r.ordinal <= through_ordinal]


def span(document: str, first: int, last: int) -> Any:
    return exporter.Span(document, first, last)


def spans_bytes(*entries: tuple[str, int, int]) -> bytes:
    return json.dumps([
        {"norm_document_id": d, "ordinal_first": f, "ordinal_last": l}
        for d, f, l in entries
    ]).encode()


@pytest.fixture
def source() -> FakeSource:
    return FakeSource().add_document(DOC_A, 30).add_document(DOC_B, 12)


def refusal(callable_: Any, *args: Any, **kwargs: Any) -> str:
    with pytest.raises(exporter.ExportRefused) as caught:
        callable_(*args, **kwargs)
    return str(caught.value)


# ---------------------------------------------------------------- format

class TestFormat:
    def test_rows_are_the_exact_map_pack_input(self, source: FakeSource) -> None:
        rows = exporter.collect_rows(source, [span(DOC_A, 3, 5)], SNAPSHOT)
        data = exporter.render_rows(rows, SNAPSHOT)
        payload = json.loads(data)
        assert list(payload) == [
            "norms_snapshot_id", "paragraphs", "paragraphs_version", "synthetic"]
        assert payload["paragraphs_version"] == "ar-beta-map-paragraphs-v1"
        assert payload["synthetic"] is False
        assert payload["norms_snapshot_id"] == SNAPSHOT
        assert [set(row) for row in payload["paragraphs"]] == [
            set(map_pack._PARAGRAPH_KEYS)] * 3
        assert payload["paragraphs"][0] == {
            "norm_document_id": DOC_A, "norm_paragraph_id": paragraph_id(DOC_A, 3),
            "designation": DESIGNATION, "title": "Synthetic title", "ordinal": 3,
            "clause_number": "1.1", "page_label": "1", "text": "fixture text A 3",
            "reliable": True,
        }
        parsed = map_pack.parse_paragraphs(data)
        assert parsed.synthetic is False and parsed.snapshot_id == SNAPSHOT
        assert [row.ordinal for row in parsed.rows] == [3, 4, 5]

    def test_rows_are_ordered_by_document_and_ordinal_whatever_the_span_order(
        self, source: FakeSource,
    ) -> None:
        wanted = [span(DOC_B, 2, 3), span(DOC_A, 7, 8), span(DOC_A, 1, 2)]
        rows = exporter.collect_rows(source, wanted, SNAPSHOT)
        assert [(r["norm_document_id"], r["ordinal"]) for r in rows] == [
            (DOC_A, 1), (DOC_A, 2), (DOC_A, 7), (DOC_A, 8), (DOC_B, 2), (DOC_B, 3)]

    def test_overlapping_spans_export_each_paragraph_once(self, source: FakeSource) -> None:
        rows = exporter.collect_rows(
            source, [span(DOC_A, 3, 6), span(DOC_A, 5, 8), span(DOC_A, 3, 6)], SNAPSHOT)
        assert [r["ordinal"] for r in rows] == [3, 4, 5, 6, 7, 8]
        map_pack.parse_paragraphs(exporter.render_rows(rows, SNAPSHOT))  # no duplicate refusal

    def test_each_document_is_read_once_up_to_its_highest_ordinal(
        self, source: FakeSource,
    ) -> None:
        exporter.collect_rows(
            source, [span(DOC_A, 1, 4), span(DOC_A, 9, 12), span(DOC_B, 0, 0)], SNAPSHOT)
        assert source.calls == [(DOC_A, 12), (DOC_B, 0)]

    def test_a_null_clause_number_and_non_ascii_text_survive(self, source: FakeSource) -> None:
        source.replace(DOC_A, 4, clause=None, text="Тест № 5 — end")
        data = exporter.render_rows(
            exporter.collect_rows(source, [span(DOC_A, 4, 4)], SNAPSHOT), SNAPSHOT)
        row = map_pack.parse_paragraphs(data).rows[0]
        assert row.clause_number is None and row.text == "Тест № 5 — end"
        assert "Тест".encode() in data  # UTF-8, not \u escapes

    def test_the_rows_go_through_the_real_map_builder_and_validator(self) -> None:
        policy = load_beta_source_policy()
        fake = FakeSource().add_document(
            DOC_A, 60, snapshot=policy.snapshot_id, designation="SYNTH-POLICY")
        items = []
        for index, policy_item in enumerate(policy.items):
            first = index * 2
            target = {
                "norm_document_id": DOC_A, "designation": "SYNTH-POLICY",
                "edition": "synthetic edition", "kind": "clause",
                "ordinal_first": first, "ordinal_last": first + 1,
                "norm_paragraph_id_first": paragraph_id(DOC_A, first),
                "norm_paragraph_id_last": paragraph_id(DOC_A, first + 1),
            }
            item = {"id": policy_item.item_id, "mode": policy_item.mode, "targets": [target]}
            if policy_item.mode == "provisional_citation":
                item["branch"] = {"id": "N", "applicability": "synthetic branch"}
                item["edition_evidence"] = []
            items.append(item)
        decisions = {
            "decision_version": map_pack.DECISIONS_VERSION, "synthetic": False,
            "comment": "SYNTHETIC unit-test decisions; never a real decision.",
            "identity": {
                "norms_snapshot_id": policy.snapshot_id, "reviewed_content_key": "UNIT-TEST",
                "embedding_build": "bge-m3-dense-v1:characters-v2:1000",
                "scenario": policy.scenario,
            },
            "query_vectors": {
                "profile": "bge-m3-dense-v1", "model_revision": "0" * 40,
                "sha256_by_scope": {s: f"{n:064x}" for n, s in enumerate(map_pack.SCOPES)},
            },
            "items": items,
        }
        wanted = [span(DOC_A, 0, 43)]
        data = exporter.render_rows(
            exporter.collect_rows(fake, wanted, policy.snapshot_id), policy.snapshot_id)
        maps = map_pack.build_scope_maps(decisions)
        summary = map_pack.validate_scope_maps(maps, map_pack.parse_paragraphs(data))
        assert [s["scope_id"] for s in summary["scopes"]] == list(map_pack.SCOPES)
        assert all(s["prompt_part_characters"] > 0 for s in summary["scopes"])


# ---------------------------------------------------------------- refusals

class TestCollectionRefusals:
    def test_unknown_document(self, source: FakeSource) -> None:
        assert refusal(exporter.collect_rows, source, [span(UNKNOWN_DOC, 0, 1)],
                       SNAPSHOT) == f"document_unknown:{UNKNOWN_DOC}"

    def test_document_of_another_snapshot(self, source: FakeSource) -> None:
        source.add_document(DOC_B, 5, snapshot=OTHER_SNAPSHOT)
        assert refusal(exporter.collect_rows, source, [span(DOC_B, 0, 1)],
                       SNAPSHOT) == f"document_not_in_snapshot:{DOC_B}"

    def test_a_document_answering_for_another_identity(self, source: FakeSource) -> None:
        source.documents[DOC_B] = exporter.DocumentFacts(DOC_A, SNAPSHOT, "X", "Y")
        assert refusal(exporter.collect_rows, source, [span(DOC_B, 0, 1)],
                       SNAPSHOT) == f"document_not_in_snapshot:{DOC_B}"

    @pytest.mark.parametrize(("dropped", "first", "last", "missing"), [
        (3, 3, 8, 3),      # first ordinal absent
        (4, 1, 4, 4),      # last ordinal absent
        (None, 28, 40, 40),  # beyond the end of the document
    ])
    def test_missing_endpoint_ordinal(
        self, source: FakeSource, dropped: int | None, first: int, last: int, missing: int,
    ) -> None:
        if dropped is not None:
            source.drop(DOC_A, dropped)
        assert refusal(exporter.collect_rows, source, [span(DOC_A, first, last)],
                       SNAPSHOT) == f"ordinal_missing:{DOC_A}:{missing}"

    def test_gap_inside_the_range(self, source: FakeSource) -> None:
        source.drop(DOC_A, 5)
        assert refusal(exporter.collect_rows, source, [span(DOC_A, 3, 8)],
                       SNAPSHOT) == f"range_gap:{DOC_A}:5"

    def test_a_gap_outside_the_requested_range_is_irrelevant(self, source: FakeSource) -> None:
        source.drop(DOC_A, 12)
        rows = exporter.collect_rows(source, [span(DOC_A, 3, 8)], SNAPSHOT)
        assert len(rows) == 6

    def test_unreliable_paragraph(self, source: FakeSource) -> None:
        source.replace(DOC_A, 6, reliable=False)
        assert refusal(exporter.collect_rows, source, [span(DOC_A, 3, 8)],
                       SNAPSHOT) == f"paragraph_unreliable:{DOC_A}:6"

    def test_an_unreliable_paragraph_outside_the_range_is_irrelevant(
        self, source: FakeSource,
    ) -> None:
        source.replace(DOC_A, 9, reliable=False)
        assert len(exporter.collect_rows(source, [span(DOC_A, 3, 8)], SNAPSHOT)) == 6

    def test_duplicate_ordinal_from_the_source(self, source: FakeSource) -> None:
        source.rows[DOC_A].append(make_paragraph(DOC_A, 4))
        assert refusal(exporter.collect_rows, source, [span(DOC_A, 3, 8)],
                       SNAPSHOT) == f"paragraph_ordinal_duplicate:{DOC_A}:4"

    def test_rows_map_pack_would_refuse_are_not_exported(self, source: FakeSource) -> None:
        source.replace(DOC_A, 4, text="é decomposed")  # not NFC
        rows = exporter.collect_rows(source, [span(DOC_A, 3, 5)], SNAPSHOT)
        assert refusal(exporter.render_rows, rows, SNAPSHOT) == (
            "rows_not_accepted_by_map_pack:paragraph_row_invalid")

    def test_text_that_cannot_be_written_as_utf8(self, source: FakeSource) -> None:
        source.replace(DOC_A, 4, text="lone \ud800 surrogate")
        rows = exporter.collect_rows(source, [span(DOC_A, 3, 5)], SNAPSHOT)
        assert refusal(exporter.render_rows, rows, SNAPSHOT) == "paragraph_text_not_encodable"


class TestSpansFile:
    def test_valid_file_is_sorted_and_deduplicated(self) -> None:
        raw = spans_bytes((DOC_B, 1, 2), (DOC_A, 5, 6), (DOC_A, 5, 6), (DOC_A, 0, 0))
        assert exporter.parse_spans(raw) == (
            span(DOC_A, 0, 0), span(DOC_A, 5, 6), span(DOC_B, 1, 2))

    @pytest.mark.parametrize("raw", [
        b"", b"[]", b"{}", b"null", b"[1]", b"not json", b"\xff\xfe",
        b'[{"norm_document_id": "' + DOC_A.encode() + b'", "ordinal_first": 1}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": 1, "ordinal_last": 2, "extra": 1}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": 1, "ordinal_first": 1, "ordinal_last": 2}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": true, "ordinal_last": 2}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": 1.0, "ordinal_last": 2}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": NaN, "ordinal_last": 2}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": -1, "ordinal_last": 2}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": 5, "ordinal_last": 4}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": 1, "ordinal_last": 2147483648}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": 0, "ordinal_last": 5000}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'", "ordinal_first": 1, "ordinal_last": 1' + b"0" * 5000 + b"}]",
        b'[{"norm_document_id": "not-an-id", "ordinal_first": 1, "ordinal_last": 2}]',
        b'[{"norm_document_id": "' + DOC_A.encode()
        + b'\\n", "ordinal_first": 1, "ordinal_last": 2}]',
        b'[{"norm_document_id": 7, "ordinal_first": 1, "ordinal_last": 2}]',
    ])
    def test_every_defect_is_refused_with_one_code(self, raw: bytes) -> None:
        assert refusal(exporter.parse_spans, raw) == "spans_file_invalid"

    def test_a_span_of_exactly_the_maximum_length_is_accepted(self) -> None:
        raw = spans_bytes((DOC_A, 0, exporter.MAX_SPAN_PARAGRAPHS - 1))
        assert exporter.parse_spans(raw)[0].ordinal_last == exporter.MAX_SPAN_PARAGRAPHS - 1

    def test_oversize_file(self) -> None:
        raw = b"[" + b" " * exporter.MAX_SPANS_BYTES + b"]"
        assert refusal(exporter.parse_spans, raw) == "spans_file_invalid"

    def test_too_many_spans(self) -> None:
        raw = spans_bytes(*[(DOC_A, n, n) for n in range(exporter.MAX_SPANS + 1)])
        assert refusal(exporter.parse_spans, raw) == "spans_file_invalid"

    @pytest.mark.parametrize("value", [
        "", "ns_", SNAPSHOT + "\n", "nsx_0000000000000000000000000A", DOC_A, None, 5,
    ])
    def test_snapshot_id_must_be_an_exact_identity(self, value: object) -> None:
        assert refusal(exporter.parse_snapshot_id, value) == "snapshot_id_invalid"

    def test_snapshot_id_accepted(self) -> None:
        assert exporter.parse_snapshot_id(SNAPSHOT) == SNAPSHOT


# ---------------------------------------------------------------- measuring

class TestMeasure:
    def test_numbers_for_a_clean_span(self, source: FakeSource) -> None:
        source.replace(DOC_A, 3, clause="4.2.7")
        report = exporter.measure_spans(source, [span(DOC_A, 3, 5)], SNAPSHOT)
        entry = report["spans"][0]
        texts = [f"fixture text A {n}" for n in (3, 4, 5)]
        assert entry["expected_paragraphs"] == entry["present_paragraphs"] == 3
        assert entry["missing_count"] == entry["unreliable_count"] == 0
        assert entry["text_characters"] == sum(len(t) for t in texts)
        assert entry["longest_paragraph_characters"] == max(len(t) for t in texts)
        assert entry["paragraph_id_first"] == paragraph_id(DOC_A, 3)
        assert entry["paragraph_id_last"] == paragraph_id(DOC_A, 5)
        assert entry["clause_number_first"] == "4.2.7"
        import hashlib
        assert entry["text_sha256"] == hashlib.sha256("\n".join(texts).encode()).hexdigest()
        assert report["documents"] == [{
            "norm_document_id": DOC_A, "designation": DESIGNATION,
            "designation_characters": len(DESIGNATION), "title_characters": 15}]

    def test_missing_and_unreliable_paragraphs_are_reported_not_refused(
        self, source: FakeSource,
    ) -> None:
        source.drop(DOC_A, 5)
        source.drop(DOC_A, 8)
        source.replace(DOC_A, 6, reliable=False)
        entry = exporter.measure_spans(source, [span(DOC_A, 3, 8)], SNAPSHOT)["spans"][0]
        assert entry["expected_paragraphs"] == 6 and entry["present_paragraphs"] == 4
        assert entry["missing_count"] == 2 and entry["missing_ordinals"] == [5, 8]
        assert entry["unreliable_count"] == 1 and entry["unreliable_ordinals"] == [6]
        assert entry["paragraph_id_last"] is None  # ordinal 8 does not exist

    def test_a_span_past_the_end_reports_every_missing_ordinal(self, source: FakeSource) -> None:
        entry = exporter.measure_spans(source, [span(DOC_B, 10, 15)], SNAPSHOT)["spans"][0]
        assert entry["missing_ordinals"] == [12, 13, 14, 15] and entry["present_paragraphs"] == 2

    def test_the_listed_missing_ordinals_are_capped_but_counted(self) -> None:
        source = FakeSource().add_document(DOC_A, 0)
        entry = exporter.measure_spans(source, [span(DOC_A, 0, 99)], SNAPSHOT)["spans"][0]
        assert entry["missing_count"] == 100
        assert len(entry["missing_ordinals"]) == exporter.MAX_LISTED_ORDINALS

    def test_the_report_carries_no_paragraph_text(self, source: FakeSource) -> None:
        source.replace(DOC_A, 4, text="SENTINEL-PARAGRAPH-TEXT")
        text = json.dumps(exporter.measure_spans(source, [span(DOC_A, 3, 5)], SNAPSHOT))
        assert "SENTINEL" not in text and "fixture text" not in text

    def test_unknown_document_and_foreign_snapshot_still_refuse(self, source: FakeSource) -> None:
        assert refusal(exporter.measure_spans, source, [span(UNKNOWN_DOC, 0, 1)],
                       SNAPSHOT) == f"document_unknown:{UNKNOWN_DOC}"
        assert refusal(exporter.measure_spans, source, [span(DOC_A, 0, 1)],
                       OTHER_SNAPSHOT) == f"document_not_in_snapshot:{DOC_A}"


# ---------------------------------------------------------------- output file

class TestOutputFile:
    def test_created_exclusively_with_mode_0600_whatever_the_umask(self, tmp_path: Path) -> None:
        path = tmp_path / "rows.json"
        previous = os.umask(0)
        try:
            exporter.write_new_file(path, b"data")
        finally:
            os.umask(previous)
        assert path.read_bytes() == b"data"
        assert stat.S_IMODE(path.stat().st_mode) == 0o600

    def test_existing_file_is_never_overwritten(self, tmp_path: Path) -> None:
        path = tmp_path / "rows.json"
        path.write_bytes(b"keep")
        assert refusal(exporter.write_new_file, path, b"new") == "output_exists"
        assert path.read_bytes() == b"keep"

    def test_a_dangling_symlink_counts_as_taken(self, tmp_path: Path) -> None:
        target = tmp_path / "elsewhere.json"
        link = tmp_path / "rows.json"
        link.symlink_to(target)
        assert refusal(exporter.write_new_file, link, b"new") == "output_exists"
        assert not target.exists()

    def test_missing_directory_is_a_typed_refusal(self, tmp_path: Path) -> None:
        assert refusal(exporter.write_new_file, tmp_path / "no" / "rows.json",
                       b"x") == "output_unwritable"

    def test_a_failed_write_leaves_no_half_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "rows.json"

        def broken(descriptor: int, mode: str) -> Any:
            os.close(descriptor)
            raise OSError("disk full")

        monkeypatch.setattr(exporter.os, "fdopen", broken)
        assert refusal(exporter.write_new_file, path, b"x") == "output_unwritable"
        assert not path.exists()

    def test_inside_the_repository_tree_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo = tmp_path / "repo"
        (repo / "docs").mkdir(parents=True)
        (repo / ".local" / "draft").mkdir(parents=True)
        monkeypatch.setattr(exporter, "_ROOT", repo)
        assert refusal(exporter.require_untracked_location,
                       repo / "docs" / "rows.json") == "output_inside_repository_tree"
        assert refusal(exporter.require_untracked_location,
                       repo / "rows.json") == "output_inside_repository_tree"
        exporter.require_untracked_location(repo / ".local" / "draft" / "rows.json")
        exporter.require_untracked_location(tmp_path / "rows.json")

    def test_a_symlinked_directory_into_the_tree_is_still_inside(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo = tmp_path / "repo"
        (repo / "docs").mkdir(parents=True)
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "link").symlink_to(repo / "docs")
        monkeypatch.setattr(exporter, "_ROOT", repo)
        assert refusal(exporter.require_untracked_location,
                       outside / "link" / "rows.json") == "output_inside_repository_tree"


# ---------------------------------------------------------------- command line

class Opener:
    """A context manager factory handing out one fake source; counts how often it was opened."""

    def __init__(self, source: FakeSource | None) -> None:
        self.source = source
        self.opened = 0

    def __call__(self) -> "Opener":
        self.opened += 1
        return self

    def __enter__(self) -> FakeSource:
        assert self.source is not None, "the database must not be opened"
        return self.source

    def __exit__(self, *exc: object) -> None:
        return None


@pytest.fixture
def spans_file(tmp_path: Path) -> Path:
    path = tmp_path / "spans.json"
    path.write_bytes(spans_bytes((DOC_A, 3, 5)))
    return path


class TestCommandLine:
    def test_export_writes_rows_and_prints_nothing(
        self, source: FakeSource, spans_file: Path, tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        out = tmp_path / "rows.json"
        code = exporter.main(["--spans", str(spans_file), "--snapshot", SNAPSHOT,
                              "--out", str(out)], opener=Opener(source))
        assert code == 0 and capsys.readouterr().out == ""
        assert [r.ordinal for r in map_pack.parse_paragraphs(out.read_bytes()).rows] == [3, 4, 5]
        assert stat.S_IMODE(out.stat().st_mode) == 0o600

    def test_measure_prints_json_and_writes_no_file(
        self, source: FakeSource, spans_file: Path, tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        code = exporter.main(["--spans", str(spans_file), "--snapshot", SNAPSHOT, "--measure"],
                             opener=Opener(source))
        assert code == 0
        assert json.loads(capsys.readouterr().out)["spans"][0]["present_paragraphs"] == 3
        assert list(tmp_path.iterdir()) == [spans_file]

    def test_refusal_prints_the_code_exits_2_and_leaves_no_output(
        self, source: FakeSource, spans_file: Path, tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        source.replace(DOC_A, 4, reliable=False)
        out = tmp_path / "rows.json"
        code = exporter.main(["--spans", str(spans_file), "--snapshot", SNAPSHOT,
                              "--out", str(out)], opener=Opener(source))
        assert code == 2
        assert capsys.readouterr().err == f"REFUSED: paragraph_unreliable:{DOC_A}:4\n"
        assert not out.exists()

    def test_existing_output_is_refused_before_the_database_is_opened(
        self, spans_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        out = tmp_path / "rows.json"
        out.write_bytes(b"keep")
        opener = Opener(None)
        code = exporter.main(["--spans", str(spans_file), "--snapshot", SNAPSHOT,
                              "--out", str(out)], opener=opener)
        assert code == 2 and opener.opened == 0
        assert capsys.readouterr().err == "REFUSED: output_exists\n"
        assert out.read_bytes() == b"keep"

    def test_output_inside_the_tree_is_refused_before_the_database_is_opened(
        self, spans_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repo = tmp_path / "repo"
        (repo / "docs").mkdir(parents=True)
        monkeypatch.setattr(exporter, "_ROOT", repo)
        opener = Opener(None)
        code = exporter.main(["--spans", str(spans_file), "--snapshot", SNAPSHOT,
                              "--out", str(repo / "docs" / "rows.json")], opener=opener)
        assert code == 2 and opener.opened == 0
        assert capsys.readouterr().err == "REFUSED: output_inside_repository_tree\n"
        assert not (repo / "docs" / "rows.json").exists()

    @pytest.mark.parametrize(("content", "code"), [
        (b"[]", "spans_file_invalid"), (None, "spans_file_unreadable"),
    ])
    def test_bad_or_missing_spans_file(
        self, tmp_path: Path, content: bytes | None, code: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = tmp_path / "spans.json"
        if content is not None:
            path.write_bytes(content)
        assert exporter.main(["--spans", str(path), "--snapshot", SNAPSHOT, "--measure"],
                             opener=Opener(None)) == 2
        assert capsys.readouterr().err == f"REFUSED: {code}\n"

    def test_bad_snapshot_id(
        self, spans_file: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert exporter.main(["--spans", str(spans_file), "--snapshot", "ns_x", "--measure"],
                             opener=Opener(None)) == 2
        assert capsys.readouterr().err == "REFUSED: snapshot_id_invalid\n"

    def test_missing_database_url_is_a_typed_refusal(
        self, spans_file: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert exporter.main(["--spans", str(spans_file), "--snapshot", SNAPSHOT,
                              "--measure"]) == 2
        assert capsys.readouterr().err == "REFUSED: database_url_missing\n"

    def test_invalid_database_url_never_echoes_the_value(
        self, spans_file: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "sqlite://user:s3cret@host/db")
        assert exporter.main(["--spans", str(spans_file), "--snapshot", SNAPSHOT,
                              "--measure"]) == 2
        err = capsys.readouterr().err
        assert err == "REFUSED: database_url_invalid\n" and "s3cret" not in err

    def test_out_and_measure_are_mutually_exclusive(self, spans_file: Path) -> None:
        with pytest.raises(SystemExit) as caught:
            exporter.main(["--spans", str(spans_file), "--snapshot", SNAPSHOT, "--measure",
                           "--out", "x.json"], opener=Opener(None))
        assert caught.value.code == 2


# ---------------------------------------------------------------- the database adapter

def view(ordinal: int, *, reliability: str = "reliable", clause: str | None = "2.1") -> Any:
    return SimpleNamespace(
        norm_paragraph_id=paragraph_id(DOC_A, ordinal), ordinal=ordinal, page_label=3,
        block_ref="blk", kind="body", clause_number=clause, text=f"text {ordinal}",
        text_reliability=reliability)


class TestDatabaseSource:
    def install(self, monkeypatch: pytest.MonkeyPatch, pages: list[list[Any]]) -> list[Any]:
        requested: list[Any] = []

        def fake_list(session: Any, document: str, *, cursor: str | None, limit: int) -> Any:
            requested.append((cursor, limit))
            index = 0 if cursor is None else int(cursor)
            more = index + 1 < len(pages)
            return None, SimpleNamespace(
                items=tuple(pages[index]), next_cursor=str(index + 1) if more else None)

        monkeypatch.setattr(exporter, "list_norm_paragraphs", fake_list)
        return requested

    def test_pages_are_followed_and_converted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        requested = self.install(monkeypatch, [[view(0), view(1)], [view(2)], [view(3)]])
        rows = exporter.DatabaseSource(object()).paragraphs(DOC_A, through_ordinal=99)
        assert [r.ordinal for r in rows] == [0, 1, 2, 3]
        assert requested == [(None, 500), ("1", 500), ("2", 500)]
        assert rows[0] == exporter.ParagraphFacts(
            paragraph_id(DOC_A, 0), 0, 3, "2.1", "text 0", True)

    def test_reading_stops_after_the_highest_requested_ordinal(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        requested = self.install(monkeypatch, [[view(0), view(1), view(2)], [view(3)]])
        rows = exporter.DatabaseSource(object()).paragraphs(DOC_A, through_ordinal=1)
        assert [r.ordinal for r in rows] == [0, 1] and len(requested) == 1

    def test_unreliable_is_carried_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.install(monkeypatch, [[view(0, reliability="unreliable", clause=None)]])
        row = exporter.DatabaseSource(object()).paragraphs(DOC_A, through_ordinal=9)[0]
        assert row.reliable is False and row.clause_number is None

    def test_an_unknown_reliability_value_is_refused(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self.install(monkeypatch, [[view(0, reliability="probably")]])
        assert refusal(exporter.DatabaseSource(object()).paragraphs, DOC_A,
                       through_ordinal=9) == "text_reliability_unknown"

    def test_a_source_that_does_not_advance_cannot_loop_forever(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self.install(monkeypatch, [[view(0), view(1)], [view(1), view(2)]])
        assert refusal(exporter.DatabaseSource(object()).paragraphs, DOC_A,
                       through_ordinal=9) == f"paragraph_order_invalid:{DOC_A}"

    def test_a_refused_read_is_typed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def broken(*args: Any, **kwargs: Any) -> Any:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="NormDocument")

        monkeypatch.setattr(exporter, "list_norm_paragraphs", broken)
        assert refusal(exporter.DatabaseSource(object()).paragraphs, DOC_A,
                       through_ordinal=9) == "database_refused:not_found"

    def test_document_conversion_and_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_get(session: Any, document: str) -> Any:
            if document == UNKNOWN_DOC:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="NormDocument")
            return SimpleNamespace(
                norm_document_id=document, norms_snapshot_id=SNAPSHOT,
                designation="SYNTH-A", title="Title", paragraph_count=1)

        monkeypatch.setattr(exporter, "get_norm_document", fake_get)
        source = exporter.DatabaseSource(object())
        assert source.document(UNKNOWN_DOC) is None
        assert source.document(DOC_A) == exporter.DocumentFacts(
            DOC_A, SNAPSHOT, "SYNTH-A", "Title")

    def test_any_other_domain_error_is_refused_not_hidden(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def broken(*args: Any, **kwargs: Any) -> Any:
            raise DomainError(ErrorCode.REQUIRED_NORM_UNAVAILABLE)

        monkeypatch.setattr(exporter, "get_norm_document", broken)
        assert refusal(exporter.DatabaseSource(object()).document,
                       DOC_A) == "database_refused:required_norm_unavailable"


class FakeSession:
    def __init__(self, answer: object) -> None:
        self.answer = answer
        self.statements: list[str] = []

    def execute(self, statement: Any) -> Any:
        self.statements.append(str(statement))
        return SimpleNamespace(scalar=lambda: self.answer)


class TestReadOnlyProof:
    def test_a_read_write_transaction_is_refused(self) -> None:
        session = FakeSession("off")
        assert refusal(exporter.require_read_only, session) == "database_not_read_only"
        assert session.statements == ["SHOW transaction_read_only"]

    @pytest.mark.parametrize("answer", [None, "", "ON ", 1, True])
    def test_only_the_exact_answer_on_passes(self, answer: object) -> None:
        assert refusal(exporter.require_read_only, FakeSession(answer)) == (
            "database_not_read_only")

    def test_a_read_only_transaction_passes(self) -> None:
        exporter.require_read_only(FakeSession("on"))


# ---------------------------------------------------------------- real database (optional)

DATABASE_URL = os.environ.get("EXPORT_PARAGRAPH_ROWS_TEST_DATABASE_URL")
QUALIFIED_SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
DOC_D1 = "ndoc_01M59N9JD4VPS1C8ACDFC01BGG"


@pytest.mark.skipif(DATABASE_URL is None, reason="EXPORT_PARAGRAPH_ROWS_TEST_DATABASE_URL not set")
class TestAgainstTheQualifiedSnapshot:
    """Needs the stopped local custody stack of AR-BETA-LOCAL-CUSTODY-01, started read-only."""

    def test_the_transaction_cannot_write(self) -> None:
        from sqlalchemy import text
        from sqlalchemy.exc import DBAPIError

        assert DATABASE_URL is not None
        with exporter.open_database_source(DATABASE_URL) as source:
            session = source._session  # type: ignore[attr-defined]
            with pytest.raises(DBAPIError, match="read-only transaction"):
                session.execute(text(
                    "UPDATE norms_snapshot SET unreliable_count = unreliable_count WHERE false"))

    def test_one_span_measures_and_exports(self, tmp_path: Path) -> None:
        assert DATABASE_URL is not None
        wanted = [span(DOC_D1, 132, 137)]
        with exporter.open_database_source(DATABASE_URL) as source:
            entry = exporter.measure_spans(source, wanted, QUALIFIED_SNAPSHOT)["spans"][0]
            rows = exporter.collect_rows(source, wanted, QUALIFIED_SNAPSHOT)
        assert entry["present_paragraphs"] == 6 and entry["missing_count"] == 0
        assert entry["text_characters"] == 1417
        data = exporter.render_rows(rows, QUALIFIED_SNAPSHOT)
        assert [r.ordinal for r in map_pack.parse_paragraphs(data).rows] == list(range(132, 138))

    def test_an_unknown_document_is_refused(self) -> None:
        assert DATABASE_URL is not None
        with exporter.open_database_source(DATABASE_URL) as source:
            assert refusal(exporter.collect_rows, source, [span(UNKNOWN_DOC, 0, 1)],
                           QUALIFIED_SNAPSHOT) == f"document_unknown:{UNKNOWN_DOC}"
