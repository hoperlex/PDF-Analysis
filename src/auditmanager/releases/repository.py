"""Transactional release history and each account's monotone read mark."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.releases.notes import ReleaseNote
from auditmanager.releases.versioning import canonical_semver_sort_key
from auditmanager.shared.errors import DomainError, ErrorCode


@dataclass(frozen=True, slots=True)
class VisibleRelease:
    version: str
    revision: int
    released_on: date
    title: str
    is_archive: bool
    range_label: str | None
    items: tuple[dict[str, str], ...]


@dataclass(frozen=True, slots=True)
class ReleaseListing:
    items: tuple[VisibleRelease, ...]
    whats_new: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LoadReport:
    inserted: tuple[str, ...]
    appended: tuple[str, ...]
    unchanged: tuple[str, ...]
    older_revision: tuple[str, ...]
    future_untouched: tuple[str, ...]


class ReleaseRepository:
    def __init__(self, sessions: sessionmaker[Session], *, product_version: str) -> None:
        self._sessions = sessions
        self.product_version = product_version
        self._max_key = canonical_semver_sort_key(product_version)

    def list_for_account(self, user_uid: str) -> ReleaseListing:
        with self._sessions() as session:
            standing = session.execute(
                text(
                    "SELECT u.created_at, m.read_through_release_pk, marked.sort_key "
                    "FROM app_user AS u "
                    "LEFT JOIN account_release_mark AS m ON m.user_uid = u.user_uid "
                    "LEFT JOIN release AS marked ON marked.pk = m.read_through_release_pk "
                    "WHERE u.user_uid = :uid"
                ),
                {"uid": user_uid},
            ).one_or_none()
            if standing is None:
                raise DomainError(ErrorCode.NOT_FOUND)
            account_created_at, _, marked_key = standing
            rows = session.execute(
                text(
                    "SELECT r.version, r.sort_key, r.is_archive, latest.revision, "
                    "latest.released_on, latest.title, latest.content, first_load.loaded_at "
                    "FROM release AS r "
                    "JOIN LATERAL (SELECT rr.revision, rr.released_on, rr.title, rr.content "
                    "  FROM release_revision AS rr WHERE rr.release_pk = r.pk "
                    "  ORDER BY rr.revision DESC LIMIT 1) AS latest ON true "
                    "JOIN LATERAL (SELECT min(rr.loaded_at) AS loaded_at "
                    "  FROM release_revision AS rr WHERE rr.release_pk = r.pk) "
                    "  AS first_load ON true "
                    "WHERE r.sort_key <= :max_key "
                    "ORDER BY r.is_archive ASC, r.sort_key DESC"
                ),
                {"max_key": self._max_key},
            ).all()
        items: list[VisibleRelease] = []
        whats_new: list[str] = []
        for version, sort_key, is_archive, revision, released_on, title, content, first_loaded in rows:
            if not isinstance(content, dict):
                raise RuntimeError("release content is not a JSON object")
            note_items = content.get("items")
            if not isinstance(note_items, list):
                raise RuntimeError("release content has no items")
            items.append(
                VisibleRelease(
                    version, revision, released_on, title, is_archive,
                    content.get("range_label"), tuple(note_items),
                )
            )
            if (
                not is_archive
                and (marked_key is None or sort_key > marked_key)
                and account_created_at < first_loaded
            ):
                whats_new.append(version)
        return ReleaseListing(tuple(items), tuple(whats_new))

    def mark_read(self, *, user_uid: str, read_through: str) -> None:
        with self._sessions.begin() as session:
            target = session.execute(
                text(
                    "SELECT pk FROM release WHERE version = :version "
                    "AND sort_key <= :max_key"
                ),
                {"version": read_through, "max_key": self._max_key},
            ).scalar_one_or_none()
            if target is None:
                raise DomainError(ErrorCode.VALIDATION_FAILED)
            session.execute(
                text(
                    "INSERT INTO account_release_mark (user_uid, read_through_release_pk) "
                    "VALUES (:uid, :pk) "
                    "ON CONFLICT (user_uid) DO UPDATE SET "
                    "read_through_release_pk = EXCLUDED.read_through_release_pk"
                ),
                {"uid": user_uid, "pk": target},
            )


def load_notes(
    sessions: sessionmaker[Session],
    *,
    notes: dict[str, ReleaseNote],
    product_version: str,
) -> LoadReport:
    """Apply the whole repository snapshot in one transaction.

    A database release at or below this image's VERSION may never disappear
    from the authored tree. A future release absent from an older image is a
    valid rollback and remains untouched.
    """
    max_key = canonical_semver_sort_key(product_version)
    regular = [note for note in notes.values() if not note.is_archive]
    if not regular or max(regular, key=lambda note: canonical_semver_sort_key(note.version)).version != product_version:
        raise ValueError("VERSION must equal the highest non-archive release note")
    inserted: list[str] = []
    appended: list[str] = []
    unchanged: list[str] = []
    older: list[str] = []
    future: list[str] = []
    with sessions.begin() as session:
        # One loader at a time, including concurrent deploy attempts.
        session.execute(text("SELECT pg_advisory_xact_lock(520016)"))
        stored = {
            row.version: row
            for row in session.execute(
                text("SELECT pk, version, sort_key, is_archive FROM release")
            ).mappings()
        }
        for version, row in stored.items():
            if version not in notes:
                if row["sort_key"] <= max_key:
                    raise ValueError(f"release note missing from image: {version}")
                future.append(version)
        for version in sorted(notes, key=canonical_semver_sort_key):
            note = notes[version]
            sort_key = canonical_semver_sort_key(version)
            if sort_key > max_key:
                raise ValueError(f"release note exceeds VERSION: {version}")
            row = stored.get(version)
            if row is None:
                pk = session.execute(
                    text(
                        "INSERT INTO release (version, sort_key, is_archive) "
                        "VALUES (:version, :sort_key, :archive) RETURNING pk"
                    ),
                    {"version": version, "sort_key": sort_key, "archive": note.is_archive},
                ).scalar_one()
                inserted.append(version)
            else:
                if row["sort_key"] != sort_key or row["is_archive"] != note.is_archive:
                    raise ValueError(f"immutable release metadata changed: {version}")
                pk = row["pk"]
            latest = session.execute(
                text(
                    "SELECT revision, content_sha256 FROM release_revision "
                    "WHERE release_pk = :pk ORDER BY revision DESC LIMIT 1"
                ),
                {"pk": pk},
            ).one_or_none()
            if latest is not None:
                revision, prior_hash = latest
                if note.revision < revision:
                    older.append(version)
                    continue
                if note.revision == revision:
                    if note.content_sha256 != prior_hash:
                        raise ValueError(f"release revision changed without bump: {version}")
                    unchanged.append(version)
                    continue
                if note.content_sha256 == prior_hash:
                    raise ValueError(f"release revision has unchanged content: {version}")
                appended.append(version)
            session.execute(
                text(
                    "INSERT INTO release_revision "
                    "(release_pk, revision, released_on, title, content, content_sha256) "
                    "VALUES (:pk, :revision, :released_on, :title, "
                    "CAST(:content AS jsonb), :sha)"
                ),
                {
                    "pk": pk, "revision": note.revision,
                    "released_on": note.released_on, "title": note.title,
                    "content": _canonical_content(note.content), "sha": note.content_sha256,
                },
            )
    return LoadReport(
        tuple(inserted), tuple(appended), tuple(unchanged), tuple(older), tuple(future)
    )


def _canonical_content(content: dict[str, Any]) -> str:
    import json

    return json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
