"""The independent source-versus-target comparison reports exactly what differs.

The comparison is the drill's cross-check, so it must be shown able to fail: two clones of the
migrated schema compare equal, and each mutation of the second clone (a row, a table, a view,
a dropped constraint, a changed trigger or function, a moved sequence) and each change of the
second bucket (a missing object, one changed byte) is named at its own path.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Callable

import pytest
from sqlalchemy import Engine

from auditmanager.shared.db.config import DatabaseSettings
from auditmanager.shared.db.engine import create_database_engine
from scripts.recovery.synthetic_drill_compare import (
    _digest,
    bucket_profile,
    database_profile,
    differences,
)


@pytest.fixture
def two_clones(migrated_database_factory: Callable[[], DatabaseSettings]):
    engines = [create_database_engine(migrated_database_factory()) for _ in range(2)]
    try:
        yield engines
    finally:
        for engine in engines:
            engine.dispose()


def _changed(engines: list[Engine], *statements: str) -> list[str]:
    with engines[1].begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
    return differences(database_profile(engines[0]), database_profile(engines[1]))


def test_two_clones_of_one_migrated_schema_are_equal(two_clones: list[Engine]) -> None:
    first, second = database_profile(two_clones[0]), database_profile(two_clones[1])
    assert differences(first, second) == []
    # `EXEC-SEAL-01`: +5 tables, +1 view; `EXEC-PULL-01` (0031): +2 tables; `0032_ar_v3_run_group`: +2 tables;
    # `0035_comparison_records`: +1 table.
    assert len(first["tables"]) == 65 and len(first["views"]) == 5
    assert set(first["shape"]) == {
        "columns", "constraints", "indexes", "triggers", "functions", "views", "sequences", "extensions",
    }


_MUTATIONS = {
    "a row": (
        ("INSERT INTO release (version, sort_key) VALUES ('0.0.1', 'a')",),
        ["/tables/release: source [0,", "/shape/sequences"],
    ),
    "a table": (("CREATE TABLE zz_extra (id integer)",), ["/tables/zz_extra: only in target",
                                                          "/shape/columns"]),
    "a view": (("DROP VIEW work_assignment_current",), ["/views/work_assignment_current: only in source",
                                                       "/shape/views"]),
    "a dropped constraint": (
        ("ALTER TABLE price_list_revision DROP CONSTRAINT ck_price_list_revision_row_counts",),
        ["/shape/constraints"],
    ),
    "a dropped trigger": (
        ("DROP TRIGGER trg_work_assignment_event_immutable ON work_assignment_event",),
        ["/shape/triggers"],
    ),
    "a disabled trigger": (
        ("ALTER TABLE price_list_revision DISABLE TRIGGER trg_price_list_revision_immutable",),
        ["/shape/triggers"],
    ),
    "a changed function body": (
        ("CREATE OR REPLACE FUNCTION am_check_price_list_blob() RETURNS trigger "
         "LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$",),
        ["/shape/functions"],
    ),
    "a dropped index": (("DROP INDEX ix_price_list_revision_blob",), ["/shape/indexes"]),
    "a moved sequence": (("SELECT setval('release_pk_seq', 7)",), ["/shape/sequences"]),
}


@pytest.mark.parametrize("name", sorted(_MUTATIONS))
def test_each_difference_is_named_at_its_own_path(two_clones: list[Engine], name: str) -> None:
    statements, expected = _MUTATIONS[name]
    found = _changed(two_clones, *statements)
    assert found, f"{name} went unnoticed"
    for fragment in expected:
        assert any(fragment in line for line in found), (fragment, found)


def test_a_check_that_only_changes_its_parentheses_is_informational_never_a_difference() -> None:
    nested = ["t ck CHECK ((((a >= 1) AND (a <= 9)) AND (a <> 5))) validated=t"]
    flat = ["t ck CHECK (((a >= 1) AND (a <= 9) AND (a <> 5))) validated=t"]
    assert _digest(nested) != _digest(flat)
    assert _digest(nested, loose=True) == _digest(flat, loose=True)
    # ...but a different operand, literal, name or count is still a difference.
    for other in (["t ck CHECK (((a >= 1) AND (a <= 9) AND (a <> 6))) validated=t"],
                  ["t ck2 CHECK (((a >= 1) AND (a <= 9) AND (a <> 5))) validated=t"],
                  ["t ck CHECK (((a >= 1) AND (a <= 9) AND (a <> 5))) validated=f"], flat + flat):
        assert _digest(other, loose=True) != _digest(flat, loose=True)


class _Bucket:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects

    def list_objects_v2(self, *, Bucket: str, ContinuationToken: str | None = None) -> dict[str, object]:
        assert Bucket == "b" and ContinuationToken is None
        return {"Contents": [{"Key": key, "Size": len(data)} for key, data in sorted(self.objects.items())],
                "IsTruncated": False}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        return {"Body": io.BytesIO(self.objects[Key])}


def test_buckets_compare_by_key_size_and_the_bytes_actually_read() -> None:
    objects = {"blobs/aa/one": b"first object", "blobs/bb/two": b"second object"}
    source = {"objects": bucket_profile(_Bucket(dict(objects)), "b")}
    assert source["objects"]["blobs/aa/one"] == [12, hashlib.sha256(b"first object").hexdigest()]
    same = {"objects": bucket_profile(_Bucket(dict(objects)), "b")}
    assert differences(source, same) == []
    flipped = dict(objects, **{"blobs/aa/one": b"first objecT"})
    assert any("/objects/blobs/aa/one" in line
               for line in differences(source, {"objects": bucket_profile(_Bucket(flipped), "b")}))
    missing = {"blobs/aa/one": objects["blobs/aa/one"]}
    assert differences(source, {"objects": bucket_profile(_Bucket(missing), "b")}) == [
        "/objects/blobs/bb/two: only in source"
    ]
    extra = dict(objects, **{"blobs/cc/three": b"orphan"})
    assert differences(source, {"objects": bucket_profile(_Bucket(extra), "b")}) == [
        "/objects/blobs/cc/three: only in target"
    ]


def test_a_listed_size_that_the_body_does_not_deliver_is_refused() -> None:
    class Short(_Bucket):
        def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
            return {"Body": io.BytesIO(b"short")}

    with pytest.raises(ValueError, match="listed 12 bytes"):
        bucket_profile(Short({"blobs/aa/one": b"first object"}), "b")
