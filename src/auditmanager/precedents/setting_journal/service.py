"""The journal of the programme's switches and settings, behind ``listPrecedentSettings`` and ``appendPrecedentSetting`` (contract 1.51.0, plan-v5 3.1 and 3.6).

The two routes are the two bodies this module fills; a route reads and writes nothing itself and asks the service below through the port of
``api/routers/precedents_ports.py``. The service answers in the contract's own shape (a mapping the route validates against ``PrecedentSetting`` and
``PrecedentSettingList``), opens its own session, and decides what the router may not:

* **who**: an administrator, checked here again although the authorization seam has refused any other role (the register is the first line, not the
  only one). A viewer or an expert gets ``permission_denied`` and nothing is read or written;
* **what a value may be**: :func:`checked_value` -- the shapes of the migration's CHECKs, said as ``validation_failed`` with a ``field`` and a
  ``constraint`` before the database has to refuse, and the one guard of the programme: ``one_list`` cannot be switched on while
  ``settings.ONE_LIST_READY`` is false (`D-683`). The check comes **before the key is claimed**, so a refused value leaves no command record and the
  same key may be used for the corrected request;
* **a keyed write**: ``Idempotency-Key`` is required and the command is recorded as ``append_precedent_setting``. The same key with the same body
  answers the revision that key made and writes nothing; the same key with another body is the ledger's ``409``. Every accepted request is a new
  revision, even one that repeats the value in force: the journal is the administrator's record of what was asked, and the contract says the
  revision is «the next one of the name»;
* **the revision is the next one of the name, without a gap**: the number is read under the advisory lock the journal's trigger takes for the same
  name, so two administrators writing one name queue instead of one of them meeting the trigger's refusal;
* **the event**: ``precedent.setting_appended`` in ``audit_event`` (a KEEP prefix of the product purge), in the same transaction as the revision. Its
  payload is the name, the revision and the actor -- never the value (the value is in the journal row, which is the record of it).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.precedents import settings as journal
from auditmanager.precedents.vectors.window import SETTING_NAME as _WINDOW_SETTING_NAME
from auditmanager.precedents.vectors.window import parse_setting as parse_window_setting
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, IdempotencyKey

__all__ = ["APPEND_PRECEDENT_SETTING_COMMAND_TYPE", "EVENT_SETTING_APPENDED", "EVENTS_LIMIT", "PrecedentSettingService", "checked_value"]

#: The command type of the keyed write, as ``command_record.command_type`` holds it (classified KEEP in ``scripts/recovery/product_purge.py``).
#: The router module exports the same word; a test holds the two equal.
APPEND_PRECEDENT_SETTING_COMMAND_TYPE: Final[str] = "append_precedent_setting"
#: The audit event of a new revision; ``precedent.`` is a KEEP prefix of the product purge.
EVENT_SETTING_APPENDED: Final[str] = "precedent.setting_appended"
_AGGREGATE_TYPE: Final[str] = "PrecedentSetting"
#: ``PrecedentSettingList.events`` holds at most this many rows, newest first.
EVENTS_LIMIT: Final[int] = 200
_ADMIN: Final[str] = "admin"

_COLUMNS = "setting_name, revision, value, actor_user_uid, created_at"
_CURRENT = text(
    f"SELECT DISTINCT ON (setting_name) {_COLUMNS} FROM precedent_setting_event ORDER BY setting_name, revision DESC"
)
_EVENTS = text(
    f"SELECT {_COLUMNS} FROM precedent_setting_event ORDER BY created_at DESC, revision DESC, setting_name LIMIT :limit"
)
_ONE = text(f"SELECT {_COLUMNS} FROM precedent_setting_event WHERE setting_name = :name AND revision = :revision")
#: The same key the journal's trigger (``am_check_gapless_number``) locks on, so the number read below cannot be taken by another writer before ours.
_LOCK = text("SELECT pg_advisory_xact_lock(hashtextextended('precedent_setting_event:' || :name, 0))")
_NEXT = text("SELECT COALESCE(MAX(revision), 0) + 1 FROM precedent_setting_event WHERE setting_name = :name")
_INSERT = text(
    "INSERT INTO precedent_setting_event (setting_name, revision, value, actor_user_uid) "
    "VALUES (:name, :revision, CAST(:value AS jsonb), :actor) RETURNING " + _COLUMNS
)
_INSERT_EVENT = text(
    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
    "VALUES (:event_id, :event_type, :aggregate_type, :aggregate_id, CAST(:payload AS jsonb))"
)


def _refuse(field: str, constraint: str, message: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field=field, constraint=constraint, message=message)


def checked_value(setting_name: object, value: object) -> dict[str, Any]:
    """The value to journal under ``setting_name``, or the ``validation_failed`` that says which rule it breaks.

    * ``one_list`` and ``critic_context``: exactly ``{"enabled": true|false}``; a flag that is not a boolean, or another member, is refused
      (``constraint: switch_shape``). ``one_list`` with ``true`` is refused while ``settings.ONE_LIST_READY`` is false
      (``constraint: one_list_not_ready``, `D-683`);
    * ``vector_window``: ``{"start": "HH:MM", "end": "HH:MM", "tz": "<zone>"}`` read by the very parser the night window reads its setting with
      (``vectors.window.parse_setting``), so a value the worker would refuse is never journalled -- a window nobody chose would stop the stand's
      runs at the wrong hour (``constraint: vector_window_shape``);
    * the others (``section_labels``, ``stop_words``, ``thresholds``): any object, the shape being their reader's own (`PREC-PASS`).

    Every value is a JSON object of at most ``settings.VALUE_MAX_OCTETS`` octets with no ``NaN`` or infinity (``jsonb`` has neither)."""
    if setting_name not in journal.SETTING_NAMES:
        raise _refuse("setting_name", "enum", "the setting is not one of the programme's settings")
    if not isinstance(value, Mapping):
        raise _refuse("value", "object", "the value of a setting is a JSON object")
    try:
        # the separators of ``jsonb``'s own text, which is what ``octet_length(value::text)`` counts
        size = len(json.dumps(dict(value), ensure_ascii=False, allow_nan=False, separators=(", ", ": ")).encode("utf-8"))
    except (TypeError, ValueError):
        raise _refuse("value", "json", "the value is not JSON the journal can hold") from None
    if size > journal.VALUE_MAX_OCTETS:
        raise _refuse("value", "value_too_large", "the value is larger than the journal admits")
    if setting_name in journal.SWITCH_NAMES:
        enabled = value.get("enabled")
        if set(value) != {"enabled"} or not isinstance(enabled, bool):
            raise _refuse("value", "switch_shape", "a switch is exactly {enabled: true or false}")
        if setting_name == journal.SETTING_ONE_LIST and enabled and not journal.ONE_LIST_READY:
            raise _refuse("value", journal.CONSTRAINT_ONE_LIST_NOT_READY,
                          "one_list cannot be switched on yet: the block findings do not meet the evidence contract (D-683)")
        return {"enabled": enabled}
    if setting_name == _WINDOW_SETTING_NAME:
        try:
            return parse_window_setting(value).as_value()
        except ValueError:
            raise _refuse("value", "vector_window_shape",
                          "the night window is {start: HH:MM, end: HH:MM, tz: a zone this stand knows}, start and end apart") from None
    return dict(value)


def _roles_of(session: Session, user_uid: str) -> frozenset[str]:
    from auditmanager.access.public import AccountRepository

    return frozenset(str(role) for role in AccountRepository().roles_of(session, user_uid))


def _utc(moment: datetime) -> datetime:
    return moment.astimezone(UTC)


def _setting(row: Any) -> dict[str, Any]:
    value = row[2]
    return {
        "setting_name": str(row[0]), "revision": int(row[1]), "value": json.loads(value) if isinstance(value, str) else dict(value),
        "actor_user_uid": str(row[3]), "created_at": _utc(row[4]),
    }


class PrecedentSettingService:
    """The journal as the surface shows it. Wired by the composition root as ``build_router(precedent_settings=PrecedentSettingService(sessions))``."""

    def __init__(
        self, session_factory: sessionmaker[Session], *, roles_of: Callable[[Session, str], frozenset[str]] = _roles_of,
    ) -> None:
        self._sessions = session_factory
        self._roles_of = roles_of

    def _require_admin(self, session: Session, user_uid: str) -> None:
        if _ADMIN not in self._roles_of(session, user_uid):
            raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin")

    # -- the read -----------------------------------------------------------------------------------------------

    def list_precedent_settings(self, *, user_uid: str) -> dict[str, Any]:
        """The revision in force of every name ever journalled (in the contract's order of the names) and the journal, newest first."""
        with self._sessions() as session:
            self._require_admin(session, user_uid)
            current = {item["setting_name"]: item for item in map(_setting, session.execute(_CURRENT).all())}
            events = [_setting(row) for row in session.execute(_EVENTS, {"limit": EVENTS_LIMIT}).all()]
        return {"current": [current[name] for name in journal.SETTING_NAMES if name in current], "events": events}

    # -- the write ----------------------------------------------------------------------------------------------

    def append_precedent_setting(self, *, setting_name: str, value: Mapping[str, Any], user_uid: str, idempotency_key: str) -> dict[str, Any]:
        # Imported here, not at the top: the command ledger lives in `ingest`, whose import pulls the document and storage stacks, and
        # `precedents.public` is the surface of a pure core that other contexts import without wanting them.
        from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint

        with self._sessions() as session:
            self._require_admin(session, user_uid)
            checked = checked_value(setting_name, value)
            ledger = CommandRepository()
            claimed = ledger.begin(
                session, command_type=APPEND_PRECEDENT_SETTING_COMMAND_TYPE, idempotency_key=IdempotencyKey(idempotency_key),
                fingerprint=payload_fingerprint({"setting_name": setting_name, "value": checked, "actor_uid": user_uid}))
            if isinstance(claimed, CommandReplay):
                row = session.execute(_ONE, {"name": claimed.outcome["setting_name"], "revision": claimed.outcome["revision"]}).first()
                if row is None:  # the journal is append-only and kept: a recorded outcome whose row is gone is not hidden
                    raise DomainError(ErrorCode.INTERNAL_ERROR, message="a recorded revision of a setting is missing")
                return _setting(row)
            session.execute(_LOCK, {"name": setting_name})
            revision = int(session.execute(_NEXT, {"name": setting_name}).scalar_one())
            row = session.execute(_INSERT, {
                "name": setting_name, "revision": revision, "value": json.dumps(checked, ensure_ascii=False), "actor": user_uid,
            }).one()
            session.execute(_INSERT_EVENT, {
                "event_id": str(AuditEventId.new()), "event_type": EVENT_SETTING_APPENDED, "aggregate_type": _AGGREGATE_TYPE,
                "aggregate_id": str(claimed.command_id),
                "payload": json.dumps({"setting_name": setting_name, "revision": revision, "actor_uid": user_uid}, sort_keys=True),
            })
            ledger.succeed(session, claimed.command_id, {"setting_name": setting_name, "revision": revision})
            view = _setting(row)
            session.commit()
            return view
