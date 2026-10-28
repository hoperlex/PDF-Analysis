"""`CMP-SEAL-C1` (ADR-0025 decision 13): while the «Сравнение версий» module is on, the three operations of
`0035` -- ``approveSheetPairing``, ``withdrawSheetPairing`` and ``generateComparisonSummary`` -- answer ``503
dependency_unavailable`` naming the module, before anything is read or written; with the module off they are
untouched. No container: the session factory handed to the adapter fails loudly if it is ever asked for a session,
so a guard that did not stop the call would show as that failure.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.bootstrap.adapters import ComparisonAdapter
from auditmanager.shared.errors import DomainError, ErrorCode

PRJ = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"
DOC = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
VER = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
VER2 = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAW"
LINK = "sln_01ARZ3NDEKTSV4RRFFQ69G5FAV"
USER = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "a" * 64


class _SessionAsked(Exception):
    """The adapter reached for a session: the guard did not stop the call."""


def _no_session() -> Any:
    raise _SessionAsked


def _adapter(modules: str | None) -> ComparisonAdapter:
    kwargs = {} if modules is None else {"comparison_modules": modules}
    return ComparisonAdapter(_no_session, blob_store=None, section_codes=frozenset({"AR"}), **kwargs)


def _calls(adapter: ComparisonAdapter) -> dict[str, Any]:
    common = {"project_uid": PRJ, "document_uid": DOC, "mode": "version", "source_run_id": None,
              "target_run_id": None, "idempotency_key": "k", "author_label": "A", "author_user_uid": USER}
    return {
        "approveSheetPairing": lambda: adapter.approve_sheet_pairing(
            source_version_uid=VER, target_version_uid=VER2, source_page_number=1, target_page_number=1,
            suggestion_sha256=SHA, **common),
        "withdrawSheetPairing": lambda: adapter.withdraw_sheet_pairing(
            source_version_uid=VER, sheet_link_id=LINK, **common),
        "generateComparisonSummary": lambda: adapter.generate_comparison_summary(
            source_version_uid=VER, target_version_uid=VER2, **common),
    }


NAMES = ("approveSheetPairing", "withdrawSheetPairing", "generateComparisonSummary")


@pytest.mark.parametrize("modules", ["versions", "versions,stages"])
@pytest.mark.parametrize("name", NAMES)
def test_the_operation_is_withdrawn_while_the_versions_module_is_on(name: str, modules: str) -> None:
    with pytest.raises(DomainError) as caught:
        _calls(_adapter(modules))[name]()
    assert caught.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(caught.value.detail_fields) == {"dependency": "comparison_versions_module"}


@pytest.mark.parametrize("modules", [None, "none"])
@pytest.mark.parametrize("name", NAMES)
def test_the_operation_is_untouched_while_the_module_is_off(name: str, modules: str | None) -> None:
    """With the module off the call goes on to its own work, which here reaches for the session."""
    with pytest.raises(_SessionAsked):
        _calls(_adapter(modules))[name]()


def test_that_check_fails_when_the_guard_is_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: without the guard the call reaches the session while the module is on."""
    monkeypatch.setattr(ComparisonAdapter, "_refuse_while_the_versions_module_is_on", lambda self: None)
    with pytest.raises(_SessionAsked):
        _calls(_adapter("versions"))["approveSheetPairing"]()


def test_the_stages_module_alone_does_not_exist_and_is_refused_where_the_set_is_parsed() -> None:
    from auditmanager.comparison.public import parse_modules

    with pytest.raises(ValueError):
        parse_modules("stages")
