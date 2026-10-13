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


#: Resealed by `W55B-SEAL-01` for ``0021_portal_bundles`` from a fresh upgrade on PostgreSQL 17 +
#: pgvector 0.8.6 (the lane's own stack). Three families moved and each by exactly what the
#: migration's DDL adds: columns +3 -> 422 (``document_version.text_character_count``,
#: ``textless_pages``, ``recognised_character_count``); constraints +4 -> 454
#: (``ck_document_version_text_character_count``, ``..._recognised_character_count``,
#: ``..._textless_pages`` and ``..._bundle_counts_together``), with ``ck_document_version_page_count``
#: redefined from ``BETWEEN 1 AND 30`` to ``BETWEEN 1 AND 500`` -- same row count, new definition,
#: which is why the digest moves beyond the count; functions +1 -> 19 (``am_is_ascending_page_list``).
#: The other eight families (relations, indexes, triggers, views, extensions, sequences, policies and
#: the state topology) were observed identical to the 0020 seal. The comparison is the three counts
#: against the DDL and the eight untouched digests; a row-by-row diff against a second database
#: upgraded to ``0020`` was not run.
#: Resealed by `W55A-FIX` for its amendment of ``0020_norms_search``'s guard triggers (the
#: strict current-snapshot history, JUDGE-X M4 / JUDGE-Y Y-3), measured, not predicted: two
#: fresh databases, one upgraded with ``0020`` as at ``cb4bdf1`` (whose inventory equalled the
#: previous seal exactly) and one with this lane's ``0020``, had every family's rows diffed.
#: constraints +1 -> 450 (the constraint trigger's own row,
#: ``trg_norm_current_snapshot_event_designates``, contype ``t``); triggers +4 -> 46
#: (``trg_norm_current_snapshot_event_stamp`` BEFORE INSERT, ``..._event_designates`` AFTER
#: INSERT DEFERRABLE INITIALLY DEFERRED, and ``trg_norm_current_snapshot_no_truncate`` /
#: ``trg_norm_current_snapshot_event_no_truncate`` BEFORE TRUNCATE FOR EACH STATEMENT);
#: functions +4 -1 -> 18 (``am_stamp_norm_current_snapshot_event``,
#: ``am_require_current_norm_snapshot_event``, ``am_refuse_norm_current_snapshot_truncate``,
#: and ``am_guard_norm_current_snapshot`` redefined with its newest-event check). Every other
#: family is byte-identical.
#: Resealed by `W55A-FIX-DB` for ``0018_norm_custody``, ``0019_execution_workers`` and
#: ``0020_norms_search`` together, from a fresh upgrade on PostgreSQL 17 + pgvector 0.8.6. The
#: delta was measured, not only predicted: two fresh databases, one upgraded to
#: ``0017_execution_queue`` (whose inventory equalled the previous seal exactly) and one to
#: head, had every family's rows diffed. Each added or removed row is one of these:
#: columns +62 (0018: analysis_artifact_publication.abandoned_at, norm_custody_admission 17,
#: norm_custody_binding 9, norm_repair_call 16, norm_paragraph.text_reliability,
#: norms_snapshot.unreliable_count; 0019: worker 6, lease.worker_id; 0020:
#: norm_current_snapshot_event 5, norm_current_snapshot 3, the generated
#: norm_document.designation_tokens and norm_paragraph.text_tsv) -> 419; relations +6 (three
#: 0018 tables, worker, the two 0020 tables) -> 50; constraints +66 -2 -> 449 (0018: admission
#: 14, binding 9, repair call 16, ck_norm_paragraph_text_reliability,
#: ck_norms_snapshot_unreliable_count, ck_analysis_artifact_abandoned_shape, and two
#: redefinitions -- ck_analysis_artifact_state gains 'abandoned', ck_norms_snapshot_raw_key
#: becomes "(repair_count = 0 AND unreliable_count = 0) = (base key = content key)"; 0019:
#: worker 5, lease's worker_id format CHECK and foreign key; 0020: event 8, current 7);
#: indexes +24 (0018 13, 0019 3, 0020 8) -> 121; triggers +10 -3 -> 42 (both effect-table
#: state guards redefined BEFORE INSERT OR UPDATE (D-148), trg_lease_frozen_guard redefined
#: to freeze worker_id, four custody/repair-call triggers, trg_worker_frozen_guard, and the
#: two 0020 triggers); functions +6 -1 -> 15 (am_guard_durable_effect_transition gains its
#: INSERT arm; three custody/repair-call guards; am_guard_norm_current_snapshot and
#: norm_designation_tokens). Views, extensions, sequences, policies and the state topology
#: are byte-identical. No row outside those three migrations changed.
#: Resealed by `W53-SEAL-01` for ``0017_execution_queue`` after a fresh upgrade.
#: The reviewed delta is +9 columns (job 2, lease 2, audit_run 1,
#: provider_call_effect 1, execution_control 3), +1 relation, +7 constraints
#: (including the re-audit ID check), +4 indexes. The run-frozen trigger
#: and durable-effect guard function retain their counts but change definition;
#: views, extensions, sequences, policies and state topology are unchanged.
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
    "columns": (422, "fce7cf026dbe28de0258157f5495d83ac4ec8f5b68658a77fb01ad5d299dcd62"),
    "relations": (50, "92a0ec6d035d72f0bb16e8ae867621a77a235a1c9a379237cf4aef2d28dd52de"),
    "constraints": (454, "c2e81198ddeebe7e179b56041fd2a920f932ad93b0a7bdaed269d93fb5f968e4"),
    "indexes": (121, "aa69f427e5b85d0d306931e4ecee46535c0a215b34799f58976bf789774a624e"),
    "triggers": (46, "42bbe67057d87b17cb9a529f36147c08e1f9bcca49db16abb9227762f40d75ae"),
    "functions": (19, "851f818fa7a1794404b24679fbafddeb1733876018f66e0738ab20beda705697"),
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
