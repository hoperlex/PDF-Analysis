"""The promotion command's bundle format, refusals and exit codes, with no database.

A fake runner stands in for the database and the object store, so these tests hold the
order of the calls and the meaning of exit status 0, 2 and 3. The same command against a
real PostgreSQL and S3 is ``tests/integration/norms/custody/test_promote_cli_db.py``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import signal
import struct
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.norms.custody import NORM_CATALOGUE, NORM_RETRIEVAL_SET, CustodyRefused
from auditmanager.norms.embedding import vectors
from auditmanager.norms.embedding.profile import DIMENSIONS, EMBEDDING_PROFILE
from auditmanager.norms.retrieval import promote_cli
from auditmanager.norms.retrieval.artifact import CanonicalBlob, canonical_json_bytes
from auditmanager.norms.retrieval.candidate import RetrievalCandidate
from auditmanager.norms.retrieval.promotion import (
    PreparedPromotion,
    PromotionOutcome,
    PromotionRefused,
    PromotionRequest,
)
from auditmanager.norms.retrieval.qualification_decision import DigestComparison
from auditmanager.norms.retrieval.ranking import PromptSelection
from auditmanager.shared.db import (
    DatabaseConfigurationError,
    reset_session_factory,
)
from auditmanager.shared.db.engine import dispose_engine
from auditmanager.shared.errors import ErrorCode
from auditmanager.shared.identity import NormRetrievalSetId
from auditmanager.storage.errors import StorageConfigurationError

SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
DOCUMENT = "ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B"
CHUNKING = "characters-v2:1200"
MAP_BYTES = canonical_json_bytes({"mapped_document_ids": [DOCUMENT], "note": "reviewed"})
SET_BYTES = canonical_json_bytes({"set": "canonical paragraph"})
CATALOGUE_BYTES = canonical_json_bytes({"catalogue": "canonical documents"})


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


SET_SHA, CATALOGUE_SHA = _sha(SET_BYTES), _sha(CATALOGUE_BYTES)
PACKED = vectors.pack([1.0] + [0.0] * (DIMENSIONS - 1))


def _request(*, expected: bool = True, set_id: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "format": promote_cli.REQUEST_FORMAT,
        "set_id": set_id or str(NormRetrievalSetId.new()),
        "snapshot_id": SNAPSHOT,
        "reviewed_content_key": "reviewed-drop",
        "embedding_build": f"{EMBEDDING_PROFILE}:{CHUNKING}",
        "chunking_profile": CHUNKING,
        "independently_checked_source_digest": "1" * 64,
        "independently_checked_embedding_digest": "2" * 64,
        "designations": [
            {"document_id": DOCUMENT, "slug": "synthetic_slug", "designation": "СП 99.1"},
        ],
        "items": [{
            "item_id": "C01",
            "query_vector_base64": vectors.to_base64(PACKED),
            "provenance": {"query_text_sha256": "3" * 64,
                           "query_vector_sha256": vectors.sha256(PACKED)},
            "targets": [{"document_id": DOCUMENT, "ordinal_first": 0, "ordinal_last": 1}],
        }],
    }
    if expected:
        value["expected_set_sha256"] = SET_SHA
        value["expected_catalogue_sha256"] = CATALOGUE_SHA
    return value


def _bundle(
    root: Path, mutate: Callable[[dict[str, Any]], None] | None = None, *,
    expected: bool = True, raw: str | None = None, name: str = "bundle",
) -> Path:
    directory = root / name
    directory.mkdir()
    (directory / "map.json").write_bytes(MAP_BYTES)
    value = _request(expected=expected)
    if mutate is not None:
        mutate(value)
    (directory / "request.json").write_text(
        raw if raw is not None else json.dumps(value, ensure_ascii=False), encoding="utf-8",
    )
    return directory


def _refusal(directory: Path, *, require_expected: bool = True) -> promote_cli.CliRefused:
    with pytest.raises(promote_cli.CliRefused) as raised:
        promote_cli.load_bundle(directory, require_expected=require_expected)
    return raised.value


# --- new-id ---------------------------------------------------------------------------------


def test_new_id_prints_a_fresh_nrs_identity(capsys: pytest.CaptureFixture[str]) -> None:
    assert promote_cli.main(["new-id"]) == 0
    first = capsys.readouterr().out.strip()
    assert promote_cli.main(["new-id"]) == 0
    second = capsys.readouterr().out.strip()
    assert str(NormRetrievalSetId.parse(first)) == first and first != second


# --- the bundle -----------------------------------------------------------------------------


def test_the_bundle_maps_into_the_library_request_with_the_map_bytes_untouched(
    tmp_path: Path,
) -> None:
    padded = MAP_BYTES + b"\n"  # whatever is on disk is hashed, never re-serialised
    directory = _bundle(tmp_path)
    (directory / "map.json").write_bytes(padded)
    loaded = promote_cli.load_bundle(directory, require_expected=True)
    request = loaded.request
    assert loaded.compared is True and isinstance(request, PromotionRequest)
    assert request.map_bytes == padded
    assert request.identity.map_sha256 == _sha(padded)
    assert (request.identity.snapshot_id, request.identity.reviewed_content_key) == (
        SNAPSHOT, "reviewed-drop",
    )
    assert request.identity.embedding_build == f"{EMBEDDING_PROFILE}:{CHUNKING}"
    assert request.chunking_profile == CHUNKING
    assert (request.expected_set_sha256, request.expected_catalogue_sha256) == (SET_SHA, CATALOGUE_SHA)
    assert request.independently_checked_source_digest == "1" * 64
    assert request.independently_checked_embedding_digest == "2" * 64
    (designation,) = request.reviewed_designations
    assert (designation.document_id, designation.slug, designation.designation) == (
        DOCUMENT, "synthetic_slug", "СП 99.1",
    )
    (item,) = request.items
    assert item.item_id == "C01"
    assert item.query_vector.typecode == "f" and tuple(item.query_vector) == vectors.unpack(PACKED)
    ((target),) = item.targets
    assert (target.document_id, target.ordinal_first, target.ordinal_last) == (DOCUMENT, 0, 1)


def test_a_plan_bundle_may_omit_the_expectations_but_never_one_of_them(tmp_path: Path) -> None:
    loaded = promote_cli.load_bundle(
        _bundle(tmp_path, expected=False), require_expected=False,
    )
    assert loaded.compared is False
    assert loaded.request.expected_set_sha256 == promote_cli._NO_EXPECTATION
    assert loaded.request.expected_catalogue_sha256 == promote_cli._NO_EXPECTATION
    only_one = _bundle(
        tmp_path, lambda value: value.pop("expected_catalogue_sha256"), name="one",
    )
    assert _refusal(only_one, require_expected=False).reason == "request_invalid"
    assert _refusal(only_one).reason == "request_invalid"


def test_promote_requires_the_reviewers_expected_digests(tmp_path: Path) -> None:
    refused = _refusal(_bundle(tmp_path, expected=False))
    assert refused.reason == "expected_digests_required" and "plan" in refused.message


def _drop(*keys: str) -> Callable[[dict[str, Any]], None]:
    def mutate(value: dict[str, Any]) -> None:
        for key in keys:
            value.pop(key)
    return mutate


def _set(*path: Any, to: Any) -> Callable[[dict[str, Any]], None]:
    def mutate(value: dict[str, Any]) -> None:
        node: Any = value
        for step in path[:-1]:
            node = node[step]
        node[path[-1]] = to
    return mutate


_NON_UNIT = base64.b64encode(struct.pack(f"!{DIMENSIONS}f", *([2.0] + [0.0] * (DIMENSIONS - 1))))

REQUEST_REFUSALS = {
    "unknown top-level key": (_set("extra", to=1), "request_invalid"),
    "missing top-level key": (_drop("snapshot_id"), "request_invalid"),
    "wrong format": (_set("format", to="other-v9"), "request_invalid"),
    "set id is not an nrs identity": (_set("set_id", to=SNAPSHOT), "request_invalid"),
    "set id missing": (_set("set_id", to=""), "request_invalid"),
    "proof digest is not lowercase sha256": (
        _set("independently_checked_source_digest", to="A" * 64), "request_invalid"),
    "expected digest is not sha256": (_set("expected_set_sha256", to="1" * 63), "request_invalid"),
    "empty items": (_set("items", to=[]), "request_invalid"),
    "empty designations": (_set("designations", to=[]), "request_invalid"),
    "unknown item key": (_set("items", 0, "extra", to=1), "request_invalid"),
    "unknown provenance key": (_set("items", 0, "provenance", "extra", to=1), "request_invalid"),
    "unknown target key": (_set("items", 0, "targets", 0, "extra", to=1), "request_invalid"),
    "unknown designation key": (_set("designations", 0, "extra", to=1), "request_invalid"),
    "missing provenance": (lambda value: value["items"][0].pop("provenance"), "request_invalid"),
    "boolean ordinal": (_set("items", 0, "targets", 0, "ordinal_first", to=True), "request_invalid"),
    "negative ordinal": (_set("items", 0, "targets", 0, "ordinal_last", to=-1), "request_invalid"),
    "vector bytes do not match the provenance digest": (
        _set("items", 0, "provenance", "query_vector_sha256", to="4" * 64),
        "query_vector_digest_mismatch"),
    "vector is not base64": (_set("items", 0, "query_vector_base64", to="!!!"), "request_invalid"),
    "vector has the wrong length": (
        _set("items", 0, "query_vector_base64", to=base64.b64encode(b"\0" * 8).decode()),
        "request_invalid"),
    "vector is not unit length": (
        _set("items", 0, "query_vector_base64", to=_NON_UNIT.decode()), "request_invalid"),
}


@pytest.mark.parametrize("case", sorted(REQUEST_REFUSALS))
def test_each_malformed_request_is_refused_with_its_reason(tmp_path: Path, case: str) -> None:
    mutate, reason = REQUEST_REFUSALS[case]
    assert _refusal(_bundle(tmp_path, mutate)).reason == reason


def test_a_changed_vector_is_caught_by_its_digest_even_when_it_is_a_valid_unit_vector(
    tmp_path: Path,
) -> None:
    other = vectors.pack([0.0, 1.0] + [0.0] * (DIMENSIONS - 2))
    mutate = _set("items", 0, "query_vector_base64", to=vectors.to_base64(other))
    assert _refusal(_bundle(tmp_path, mutate)).reason == "query_vector_digest_mismatch"


RAW_REFUSALS = {
    "duplicate key": lambda text: text.replace('"set_id"', '"set_id": "nrs_x", "set_id"', 1),
    "float": lambda text: text.replace('"ordinal_last": 1', '"ordinal_last": 1.5'),
    "NaN": lambda text: text.replace('"ordinal_last": 1', '"ordinal_last": NaN'),
    "not json": lambda text: "{" + text,
    "top-level array": lambda text: "[" + text + "]",
    "trailing garbage": lambda text: text + " x",
}


@pytest.mark.parametrize("case", sorted(RAW_REFUSALS))
def test_request_json_must_be_strict(tmp_path: Path, case: str) -> None:
    text = json.dumps(_request(), ensure_ascii=False)
    refused = _refusal(_bundle(tmp_path, raw=RAW_REFUSALS[case](text)))
    assert refused.reason == "request_invalid"


def test_invalid_utf8_is_refused(tmp_path: Path) -> None:
    directory = _bundle(tmp_path)
    good = json.dumps(_request(), ensure_ascii=False).encode("utf-8")
    assert b"reviewed-drop" in good  # otherwise valid: only the one bad byte can refuse it
    (directory / "request.json").write_bytes(good.replace(b"reviewed-drop", b"reviewed-\xff"))
    assert _refusal(directory).reason == "request_invalid"


def test_the_bundle_directory_holds_exactly_the_two_files(tmp_path: Path) -> None:
    extra = _bundle(tmp_path, name="extra")
    (extra / "notes.txt").write_text("x")
    assert _refusal(extra).reason == "bundle_layout"
    missing = _bundle(tmp_path, name="missing")
    (missing / "request.json").unlink()
    assert _refusal(missing).reason == "bundle_layout"
    assert _refusal(tmp_path / "absent").reason == "bundle_unreadable"
    plain = tmp_path / "plain"
    plain.write_text("x")
    assert _refusal(plain).reason == "bundle_unreadable"


def test_symlinks_are_refused_for_the_directory_and_for_each_file(tmp_path: Path) -> None:
    real = _bundle(tmp_path, name="real")
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    assert _refusal(link).reason == "bundle_unreadable"
    for name in ("map.json", "request.json"):
        directory = _bundle(tmp_path, name=f"files-{name[:3]}")
        target = tmp_path / f"target-{name}"
        target.write_bytes((directory / name).read_bytes())
        (directory / name).unlink()
        (directory / name).symlink_to(target)
        assert _refusal(directory).reason == "bundle_unreadable", name


def test_a_fifo_in_place_of_a_file_is_refused_not_waited_on(tmp_path: Path) -> None:
    directory = _bundle(tmp_path)
    (directory / "map.json").unlink()
    os.mkfifo(directory / "map.json")

    def hung(_signal: int, _frame: Any) -> None:
        raise AssertionError("load_bundle blocked on a FIFO")

    previous = signal.signal(signal.SIGALRM, hung)
    signal.alarm(5)
    try:
        assert _refusal(directory).reason == "bundle_unreadable"
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def test_oversize_files_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(promote_cli, "MAX_REQUEST_BYTES", 100)
    assert _refusal(_bundle(tmp_path, name="request")).reason == "bundle_oversize"
    monkeypatch.undo()
    monkeypatch.setattr(promote_cli, "MAX_ARTIFACT_BYTES", len(MAP_BYTES) - 1)
    assert _refusal(_bundle(tmp_path, name="map")).reason == "bundle_oversize"
    monkeypatch.setattr(promote_cli, "MAX_ARTIFACT_BYTES", len(MAP_BYTES))
    promote_cli.load_bundle(_bundle(tmp_path, name="exact"), require_expected=True)


# --- the custody manifest and source ----------------------------------------------------------


def test_the_manifest_names_only_this_sets_two_artifact_slots() -> None:
    set_id = str(NormRetrievalSetId.new())
    content = promote_cli.DeclaredContent(SET_SHA, len(SET_BYTES), "application/json")
    manifest = promote_cli._Manifest(set_id, {NORM_RETRIEVAL_SET: content})
    slot = promote_cli.CustodySlot(
        NORM_RETRIEVAL_SET, "norm_retrieval_set", set_id, "artifact", "retrieval-set.json",
    )
    assert manifest.declared(slot) == content
    assert manifest.declared(
        promote_cli.CustodySlot(NORM_CATALOGUE, "norm_retrieval_set", set_id, "artifact", "x")
    ) is None
    for other in (
        promote_cli.CustodySlot(NORM_RETRIEVAL_SET, "norm_retrieval_set",
                                str(NormRetrievalSetId.new()), "artifact", "retrieval-set.json"),
        promote_cli.CustodySlot(NORM_RETRIEVAL_SET, "norm_retrieval_set", set_id, "pdf", "x"),
        promote_cli.CustodySlot(NORM_RETRIEVAL_SET, "norm_document", set_id, "artifact", "x"),
    ):
        assert manifest.declared(other) is None


def test_the_source_serves_this_sets_bytes_and_never_a_foreign_admission() -> None:
    set_id = str(NormRetrievalSetId.new())
    source = promote_cli._Source(set_id, {NORM_RETRIEVAL_SET: SET_BYTES})
    ours = SimpleNamespace(target_id=set_id, role=NORM_RETRIEVAL_SET)
    assert source.open(ours) == SET_BYTES  # type: ignore[arg-type]
    for foreign in (
        SimpleNamespace(target_id=str(NormRetrievalSetId.new()), role=NORM_RETRIEVAL_SET),
        SimpleNamespace(target_id=set_id, role=NORM_CATALOGUE),
    ):
        with pytest.raises(FileNotFoundError):
            source.open(foreign)  # type: ignore[arg-type]


# --- exit status, with a fake runner ------------------------------------------------------------


class FakeRunner:
    """Records the order of calls; its candidate is always SET_BYTES and CATALOGUE_BYTES."""

    def __init__(
        self, *, states: dict[str, str] | None = None, replayed: bool = False,
        prepare_error: BaseException | None = None, admit_error: BaseException | None = None,
        settle_error: BaseException | None = None, finalize_error: BaseException | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.requests: list[PromotionRequest] = []
        self._states = states or {NORM_RETRIEVAL_SET: "confirmed", NORM_CATALOGUE: "confirmed"}
        self._replayed = replayed
        self._errors = {
            "prepare": prepare_error, "admit": admit_error,
            "settle": settle_error, "finalize": finalize_error,
        }

    def _step(self, name: str) -> None:
        self.calls.append(name)
        if self._errors[name] is not None:
            raise self._errors[name]  # type: ignore[misc]

    def prepare(self, request: PromotionRequest) -> PreparedPromotion:
        self.requests.append(request)
        self._step("prepare")
        different = tuple(
            name for name, expected, observed in (
                ("retrieval_set", request.expected_set_sha256, SET_SHA),
                ("catalogue", request.expected_catalogue_sha256, CATALOGUE_SHA),
            ) if expected != observed
        )
        return PreparedPromotion(
            request,
            RetrievalCandidate(
                CanonicalBlob(SET_BYTES, SET_SHA), CanonicalBlob(CATALOGUE_BYTES, CATALOGUE_SHA),
                PromptSelection((), "bounded prompt", 0, False), "2" * 64,
            ),
            DigestComparison(
                "rejected" if different else "matched", request.expected_set_sha256, SET_SHA,
                request.expected_catalogue_sha256, CATALOGUE_SHA, different,  # type: ignore[arg-type]
            ),
        )

    def admit(self, prepared: PreparedPromotion) -> tuple[str, str]:
        self._step("admit")
        return ("nad_set", "nad_catalogue")

    def settle(self, prepared: PreparedPromotion) -> dict[str, str]:
        self._step("settle")
        return self._states

    def finalize(self, prepared: PreparedPromotion) -> PromotionOutcome:
        self._step("finalize")
        return PromotionOutcome(prepared.request.set_id, "verified", self._replayed)


@pytest.fixture
def stores() -> list[bool]:
    return []


def _run(
    runner: FakeRunner, command: str, directory: Path, stores: list[bool],
) -> int:
    def factory(with_store: bool) -> FakeRunner:
        stores.append(with_store)
        return runner

    return promote_cli.main([command, str(directory)], runner_factory=factory)  # type: ignore[arg-type]


def test_plan_prints_the_candidate_digests_and_touches_neither_admission_nor_store(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    runner = FakeRunner()
    assert _run(runner, "plan", _bundle(tmp_path, expected=False), stores) == 0
    out = capsys.readouterr().out
    assert runner.calls == ["prepare"] and stores == [False]
    assert f"set_sha256: {SET_SHA}\n" in out and f"catalogue_sha256: {CATALOGUE_SHA}\n" in out
    assert "verdict: not_compared\n" in out
    assert f"set_size_bytes: {len(SET_BYTES)}\n" in out
    assert runner.requests[0].expected_set_sha256 == promote_cli._NO_EXPECTATION


def test_plan_reports_a_matching_verdict_and_refuses_a_differing_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    assert _run(FakeRunner(), "plan", _bundle(tmp_path), stores) == 0
    assert "verdict: matched\n" in capsys.readouterr().out
    wrong = _bundle(tmp_path, _set("expected_set_sha256", to="9" * 64), name="wrong")
    runner = FakeRunner()
    assert _run(runner, "plan", wrong, stores) == promote_cli.EXIT_REFUSED
    captured = capsys.readouterr()
    assert "verdict: rejected\n" in captured.out and f"set_sha256: {SET_SHA}\n" in captured.out
    assert "REFUSED [expected_digest_mismatch]" in captured.err and "retrieval_set" in captured.err
    assert runner.calls == ["prepare"]


def test_promote_runs_prepare_admit_settle_finalize_in_that_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    runner = FakeRunner()
    assert _run(runner, "promote", _bundle(tmp_path), stores) == 0
    assert runner.calls == ["prepare", "admit", "settle", "finalize"] and stores == [True]
    out = capsys.readouterr().out
    assert "promote: verified\n" in out and "replayed: false\n" in out
    assert f"set_sha256: {SET_SHA}\n" in out
    assert f"set_blob_id: {promote_cli.blob_id_for(SET_SHA, len(SET_BYTES))}\n" in out
    assert f"catalogue_blob_id: {promote_cli.blob_id_for(CATALOGUE_SHA, len(CATALOGUE_BYTES))}\n" in out


def test_an_exact_replay_is_reported_as_replayed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    assert _run(FakeRunner(replayed=True), "promote", _bundle(tmp_path), stores) == 0
    assert "replayed: true\n" in capsys.readouterr().out


def test_promote_without_expected_digests_refuses_before_any_runner_is_built(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    runner = FakeRunner()
    assert _run(runner, "promote", _bundle(tmp_path, expected=False), stores) == 2
    assert "REFUSED [expected_digests_required]" in capsys.readouterr().err
    assert runner.calls == [] and stores == []


def test_a_bundle_fault_refuses_plan_before_any_runner_is_built(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    runner = FakeRunner()
    assert _run(runner, "plan", _bundle(tmp_path, _set("extra", to=1)), stores) == 2
    assert "plan: REFUSED [request_invalid]" in capsys.readouterr().err
    assert runner.calls == [] and stores == []


def test_a_mismatched_expected_digest_refuses_with_no_admission(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    runner = FakeRunner()
    wrong = _bundle(tmp_path, _set("expected_catalogue_sha256", to="9" * 64))
    assert _run(runner, "promote", wrong, stores) == 2
    captured = capsys.readouterr()
    assert runner.calls == ["prepare"]
    assert "REFUSED [expected_digest_mismatch]" in captured.err and "catalogue" in captured.err
    assert f"catalogue_sha256: {CATALOGUE_SHA}\n" in captured.out


@pytest.mark.parametrize("error, reason", [
    (PromotionRefused("reviewed map bytes differ from digest"), "promotion_refused"),
    (StorageConfigurationError(field="S3_BUCKET", constraint="required"), "blob_store_unavailable"),
    (DatabaseConfigurationError("DATABASE_URL is not set"), "database_unavailable"),
])
def test_a_refusal_while_preparing_exits_2_with_nothing_else_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
    error: BaseException, reason: str,
) -> None:
    runner = FakeRunner(prepare_error=error)
    assert _run(runner, "promote", _bundle(tmp_path), stores) == 2
    assert f"promote: REFUSED [{reason}]" in capsys.readouterr().err
    assert runner.calls == ["prepare"]


def test_a_runner_that_cannot_be_built_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    def broken(_with_store: bool) -> FakeRunner:
        raise StorageConfigurationError(field="S3_ENDPOINT_URL", constraint="required")

    code = promote_cli.main(["promote", str(_bundle(tmp_path))], runner_factory=broken)  # type: ignore[arg-type]
    assert code == 2 and "REFUSED [blob_store_unavailable]" in capsys.readouterr().err


@pytest.mark.parametrize("error, reason", [
    (promote_cli.CliRefused("foreign_pending_admissions", "another admission is pending"),
     "foreign_pending_admissions"),
    (PromotionRefused("verified identity already belongs to another set"), "promotion_refused"),
    (CustodyRefused("slot_reuse", ErrorCode.IDEMPOTENCY_KEY_REUSE), "slot_reuse"),
])
def test_a_typed_refusal_while_admitting_exits_2_and_never_dispatches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
    error: BaseException, reason: str,
) -> None:
    runner = FakeRunner(admit_error=error)
    assert _run(runner, "promote", _bundle(tmp_path), stores) == 2
    assert f"promote: REFUSED [{reason}]" in capsys.readouterr().err
    assert runner.calls == ["prepare", "admit"]


def _uncertain_report(captured: Any, bundle: Path, reason: str) -> str:
    assert f"promote: UNCERTAIN [{reason}]" in captured.err
    assert "set_id: nrs_" in captured.err
    assert f"next: python -m auditmanager.norms.retrieval.promote_cli promote {bundle}\n" in captured.err
    return captured.err


def test_an_unclassified_failure_while_admitting_is_uncertain_not_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    runner = FakeRunner(admit_error=RuntimeError("connection reset during commit"))
    bundle = _bundle(tmp_path)
    assert _run(runner, "promote", bundle, stores) == 3
    _uncertain_report(capsys.readouterr(), bundle, "admission_uncertain")
    assert runner.calls == ["prepare", "admit"]


@pytest.mark.parametrize("state", ["pending", "poisoned", "none"])
def test_an_admission_that_is_not_confirmed_is_uncertain_and_never_finalized(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool], state: str,
) -> None:
    runner = FakeRunner(states={NORM_RETRIEVAL_SET: "confirmed", NORM_CATALOGUE: state})
    bundle = _bundle(tmp_path)
    assert _run(runner, "promote", bundle, stores) == 3
    report = _uncertain_report(capsys.readouterr(), bundle, "dispatch_unsettled")
    assert f"norm_catalogue={state}" in report and "norm_retrieval_set=" not in report
    assert runner.calls == ["prepare", "admit", "settle"]


def test_an_interrupted_dispatch_is_uncertain_with_the_rerun_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    for error in (KeyboardInterrupt(), OSError("staged upload lost")):
        runner = FakeRunner(settle_error=error)
        bundle = _bundle(tmp_path, name=f"b-{type(error).__name__}")
        assert _run(runner, "promote", bundle, stores) == 3
        _uncertain_report(capsys.readouterr(), bundle, "interrupted")
        assert runner.calls == ["prepare", "admit", "settle"]


def test_a_finalize_refusal_after_admission_is_uncertain(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    runner = FakeRunner(finalize_error=PromotionRefused("canonical Blob is unavailable"))
    bundle = _bundle(tmp_path)
    assert _run(runner, "promote", bundle, stores) == 3
    report = _uncertain_report(capsys.readouterr(), bundle, "finalize_refused")
    assert "canonical Blob is unavailable" in report
    assert runner.calls == ["prepare", "admit", "settle", "finalize"]


def test_the_rerun_command_quotes_a_bundle_path_with_spaces(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stores: list[bool],
) -> None:
    bundle = _bundle(tmp_path, name="a bundle")
    assert _run(FakeRunner(admit_error=RuntimeError("x")), "promote", bundle, stores) == 3
    assert f"promote '{bundle}'\n" in capsys.readouterr().err


def test_the_default_runner_refuses_cleanly_without_its_environment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "DATABASE_URL", "S3_ENDPOINT_URL", "S3_REGION", "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
    ):
        monkeypatch.delenv(name, raising=False)
    reset_session_factory()
    dispose_engine()
    assert promote_cli.main(["plan", str(_bundle(tmp_path, expected=False, name="p"))]) == 2
    assert "plan: REFUSED [database_unavailable]" in capsys.readouterr().err
    assert promote_cli.main(["promote", str(_bundle(tmp_path, name="q"))]) == 2
    assert "promote: REFUSED [blob_store_unavailable]" in capsys.readouterr().err


def test_an_unreached_unclassified_state_in_plan_is_not_swallowed(
    tmp_path: Path, stores: list[bool],
) -> None:
    runner = FakeRunner(prepare_error=RuntimeError("bug"))
    with pytest.raises(RuntimeError, match="bug"):
        _run(runner, "plan", _bundle(tmp_path, expected=False), stores)


@pytest.fixture(autouse=True)
def _no_ambient_alarm() -> Iterator[None]:
    yield
    signal.alarm(0)
