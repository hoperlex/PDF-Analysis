"""Complete catalog inventory for invariants installed by a fresh migration.

The behavioural tests beside this file prove important consequences one by one.  D-87
showed the remaining hole: an edited migration can still be green when no test happens to
exercise the changed object, especially when a suite reads an already-migrated lane.  This
inventory is deliberately different.  Its fixture creates an empty database, applies the
current migration bytes, and only then reads every schema-bearing catalog family.

Each family is pinned by both member count and a digest over sorted, whitespace-normalised
definitions.  A missing object, a weakened CHECK, a changed trigger arm, a relaxed NULL rule,
an altered partial-index predicate, a rewritten function or view, and a changed state edge all
change at least one family.  The failure prints the complete observed inventory so a successor
migration can review the semantic delta before deliberately resealing it.

Not schema invariants, and therefore intentionally outside this inventory:

* repository query/aggregation semantics -- composition and repository tests own them;
* API/transport vocabulary and identity allocation -- contract and boundary tests own them;
* S3 addressing, object bytes and bucket policy -- the storage integration suite owns them;
* the randomly salted bootstrap credential -- ``test_app_user_migration.py`` verifies its
  behaviour without pretending random bytes can be a catalog constant.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable

from sqlalchemy import Engine, text


#: Resealed by `W52-SEAL-01` for ``0016_release_notes``. The 0015 inventory below gained
#: fourteen columns in three tables, four relations (three tables and one identity
#: sequence), fourteen constraints, six indexes, three triggers and two functions.
#: Views, extensions, policies and state topology are unchanged. The previous
#: `W49-ACCESS-01a` review for ``0015_accounts_roles_registration`` found the delta was
#: reviewed family by family against the migration (columns +29: six on ``app_user``,
#: four on ``app_user_role``, eighteen on ``registration_request``, one on
#: ``expert_decision_event``; relations +2; constraints +33 -- +8 and -1 (the UNIQUE
#: constraint ``uq_app_user_login`` became a partial unique index) on ``app_user``, +6, +18
#: and +2 on the others; indexes +11;
#: triggers +1; functions +1 -- ``am_guard_registration_request``). Views, extensions,
#: sequences, policies and the state topology are unchanged: ``0015`` adds no machine to
#: ``contract_state_transition`` (the seal adds ``app_user`` and ``registration_request``
#: to ``state-machines.json``; the registration lifecycle is guarded by its own trigger).
EXPECTED_INVENTORY: dict[str, tuple[int, str]] = {
    "columns": (348, "64e793b7997d8aa5d5355e3f59a93d084207517c43b895e9a489e23cd55045bc"),
    "relations": (43, "c6b6ae6de7689280d2c30a3ec65a445b04bbbe59f11b813957ed719abe4d7b7d"),
    "constraints": (378, "6f708e38a5691b29ecd3d1162bd790af5f45fa813f86a03b089a9f5ea35b86c6"),
    "indexes": (93, "c85e0294447c2989af3e7966e7e8040680537893971229306426d1bc54e9e27a"),
    "triggers": (35, "8b5c558507c0adf51db43012d2f767cada400f7f51fd8f561b36e73a8b5b609f"),
    "functions": (10, "2ee97345179abc7b397b6559b49d92dc71e35c0638ab61a916a80797f38252db"),
    "views": (1, "099049415234da3d04583c58a693a68fda934f77e9eaf00b0d12e2542842734d"),
    "extensions": (1, "81a067095db43b64056597402d99e045d6deba0c83f1a535889dda45ec7fefb1"),
    "sequences": (7, "6d533fe16349a92b16b5ca89d51fcb083f1ecdf4f252bc276667a92361bf1656"),
    "policies": (0, "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"),
    "state_topology": (51, "776830836156e8f9f890ee698a2a7ae02bd98a0cc33cbf6b628ce795b2201ce4"),
}


def _normalise(value: object) -> str:
    if value is None:
        return "<NULL>"
    return re.sub(r"\s+", " ", str(value)).strip()


def _fingerprint(rows: Iterable[object]) -> tuple[int, str]:
    serialised = sorted(
        tuple(_normalise(value) for value in row)
        for row in rows
    )
    payload = json.dumps(serialised, ensure_ascii=True, separators=(",", ":"))
    return len(serialised), hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _inventory(engine: Engine) -> dict[str, tuple[int, str]]:
    queries = {
        "columns": """
            SELECT table_name, column_name, ordinal_position, data_type, udt_schema,
                   udt_name, is_nullable, column_default, is_identity,
                   identity_generation, is_generated, generation_expression,
                   character_maximum_length, numeric_precision, numeric_scale,
                   datetime_precision, collation_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """,
        "relations": """
            SELECT c.relname, c.relkind, c.relpersistence, c.relrowsecurity,
                   c.relforcerowsecurity
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind IN ('r', 'p', 'v', 'm', 'S')
            ORDER BY c.relkind, c.relname
        """,
        "constraints": """
            SELECT t.relname, c.conname, c.contype, pg_get_constraintdef(c.oid, true)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public'
            ORDER BY t.relname, c.conname
        """,
        "indexes": """
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """,
        "triggers": """
            SELECT c.relname, t.tgname, t.tgenabled, pg_get_triggerdef(t.oid, true)
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND NOT t.tgisinternal
            ORDER BY c.relname, t.tgname
        """,
        "functions": """
            SELECT p.proname, pg_get_function_identity_arguments(p.oid),
                   pg_get_functiondef(p.oid)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public'
              AND NOT EXISTS (
                  SELECT 1
                  FROM pg_depend d
                  WHERE d.classid = 'pg_proc'::regclass
                    AND d.objid = p.oid
                    AND d.deptype = 'e'
              )
            ORDER BY p.proname, pg_get_function_identity_arguments(p.oid)
        """,
        "views": """
            SELECT c.relname, pg_get_viewdef(c.oid, true)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'v'
            ORDER BY c.relname
        """,
        "extensions": """
            SELECT e.extname, e.extversion
            FROM pg_extension e
            WHERE e.extname <> 'plpgsql'
            ORDER BY e.extname
        """,
        "sequences": """
            SELECT c.relname, s.seqtypid::regtype::text, s.seqstart, s.seqincrement,
                   s.seqmax, s.seqmin, s.seqcache, s.seqcycle
            FROM pg_sequence s
            JOIN pg_class c ON c.oid = s.seqrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
            ORDER BY c.relname
        """,
        "policies": """
            SELECT tablename, policyname, permissive, roles::text, cmd, qual, with_check
            FROM pg_policies
            WHERE schemaname = 'public'
            ORDER BY tablename, policyname
        """,
        "state_topology": """
            SELECT machine, from_state, to_state
            FROM contract_state_transition
            ORDER BY machine, from_state NULLS FIRST, to_state
        """,
    }
    with engine.connect() as connection:
        return {
            family: _fingerprint(connection.execute(text(query)).all())
            for family, query in queries.items()
        }


def test_every_migration_invariant_family_matches_the_reviewed_fresh_database(
    migrated_engine: Engine,
) -> None:
    observed = _inventory(migrated_engine)
    assert observed == EXPECTED_INVENTORY, (
        "fresh-migration invariant inventory changed; review every changed catalog family "
        f"before resealing EXPECTED_INVENTORY. Observed: {observed!r}"
    )


def test_no_fresh_check_constraint_is_a_tautology(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        tautologies = connection.execute(
            text(
                "SELECT t.relname, c.conname, pg_get_constraintdef(c.oid, true) "
                "FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN pg_namespace n ON n.oid = t.relnamespace "
                "WHERE n.nspname = 'public' AND c.contype = 'c' "
                "AND lower(regexp_replace(pg_get_constraintdef(c.oid, true), "
                "'\\s+', '', 'g')) IN ('check(true)', 'check((true))')"
            )
        ).all()
    assert tautologies == [], f"tautological CHECK constraints: {tautologies!r}"
