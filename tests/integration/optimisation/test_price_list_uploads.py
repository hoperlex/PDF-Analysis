"""`W60-PRICE-LIST-01` phase A: uploading and reading price lists on real PostgreSQL and MinIO.

Through ``auditmanager.optimisation.public`` only: who may upload and read; the revision bound
to its file's Blob; exact repeats answered and same-key conflicts refused; refused files that
leave nothing behind; a storage failure that leaves only its breadcrumb; earlier revisions
staying readable; paging; foreign scopes unseen; uploaders that cannot be purged.
"""

from __future__ import annotations

import threading
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository
from auditmanager.optimisation.public import (
    COMMAND_TYPE_UPLOAD_PRICE_LIST,
    PriceListUploads,
    get_price_list_revision,
    list_price_list_positions,
    list_price_list_revisions,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage import S3BlobStore, StorageUnavailableError
from tests.unit.optimisation.xlsx_builder import Num, simple_xlsx  # type: ignore[import-not-found]

accounts = AccountRepository()

PRICE_LIST = (
    "Прайс-лист ООО «Ромашка»\n"
    "Код;Наименование;Ед. изм.;Цена, руб.;Поставщик;Раздел\n"
    "К-1;Кабель ВВГнг-LS 3х2,5;м;125,50;Кабельный завод;ЭОМ\n"
    "К-2;Труба ПП 20;м;по запросу;;ВК\n"
    "К-3;Щит ЩР-1;шт;12 345,67;;\n"
).encode("cp1251")
OTHER_PRICE_LIST = "Наименование;Ед. изм.;Цена\nЛампа;шт;150\n".encode("utf-8")


def _uploads(store: S3BlobStore, factory: sessionmaker[Session]) -> PriceListUploads:
    return PriceListUploads(store, session_factory=factory)


def _upload(service: PriceListUploads, cast: Any, **overrides: Any):
    arguments: dict[str, Any] = {
        "project_uid": cast.project,
        "content": PRICE_LIST,
        "source_filename": "Прайс 2026.csv",
        "idempotency_key": "upload-1",
        "actor_uid": cast.expert,
    }
    arguments.update(overrides)
    return service.upload(**arguments)


def _refused(code: ErrorCode, call: Any, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    assert caught.value.code is code, (caught.value.code, dict(caught.value.detail_fields))
    return caught.value


def _count(session: Session, statement: str, **parameters: Any) -> int:
    session.rollback()
    return int(session.execute(text(statement), parameters).scalar_one())


def _roles(session: Session, uid: str) -> frozenset[str]:
    return accounts.roles_of(session, uid)


# -- the happy path ---------------------------------------------------------------------------


def test_an_expert_upload_is_one_revision_bound_to_its_available_blob(
    store: S3BlobStore, factory, session: Session, cast, bucket_keys
) -> None:
    outcome = _upload(_uploads(store, factory), cast)
    revision = outcome.revision
    assert outcome.replayed is False
    assert revision.price_list_id.startswith("prl_")
    assert (revision.project_uid, revision.revision_number, revision.is_current) == (cast.project, 1, True)
    assert revision.uploaded_by_user_uid == cast.expert
    assert (revision.source_format, revision.media_type) == ("csv", "text/csv")
    assert revision.source_filename == "Прайс 2026.csv"
    assert (revision.data_row_count, revision.accepted_row_count, revision.skipped_row_count) == (3, 2, 1)
    assert revision.parse_report["encoding"] == "cp1251"
    assert revision.parse_report["skipped"] == [{"row": 4, "reason": "price_not_a_number"}]
    assert revision.size_bytes == len(PRICE_LIST)

    # The binding: the Blob row is available with the file's digest, and the bytes are stored
    # exactly once, canonically, with no temporary object left behind.
    assert store.read(revision.blob_id) == PRICE_LIST
    session.rollback()
    state, sha256, size = session.execute(
        text("SELECT state, sha256, size_bytes FROM blob WHERE blob_id = :b"), {"b": revision.blob_id}
    ).one()
    assert (state, sha256, size) == ("available", revision.sha256, len(PRICE_LIST))
    keys = bucket_keys()
    assert len(keys) == 1 and keys[0].startswith("blobs/")
    assert session.execute(
        text("SELECT state, outcome->>'price_list_id' FROM command_record WHERE command_type = :t"),
        {"t": COMMAND_TYPE_UPLOAD_PRICE_LIST},
    ).one() == ("succeeded", revision.price_list_id)

    page = list_price_list_positions(
        session, price_list_id=revision.price_list_id, actor_roles=_roles(session, cast.expert)
    )
    assert [(p.row_number, p.code, p.name, p.unit, p.unit_price, p.currency, p.vendor, p.section_code)
            for p in page.positions] == [
        (3, "К-1", "Кабель ВВГнг-LS 3х2,5", "м", Decimal("125.5"), "RUB", "Кабельный завод", "EOM"),
        (5, "К-3", "Щит ЩР-1", "шт", Decimal("12345.67"), "RUB", None, None),
    ]
    assert all(p.price_list_position_id.startswith("prp_") for p in page.positions)
    assert (page.total, page.next_offset) == (2, None)


def test_an_xlsx_upload_records_its_format_and_default_currency(
    store: S3BlobStore, factory, session: Session, cast
) -> None:
    data = simple_xlsx([["Наименование", "Ед. изм.", "Цена"], ["Лампа", "шт", Num("150.25")]])
    revision = _upload(
        _uploads(store, factory), cast, content=data, source_filename="прайс.xlsx",
        default_currency="RUB",
    ).revision
    assert revision.source_format == "xlsx"
    assert revision.media_type.endswith("spreadsheetml.sheet")
    assert revision.default_currency == "RUB"
    assert revision.parse_report["currency_sources"] == {"default": 1}
    position = list_price_list_positions(
        session, price_list_id=revision.price_list_id, actor_roles=_roles(session, cast.expert)
    ).positions[0]
    assert (position.unit_price, position.currency) == (Decimal("150.25"), "RUB")


# -- idempotency ------------------------------------------------------------------------------


def test_the_same_key_and_file_answer_the_stored_revision_and_create_nothing(
    store: S3BlobStore, factory, session: Session, cast
) -> None:
    service = _uploads(store, factory)
    first = _upload(service, cast)
    again = _upload(service, cast)
    assert again.replayed is True
    assert again.revision.price_list_id == first.revision.price_list_id
    assert _count(session, "SELECT count(*) FROM price_list_revision") == 1
    assert _count(session, "SELECT count(*) FROM price_list_position") == 2


def test_the_same_key_with_another_file_or_project_is_refused_and_creates_nothing(
    store: S3BlobStore, factory, session: Session, cast
) -> None:
    service = _uploads(store, factory)
    _upload(service, cast)
    for overrides in (
        {"content": OTHER_PRICE_LIST},
        {"source_filename": "другое имя.csv"},
        {"default_currency": "USD"},
        {"project_uid": cast.other_project},
        {"actor_uid": cast.other_expert},
    ):
        refused = _refused(ErrorCode.IDEMPOTENCY_KEY_REUSE, _upload, service, cast, **overrides)
        assert dict(refused.detail_fields) == {"command_type": COMMAND_TYPE_UPLOAD_PRICE_LIST}
    assert _count(session, "SELECT count(*) FROM price_list_revision") == 1


def test_a_new_key_is_a_new_revision_and_the_earlier_one_stays_readable(
    store: S3BlobStore, factory, session: Session, cast
) -> None:
    service = _uploads(store, factory)
    first = _upload(service, cast).revision
    second = _upload(service, cast, idempotency_key="upload-2", content=OTHER_PRICE_LIST,
                     default_currency="RUB").revision
    same_bytes = _upload(service, cast, idempotency_key="upload-3").revision
    assert [second.revision_number, same_bytes.revision_number] == [2, 3]
    assert same_bytes.blob_id == first.blob_id  # the Blob is shared, the revision is not
    roles = _roles(session, cast.admin)
    listed = list_price_list_revisions(session, project_uid=cast.project, actor_roles=roles)
    assert [(r.revision_number, r.is_current) for r in listed] == [(3, True), (2, False), (1, False)]
    earlier = get_price_list_revision(session, price_list_id=first.price_list_id, actor_roles=roles)
    assert earlier.is_current is False and earlier.parse_report == first.parse_report
    assert len(list_price_list_positions(
        session, price_list_id=first.price_list_id, actor_roles=roles
    ).positions) == 2


def test_concurrent_uploads_to_one_project_get_distinct_revision_numbers(
    store: S3BlobStore, factory, session: Session, cast
) -> None:
    errors: list[BaseException] = []

    def upload(n: int) -> None:
        content = PRICE_LIST + f"П-{n};Позиция {n};шт;{n + 1}\n".encode("cp1251")
        try:
            _upload(_uploads(store, factory), cast, idempotency_key=f"parallel-{n}", content=content)
        except BaseException as exc:  # noqa: BLE001 - reported below
            errors.append(exc)

    threads = [threading.Thread(target=upload, args=(n,)) for n in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    session.rollback()
    numbers = session.execute(
        text("SELECT revision_number FROM price_list_revision ORDER BY revision_number")
    ).scalars().all()
    assert numbers == [1, 2, 3]


# -- refusals ---------------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["admin", "nobody"])
def test_only_an_expert_uploads(store: S3BlobStore, factory, session: Session, cast, who: str, bucket_keys) -> None:
    refused = _refused(
        ErrorCode.PERMISSION_DENIED, _upload, _uploads(store, factory), cast, actor_uid=getattr(cast, who)
    )
    assert dict(refused.detail_fields) == {"aggregate_type": "PriceList", "required_capability": "role:expert"}
    assert _count(session, "SELECT count(*) FROM command_record") == 0
    assert _count(session, "SELECT count(*) FROM blob") == 0
    assert bucket_keys() == []


def test_an_administrator_who_is_also_an_expert_uploads(store: S3BlobStore, factory, cast) -> None:
    assert _upload(_uploads(store, factory), cast, actor_uid=cast.admin_expert).revision.revision_number == 1


@pytest.mark.parametrize(
    ("overrides", "code", "field"),
    [
        ({"project_uid": "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"}, ErrorCode.NOT_FOUND, None),
        ({"project_uid": "not-a-project"}, ErrorCode.VALIDATION_FAILED, "project_uid"),
        ({"source_filename": "a/b.csv"}, ErrorCode.VALIDATION_FAILED, "source_filename"),
        ({"source_filename": "  "}, ErrorCode.VALIDATION_FAILED, "source_filename"),
        ({"idempotency_key": "has space"}, ErrorCode.VALIDATION_FAILED, "idempotency_key"),
        ({"default_currency": "руб"}, ErrorCode.VALIDATION_FAILED, "default_currency"),
        ({"content": b""}, ErrorCode.VALIDATION_FAILED, "content"),
        ({"content": b"x" * (10 * 1024 * 1024 + 1)}, ErrorCode.VALIDATION_FAILED, "content"),
        ({"content": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64}, ErrorCode.VALIDATION_FAILED, "content"),
        ({"content": "Наименование;Цена\nКабель;10\n".encode()}, ErrorCode.VALIDATION_FAILED, "content"),
        ({"content": "Наименование;Ед. изм.;Цена, руб.\nКабель;м;по запросу\n".encode()},
         ErrorCode.VALIDATION_FAILED, "content"),
    ],
)
def test_a_refused_request_or_file_leaves_nothing_behind(
    store: S3BlobStore, factory, session: Session, cast, bucket_keys,
    overrides: dict[str, Any], code: ErrorCode, field: str | None,
) -> None:
    refused = _refused(code, _upload, _uploads(store, factory), cast, **overrides)
    if field is not None:
        assert refused.detail_fields["field"] == field
    else:
        assert dict(refused.detail_fields) == {"aggregate_type": "Project"}
    for table in ("command_record", "blob", "price_list_revision", "price_list_position"):
        assert _count(session, f"SELECT count(*) FROM {table}") == 0
    assert bucket_keys() == []


def test_an_upload_read_from_a_handle_is_bounded(store: S3BlobStore, factory, cast) -> None:
    import io

    oversized = io.BytesIO(b"x" * (10 * 1024 * 1024 + 10))
    refused = _refused(ErrorCode.VALIDATION_FAILED, _upload, _uploads(store, factory), cast, content=oversized)
    assert refused.detail_fields["constraint"] == "byte_size <= 10485760"
    assert oversized.tell() == 10 * 1024 * 1024 + 1
    revision = _upload(_uploads(store, factory), cast, content=io.BytesIO(PRICE_LIST)).revision
    assert revision.accepted_row_count == 2


class _FailingPublish:
    """The real store, except that canonical publication is unreachable."""

    def __init__(self, store: S3BlobStore) -> None:
        self._store = store

    def __getattr__(self, name: str) -> Any:
        return getattr(self._store, name)

    def publish(self, verified: Any) -> Any:
        raise StorageUnavailableError()


def test_a_storage_failure_leaves_its_breadcrumb_and_no_revision_and_the_key_answers_it(
    store: S3BlobStore, factory, session: Session, cast, bucket_keys
) -> None:
    failing = PriceListUploads(_FailingPublish(store), session_factory=factory)  # type: ignore[arg-type]
    refused = _refused(ErrorCode.DEPENDENCY_UNAVAILABLE, _upload, failing, cast)
    assert "dependency" in refused.detail_fields
    assert _count(session, "SELECT count(*) FROM price_list_revision") == 0
    assert session.execute(text("SELECT state FROM blob")).scalars().all() == ["verifying"]
    assert session.execute(text("SELECT state, error_code FROM command_record")).one() == (
        "failed", "dependency_unavailable",
    )
    assert bucket_keys() == []  # the staged object was discarded
    # The key is spent: a repeat is answered with the recorded failure, not re-run.
    _refused(ErrorCode.DEPENDENCY_UNAVAILABLE, _upload, _uploads(store, factory), cast)
    # A new key on a working store converges on the same Blob row.
    revision = _upload(_uploads(store, factory), cast, idempotency_key="upload-retry").revision
    assert _count(session, "SELECT count(*) FROM blob WHERE state = 'available'") == 1
    assert store.read(revision.blob_id) == PRICE_LIST


class _RevokingPublish(_FailingPublish):
    """Publishes, but the uploader loses the expert role while the bytes are being stored."""

    def __init__(self, store: S3BlobStore, factory: sessionmaker[Session], admin: str, expert: str) -> None:
        super().__init__(store)
        self._factory, self._admin, self._expert = factory, admin, expert

    def publish(self, verified: Any) -> Any:
        published = self._store.publish(verified)
        with self._factory() as session:
            accounts.set_roles(session, actor_uid=self._admin, user_uid=self._expert, roles=frozenset())
            session.commit()
        return published


def test_the_role_is_read_again_in_the_writing_transaction(
    store: S3BlobStore, factory, session: Session, cast
) -> None:
    revoking = PriceListUploads(
        _RevokingPublish(store, factory, cast.admin, cast.expert), session_factory=factory  # type: ignore[arg-type]
    )
    _refused(ErrorCode.PERMISSION_DENIED, _upload, revoking, cast)
    assert _count(session, "SELECT count(*) FROM price_list_revision") == 0
    assert session.execute(text("SELECT state FROM command_record")).scalar_one() == "failed"


# -- reads ------------------------------------------------------------------------------------


def test_positions_are_paged_in_source_row_order(store: S3BlobStore, factory, session: Session, cast) -> None:
    body = "".join(f"Позиция {n};шт;{n + 1}\n" for n in range(250))
    revision = _upload(
        _uploads(store, factory), cast, content=("Наименование;Ед. изм.;Цена, руб.\n" + body).encode()
    ).revision
    roles = _roles(session, cast.expert)
    pages = []
    offset: int | None = 0
    while offset is not None:
        page = list_price_list_positions(
            session, price_list_id=revision.price_list_id, actor_roles=roles, offset=offset, limit=100
        )
        pages.append(page)
        offset = page.next_offset
    assert [len(page.positions) for page in pages] == [100, 100, 50]
    assert [page.next_offset for page in pages] == [100, 200, None]
    rows = [p.row_number for page in pages for p in page.positions]
    assert rows == list(range(2, 252))
    beyond = list_price_list_positions(
        session, price_list_id=revision.price_list_id, actor_roles=roles, offset=1000, limit=10
    )
    assert (beyond.positions, beyond.next_offset, beyond.total) == ((), None, 250)
    for bad in ({"limit": 0}, {"limit": 501}, {"offset": -1}):
        refused = _refused(
            ErrorCode.VALIDATION_FAILED, list_price_list_positions, session,
            price_list_id=revision.price_list_id, actor_roles=roles, **bad,
        )
        assert refused.detail_fields["field"] in {"limit", "offset"}


def test_reads_need_a_role_and_never_show_another_projects_price_list(
    store: S3BlobStore, factory, session: Session, cast
) -> None:
    revision = _upload(_uploads(store, factory), cast).revision
    nobody = _roles(session, cast.nobody)
    for call, kwargs in (
        (list_price_list_revisions, {"project_uid": cast.project}),
        (get_price_list_revision, {"price_list_id": revision.price_list_id}),
        (list_price_list_positions, {"price_list_id": revision.price_list_id}),
    ):
        refused = _refused(ErrorCode.PERMISSION_DENIED, call, session, actor_roles=nobody, **kwargs)
        assert refused.detail_fields["required_capability"] == "role:admin|expert"

    roles = _roles(session, cast.admin)
    assert list_price_list_revisions(session, project_uid=cast.other_project, actor_roles=roles) == ()
    for call in (get_price_list_revision, list_price_list_positions):
        refused = _refused(
            ErrorCode.NOT_FOUND, call, session, price_list_id=revision.price_list_id,
            actor_roles=roles, project_uid=cast.other_project,
        )
        assert dict(refused.detail_fields) == {"aggregate_type": "PriceList"}
    _refused(ErrorCode.NOT_FOUND, get_price_list_revision, session,
             price_list_id="prl_01ARZ3NDEKTSV4RRFFQ69G5FAV", actor_roles=roles)
    _refused(ErrorCode.VALIDATION_FAILED, get_price_list_revision, session,
             price_list_id="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", actor_roles=roles)
    _refused(ErrorCode.NOT_FOUND, list_price_list_revisions, session,
             project_uid="prj_01ARZ3NDEKTSV4RRFFQ69G5FAV", actor_roles=roles)
    assert get_price_list_revision(
        session, price_list_id=revision.price_list_id, actor_roles=roles, project_uid=cast.project
    ).price_list_id == revision.price_list_id


def test_an_uploader_cannot_be_purged(store: S3BlobStore, factory, session: Session, cast) -> None:
    _upload(_uploads(store, factory), cast)
    seed = str(session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one())
    accounts.archive_account(session, actor_uid=seed, user_uid=cast.expert)
    session.commit()
    refused = _refused(ErrorCode.CONFLICT, accounts.purge_account, session, actor_uid=seed, user_uid=cast.expert)
    session.rollback()
    assert dict(refused.detail_fields) == {"conflict_reason": "account_referenced"}
    assert "price_list_revision.uploaded_by_user_uid" in accounts.references_to(session, cast.expert)
