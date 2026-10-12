"""The copy record the importer runs under, its acceptance rule and the stand fingerprint.

The record is ``<STAND_COPY_DIR>/record.json``, written only by the copy key's
``copy-serve.sh`` (`W54-STAND-COPY-01` §3.2) and mounted read-only into the importer's
container at ``/run/copy-record.json``. This module reads it as ordinary JSON and never
writes it.

**The acceptance rule** (`W54-FREEZE-01` amendment 2; `W54-STAND-COPY-01` §3.8, adopted
here). An import is accepted under exactly

* ``kind "copy"``: ``record_version 1``, ``state "open"``, ``purpose "import"``, an
  attestation whose ``dump_sha256`` is the dump's, ``now ≤ quiesced_at + 12 h``; or
* ``kind "test_data_waiver"``: ``record_version 1``, ``state "open"``, ``purpose "import"``,
  a waiver with ``now ≤ expires_at``, ``real_data_marker false``, no dump and no
  attestation;

and in both cases every writer present is recorded stopped, the record's migration head is
the database's, and the fingerprint recomputed now equals the record's. Anything else is
refused: a missing or unreadable record, another version, a closed (stale) record, one the
stand migrated past, an unattested copy, an expired copy or waiver, a waiver once the
``real_data`` marker is set, a drifted fingerprint. The marker *file* beside the record is
not visible in the container; the inbound key's ``waiver-before-real-data`` guard checks it
(`receive-bundle.sh`), and this rule checks the record's field.

**The fingerprint**, ``stand-fingerprint-v1``, is :data:`FINGERPRINT_SCRIPT`: byte for byte
the block ``copy-serve.sh`` keeps between ``-- >>> stand-fingerprint-v1`` and
``-- <<< stand-fingerprint-v1`` (``test_copy_record.py`` compares the two). The api image
carries ``src/`` but not ``infra/``, so the text travels here; one SQL text, two carriers,
one test that fails when they differ. :func:`compute_fingerprint` runs the same statements
the same way: the session settings, one ``REPEATABLE READ READ ONLY`` transaction, the
generating query, then each statement it generates.

**An import alone leaves the fingerprint unchanged.** Every row the importer writes is in a
``norm*`` table, an ``audit_event`` of type ``norm_custody.*``, or a ``blob`` row a
``norm_custody_admission`` names -- the three exclusions of the fingerprint. The importer
writes no other table (no ``job``, no ``command_record``, no other event type).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

from sqlalchemy import Engine, text

from .errors import BundleRefused

RECORD_VERSION: Final[int] = 1
FINGERPRINT_ALGORITHM: Final[str] = "stand-fingerprint-v1"
#: `W54-PLAN.md` §3.5: an attested copy admits an import for at most 12 h after quiesce.
IMPORT_WINDOW: Final[timedelta] = timedelta(seconds=43200)
WRITERS: Final[frozenset[str]] = frozenset({"web", "api", "worker"})

#: Verbatim from ``infra/deploy/copy-serve.sh`` (``fingerprint_sql``), markers included.
FINGERPRINT_SCRIPT: Final[str] = r"""-- >>> stand-fingerprint-v1
SET TimeZone = 'UTC';
SET DateStyle = 'ISO, YMD';
SET IntervalStyle = 'postgres';
SET extra_float_digits = 1;
SET bytea_output = 'hex';
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT format(
    'SELECT %L || ''|'' || count(*) || ''|'' || encode(sha256(convert_to(coalesce(string_agg(r.t, E''\n'' ORDER BY r.t COLLATE "C"), ''''), ''UTF8'')), ''hex'') FROM (SELECT x::text AS t FROM %I AS x %s) AS r',
    c.relname,
    c.relname,
    CASE
        WHEN c.relname = 'audit_event' THEN 'WHERE x.event_type NOT LIKE ''norm\_custody.%'''
        WHEN c.relname = 'command_record' THEN 'WHERE x.command_type NOT LIKE ''norm\_custody.%'''
        WHEN c.relname = 'blob' AND to_regclass('norm_custody_admission') IS NOT NULL
            THEN 'WHERE NOT EXISTS (SELECT 1 FROM norm_custody_admission AS a WHERE a.blob_id = x.blob_id)'
        ELSE ''
    END)
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = current_schema()
  AND c.relkind IN ('r', 'p')
  AND NOT c.relispartition
  AND c.relname NOT LIKE 'norm%'
ORDER BY c.relname COLLATE "C"
\gexec
COMMIT;
-- <<< stand-fingerprint-v1
"""

_SET = re.compile(r"^SET ([A-Za-z_]+) = (.+);$")
_LINE = re.compile(r"^([a-z_][a-z0-9_]*)\|(0|[1-9][0-9]*)\|([0-9a-f]{64})$")


def _script_parts() -> tuple[tuple[str, ...], str]:
    """The ``SET`` statements and the generating query, cut from :data:`FINGERPRINT_SCRIPT`."""
    lines = FINGERPRINT_SCRIPT.splitlines()
    settings = tuple(line for line in lines if _SET.match(line))
    start = next(index for index, line in enumerate(lines) if line.startswith("SELECT format("))
    end = lines.index("\\gexec")
    return settings, "\n".join(lines[start:end])


@dataclass(frozen=True, slots=True)
class TableFingerprint:
    rows: int
    sha256: str


@dataclass(frozen=True, slots=True)
class StandFingerprint:
    """``<table>|<rows>|<sha256>`` per client table, and the SHA-256 of those lines."""

    tables: Mapping[str, TableFingerprint]
    sha256: str

    @classmethod
    def from_lines(cls, lines: Sequence[str]) -> StandFingerprint:
        tables: dict[str, TableFingerprint] = {}
        previous = None
        for line in lines:
            match = _LINE.fullmatch(line)
            if match is None:
                raise BundleRefused("fingerprint_unreadable", f"fingerprint line {line[:80]!r}")
            name = match.group(1)
            if previous is not None and not name > previous:
                raise BundleRefused("fingerprint_unreadable", "fingerprint tables out of order")
            previous = name
            tables[name] = TableFingerprint(rows=int(match.group(2)), sha256=match.group(3))
        if not tables:
            raise BundleRefused("fingerprint_unreadable", "the fingerprint names no table")
        digest = hashlib.sha256("".join(f"{line}\n" for line in lines).encode("ascii")).hexdigest()
        return cls(tables=tables, sha256=digest)


def compute_fingerprint(engine: Engine) -> StandFingerprint:
    """The stand fingerprint now, computed exactly as ``copy-serve.sh`` computes it."""
    settings, generator = _script_parts()
    with engine.connect() as connection:
        connection = connection.execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True
        )
        with connection.begin():
            for setting in settings:
                connection.execute(text("SET LOCAL " + setting[len("SET "):].rstrip(";")))
            statements = [str(row[0]) for row in connection.execute(text(generator))]
            lines = [str(connection.execute(text(statement)).scalar_one()) for statement in statements]
    return StandFingerprint.from_lines(lines)


# --- the record -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CopyRecord:
    raw: Mapping[str, Any]

    def get(self, key: str) -> Any:
        return self.raw.get(key)

    @property
    def kind(self) -> Any:
        return self.raw.get("kind")

    @property
    def stamp(self) -> str:
        return str(self.raw.get("stamp"))

    @property
    def fingerprint_sha256(self) -> Any:
        fingerprint = self.raw.get("fingerprint")
        return fingerprint.get("sha256") if isinstance(fingerprint, dict) else None

    def fingerprint_tables(self) -> dict[str, TableFingerprint]:
        fingerprint = self.raw.get("fingerprint")
        tables = fingerprint.get("tables") if isinstance(fingerprint, dict) else None
        found: dict[str, TableFingerprint] = {}
        for name, value in (tables or {}).items():
            if isinstance(value, dict):
                found[str(name)] = TableFingerprint(rows=value.get("rows"), sha256=value.get("sha256"))
        return found


def read_copy_record(path: Path | None) -> CopyRecord:
    """The record as JSON, or a refusal: absent, unreadable, or not ``record_version 1``."""
    if path is None or not path.exists():
        raise BundleRefused(
            "copy_record_absent",
            "there is no copy record: open a copy (R-88) or, while the stand holds only test "
            "data, a test-data waiver (R-110) with the copy key first",
        )
    if path.is_dir() or not path.is_file():
        # `D-37`: a bind mount of a missing source arrives as an empty directory.
        raise BundleRefused("copy_record_absent", f"{path} is not a copy record file")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundleRefused("copy_record_unreadable", f"the copy record is not JSON: {exc}") from None
    if not isinstance(document, dict):
        raise BundleRefused("copy_record_unreadable", "the copy record is not a JSON object")
    if document.get("record_version") != RECORD_VERSION or isinstance(document.get("record_version"), bool):
        raise BundleRefused(
            "copy_record_version",
            f"record_version {document.get('record_version')!r} is not {RECORD_VERSION}",
        )
    return CopyRecord(raw=document)


def parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise BundleRefused("copy_record_unreadable", f"{field} {value!r} is not a UTC time")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class AcceptedRecord:
    """What admitted the import, for the log: which kind, its stamp, until when."""

    kind: str
    stamp: str
    valid_until: datetime
    fingerprint_sha256: str


def check_record_shape(record: CopyRecord, *, now: datetime) -> datetime:
    """Every rule that needs no database. Returns the end of the record's window."""
    kind = record.kind
    if kind not in ("copy", "test_data_waiver"):
        raise BundleRefused("copy_record_unreadable", f"kind {kind!r} is neither copy nor test_data_waiver")
    if record.get("state") != "open":
        raise BundleRefused(
            "copy_record_closed",
            f"the copy record {record.stamp} is {record.get('state')!r}: it is stale. Open a new "
            "copy or waiver with the copy key",
        )
    if record.get("purpose") != "import":
        raise BundleRefused(
            "copy_record_not_import",
            f"the open record {record.stamp} has purpose {record.get('purpose')!r}, not import",
        )
    present = record.get("writers_present")
    stopped = record.get("writers_stopped")
    if (
        not isinstance(present, list)
        or not isinstance(stopped, list)
        or not set(present) <= WRITERS
        or not set(present) <= set(stopped)
    ):
        raise BundleRefused(
            "copy_record_not_quiesced",
            f"the record lists writers {present!r} and stopped {stopped!r}: it does not say the "
            "database was quiesced",
        )
    if record.get("quiesced_at") is None:
        raise BundleRefused("copy_record_not_quiesced", "the record carries no quiesced_at")
    if kind == "copy":
        attestation = record.get("attestation")
        dump = record.get("dump")
        if not isinstance(attestation, dict):
            raise BundleRefused(
                "copy_record_unattested",
                f"the copy {record.stamp} is not attested: attest binds the dump and the "
                "restore report to it first",
            )
        if not isinstance(dump, dict) or attestation.get("dump_sha256") != dump.get("sha256"):
            raise BundleRefused(
                "copy_record_unattested",
                f"the copy {record.stamp}'s attestation does not name its dump's SHA-256",
            )
        until = parse_utc(record.get("quiesced_at"), "quiesced_at") + IMPORT_WINDOW
    else:
        if record.get("real_data_marker") is not False:
            raise BundleRefused(
                "waiver_after_real_data",
                "a test_data_waiver is refused once the real_data marker is set: R-88 and R-93 "
                "apply in full from the first full copy (W54-FREEZE-01 amendment 2)",
            )
        waiver = record.get("waiver")
        if not isinstance(waiver, dict):
            raise BundleRefused("copy_record_unattested", f"the waiver {record.stamp} carries no statement")
        if record.get("dump") is not None or record.get("attestation") is not None:
            raise BundleRefused(
                "copy_record_unreadable", "a test_data_waiver carries a dump or an attestation"
            )
        until = parse_utc(waiver.get("expires_at"), "waiver.expires_at")
    if now > until:
        raise BundleRefused(
            "copy_record_expired",
            f"the {kind} {record.stamp} admitted an import until {until:%Y-%m-%dT%H:%M:%SZ}; "
            "resume it with the copy key and open a new one",
        )
    fingerprint = record.get("fingerprint")
    if not isinstance(fingerprint, dict) or fingerprint.get("algorithm") != FINGERPRINT_ALGORITHM:
        raise BundleRefused(
            "copy_record_unreadable", f"the record's fingerprint is not {FINGERPRINT_ALGORITHM}"
        )
    return until


def accept_for_import(
    record: CopyRecord,
    *,
    now: datetime,
    database_head: str | None,
    fingerprint: StandFingerprint,
) -> AcceptedRecord:
    """The importer's acceptance rule. Refuses unless the record admits this import now."""
    until = check_record_shape(record, now=now)
    if record.get("migration_head") != database_head:
        raise BundleRefused(
            "copy_record_stale",
            f"the record was taken at migration {record.get('migration_head')!r}; the database is "
            f"at {database_head!r}. Open a new copy or waiver",
        )
    if fingerprint.sha256 != record.fingerprint_sha256:
        drifted = sorted(
            name
            for name in set(fingerprint.tables) | set(record.fingerprint_tables())
            if fingerprint.tables.get(name) != record.fingerprint_tables().get(name)
        )
        raise BundleRefused(
            "fingerprint_drifted",
            f"the stand's client tables changed since the record {record.stamp} was taken "
            f"(fingerprint {fingerprint.sha256}, record {record.fingerprint_sha256}; tables "
            f"{drifted[:5]!r}). Something wrote while the writers were meant to be stopped",
        )
    return AcceptedRecord(
        kind=str(record.kind),
        stamp=record.stamp,
        valid_until=until,
        fingerprint_sha256=fingerprint.sha256,
    )


__all__ = [
    "FINGERPRINT_ALGORITHM",
    "FINGERPRINT_SCRIPT",
    "IMPORT_WINDOW",
    "RECORD_VERSION",
    "AcceptedRecord",
    "CopyRecord",
    "StandFingerprint",
    "TableFingerprint",
    "accept_for_import",
    "check_record_shape",
    "compute_fingerprint",
    "parse_utc",
    "read_copy_record",
]
