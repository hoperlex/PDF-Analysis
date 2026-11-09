"""DECISION-MEMORY-01 phase M2: show and change the installation settings of the decision memory (`D-390`, `Q3c`).

Two settings, kept as the append-only journal ``decision_memory_setting_event`` (migration ``0061``):

* ``data_class`` -- ``test`` or ``real``: what the cases captured FROM NOW ON are. The default, with nothing journalled, is ``test``
  (the safe direction: an export defaults to ``real`` only). A case already captured keeps its class (the column is immutable); this
  switch is not a reclassification of history. Flip it to ``real`` before the first real client document is decided, not after.
* ``training_use`` -- ``off`` or ``on``: whether the training export may run. The default is ``off`` (`Q3c`). ``on`` is a release of
  client-derived content off the host (`ADR-0022` section 4, `A-2`), so it needs ``--owner-permission-ref`` and the database refuses an
  ``on`` row without one.

The application only reads the journal. This operator tool writes it, as the table owner (the migrator), naming an ADMIN account: the
journal holds that account's ``usr_`` identity, never its login. Setting a value that is already in force records nothing.

USAGE (``DATABASE_URL`` is the owner role's; no ``PG*`` variable):

    python -m scripts.recovery.memory_setting --database D show
    python -m scripts.recovery.memory_setting --database D set data_class real --actor <admin login>
    python -m scripts.recovery.memory_setting --database D set training_use on --actor <admin login> \\
        --owner-permission-ref "<where the owner's permission is recorded>"

Exit codes: 0 done (or nothing to do), 2 usage, 3 REFUSED (nothing was changed), 4 FAILED.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Engine, text

from auditmanager.decision_memory.public import SETTING_DEFAULTS, SETTING_NAMES, SETTING_VALUES, MemoryReader
from auditmanager.shared.db.config import load_settings
from auditmanager.shared.db.engine import create_database_engine
from scripts.recovery import project_erase as erase
from scripts.recovery.schema_coverage import HEAD

EXIT_OK, EXIT_USAGE, EXIT_REFUSED, EXIT_FAILED = 0, 2, 3, 4
ADVISORY_LOCK_NAME = "auditmanager.memory_setting"
PERMISSION_REF_MAX = erase.PERMISSION_REF_MAX


class SettingRefused(Exception):
    """Nothing was changed, and the reason is in the message. Exit 3."""


def _no_ambient_libpq() -> None:
    ambient = sorted(name for name in os.environ if name.startswith("PG"))
    # >>> guard: no-ambient-libpq
    if ambient:
        raise SettingRefused(f"libpq environment variable(s) {ambient} can redirect the connection that DATABASE_URL names. "
                             "Unset them; DATABASE_URL is the only target. Nothing was touched.")
    # <<< guard: no-ambient-libpq


def check_arguments(args: argparse.Namespace) -> None:
    """The refusals that need no database."""
    if args.command != "set":
        return
    # >>> guard: value-in-list
    if args.name not in SETTING_NAMES or args.value not in SETTING_VALUES[args.name]:
        raise SettingRefused(f"{args.name} admits {list(SETTING_VALUES.get(args.name, ()))}; {args.value!r} is refused. "
                             "Nothing was touched.")
    # <<< guard: value-in-list
    reference = (args.owner_permission_ref or "").strip()
    # >>> guard: reference-shape
    if reference and (len(reference) > PERMISSION_REF_MAX or any(ord(ch) < 32 or ord(ch) == 127 for ch in reference)):
        raise SettingRefused(f"--owner-permission-ref must be one line of at most {PERMISSION_REF_MAX} characters. Nothing was touched.")
    # <<< guard: reference-shape
    # >>> guard: training-needs-permission
    if args.name == "training_use" and args.value == "on" and not reference:
        raise SettingRefused("training_use = on releases client-derived content off the host: --owner-permission-ref is required "
                             "(where the owner's permission is recorded; it is recorded, not verified). Nothing was touched.")
    # <<< guard: training-needs-permission


def _check_head(engine: Engine, database: str) -> None:
    with engine.connect() as connection:
        actual = str(connection.execute(text("SELECT current_database()")).scalar_one())
        head = str(connection.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one())
    # >>> guard: names-match
    if actual != database:
        raise SettingRefused(f"the typed name is not the connected database: {database!r} vs {actual!r}. Nothing was touched.")
    # <<< guard: names-match
    # >>> guard: head-is-declared
    if head != HEAD:
        raise SettingRefused(f"the database is at migration {head}, the tool was written for {HEAD}. Nothing was touched.")
    # <<< guard: head-is-declared


def show(engine: Engine, out: Any) -> None:
    with engine.connect() as connection:
        settings = MemoryReader().settings(connection)  # type: ignore[arg-type]
    for name, value, revision in (("data_class", settings.data_class, settings.data_class_revision),
                                  ("training_use", settings.training_use, settings.training_use_revision)):
        origin = "default" if revision == 0 else f"revision {revision}"
        print(f"{name}: {value} ({origin}; default {SETTING_DEFAULTS[name]})", file=out)


def apply_setting(engine: Engine, args: argparse.Namespace, out: Any) -> int:
    reference = (args.owner_permission_ref or "").strip() or None
    with engine.begin() as connection:
        try:
            actor = erase.resolve_actor(connection, args.actor)  # an active account that holds admin; its usr_ identity is journalled
        except erase.EraseRefused as error:
            raise SettingRefused(str(error).replace("erase a project", "change a setting")) from error
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:name, 0))"), {"name": ADVISORY_LOCK_NAME})
        row = connection.execute(text(
            "SELECT value, revision FROM public.decision_memory_setting_event WHERE setting_name = :name "
            "ORDER BY revision DESC LIMIT 1"), {"name": args.name}).one_or_none()
        current, revision = (SETTING_DEFAULTS[args.name], 0) if row is None else (str(row[0]), int(row[1]))
        if current == args.value:
            print(f"memory-setting: {args.name} is already {current}; nothing to do.", file=out)
            return EXIT_OK
        connection.execute(text(
            "INSERT INTO public.decision_memory_setting_event (setting_name, revision, value, actor_user_uid, owner_permission_ref) "
            "VALUES (:name, :revision, :value, :actor, :ref)"),
            {"name": args.name, "revision": revision + 1, "value": args.value, "actor": actor, "ref": reference})
    print(f"memory-setting: {args.name}: {current} -> {args.value} (revision {revision + 1}).", file=out)
    if args.name == "data_class":
        print("  Cases already captured keep the class they were captured with; the new value applies to the next capture.", file=out)
    return EXIT_OK


def run(argv: Sequence[str] | None = None, *, out: Any = None) -> int:
    out = out or sys.stdout
    parser = argparse.ArgumentParser(prog="memory_setting", description=__doc__.split("\n", 1)[0])
    parser.add_argument("--database", required=True, help="the typed name of the connected database")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("show", help="print the settings in force")
    change = commands.add_parser("set", help="journal a new value")
    change.add_argument("name", help=f"one of {', '.join(SETTING_NAMES)}")
    change.add_argument("value")
    change.add_argument("--actor", required=True, help="login of an active account that holds admin")
    change.add_argument("--owner-permission-ref", help="training_use on: where the owner's permission is recorded (one line)")
    args = parser.parse_args(argv)
    engine: Engine | None = None
    try:
        check_arguments(args)
        _no_ambient_libpq()
        engine = create_database_engine(load_settings())
        _check_head(engine, args.database)
        if args.command == "show":
            show(engine, out)
            return EXIT_OK
        return apply_setting(engine, args, out)
    except SettingRefused as error:
        print(f"memory_setting: REFUSED: {error}", file=sys.stderr)
        return EXIT_REFUSED
    except Exception as error:  # noqa: BLE001 - the operator needs a status, not a traceback
        print(f"memory_setting: FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        return EXIT_FAILED
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(run())
