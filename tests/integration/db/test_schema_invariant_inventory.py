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


EXPECTED_INVENTORY: dict[str, tuple[int, str]] = {
    "columns": (256, "8a8c2428930d576d8eb53a595a613e225d6076f7f07c3bd7b92990910a21352a"),
    "relations": (32, "42200df23c4d57b95ae7e0e58a0ffb31e07548550217e2b00c8981394c709ca0"),
    "constraints": (261, "279d9208114474a4293ef42e075f1264ab10e5876f1440a9c1d66bc11f318bbe"),
    "indexes": (57, "f7a5ba4937bfebcc9fbee3d1f19b0a7dc00c842b7c20792acf5183e6b2fcbefd"),
    "triggers": (22, "eb29f00db128601591f70f2db06e6ac66a856a3619eecfbdf555dd5a941ec804"),
    "functions": (6, "8ebe465b584b2209f5439443b7641d1865ae401631be83dea98bf583a6d159b5"),
    "views": (1, "099049415234da3d04583c58a693a68fda934f77e9eaf00b0d12e2542842734d"),
    "extensions": (1, "81a067095db43b64056597402d99e045d6deba0c83f1a535889dda45ec7fefb1"),
    "sequences": (6, "c93f818ef0134cc85c2d8664bd97842ccaa20dc96fd25adbeb610fb40cc4d7e1"),
    "policies": (0, "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"),
    "state_topology": (24, "5dbff1960b80b4ef9e48789a48708a88c6cfc84b4ed8a30bbe177c651a5f5176"),
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
