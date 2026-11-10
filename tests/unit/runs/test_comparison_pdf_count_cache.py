"""The native-text count of a comparison PDF is parsed by the estimate, once per file, and never by the start (`REVIEW-FIX-CMP-SPEC-1102`).

Code review 2026-11-02, S6-04. A comparison PDF stores no ``text_character_count``, so pricing a run on it parses the whole file; the start
recomputes the estimate inside its write transaction, where a parse of minutes holds a database connection. The count is a function of the
file's bytes and page count, so the estimate keeps it per process under ``(sha256, page_count)`` and the start only reads it: a start whose
file was never estimated in this process is refused as ``cost_text_count_unavailable`` (the estimate is then asked for again), never parsed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import ProviderConfig, ProviderMode
from auditmanager.ingest.public import CommandStarted
from auditmanager.runs import preflight
from auditmanager.runs.commands import reaudit_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import CommandId
from auditmanager.storage.public import derive_blob_id

VERSION = "ver_01M2545JSD15ETSNNV904X991J"
PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
SOURCE_RUN = "run_01M2545JSD15ETSNNV904X991K"
PROFILE = "ap_01M2545JSD15ETSNNV904X991A"
BUNDLE = "pb_01M2545JSD15ETSNNV904X991P"
BLOB = "blob_sha256_" + "b" * 64
MODEL = "claude-opus-5"


@pytest.fixture(autouse=True)
def empty_cache() -> Any:
    preflight._NATIVE_COUNTS.clear()  # noqa: SLF001
    yield
    preflight._NATIVE_COUNTS.clear()  # noqa: SLF001


def comparison_version(sha: str = "a" * 64, pages: int = 6) -> Any:
    return SimpleNamespace(
        version_uid=VERSION, sha256=sha, text_character_count=None, recognised_character_count=0, page_count=pages,
        upload_kind="comparison_pdf",
        classification=SimpleNamespace(version_uid=VERSION, confirmed_by_user_uid="usr_x", section_code="AR", project_stage="P", revision=1),
        manifest=(SimpleNamespace(role="comparison.source_pdf", blob_id=str(derive_blob_id(sha256=sha, size=10)), sha256=sha,
                                  size_bytes=10, media_type="application/pdf"),),
    )


class Counter:
    """``count_native_text_characters``: a parse that is counted."""

    def __init__(self, value: int = 12_345) -> None:
        self.calls, self.value = 0, value

    def __call__(self, store: Any, blob_id: Any, *, expected_sha256: str, expected_page_count: int) -> int:
        self.calls += 1
        return self.value


def policy(monkeypatch: pytest.MonkeyPatch, counter: Counter) -> preflight.RunCostPreflight:
    monkeypatch.setattr(preflight, "count_native_text_characters", counter)
    return preflight.RunCostPreflight(
        section_profiles=None, text_profiles=None, provider_config=ProviderConfig(ProviderMode.RECORDED, MODEL, 1.0, None, False),
        provider_mode="recorded", blob_store=object())


def test_the_estimate_parses_once_per_file_and_the_start_reads_the_count(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = Counter()
    service, version = policy(monkeypatch, counter), comparison_version()
    first = service._source(None, VERSION, version)  # noqa: SLF001
    assert counter.calls == 1 and first[1] == 12_345
    again = service._source(None, VERSION, version)  # noqa: SLF001
    start = service._source(None, VERSION, version, parse_native_text=False)  # noqa: SLF001
    assert counter.calls == 1, "the second estimate and the start parsed the file again"
    assert again[1] == start[1] == 12_345 and again[2] == start[2], "the facts the digest binds are the same"


def test_a_start_whose_file_was_never_estimated_is_refused_and_does_not_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = Counter()
    with pytest.raises(DomainError) as refusal:
        policy(monkeypatch, counter)._source(None, VERSION, comparison_version(), parse_native_text=False)  # noqa: SLF001
    assert refusal.value.code is ErrorCode.ANALYSIS_INPUT_INVALID and dict(refusal.value.detail_fields)["reason"] == "cost_text_count_unavailable"
    assert counter.calls == 0


def test_the_count_is_kept_per_file_and_page_count(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = Counter()
    service = policy(monkeypatch, counter)
    service._source(None, VERSION, comparison_version("a" * 64, 6))  # noqa: SLF001
    for other in (comparison_version("c" * 64, 6), comparison_version("a" * 64, 7)):
        with pytest.raises(DomainError):
            service._source(None, VERSION, other, parse_native_text=False)  # noqa: SLF001
    assert counter.calls == 1


def test_the_cache_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preflight, "_NATIVE_COUNTS_MAX", 3)
    counter = Counter()
    service = policy(monkeypatch, counter)
    for index in range(5):
        service._source(None, VERSION, comparison_version(f"{index:x}" * 64))  # noqa: SLF001
    assert len(preflight._NATIVE_COUNTS) == 3  # noqa: SLF001
    with pytest.raises(DomainError):  # the oldest two were dropped
        service._source(None, VERSION, comparison_version("0" * 64), parse_native_text=False)  # noqa: SLF001


def test_a_portal_version_never_touches_the_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = Counter()
    service = policy(monkeypatch, counter)
    portal = comparison_version()
    portal.upload_kind, portal.text_character_count = "portal_bundle", 777
    assert service._source(None, VERSION, portal, parse_native_text=False)[1] == 777  # noqa: SLF001
    assert counter.calls == 0 and not preflight._NATIVE_COUNTS  # noqa: SLF001


# -- the starts pass it -----------------------------------------------------------------------------------------------


class Stop(Exception):
    pass


class Preflight:
    """Records the keywords of the estimate the command asks for, and stops the command there."""

    def __init__(self) -> None:
        self.asked: list[dict[str, Any]] = []

    def estimate_run(self, session: Any, **kwargs: Any) -> Any:
        self.asked.append(kwargs)
        raise Stop

    def estimate_reaudit(self, session: Any, **kwargs: Any) -> Any:
        self.asked.append(kwargs)
        raise Stop


class Ledger:
    def find(self, session: Any, **_: Any) -> None:
        return None

    def begin(self, session: Any, **_: Any) -> Any:
        return CommandStarted(CommandId("cmd_01M2545JSD15ETSNNV904X991C"))


class Documents:
    def get_version(self, session: Any, version_uid: Any) -> Any:
        return SimpleNamespace(project_uid=PROJECT, text_character_count=None, upload_kind="comparison_pdf",
                               manifest=(SimpleNamespace(role="comparison.source_pdf", blob_id=BLOB),))


class Runs:
    def get(self, session: Any, run_id: str) -> Any:
        return SimpleNamespace(run_id=run_id, project_uid=PROJECT, version_uid=VERSION, state="failed", frozen_input_digest="c" * 64,
                               norms_snapshot_id=None,
                               # The source's pinned pair.
                               analysis_profile_id="ap_01M5M28ZCDD8VPSP1BTAEW92YF", prompt_bundle_id="pb_01M5M28ZCDVCR37BX1884JGSPN",)

    def chosen_executor_connection(self, session: Any, run_id: str) -> None:
        return None


class Session:
    def execute(self, statement: Any, parameters: Any = None) -> Any:
        return SimpleNamespace(scalar_one_or_none=lambda: None)


def test_the_start_asks_for_an_estimate_that_does_not_parse() -> None:
    preflight_double = Preflight()
    with pytest.raises(Stop):
        start_audit_run(
            Session(), version_uid=VERSION, analysis_profile_id=PROFILE, prompt_bundle_id=BUNDLE, provider_mode="recorded",
            idempotency_key="count-1", commands=Ledger(), runs=Runs(), documents=Documents(), norms_snapshot=lambda s: None,
            cost_preflight=preflight_double)
    assert [call["parse_native_text"] for call in preflight_double.asked] == [False]


def test_the_re_audit_asks_for_an_estimate_that_does_not_parse() -> None:
    preflight_double = Preflight()
    with pytest.raises(Stop):
        reaudit_run(
            Session(), source_run_id=SOURCE_RUN, roles=frozenset({"expert"}), idempotency_key="count-2", analysis_profile_id=PROFILE,
            prompt_bundle_id=BUNDLE, provider_mode="recorded", runs=Runs(), commands=Ledger(), documents=Documents(),
            norms_snapshot=lambda s: None, cost_preflight=preflight_double)
    assert [call["parse_native_text"] for call in preflight_double.asked] == [False]
