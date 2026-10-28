"""PostgreSQL, object store and a seeded world for the pair-tile integration tests (`CMP-VIEWER-01`).

A lane's own services are required, never skipped. The world is one project with one document of two versions (the
synthetic corpus' VS-1 v1 and v2, six pages each, page 5 an A1 plan of 6623 x 4678 px at 200 dpi and five pyramid
levels), whose page profiles are built by the real children once per module. The rows the later lanes write -- the
series, the transition, the sheet pairs and their results, the mask blob -- are inserted here directly, as the lane's
brief says.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy
import pytest
from sqlalchemy import text

from auditmanager.comparison.profile.builder import build_version_page_profiles
from auditmanager.comparison.profile.publish import ProfileBlobPublisher
from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT
from auditmanager.shared.db import session_scope
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.db.session import create_session_factory
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid, new_ulid
from auditmanager.storage.public import S3BlobStore, S3StorageSettings, StorageError

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "fixtures" / "comparison"
_NAMES = (
    "DATABASE_URL", "S3_ENDPOINT_URL", "S3_API_PORT", "S3_REGION", "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
)
ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _load_dotenv() -> None:
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    for raw in dotenv.read_text(encoding="utf-8").splitlines():
        name, separator, value = raw.strip().partition("=")
        if separator and name in _NAMES and not os.environ.get(name):
            os.environ[name] = value.strip().strip("\"'")


@pytest.fixture(scope="session")
def session_factory():
    _load_dotenv()
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail("DATABASE_URL is not set: run `make up` and `make migrate` for this lane. These tests never skip.")
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(raw)))
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT to_regclass('public.comparison_sheet_pair')")).scalar_one_or_none() is None:
                pytest.fail("the database has no comparison_sheet_pair table: run `make migrate` (head 0039)")
        yield create_session_factory(engine)
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def blob_store() -> S3BlobStore:
    _load_dotenv()
    try:
        store = S3BlobStore(S3StorageSettings.from_env())
        store.check_access()
    except StorageError as failure:
        pytest.fail(f"the lane's private bucket is not reachable: {failure}")
    return store


@dataclass(frozen=True)
class World:
    project: str
    document: str
    older: str
    newer: str
    older_pages: dict[int, str]
    newer_pages: dict[int, str]
    transition: str


def _command(connection: Any) -> str:
    command = f"cmd_{new_ulid()}"
    connection.execute(
        text("INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
             "VALUES (:c, 'start_comparison_series', :k, :f)"),
        {"c": command, "k": f"k_{new_ulid()}"[:20], "f": "a" * 64},
    )
    return command


def _seed_world(session_factory, blob_store) -> World:
    project, document = str(ProjectUid.new()), str(DocumentUid.new())
    publisher = ProfileBlobPublisher(session_factory, blob_store)
    versions: list[str] = []
    with session_scope(session_factory) as session:
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Пары листов')"), {"p": project})
        session.execute(
            text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Комплект')"),
            {"d": document, "p": project},
        )
    for ordinal, name in ((1, "v1.pdf"), (2, "v2.pdf")):
        data = (FIXTURES / "vs1" / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        version = str(VersionUid.new())
        blob_id = publisher.publish(data, role="source_document", media_type="application/pdf")
        with session_scope(session_factory) as session:
            session.execute(
                text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                     "sha256, page_count) VALUES (:v, :d, :o, 'application/pdf', :n, :s, 6)"),
                {"v": version, "d": document, "o": ordinal, "n": len(data), "s": digest},
            )
            session.execute(
                text("INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
                     "VALUES (:v, :r, :b, :s, :n, 'application/pdf')"),
                {"v": version, "r": MANIFEST_ROLE_SOURCE_DOCUMENT, "b": blob_id, "s": digest, "n": len(data)},
            )
        build_version_page_profiles(session_factory, blob_store, version)
        versions.append(version)
    pages: list[dict[int, str]] = []
    with session_scope(session_factory) as session:
        for version in versions:
            rows = session.execute(
                text("SELECT page_number, comparison_page_profile_id FROM comparison_page_profile "
                     "WHERE version_uid = :v ORDER BY page_number"), {"v": version}).all()
            pages.append({int(n): str(i) for n, i in (tuple(r) for r in rows)})
    with session_scope(session_factory) as session:
        matrix, series, transition = f"cmx_{new_ulid()}", f"cser_{new_ulid()}", f"ctn_{new_ulid()}"
        session.execute(
            text("INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, order_id, "
                 "profile_signature, rules_version, algo_version, rows) VALUES (:m, :p, :d, 1, NULL, :s, 'v1.2', 'm1', '[]')"),
            {"m": matrix, "p": project, "d": document, "s": "1" * 64},
        )
        connection = session.connection()
        session.execute(
            text("INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, state, "
                 "comparison_matrix_id, matrix_edit_no, input_sha256, actor_user_uid, actor_label, command_id) "
                 "VALUES (:s, :p, :d, 'queued', :m, 0, :sha, :a, 'Эксперт', :c)"),
            {"s": series, "p": project, "d": document, "m": matrix, "sha": "b" * 64, "a": ACTOR, "c": _command(connection)},
        )
        session.execute(
            text("INSERT INTO comparison_transition (comparison_transition_id, comparison_series_id, transition_no, "
                 "source_version_uid, target_version_uid) VALUES (:t, :s, 1, :a, :b)"),
            {"t": transition, "s": series, "a": versions[0], "b": versions[1]},
        )
    return World(project, document, versions[0], versions[1], pages[0], pages[1], transition)


@pytest.fixture(scope="module")
def world(session_factory, blob_store) -> World:
    return _seed_world(session_factory, blob_store)


@pytest.fixture(scope="module")
def make_pair(session_factory, blob_store, world) -> Callable[..., str]:
    """``make_pair(page_a=5, page_b=5, status="different", result=None, mask=None) -> ctp id``.

    ``result`` is the result ``jsonb`` (merged over a default with a canvas, an identity transform and the dpi of the
    A1 plan), ``mask`` the bytes of a mask blob to publish, or ``None``. ``status`` ``added`` / ``removed`` make a pair
    with one page and no result; ``queued`` makes a pair that was never compared.
    """
    publisher = ProfileBlobPublisher(session_factory, blob_store)
    counter = iter(range(1, 10_000))

    def make(
        *, page_a: int | None = 5, page_b: int | None = 5, status: str = "different", result: dict[str, Any] | None = None,
        mask: bytes | None = None, mask_blob_id: str | None = None, result_status: str | None = None,
        default_result: bool = True,
    ) -> str:
        pair = f"ctp_{new_ulid()}"
        a = world.older_pages[page_a] if page_a is not None else None
        b = world.newer_pages[page_b] if page_b is not None else None
        compared = status in ("same", "same_zones_changed", "different", "needs_review")
        result_id = None
        if compared:
            document: dict[str, Any] = {}
            if default_result:
                document = {
                    "format": 1, "canvas": {"width_pt": 2383.94, "height_pt": 1683.78},
                    "how_compared": {"algo_version": "t", "dpi": 200, "tolerance_pt": 0.5, "transform": [1, 0, 0, 1, 0, 0]},
                    "aligned_blocks": [], "mask": None, "differences": [], "text_changes": [], "service_notes": [],
                }
            for key, value in (result or {}).items():
                document[key] = value
            blob = mask_blob_id
            if mask is not None:
                blob = publisher.publish(mask, role="comparison_pair_mask", media_type="application/octet-stream")
            result_id = f"csp_{new_ulid()}"
            with session_scope(session_factory) as session:
                session.execute(
                    text("INSERT INTO comparison_sheet_pair_result (comparison_sheet_pair_result_id, project_uid, "
                         "content_key, algo_version, status, result, page_a_profile_id, page_b_profile_id, mask_blob_id) "
                         "VALUES (:r, :p, :k, 't', :s, CAST(:j AS jsonb), :a, :b, :m)"),
                    {"r": result_id, "p": world.project, "k": secrets.token_hex(32), "s": result_status or status,
                     "j": json.dumps(document), "a": a, "b": b, "m": blob},
                )
        with session_scope(session_factory) as session:
            session.execute(
                text("INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, "
                     "state, status, page_a_profile_id, page_b_profile_id, result_id) "
                     "VALUES (:i, :t, :n, :st, :s, :a, :b, :r)"),
                {"i": pair, "t": world.transition, "n": next(counter), "st": "queued" if status == "queued" else "done",
                 "s": None if status == "queued" else status, "a": a, "b": b, "r": result_id},
            )
        return pair

    return make


@pytest.fixture(scope="session")
def support() -> SimpleNamespace:
    def mask_blob(planes: "numpy.ndarray", **overrides: Any) -> bytes:
        import struct
        import zlib

        height, width = planes.shape[1], planes.shape[2]
        fields = {"magic": b"AMCM", "fmt": 1, "layers": 8, "reserved": 0, **overrides}
        header = struct.pack("<4sBBHII", fields["magic"], fields["fmt"], fields["layers"], fields["reserved"], width, height)
        return header + zlib.compress(numpy.packbits(planes, axis=-1, bitorder="big").tobytes(), 6)

    def packed_planes(width: int, height: int, pixels: dict[str, list[tuple[int, int]]]) -> "numpy.ndarray":
        """The packed planes of a mask of the size of an A1 raster, built without a 250 MB ``bool`` array."""
        from auditmanager.comparison.engine.mask_codec import LAYERS

        packed = numpy.zeros((8, height, (width + 7) // 8), dtype=numpy.uint8)
        for name, points in pixels.items():
            for x, y in points:
                packed[LAYERS.index(name), y, x // 8] |= 0x80 >> (x % 8)
        return packed

    def packed_mask_blob(width: int, height: int, pixels: dict[str, list[tuple[int, int]]]) -> bytes:
        """The blob the ENGINE's codec writes for those pixels (`encode_packed_planes`, what a worker publishes)."""
        from auditmanager.comparison.engine.mask_codec import encode_packed_planes

        return encode_packed_planes(packed_planes(width, height, pixels), width, height, level=1)

    def brief_mask_blob(width: int, height: int, pixels: dict[str, list[tuple[int, int]]]) -> bytes:
        """The same planes written per the TEXT of wave brief C1 section 4 item 1, without the engine's codec."""
        import struct
        import zlib

        return struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, width, height) + zlib.compress(packed_planes(width, height, pixels).tobytes(), 1)

    return SimpleNamespace(mask_blob=mask_blob, packed_mask_blob=packed_mask_blob, brief_mask_blob=brief_mask_blob)
