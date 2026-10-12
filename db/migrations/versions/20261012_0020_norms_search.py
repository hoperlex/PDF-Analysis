"""The current norms snapshot, its history, and text search over canonical paragraphs.

Revision ID: 0020_norms_search
Revises: 0019_execution_workers

`W55A-SEAL-01` (`W55-PLAN.md` sections A3.2 and A3.4; owner rulings R-112 and R-113).

* ``norm_current_snapshot`` is one row: the snapshot every new run and re-audit pins and the
  scope of text search. There is no unset -- a wrong current snapshot is replaced by another
  qualifying one -- so DELETE is refused. Every INSERT or UPDATE must name its **own** fresh
  ``norm_current_snapshot_event`` whose ``from`` is the previous current snapshot (NULL for
  the first designation) and whose ``to`` is the new one: a change without a history row is
  refused by the database, not merely by the application.
* ``norm_current_snapshot_event`` is the append-only history: actor (``usr_``), from, to and
  time. UPDATE and DELETE are refused (``am_immutable_row``). Its identity is an
  ``audit_event_id`` (``evt_``): a designation is an appended audit event, and the domain
  catalog already declares that identity, so none is added. ``to_snapshot_id`` is indexed
  because search accepts an explicit snapshot only if it has been current at least once.

The history is **strict** (`W55A-FIX`; JUDGE-X M4, JUDGE-Y Y-3), so that "has been current"
and the order of the listing can be trusted against direct SQL too:

* *an event is current when its transaction commits*: a deferred constraint trigger on
  INSERT requires ``norm_current_snapshot.event_id`` to name the inserted event at COMMIT. An
  event inserted without moving the current row -- which would make a never-current snapshot
  searchable by explicit scope -- is refused, and so is a second designation in one
  transaction (its first event is no longer current at COMMIT);
* *the current row names the newest event*: the guard requires ``NEW.event_id`` to be first
  in the listing's order (``changed_at``, then ``event_id`` under ``"C"``, descending). Since
  every event was current when it committed and only a newer event can displace it, an older
  event has been referenced by an earlier change; reusing one -- ``A -> B`` again after
  ``B -> A`` -- is refused. The newest event itself is named only by the row it would replace,
  which the guard already refuses (``NEW.event_id = OLD.event_id``);
* *the time is the database's*: a BEFORE INSERT trigger sets ``changed_at`` to
  ``clock_timestamp()`` -- the column's own default -- whatever the INSERT named, so an event
  cannot be backdated below, or post-dated above, the history it joins. Not ``now()``: under
  the setter's advisory lock a designation may begin before the one it waits for commits,
  and its transaction-start time would then sort it below its predecessor;
* *TRUNCATE is refused* on both tables (BEFORE TRUNCATE, statement level), including a
  TRUNCATE that reaches them by CASCADE from ``norms_snapshot``: row triggers do not fire on
  TRUNCATE, so without this the history could be erased whole. A suite that owns a throwaway
  database resets it by the owner's ``ALTER TABLE ... DISABLE TRIGGER`` around its TRUNCATE,
  which no DML can do.
* ``norm_designation_tokens(text)`` is an ``IMMUTABLE`` SQL function: the slug before
  ``__``, case and Latin/Cyrillic homoglyphs folded by explicit ``translate`` tables (never
  ``lower()``, whose result depends on the database's ``lc_ctype``), split on ``[ ._-]``,
  empty tokens dropped. ``norm_document.designation_tokens`` is generated from it, and a
  query's designation goes through the same function, so the two cannot disagree.
* ``norm_paragraph.text_tsv`` is ``to_tsvector('russian', text)``, generated and stored, with
  a GIN index restricted to reliable paragraphs: an unreliable paragraph is never found.
  ``ix_norm_paragraph_clause`` serves the dotted-segment clause prefix the same way.

Generated columns are never written by the importer and are not in W54's canonical row
digest, which covers declared columns only. Adding them rewrites both tables but fires no
row trigger, so the immutability triggers of ``0012`` are not engaged.

A populated 0020 is not downgraded: a current snapshot or any history row refuses it, and a
database backup is restored instead. The generated columns are derived data and are dropped.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from alembic import op
from sqlalchemy import text

revision: str = "0020_norms_search"
down_revision: str | None = "0019_execution_workers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ULID_BODY = "[0-9A-HJKMNP-TV-Z]{26}"

# --- the designation fold --------------------------------------------------------------
#
# Written out character by character, so the fold is a property of this file and not of the
# server's locale. ``lower()`` folds by ``lc_ctype``: under ``C`` it leaves Cyrillic
# untouched, so ``ГОСТ`` and ``гост`` would be two keys on one server and one on another.

_CYRILLIC_UPPER: Final[str] = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
_CYRILLIC_LOWER: Final[str] = "абвгдеежзийклмнопрстуфхцчшщъыьэюя"
#: ``ё`` folds to ``е`` as its capital does; every other lower-case Cyrillic letter is its
#: own fold and is not listed.
_CYRILLIC_YO: Final[tuple[str, str]] = ("ё", "е")

#: Latin letters that are visually a Cyrillic letter in either case, and that letter. Both
#: cases of the Latin letter fold to the Cyrillic lower case, so ``CП``, ``Cп`` and ``СП``
#: are one designation and the fold stays case-insensitive.
_HOMOGLYPHS: Final[tuple[tuple[str, str], ...]] = (
    ("A", "а"), ("a", "а"),
    ("B", "в"), ("b", "в"),
    ("C", "с"), ("c", "с"),
    ("E", "е"), ("e", "е"),
    ("H", "н"), ("h", "н"),
    ("K", "к"), ("k", "к"),
    ("M", "м"), ("m", "м"),
    ("O", "о"), ("o", "о"),
    ("P", "р"), ("p", "р"),
    ("T", "т"), ("t", "т"),
    ("X", "х"), ("x", "х"),
    ("Y", "у"), ("y", "у"),
)

#: Every other Latin capital, to its own lower case.
_LATIN_REST_UPPER: Final[str] = "DFGIJLNQRSUVWZ"


def _fold_tables() -> tuple[str, str]:
    source = _CYRILLIC_UPPER + _CYRILLIC_YO[0] + _LATIN_REST_UPPER
    target = _CYRILLIC_LOWER + _CYRILLIC_YO[1] + _LATIN_REST_UPPER.lower()
    for latin, cyrillic in _HOMOGLYPHS:
        source += latin
        target += cyrillic
    if len(source) != len(target) or len(set(source)) != len(source):
        raise RuntimeError("the designation fold tables are not a one-to-one character map")
    return source, target


FOLD_FROM, FOLD_TO = _fold_tables()

#: The designation is the slug before ``__``; tokens are separated by space, dot,
#: underscore or hyphen, and a run of separators yields no empty token.
DESIGNATION_TOKENS_SQL: Final[str] = f"""
CREATE FUNCTION norm_designation_tokens(value text) RETURNS text[]
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
RETURN array_remove(
    regexp_split_to_array(
        translate(split_part(value, '__', 1), '{FOLD_FROM}', '{FOLD_TO}'),
        '[ ._-]+'
    ),
    ''
);
"""


def upgrade() -> None:
    _current_snapshot()
    _designation_key()
    _text_search()


def _current_snapshot() -> None:
    op.execute(
        f"""
        CREATE TABLE norm_current_snapshot_event (
            event_id         text PRIMARY KEY,
            from_snapshot_id text NULL REFERENCES norms_snapshot (norms_snapshot_id),
            to_snapshot_id   text NOT NULL REFERENCES norms_snapshot (norms_snapshot_id),
            actor_user_uid   text NOT NULL,
            changed_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
            CONSTRAINT ck_norm_current_snapshot_event_id_format
                CHECK (event_id ~ '^evt_{ULID_BODY}$'),
            CONSTRAINT ck_norm_current_snapshot_event_from_format
                CHECK (from_snapshot_id IS NULL OR from_snapshot_id ~ '^ns_{ULID_BODY}$'),
            CONSTRAINT ck_norm_current_snapshot_event_to_format
                CHECK (to_snapshot_id ~ '^ns_{ULID_BODY}$'),
            CONSTRAINT ck_norm_current_snapshot_event_actor_format
                CHECK (actor_user_uid ~ '^usr_{ULID_BODY}$'),
            CONSTRAINT ck_norm_current_snapshot_event_changes
                CHECK (from_snapshot_id IS DISTINCT FROM to_snapshot_id)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_norm_current_snapshot_event_changed "
        "ON norm_current_snapshot_event (changed_at DESC, event_id DESC)"
    )
    op.execute(
        "CREATE INDEX ix_norm_current_snapshot_event_to "
        "ON norm_current_snapshot_event (to_snapshot_id)"
    )
    op.execute(
        "CREATE TRIGGER trg_norm_current_snapshot_event_immutable "
        "BEFORE UPDATE OR DELETE ON norm_current_snapshot_event "
        "FOR EACH ROW EXECUTE FUNCTION am_immutable_row()"
    )
    op.execute(
        "COMMENT ON TABLE norm_current_snapshot_event IS "
        "'R-113 append-only history of the current norms snapshot: who designated which "
        "snapshot over which, and when. actor_user_uid is history, not an account reference: "
        "it carries no foreign key, so purging an account never rewrites this record.';"
    )

    op.execute(
        f"""
        CREATE TABLE norm_current_snapshot (
            singleton         boolean PRIMARY KEY DEFAULT true,
            norms_snapshot_id text NOT NULL REFERENCES norms_snapshot (norms_snapshot_id),
            event_id          text NOT NULL
                REFERENCES norm_current_snapshot_event (event_id),
            CONSTRAINT ck_norm_current_snapshot_singleton CHECK (singleton),
            CONSTRAINT ck_norm_current_snapshot_snapshot_id_format
                CHECK (norms_snapshot_id ~ '^ns_{ULID_BODY}$'),
            CONSTRAINT ck_norm_current_snapshot_event_ref_format
                CHECK (event_id ~ '^evt_{ULID_BODY}$'),
            CONSTRAINT uq_norm_current_snapshot_event UNIQUE (event_id)
        );
        """
    )
    op.execute(
        """
        CREATE FUNCTION am_guard_norm_current_snapshot() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        DECLARE
            expected_from text;
            event_from text;
            event_to text;
            event_at timestamptz;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the current norms snapshot has no unset'
                    USING ERRCODE = 'AM003',
                          HINT = 'Designate another qualifying snapshot instead.';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                expected_from := OLD.norms_snapshot_id;
                IF NEW.event_id = OLD.event_id THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: a change of the current norms snapshot must name its own history event'
                        USING ERRCODE = 'AM003';
                END IF;
            ELSE
                expected_from := NULL;
            END IF;
            SELECT from_snapshot_id, to_snapshot_id, changed_at
              INTO event_from, event_to, event_at
              FROM norm_current_snapshot_event WHERE event_id = NEW.event_id;
            IF NOT FOUND
               OR event_to IS DISTINCT FROM NEW.norms_snapshot_id
               OR event_from IS DISTINCT FROM expected_from THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: the history event does not record this change of the current norms snapshot'
                    USING ERRCODE = 'AM003';
            END IF;
            IF EXISTS (
                SELECT 1 FROM norm_current_snapshot_event later
                 WHERE (later.changed_at, later.event_id COLLATE "C")
                       > (event_at, NEW.event_id COLLATE "C")
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: a change of the current norms snapshot must name the newest history event'
                    USING ERRCODE = 'AM003',
                          HINT = 'An older event was already used by an earlier change; append a new one.';
            END IF;
            RETURN NEW;
        END
        $fn$;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_norm_current_snapshot_guard "
        "BEFORE INSERT OR UPDATE OR DELETE ON norm_current_snapshot "
        "FOR EACH ROW EXECUTE FUNCTION am_guard_norm_current_snapshot()"
    )
    op.execute(
        "COMMENT ON TABLE norm_current_snapshot IS "
        "'R-113 the one current norms snapshot (G-6): what new runs and re-audits pin and "
        "what text search reads. Never deleted; every change names its own history event.';"
    )
    _strict_history()


def _strict_history() -> None:
    """`W55A-FIX`: the time, the commit-time check and the TRUNCATE refusals (docstring)."""
    op.execute(
        """
        CREATE FUNCTION am_stamp_norm_current_snapshot_event() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            NEW.changed_at := clock_timestamp();
            RETURN NEW;
        END
        $fn$;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_norm_current_snapshot_event_stamp "
        "BEFORE INSERT ON norm_current_snapshot_event "
        "FOR EACH ROW EXECUTE FUNCTION am_stamp_norm_current_snapshot_event()"
    )
    op.execute(
        """
        CREATE FUNCTION am_require_current_norm_snapshot_event() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM norm_current_snapshot
                 WHERE singleton AND event_id = NEW.event_id
            ) THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: a history event of the current norms snapshot must be the current designation when its transaction commits'
                    USING ERRCODE = 'AM003',
                          HINT = 'Insert the event and move the current row to it in one transaction, one designation per transaction.';
            END IF;
            RETURN NULL;
        END
        $fn$;
        """
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_norm_current_snapshot_event_designates "
        "AFTER INSERT ON norm_current_snapshot_event "
        "DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION am_require_current_norm_snapshot_event()"
    )
    op.execute(
        """
        CREATE FUNCTION am_refuse_norm_current_snapshot_truncate() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            RAISE EXCEPTION
                'state_transition_not_allowed: % is not truncated; the current norms snapshot has no unset and its history is append-only',
                TG_TABLE_NAME
                USING ERRCODE = 'AM003';
        END
        $fn$;
        """
    )
    for table in ("norm_current_snapshot", "norm_current_snapshot_event"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_no_truncate BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION am_refuse_norm_current_snapshot_truncate()"
        )


def _designation_key() -> None:
    op.execute(DESIGNATION_TOKENS_SQL)
    op.execute(
        "COMMENT ON FUNCTION norm_designation_tokens(text) IS "
        "'G-5 designation key: the slug before __, folded by explicit translate tables (never "
        "lower(), which depends on lc_ctype), split on [ ._-]. A query designation goes "
        "through the same function and matches the leading tokens.';"
    )
    op.execute(
        "ALTER TABLE norm_document ADD COLUMN designation_tokens text[] "
        "GENERATED ALWAYS AS (norm_designation_tokens(slug)) STORED"
    )
    op.execute(
        "CREATE INDEX ix_norm_document_designation_tokens "
        "ON norm_document USING gin (designation_tokens)"
    )


def _text_search() -> None:
    op.execute(
        "ALTER TABLE norm_paragraph ADD COLUMN text_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('russian'::regconfig, text)) STORED"
    )
    op.execute(
        "CREATE INDEX ix_norm_paragraph_text_tsv ON norm_paragraph USING gin (text_tsv) "
        "WHERE text_reliability = 'reliable'"
    )
    op.execute(
        "CREATE INDEX ix_norm_paragraph_clause "
        "ON norm_paragraph (norms_snapshot_id, clause_number text_pattern_ops) "
        "WHERE text_reliability = 'reliable' AND clause_number IS NOT NULL"
    )
    op.execute(
        "COMMENT ON COLUMN norm_paragraph.text_tsv IS "
        "'G-5 generated Russian text-search vector of the canonical text. Never written by the "
        "importer and outside the canonical row digest; indexed for reliable rows only.';"
    )


# --- downgrade ----------------------------------------------------------------------------

_RETAINED_DATA: Final[tuple[tuple[str, str], ...]] = (
    ("norm_current_snapshot", "SELECT EXISTS (SELECT 1 FROM norm_current_snapshot)"),
    ("norm_current_snapshot_event", "SELECT EXISTS (SELECT 1 FROM norm_current_snapshot_event)"),
)


def downgrade() -> None:
    bind = op.get_bind()
    retained = [name for name, probe in _RETAINED_DATA if bind.execute(text(probe)).scalar_one()]
    if retained:
        raise RuntimeError(
            "refusing to downgrade 0020_norms_search with a retained current snapshot or "
            f"history ({', '.join(retained)}); restore a database backup instead"
        )
    op.execute("DROP INDEX ix_norm_paragraph_clause")
    op.execute("DROP INDEX ix_norm_paragraph_text_tsv")
    op.execute("ALTER TABLE norm_paragraph DROP COLUMN text_tsv")
    op.execute("DROP INDEX ix_norm_document_designation_tokens")
    op.execute("ALTER TABLE norm_document DROP COLUMN designation_tokens")
    op.execute("DROP FUNCTION norm_designation_tokens(text)")
    op.execute("DROP TABLE norm_current_snapshot")
    op.execute("DROP FUNCTION am_guard_norm_current_snapshot()")
    op.execute("DROP TABLE norm_current_snapshot_event")
    op.execute("DROP FUNCTION am_refuse_norm_current_snapshot_truncate()")
    op.execute("DROP FUNCTION am_require_current_norm_snapshot_event()")
    op.execute("DROP FUNCTION am_stamp_norm_current_snapshot_event()")
