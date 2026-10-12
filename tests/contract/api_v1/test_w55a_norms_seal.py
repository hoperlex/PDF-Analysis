"""`W55A-SEAL-01`: what the norms seal declares, checked without a database.

The database half -- the migration applied, the generated columns filled, the guards firing --
is ``tests/integration/db/test_norms_search_migration.py``, which runs in the owner's window
(R-102, R-111). This module holds the parts that are pure functions of the tree:

* the designation fold of ``0020_norms_search`` (`W55-PLAN.md` section A3.4): explicit
  ``translate`` tables, never ``lower()``; ``СП 54`` never finds ``СП_542_...``;
* :class:`~auditmanager.api.schemas.content.ByteRange` answers exactly what
  ``streamDocumentVersionContent``'s own range rule answered, so `W55A-CONTENT-01` could move
  that operation onto it without changing one ``206`` or ``422`` (the retired rule is kept
  below, verbatim, as the oracle);
* ``RunStatus.norms_snapshot_id`` is rendered only when a run pinned one (records 14, 15
  and 31 carry none);
* the sealed stubs refuse explicitly, each naming its dependency.
"""

from __future__ import annotations

import importlib.util
import re
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest

from auditmanager.api.schemas.content import ByteRange, StreamedContent
from auditmanager.api.schemas.runs import RunStatusView, run_status_body
from auditmanager.api.security import OPERATION_ROLES
from auditmanager.bootstrap.adapters import NormContentAdapter, NormsSearchAdapter
from auditmanager.shared.errors import DomainError, ErrorCode

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MIGRATION = REPOSITORY_ROOT / "db/migrations/versions/20261012_0020_norms_search.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("w55a_seal_0020", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tokens(module: ModuleType, value: str) -> list[str]:
    """``norm_designation_tokens`` restated in Python from the migration's own tables.

    ``split_part(value, '__', 1)``, then ``translate`` with :data:`FOLD_FROM` /
    :data:`FOLD_TO`, then ``regexp_split_to_array(..., '[ ._-]+')`` with empty tokens
    removed. The database test compares the SQL function against this on the same inputs.
    """
    head = value.split("__", 1)[0]
    folded = head.translate(str.maketrans(module.FOLD_FROM, module.FOLD_TO))
    return [token for token in re.split(r"[ ._-]+", folded) if token]


# --- the designation fold ---------------------------------------------------------------


def test_the_fold_is_a_one_to_one_character_map_with_no_case_function() -> None:
    module = _migration()
    assert len(module.FOLD_FROM) == len(module.FOLD_TO)
    assert len(set(module.FOLD_FROM)) == len(module.FOLD_FROM)
    sql = module.DESIGNATION_TOKENS_SQL
    assert "IMMUTABLE" in sql
    for case_function in ("lower(", "upper(", "initcap(", "ILIKE"):
        assert case_function not in sql, f"the fold must not depend on lc_ctype: {case_function}"
    assert f"'{module.FOLD_FROM}'" in sql and f"'{module.FOLD_TO}'" in sql


def test_every_capital_and_every_homoglyph_folds_to_a_lower_case_letter() -> None:
    module = _migration()
    table = dict(zip(module.FOLD_FROM, module.FOLD_TO))
    for capital in "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ":
        assert capital in table, capital
        assert table[capital] == ("е" if capital == "Ё" else capital.lower())
    for latin in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        assert latin in table, latin
        assert table[latin] == table.get(latin.lower(), latin.lower()), latin
    # The homoglyphs land on the Cyrillic letter, in either case.
    for latin, cyrillic in zip("ABCEHKMOPTXY", "авсенкмортху"):
        assert table[latin] == cyrillic and table[latin.lower()] == cyrillic, latin


@pytest.mark.parametrize(
    ("slug", "expected"),
    [
        ("ГОСТ_10140-2003__Межгосударственный_стандарт__Плиты", ["гост", "10140", "2003"]),
        ("СП_54_13330_2022__Свод_правил__Здания_жилые", ["сп", "54", "13330", "2022"]),
        ("СП_542_1325800_2024__Свод_правил__Защитные", ["сп", "542", "1325800", "2024"]),
        ("ГОСТ_11533-75___Государственный_стандарт", ["гост", "11533", "75"]),
        ("ГОСТ_13463-77", ["гост", "13463", "77"]),
    ],
)
def test_a_slug_yields_its_designation_tokens(slug: str, expected: list[str]) -> None:
    assert _tokens(_migration(), slug) == expected


def _matches(module: ModuleType, query: str, slug: str) -> bool:
    wanted = _tokens(module, query)
    key = _tokens(module, slug)
    return bool(wanted) and key[: len(wanted)] == wanted


def test_a_designation_matches_whole_leading_tokens_only() -> None:
    module = _migration()
    sp54 = "СП_54_13330_2022__Свод_правил__Здания_жилые"
    sp542 = "СП_542_1325800_2024__Свод_правил__Защитные"
    assert _matches(module, "СП 54", sp54)
    assert not _matches(module, "СП 54", sp542)
    assert _matches(module, "сп 542", sp542)
    assert _matches(module, "ГОСТ 10140", "ГОСТ_10140-2003__Межгосударственный_стандарт")
    assert not _matches(module, "ГОСТ 1014", "ГОСТ_10140-2003__Межгосударственный_стандарт")


def test_latin_homoglyphs_and_case_find_the_same_designation() -> None:
    module = _migration()
    sp54 = "СП_54_13330_2022__Свод_правил"
    for typed in ("CП 54", "сп 54", "Cп.54", "СП-54"):
        assert _matches(module, typed, sp54), typed
    # Latin `P` is the homoglyph of `Р`, not of `П`: `CP 54` is another designation.
    assert not _matches(module, "CP 54", sp54)
    assert _matches(module, "rOCT 10140", "ГОСТ_10140-2003") is False  # `r` is no homoglyph
    assert _matches(module, "ГOCT 10140", "ГОСТ_10140-2003")


# --- the byte range ---------------------------------------------------------------------


_LEGACY_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


def _resolve_range(header: str, size: int) -> tuple[int, int]:
    """``documents.py``'s range rule as it stood at `W55A-SEAL-01`, copied verbatim.

    `W55A-CONTENT-01` moved the operation onto :class:`ByteRange` and retired the router's
    own copy; the oracle stays here so this comparison can still fail.
    """
    match = _LEGACY_RANGE.match(header.strip())
    if match is None:
        raise _legacy_refusal("format")
    first, last = match.group(1), match.group(2)
    if first == "" and last == "":
        raise _legacy_refusal("format")
    if first == "":
        length = int(last)
        if length == 0:
            raise _legacy_refusal("unsatisfiable")
        start = max(0, size - length)
        end = size - 1
    else:
        start = int(first)
        end = size - 1 if last == "" else min(int(last), size - 1)
    if size == 0 or start >= size or start > end:
        raise _legacy_refusal("unsatisfiable")
    return start, end


def _legacy_refusal(constraint: str) -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED,
        message="The Range header is not a single satisfiable byte range.",
        field="Range",
        constraint=constraint,
    )


_HEADERS = [
    "bytes=0-0", "bytes=0-99", "bytes=5-", "bytes=-1", "bytes=-50", "bytes=-0",
    "bytes=99-99", "bytes=100-", "bytes=10-5", "bytes=0-1000", "  bytes=3-7  ",
    "bytes=", "bytes=-", "items=0-1", "bytes=0-1,4-5", "bytes=a-b",
]


@pytest.mark.parametrize("size", [0, 1, 100])
@pytest.mark.parametrize("header", _HEADERS)
def test_the_parsed_range_answers_what_the_document_route_answers(header: str, size: int) -> None:
    def outcome(call):
        try:
            return ("ok", call())
        except DomainError as error:
            return ("refused", error.code, dict(error.detail_fields))

    legacy = outcome(lambda: _resolve_range(header, size))
    sealed = outcome(lambda: ByteRange.parse(header).resolve(size))
    assert sealed == legacy


def test_a_streamed_window_states_its_own_length() -> None:
    whole = StreamedContent("application/pdf", 10, None, iter(()))
    window = StreamedContent("application/pdf", 10, (2, 4), iter(()))
    assert whole.content_length == 10 and window.content_length == 3


# --- RunStatus.norms_snapshot_id ----------------------------------------------------------


def _run(**extra: object) -> RunStatusView:
    return RunStatusView(
        run_id="run_01M2545JSD15ETSNNV904X991K",
        project_uid="prj_01M2545JSD15ETSNNV904X991F",
        version_uid="ver_01M2545JSD15ETSNNV904X991J",
        state="queued",
        provider_mode="recorded",
        created_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
        prompt_bundle_id="pb_01M2545JSD15ETSNNV904X991P",
        **extra,  # type: ignore[arg-type]
    )


def test_a_run_with_no_pinned_snapshot_renders_no_snapshot_key() -> None:
    assert "norms_snapshot_id" not in run_status_body(_run())


def test_a_pinned_run_renders_its_snapshot_after_the_bundle() -> None:
    body = run_status_body(_run(norms_snapshot_id="ns_01M2545JSD15ETSNNV904X991N"))
    assert body["norms_snapshot_id"] == "ns_01M2545JSD15ETSNNV904X991N"
    keys = list(body)
    assert keys.index("norms_snapshot_id") == keys.index("prompt_bundle_id") + 1


# --- the sealed stubs and their roles ------------------------------------------------------


def _refusal(call) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def test_every_sealed_norms_method_refuses_with_its_dependency() -> None:
    search = NormsSearchAdapter(None)  # type: ignore[arg-type]
    calls = [
        lambda: search.search(q="СП 54", norms_snapshot_id=None, cursor=None, limit=50),
        lambda: search.get_document(norm_document_id="ndoc_01M2545JSD15ETSNNV904X991V"),
        lambda: search.list_paragraphs(
            norm_document_id="ndoc_01M2545JSD15ETSNNV904X991V", cursor=None, limit=50
        ),
        lambda: search.list_snapshots(cursor=None, limit=50),
        lambda: search.list_snapshot_events(cursor=None, limit=50),
        lambda: search.set_current_snapshot(
            norms_snapshot_id="ns_01M2545JSD15ETSNNV904X991N", expected_current=None,
            user_uid="usr_01M2545JSD15ETSNNV904X991S",
        ),
    ]
    for call in calls:
        error = _refusal(call)
        assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert dict(error.detail_fields) == {"dependency": "norms_search"}
    content = NormContentAdapter(None, blob_store=None)  # type: ignore[arg-type]
    error = _refusal(lambda: content.stream_content(
        norm_document_id="ndoc_01M2545JSD15ETSNNV904X991V", byte_range=None
    ))
    assert (error.code, dict(error.detail_fields)) == (
        ErrorCode.DEPENDENCY_UNAVAILABLE, {"dependency": "norm_content"}
    )
    # `DocumentAdapter.stream_content` was sealed here too; `W55A-CONTENT-01` gave it its
    # body, and `tests/integration/api/test_document_content_streaming.py` drives it.


def test_the_norms_reads_need_a_role_and_the_designation_needs_admin() -> None:
    """`R-80` any-role reads; `R-113` the history and the designation for `admin`."""
    any_role = frozenset({"expert", "admin"})
    for operation in (
        "searchNorms", "getNormDocument", "listNormParagraphs",
        "streamNormDocumentContent", "listNormSnapshots",
    ):
        assert OPERATION_ROLES[operation] == any_role, operation
    for operation in ("listNormSnapshotEvents", "setCurrentNormSnapshot"):
        assert OPERATION_ROLES[operation] == frozenset({"admin"}), operation
