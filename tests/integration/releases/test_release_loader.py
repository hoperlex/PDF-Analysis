"""Real database evidence for authored revisions, rollback and account marks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from auditmanager.releases.notes import parse_note, read_notes
from auditmanager.releases.repository import ReleaseRepository, load_notes
from auditmanager.releases.versioning import canonical_semver_sort_key
from auditmanager.shared.db import create_session_factory
from auditmanager.shared.errors import DomainError, ErrorCode

ROOT = Path(__file__).resolve().parents[3]


def _notes():
    return read_notes(ROOT / "release-notes")


def _changed(note, *, revision: int, title: str):
    return parse_note(
        {
            "version": note.version,
            "revision": revision,
            "date": note.released_on.isoformat(),
            "title": title,
            "items": list(note.items),
            **({"is_archive": True, "range_label": note.range_label} if note.is_archive else {}),
        },
        filename=f"{note.version}.json",
    )


def _revisions(engine: Engine) -> list[tuple[str, int]]:
    with engine.connect() as connection:
        return list(connection.execute(
            text("SELECT r.version, rr.revision FROM release r "
                 "JOIN release_revision rr ON rr.release_pk = r.pk "
                 "ORDER BY r.version, rr.revision")
        ))


def test_shape_schema_matches_the_served_item_and_kind() -> None:
    schema = json.loads((ROOT / "release-notes/schema.json").read_text())
    api = json.loads((ROOT / "contracts/api/v1/openapi.json").read_text())
    served = api["components"]["schemas"]
    assert schema["$defs"]["kind"]["enum"] == served["ReleaseNoteKind"]["enum"]
    assert set(schema["$defs"]["item"]["properties"]) == set(
        served["ReleaseNoteItem"]["properties"]
    )
    assert set(schema["$defs"]["item"]["required"]) == set(
        served["ReleaseNoteItem"]["required"]
    )
    assert set(_notes()) == {"0.2.0", "0.3.0"}


@pytest.mark.parametrize(
    "extra_name,contents",
    [
        ("surprise.txt", "{}"),
        ("0.3.00.json", "{}"),
        ("0.4.0.json", '{"version":"0.4.0","revision":1,"date":"bad"}'),
    ],
)
def test_unknown_or_invalid_entry_refuses_before_database(
    tmp_path: Path, extra_name: str, contents: str
) -> None:
    notes_dir = tmp_path / "release-notes"
    notes_dir.mkdir()
    (notes_dir / "schema.json").write_bytes((ROOT / "release-notes/schema.json").read_bytes())
    (notes_dir / extra_name).write_text(contents)
    with pytest.raises(ValueError):
        read_notes(notes_dir)


def test_loader_is_idempotent_and_serves_the_highest_revision(
    migrated_engine: Engine,
) -> None:
    sessions = create_session_factory(migrated_engine)
    notes = _notes()
    archive_revision = notes["0.2.0"].revision
    current_revision = notes["0.3.0"].revision
    first = load_notes(sessions, notes=notes, product_version="0.3.0")
    assert first.inserted == ("0.2.0", "0.3.0")
    second = load_notes(sessions, notes=notes, product_version="0.3.0")
    assert second.unchanged == ("0.2.0", "0.3.0")
    assert _revisions(migrated_engine) == [
        ("0.2.0", archive_revision), ("0.3.0", current_revision)
    ]

    changed = _changed(notes["0.3.0"], revision=current_revision + 1, title="Новая редакция истории")
    revised = {**notes, "0.3.0": changed}
    assert load_notes(sessions, notes=revised, product_version="0.3.0").appended == ("0.3.0",)
    assert _revisions(migrated_engine) == [
        ("0.2.0", archive_revision),
        ("0.3.0", current_revision),
        ("0.3.0", current_revision + 1),
    ]
    uid = _seeded_uid(migrated_engine)
    listing = ReleaseRepository(sessions, product_version="0.3.0").list_for_account(uid)
    assert [item.version for item in listing.items] == ["0.3.0", "0.2.0"]
    assert listing.items[0].title == "Новая редакция истории"
    assert listing.items[1].is_archive
    assert listing.whats_new == ("0.3.0",)
    assert load_notes(sessions, notes=notes, product_version="0.3.0").older_revision == ("0.3.0",)


def _seeded_uid(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT user_uid FROM app_user LIMIT 1")).scalar_one()


def test_conflicts_and_missing_history_roll_back_the_whole_load(
    migrated_engine: Engine,
) -> None:
    sessions = create_session_factory(migrated_engine)
    notes = _notes()
    current_revision = notes["0.3.0"].revision
    load_notes(sessions, notes=notes, product_version="0.3.0")
    original = _revisions(migrated_engine)
    with pytest.raises(ValueError, match="without bump"):
        load_notes(sessions, notes={
            **notes, "0.3.0": _changed(
                notes["0.3.0"], revision=current_revision, title="Изменено без ревизии"
            )
        }, product_version="0.3.0")
    with pytest.raises(ValueError, match="unchanged content"):
        load_notes(sessions, notes={
            **notes, "0.3.0": _changed(
                notes["0.3.0"], revision=current_revision + 1, title=notes["0.3.0"].title
            )
        }, product_version="0.3.0")
    with pytest.raises(ValueError, match="missing from image"):
        load_notes(sessions, notes={"0.3.0": notes["0.3.0"]}, product_version="0.3.0")
    assert _revisions(migrated_engine) == original


def test_future_database_release_survives_rollback_and_is_hidden(
    migrated_engine: Engine,
) -> None:
    sessions = create_session_factory(migrated_engine)
    notes = _notes()
    load_notes(sessions, notes=notes, product_version="0.3.0")
    with migrated_engine.begin() as connection:
        pk = connection.execute(
            text("INSERT INTO release(version, sort_key, is_archive) "
                 "VALUES ('0.4.0', :key, false) RETURNING pk"),
            {"key": canonical_semver_sort_key("0.4.0")},
        ).scalar_one()
        connection.execute(
            text("INSERT INTO release_revision "
                 "(release_pk, revision, released_on, title, content, content_sha256) "
                 "VALUES (:pk, 1, DATE '2026-10-09', 'Future', "
                 """'{"items":[]}'::jsonb, :digest)"""),
            {"pk": pk, "digest": "a" * 64},
        )
    report = load_notes(sessions, notes=notes, product_version="0.3.0")
    assert report.future_untouched == ("0.4.0",)
    repo = ReleaseRepository(sessions, product_version="0.3.0")
    assert [item.version for item in repo.list_for_account(_seeded_uid(migrated_engine)).items] == [
        "0.3.0", "0.2.0"
    ]
    with pytest.raises(DomainError) as future:
        repo.mark_read(user_uid=_seeded_uid(migrated_engine), read_through="0.4.0")
    assert future.value.code is ErrorCode.VALIDATION_FAILED


def test_account_mark_only_rises_and_new_accounts_see_no_old_whats_new(
    migrated_engine: Engine,
) -> None:
    sessions = create_session_factory(migrated_engine)
    load_notes(sessions, notes=_notes(), product_version="0.3.0")
    repo = ReleaseRepository(sessions, product_version="0.3.0")
    old_uid = _seeded_uid(migrated_engine)
    assert repo.list_for_account(old_uid).whats_new == ("0.3.0",)
    repo.mark_read(user_uid=old_uid, read_through="0.3.0")
    assert repo.list_for_account(old_uid).whats_new == ()
    repo.mark_read(user_uid=old_uid, read_through="0.2.0")
    with migrated_engine.connect() as connection:
        marked = connection.execute(
            text("SELECT r.version FROM account_release_mark m JOIN release r "
                 "ON r.pk=m.read_through_release_pk WHERE m.user_uid=:uid"),
            {"uid": old_uid},
        ).scalar_one()
    assert marked == "0.3.0"
    with pytest.raises(DomainError) as unknown:
        repo.mark_read(user_uid=old_uid, read_through="9.9.9")
    assert unknown.value.code is ErrorCode.VALIDATION_FAILED

    new_uid = "usr_" + "7" * 26
    with migrated_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO app_user (user_uid, login, password_algorithm, "
                 "password_iterations, password_salt, password_hash, "
                 "is_default_credential, created_at) "
                 "SELECT :uid, 'new-release-reader', password_algorithm, "
                 "password_iterations, password_salt, password_hash, false, "
                 "(SELECT max(loaded_at) + interval '1 minute' FROM release_revision) "
                 "FROM app_user LIMIT 1"),
            {"uid": new_uid},
        )
    assert repo.list_for_account(new_uid).whats_new == ()
    notes = _notes()
    revised = {
        **notes,
        "0.3.0": _changed(
            notes["0.3.0"],
            revision=notes["0.3.0"].revision + 1,
            title="Уточнённая история изменений",
        ),
    }
    load_notes(sessions, notes=revised, product_version="0.3.0")
    assert repo.list_for_account(new_uid).whats_new == (
    ), "a revision does not change when this release first reached the database"
