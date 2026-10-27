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


#: Resealed by `CMP-SEAL-C0` for ``0038_comparison_foundation``, measured, not predicted: a fresh
#: database upgraded to ``0038`` was recomputed in all eleven families and compared with the 0037 seal
#: below. Every count moved by exactly the migration's DDL and nothing was removed: columns +126 -> 908
#: (nine tables 124, ``document_version.upload_kind`` and ``executor_task.comparison_attempt_id``);
#: relations +9 -> 88 (the tables); constraints +156 -> 1038; indexes +38 -> 236; triggers +25 -> 118
#: (the state-edge, frozen, write-once, insert and immutable guards of the nine tables; the frozen guard
#: of ``executor_task`` is recreated with ``comparison_attempt_id``, so its row is redefined and the
#: count is unchanged by it); functions +5 -> 41 (``am_guard_comparison_state_edges`` and the four
#: insert and chain checks). Views, extensions, sequences, policies and the state topology are
#: identical to the 0037 seal (their digests are unchanged).
#: Resealed by `ANALYSIS-PRESETS-01` for ``0037_analysis_presets``, measured, not predicted: a fresh
#: database upgraded to ``0037`` was recomputed in all eleven families and compared with the 0036 seal
#: below. Every count moved by exactly the migration's DDL and nothing was removed: columns +9 -> 782
#: (``analysis_preset_revision`` 8, ``audit_run.preset_revision_id`` 1); relations +1 -> 79 (the
#: table); constraints +14 -> 882 (the table: primary key, one unique key, one foreign key, nine
#: CHECKs; ``audit_run``: one foreign key and the format CHECK of the new column); indexes +4 -> 198
#: (the primary key, the unique ``(preset_id, revision_no)``, ``ix_analysis_preset_revision_connection``
#: and the partial ``ix_audit_run_preset_revision``); triggers +3 -> 93 (the table's
#: ``am_immutable_row`` and chain trigger, and the INSERT check on ``audit_run``; the frozen guard of
#: ``audit_run`` is recreated with ``preset_revision_id`` in its column list, so its row is redefined
#: and the count is unchanged by it); functions +2 -> 36 (``am_check_analysis_preset_chain``,
#: ``am_check_audit_run_preset``). Views, extensions, sequences, policies and the state topology are
#: identical to the 0036 seal.
#: Resealed by `AR-V3-DECISIONS-01` for ``0036_cite_partition_v3``, measured, not predicted: a fresh
#: database upgraded to ``0036`` was recomputed in all eleven families and compared with the 0035 seal
#: below. One family moved and by exactly the migration's DDL: ``functions`` keeps its 34 rows and
#: ``am_verify_norm_citation_partition`` is redefined (same row) -- the stage test reads
#: ``norm_verification`` or ``ar_v3_citation_review`` -- so only its digest changed
#: (``6ee1b2f0...3bd9`` -> ``6e5b1c9d...37ad``). Columns, relations, constraints, indexes, triggers,
#: views, extensions, sequences, policies and the state topology are identical to the 0035 seal.
#: Resealed by `COMPARE-PERSISTED-SUMMARY-01` for ``0035_comparison_records``, measured, not
#: predicted: a fresh database upgraded to ``0035`` was recomputed in all eleven families and compared
#: with the 0034 seal below. Every added row is this revision's and nothing was removed or redefined:
#: columns +37 -> 773 (``comparison_sheet_link`` 18, ``comparison_summary`` 19); relations +2 -> 78 (the
#: two tables); constraints +54 -> 868 (``comparison_sheet_link``: primary key, three unique keys, five
#: foreign keys, nineteen CHECKs; ``comparison_summary``: primary key, one unique key, three foreign
#: keys, twenty-one CHECKs); indexes +10 -> 194 (the two primary keys, the four unique keys, the partial
#: unique index of the one ready summary per input, ``ix_comparison_sheet_link_project``,
#: ``ix_comparison_sheet_link_target_version`` and ``ix_comparison_summary_project``); triggers +4 -> 90
#: (an ``am_immutable_row`` trigger and a BEFORE INSERT check on each table); functions +2 -> 34
#: (``am_check_comparison_sheet_link_chain``, ``am_check_comparison_summary``). Views, extensions,
#: sequences, policies and the state topology are identical to the 0034 seal.
#: Resealed by `OPT-PROJECT-ALL-SECTIONS-01` for ``0034_pass_scope_all_sections``, measured, not
#: predicted: one fresh database upgraded to ``0033`` (whose inventory equalled the 0033 seal below
#: in every family) and then to ``0034`` had all eleven families recomputed. One family moved and by
#: exactly the migration's DDL: ``functions`` keeps its 32 rows and ``am_check_optimisation_pass_scope``
#: is redefined (same row) -- the version's classification no longer has to be ``AR`` and the vendor
#: list's section equals the version's -- so only its digest changed. Columns, relations,
#: constraints, indexes, triggers, views, extensions, sequences, policies and the state topology are
#: identical to the 0033 seal.
#: Resealed by `PROD-11B-V3-STAGE-ID-MIGRATION-01` for ``0033_ar_v3_cite_stage_id``, measured, not
#: predicted: two fresh databases on the lane's PostgreSQL 17 stack, one upgraded to ``0032`` and one
#: to ``0033``, had the columns, relations, constraints, indexes and triggers diffed row by row.
#: One family moved and by exactly the migration's DDL: constraints stay 814 with no row added or
#: removed, and one row is redefined -- ``stage_result.ck_stage_result_stage_id`` -- by one quoted
#: literal, ``ar_v3_citation_review``, appended after the nine registry ids and by nothing else
#: (still validated). The other ten families are identical to the 0032 seal.
#: Resealed by `AR-V3-BETA-SIX-RUN-02` for ``0032_ar_v3_run_group`` on a fresh
#: PostgreSQL clone: columns +19, relations +2, constraints +31, indexes +5,
#: triggers +3 and functions +1. Views, extensions, sequences, policies and
#: state topology retain the 0031 digests. The two tables freeze group and member
#: pins; the deferred trigger requires six exact members at commit.
#: Resealed by `EXEC-PULL-01` for ``0031_executor_pull_channel``, measured against a fresh upgrade
#: of the lane's PostgreSQL 17 + pgvector stack, and equal to the migration's DDL in every family
#: it moved: columns +35 -> 717 (``executor_runner_token`` 11, ``executor_task`` 24); relations +2
#: -> 74 (two tables); constraints +44 -> 783 (two primary keys, three unique keys, seven foreign
#: keys and thirty-two CHECKs, eight of them the identity-format CHECKs of the id columns);
#: indexes +11 -> 179 (the two primary keys, the token's three unique keys and connection index,
#: and the task's five partial indexes); triggers +4 -> 83 (the frozen and write-once guards of
#: each table). Functions, views, extensions, sequences, policies and the state topology are
#: identical to the 0030 seal.
#: Resealed by `EXEC-SEAL-01` for ``0030_executor_connections``, measured, not predicted: a fresh
#: upgrade of the lane's PostgreSQL 17 + pgvector stack, whose per-family counts were taken against
#: the 0029 seal below (and the constraint and index totals were predicted from the migration's DDL
#: before the run and equalled the measurement). Six families moved, each by exactly the
#: migration's DDL: columns +76 -> 682 (the five tables 64, the view ``executor_route_current`` 7,
#: ``audit_run`` +1, ``model_call`` +2, ``provider_call_effect`` +2); relations +6 -> 72 (five
#: tables and a view); constraints +82 -> 739 (five primary keys, nine foreign keys, three unique
#: keys and sixty-five CHECKs, seven of them the identity-format CHECKs of the foreign-key columns, among them ``ck_model_call_cost_basis`` redefined with
#: ``unmetered``); indexes +15 -> 168; triggers +7 -> 79 (the connection's frozen and write-once
#: guards, the revision's immutable guard, the probe's frozen guard, the route events' append-only
#: guard and the secret's frozen and write-once guards; ``trg_audit_run_frozen_guard`` is redefined,
#: same row, with ``connection_revision_id`` frozen); views +1 -> 5. Functions, extensions,
#: sequences, policies and the state topology are identical to the 0029 seal.
#: Resealed by `BETA-CONTRACT-SEAL-01` for ``0029_routing_refusal_codes``, measured, not
#: predicted: two fresh databases on the lane's PostgreSQL 17 + pgvector stack, one upgraded to
#: ``0028`` (whose inventory equalled the 0028 seal below in every family) and one to ``0029``,
#: had every family's rows diffed. One family moved and by exactly the migration's DDL:
#: constraints stay 657 with no row added or removed, and four rows are redefined --
#: ``ck_command_record_error_code``, ``ck_audit_run_terminal_reason``, ``ck_model_call_error_code``
#: and ``ck_provider_effect_error_code`` -- each by the same two quoted codes,
#: ``version_classification_required`` and ``section_profile_unavailable``, and by nothing else.
#: Columns, relations, indexes, triggers, functions, views, extensions, sequences, policies and
#: the state topology are identical to the 0028 seal.
#: Resealed by `CLASSIFICATION-CORRECTION-01` for ``0028_classification_corrections``, measured,
#: not predicted: a fresh upgrade of the lane's PostgreSQL 17 + pgvector stack, whose per-family
#: counts were taken against the 0027 seal below, and the whole of 0028 was shown to be the
#: difference by ``test_downgrade_chain_round_trip.py`` (downgrading 0028 restores the 0027
#: inventory row for row). Seven families moved, each by exactly the migration's DDL: columns +20
#: -> 606 (``document_version_classification_correction`` 7, the view
#: ``version_classification_revision`` 7, the view ``version_classification_current`` 6);
#: relations +3 -> 66 (one table, two views); constraints +9 -> 657 (the correction table's
#: primary key, two foreign keys and six CHECKs); indexes +1 -> 153 (its primary key's index);
#: triggers +2 -> 72 (``trg_document_version_classification_correction_immutable`` and
#: ``trg_document_version_classification_correction_chain``); functions +1 -> 31
#: (``am_check_classification_correction_chain``), with ``am_check_optimisation_pass_scope``
#: redefined -- same row, now reading ``version_classification_current``; views +2 -> 4.
#: Extensions, sequences, policies and the state topology are identical to the 0027 seal.
#: Resealed by `W60-OPT-PROPOSALS-01` for ``0027_optimisation_proposals``, measured, not
#: predicted: two fresh databases on the lane's PostgreSQL 17 + pgvector stack, one upgraded to
#: ``0026`` (whose inventory equalled the 0026 seal below in every family) and one to ``0027``,
#: had every family's rows diffed. Every added row is this revision's and nothing was removed
#: or redefined: columns +52 -> 586 (``optimisation_pass`` 18, ``optimisation_proposal`` 26,
#: ``optimisation_proposal_decision`` 8); relations +3 -> 63 (three tables); constraints
#: +66 -> 648 (``optimisation_pass``: primary key, the inputs' unique key, seven foreign keys,
#: twelve CHECKs and the constraint trigger's row ``trg_optimisation_pass_has_proposals``;
#: ``optimisation_proposal``: primary key, two unique pairs, three foreign keys, twenty-four
#: CHECKs; ``optimisation_proposal_decision``: primary key, two unique keys, three foreign
#: keys, eight CHECKs); indexes +11 -> 152 (the three primary keys, the five unique keys,
#: ``ix_optimisation_pass_project``, ``ix_optimisation_pass_started_by`` and
#: ``ix_optimisation_proposal_decision_actor``); triggers +6 -> 70 (three ``am_immutable_row``
#: triggers, ``trg_optimisation_pass_scope``, ``trg_optimisation_proposal_prices`` and the
#: deferred ``trg_optimisation_pass_has_proposals``); functions +3 -> 30
#: (``am_check_optimisation_pass_scope``, ``am_check_optimisation_proposal_prices``,
#: ``am_require_optimisation_proposals``). Views, extensions, sequences, policies and the
#: state topology are identical to the 0026 seal.
#: Resealed by `W60-PRICE-LIST-01` for ``0026_price_lists``, measured, not predicted: two
#: fresh databases on the lane's PostgreSQL 17 + pgvector stack, one upgraded to ``0025``
#: (whose inventory equalled the 0025 seal below in every family) and one to ``0026``, had
#: every family's rows diffed. Every added row is this revision's and nothing was removed or
#: redefined: columns +41 -> 534 (``price_list_revision`` 16, ``price_list_position`` 11,
#: ``vendor_list_revision`` 9, ``vendor_list_entry`` 5); relations +4 -> 60 (four tables);
#: constraints +56 -> 582 (``price_list_revision``: primary key, unique revision number, three
#: foreign keys, fourteen CHECKs and the constraint trigger's row
#: ``trg_price_list_revision_has_positions``; ``price_list_position``: primary key, unique row
#: number, one foreign key, eleven CHECKs; ``vendor_list_revision``: primary key, the
#: ``NULLS NOT DISTINCT`` unique revision number, two foreign keys, ten CHECKs and
#: ``trg_vendor_list_revision_has_entries``; ``vendor_list_entry``: primary key, one foreign
#: key, five CHECKs); indexes +9 -> 141 (the four primary keys, the three unique pairs,
#: ``ix_price_list_revision_blob`` and ``ix_vendor_list_revision_set_by``); triggers +7 -> 64
#: (four ``am_immutable_row`` triggers, ``trg_price_list_revision_blob_available`` and the two
#: deferred constraint triggers); functions +3 -> 27 (``am_check_price_list_blob``,
#: ``am_require_price_list_positions``, ``am_require_vendor_list_entries``). Views,
#: extensions, sequences, policies and the state topology are identical to the 0025 seal.
#: Resealed by `W61-DISPATCHER-01` for ``0025_work_assignments``, measured, not predicted:
#: two fresh databases on the lane's PostgreSQL 17 + pgvector stack, one upgraded to ``0024``
#: (whose inventory equalled the 0024 seal below in every family) and one to ``0025``, had
#: every family's rows diffed. Every added row is this revision's and nothing was removed or
#: redefined: columns +28 -> 493 (``work_assignment`` 7, ``work_assignment_event`` 8, the
#: view ``work_assignment_current`` 13); relations +3 -> 56 (two tables, one view);
#: constraints +27 -> 526 (``work_assignment``: primary key, four foreign keys, six CHECKs
#: and the constraint trigger's row ``trg_work_assignment_has_assigned_event``;
#: ``work_assignment_event``: primary key, ``uq_..._assignment_uid_seq``, three foreign keys
#: and ten CHECKs); indexes +6 -> 132 (two primary keys, the unique ``seq`` pair,
#: ``ix_work_assignment_scope``, ``ix_work_assignment_created`` and the partial
#: ``ix_work_assignment_event_new_assignee``); triggers +3 -> 57 (the two
#: ``am_immutable_row`` triggers and the deferred constraint trigger); functions +1 -> 24
#: (``am_require_work_assignment_event``); views +1 -> 2. Extensions, sequences, policies
#: and the state topology are identical to the 0024 seal (the ``work_assignment`` machine is
#: decided by ``auditmanager.dispatch``; nothing is seeded into ``contract_state_transition``).
#: Resealed by `W59-SECTION-SEAL-01` for ``0024_version_classification`` from a fresh
#: upgrade on the lane's PostgreSQL 17 + pgvector stack. Against the 0023 seal below, five
#: families moved and each by exactly the migration's DDL: columns +5 -> 465 (the five
#: columns of ``document_version_classification``); relations +1 -> 53 (the table);
#: constraints +7 -> 499 (its primary key, ``fk_..._version``, ``fk_..._confirmed_by`` and the
#: four ``ck_document_version_classification_*`` checks), with ``ck_document_section``
#: redefined from legacy's fourteen to the fifteen sections -- same row, new definition;
#: indexes +1 -> 126 (the primary key's index); triggers +1 -> 54
#: (``trg_document_version_classification_immutable``). Functions, views, extensions,
#: sequences, policies and the state topology were observed identical to the 0023 seal.
#: Resealed by `W57A-SEAL-01A` for ``0023_norm_citations`` from two disposable
#: PostgreSQL 17 + pgvector 0.8.6 databases, one upgraded to published 0022 and
#: one to 0023. Against the measured 0022 baseline: columns +34 (the retrieval
#: set and citation tables, one Run pin and three observation fields);
#: relations +2; constraints +33 (new table PK/FK/CHECKs, the Run pin, three
#: observation checks, a forward CHECK for 0022's canonical observation ID,
#: and three constraint triggers); indexes +3; triggers +7; functions +4
#: (including the replacement custody guard's changed definition). The 0022
#: severity view, extension, sequences, policies and state topology are
#: unchanged. All newly named objects are in migration 0023; published 0022
#: migration bytes remain untouched.
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
    "columns": (908, "954eb10214597d10ace4f2af316cb7de34c3c988876312a7490441cb7a9d32bd"),
    "relations": (88, "483e8af8025b3813202abf1222426f7b5e9315b46ee699506e2623e04fb31702"),
    "constraints": (1038, "a80813a10d4db584a9f69800226f43fc2d9221c5efe335a006ad3a9476ba6636"),
    "indexes": (236, "18d4ef90b0c771cb3df8432b4febf79628372c39b51b3924a917223838278eac"),
    "triggers": (118, "96198c83bdfdf5b60b70395201951d916e64a5f88b1dd4d82b9a8484552ef70a"),
    "functions": (41, "25ad0a1f09f23418b94cdf83e6dfc1551bc15d1fbc3ec1fb5aa67a5c7296658e"),
    "views": (5, "c41ad974669882ee5d818591ee1d485b70455ddd4e51d236cc83892d18d11b93"),
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
