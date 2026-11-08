"""Column- and trigger-level claims, asserted against the live database.

These belong here rather than in the contract suite. Grepping the migration source
for a column name also matches the comment that explains why the column is absent,
so such a test ends up proving that a docstring exists. ``information_schema`` and
``pg_trigger`` describe what was actually created.
"""

from __future__ import annotations

from sqlalchemy import Engine, text

#: Names that would turn an address or a presentation value into a de facto key.
BANNED_COLUMN_NAMES = {
    "bucket",
    "bucket_name",
    "object_key",
    "s3_key",
    "storage_key",
    "storage_path",
    "file_path",
    "filesystem_path",
    "directory",
    "url",
    "presigned_url",
    "download_url",
    "password",
    "secret",
    "credential",
    "api_key",
    "token",
    "execution_token",
    "fencing_token",
    "authority_token",
    "prompt",
    "prompt_text",
    "raw_response",
    "response_body",
}

# `0030_executor_connections`: the route of each kind of model work is appended, never edited.
# `0047_executor_groups_rules` (`EXEC2-SEAL-2`, ADR-0026 decisions 11 and 17): a rule revision and a routing-mode change
# are appended, never edited; the current rule and the current mode are queries over them.
APPEND_ONLY_TABLES = {
    "expert_decision_event", "audit_event", "executor_route_event",
    "executor_routing_rule_revision", "executor_routing_mode_event",
}

IMMUTABLE_TABLES = {
    "document_version",
    "input_manifest_entry",
    "finding_observation",
    "finding_evidence",
    "model_call",
    "contract_state_transition",
    "norm_document",
    "norm_embedding_profile",
    "norm_paragraph",
    "norms_snapshot",
    # `0018_norm_custody`: a published custody binding is never rewritten or removed
    # (NORM-Q06). The admission and repair-call journals refuse DELETE inside their own
    # state guards instead, because their state moves.
    "norm_custody_binding",
    # `0020_norms_search`: the current snapshot's history is append-only (R-113). The
    # current row itself moves, so its own guard refuses DELETE and an unrecorded change.
    "norm_current_snapshot_event",
    "norm_retrieval_set",
    "ar_v3_run_group",
    "ar_v3_run_group_member",
    "finding_observation_norm_citation",
    # `0024_version_classification`: the first expert classification stands (``AM003``).
    "document_version_classification",
    # `0025_work_assignments`: an assignment header and its append-only history; the
    # status is derived from the history (view ``work_assignment_current``), never updated.
    "work_assignment",
    "work_assignment_event",
    # `0026_price_lists`: an uploaded price list, its positions, and each vendor-list
    # revision with its entries are written once; the current one is a query.
    "price_list_revision",
    "price_list_position",
    "vendor_list_revision",
    "vendor_list_entry",
    # `0027_optimisation_proposals`: a pass and its proposals are written once; each expert
    # decision is an appended row, and the current decision is a query.
    "optimisation_pass",
    "optimisation_proposal",
    "optimisation_proposal_decision",
    # `0028_classification_corrections`: a correction is appended once and never changed; the
    # original confirmation above is revision 1 and the current classification is a view.
    "document_version_classification_correction",
    # `0030_executor_connections`: a revision of a connection's settings is written once; a changed
    # address is a new revision.
    "executor_connection_revision",
    # `0035_comparison_records`: an approval or withdrawal of a sheet pairing is appended once and
    # never changed; the approved set is a query.
    "comparison_sheet_link",
    "comparison_summary",
    # `0037_analysis_presets`: a revision of a preset is appended once and never changed; the
    # current revision is a query, and an archive is a revision.
    "analysis_preset_revision",
    # `0038_comparison_foundation`: an order revision of a document set is appended once and never
    # changed; the current order is a query.
    "comparison_version_order",
    # `0039_comparison_core`: a build of the matrix, an edit event and an accepted AI link are appended once and
    # never changed; the effective matrix is a read model over them.
    "comparison_matrix",
    "comparison_matrix_edit",
    "comparison_ai_link",
    # `0040_comparison_ai_reports`: the content-keyed pair-check answers, sheet descriptions and specification extractions
    # and the stored files of a report are appended once and never changed.
    "comparison_ai_pair_answer",
    "comparison_sheet_description",
    "comparison_spec_extraction",
    "comparison_report_artifact",
    # `0041_comparison_stage_core`: assembly acts, full maps and raw evidence are append-only.
    "stage_assembly", "stage_assembly_member", "stage_link_revision", "stage_link_item",
    "stage_text_fragment", "stage_text_exclusion", "stage_text_difference", "stage_text_hint",
    # `0042_comparison_stage_review` (`CMP-SEAL-C4`): the stage AI's per-unit review, classification and synthesis answers, the
    # graphic evidence, a link repair and each of its events, a change card with its evidence and each expert verdict are written
    # once; a changed card or a new verdict is a new row, and the effective state is a query. The unit and the batch rows
    # (``stage_ai_unit``, ``stage_chain_batch``, ``stage_chain_batch_item``) move through states, so they carry the frozen-column
    # guard instead -- the migration's own ``IMMUTABLE`` tuple is the nine tables below.
    "stage_ai_review", "stage_ai_classification", "stage_ai_synthesis", "stage_graphic_evidence",
    "stage_link_repair", "stage_link_repair_event", "stage_change_card", "stage_card_evidence", "stage_card_verdict",
    # `0047_executor_groups_rules` (`EXEC2-SEAL-2`, ADR-0026 decision 10): a group revision and its member snapshots are
    # written once, and a changed group is a new revision. The group row itself is never deleted (``am_immutable_row``
    # guards DELETE only; its name and creation are frozen, its archive is write-once and its rotation cursor advances).
    "executor_group", "executor_group_revision", "executor_group_member",
    # `0055_work_schedule` (`UI-PARITY-P0P`): the five journals of «График работ» are `am_immutable_row` (this set lacked them).
    "engineer_absence_event", "schedule_plan_event", "schedule_setting_event", "work_assignment_schedule_event",
    "work_calendar_event",
    # `0059_decision_memory` (`ADR-0027`): the case of a decision and everything it keeps are written once; a later decision on the
    # same observation is a new `decision_memory_decision` row, and a withdrawal is a status event.
    "decision_memory_case", "decision_memory_decision", "decision_memory_decision_text", "decision_memory_status_event",
    "decision_memory_content", "decision_memory_evidence", "decision_memory_norm_ref", "decision_memory_crop",
}


def _columns(engine: Engine) -> list[tuple[str, str]]:
    with engine.connect() as connection:
        return [
            (row[0], row[1])
            for row in connection.execute(
                text(
                    "SELECT table_name, column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public'"
                )
            )
        ]


def _trigger_functions(engine: Engine, table: str) -> set[str]:
    with engine.connect() as connection:
        return {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT p.proname FROM pg_trigger t "
                    "JOIN pg_class c ON c.oid = t.tgrelid "
                    "JOIN pg_proc p ON p.oid = t.tgfoid "
                    "WHERE NOT t.tgisinternal AND c.relname = :table"
                ),
                {"table": table},
            )
        }


#: The one secret-class column of the run's Attempt, and its twin of the comparison queue
#: (`0038_comparison_foundation`, ADR-0025 decision 4): an opaque equality-only capability, never
#: returned, parsed or ordered.
SECRET_CLASS_COLUMNS = {("attempt", "execution_token"), ("comparison_work_attempt", "execution_token")}


def test_no_column_names_an_address_a_secret_or_a_model_payload(
    migrated_engine: Engine,
) -> None:
    offenders = [
        f"{table}.{column}"
        for table, column in _columns(migrated_engine)
        if column in BANNED_COLUMN_NAMES
        and (table, column) not in SECRET_CLASS_COLUMNS
    ]
    assert offenders == [], (
        "the object-key layout is confined to the S3 adapter and secrets are stored "
        "only in the exact contract-owned attempt.execution_token column and its comparison twin; "
        f"found {offenders}"
    )


def test_the_columns_that_are_not_identities_exist_and_are_referenced_by_nothing(
    migrated_engine: Engine,
) -> None:
    """A path, a file name, an ordinal and a checksum may be columns - never keys."""
    columns = set(_columns(migrated_engine))
    for expected in (
        ("document_version", "source_filename"),
        ("document_version", "version_ordinal"),
        ("blob", "sha256"),
        ("expert_decision_event", "sequence_no"),
    ):
        assert expected in columns, f"{expected} is missing"

    with migrated_engine.connect() as connection:
        referencing = connection.execute(
            text(
                "SELECT c.conname, a.attname FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.confrelid "
                "JOIN unnest(c.confkey) AS k(attnum) ON TRUE "
                "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum "
                "WHERE c.contype = 'f'"
            )
        ).all()
    referenced_columns = {row[1] for row in referencing}
    for non_identity in ("source_filename", "version_ordinal", "sha256", "sequence_no"):
        assert non_identity not in referenced_columns, (
            f"{non_identity} is the target of a foreign key; the contract lists it "
            "among the non-identities"
        )


def test_exactly_the_declared_tables_are_append_only(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r'"
                )
            )
        }
    with_append_only = {
        table for table in tables if "am_append_only" in _trigger_functions(migrated_engine, table)
    }
    assert with_append_only == APPEND_ONLY_TABLES


def test_exactly_the_declared_tables_are_immutable(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r'"
                )
            )
        }
    with_immutability = {
        table
        for table in tables
        if "am_immutable_row" in _trigger_functions(migrated_engine, table)
    }
    assert with_immutability == IMMUTABLE_TABLES


def test_every_contract_state_column_carries_the_transition_guard(migrated_engine: Engine) -> None:
    for table in ("audit_run", "blob", "command_record", "job", "attempt"):
        assert "am_guard_state_transition" in _trigger_functions(migrated_engine, table), (
            f"{table} has a state column with no transition guard"
        )


#: Columns whose name ends in ``_id`` but which are not contract identities.
#: ``sequence_no`` is a server row order, ``aggregate_id`` holds any prefix by design,
#: ``correlation_id`` is declared ``is_entity_identity: false``, ``block_id`` and
#: ``section_id`` are anchors inside one artifact, and ``stage_id`` is a registry name.
#:
#: ``user_uid`` (``0006_app_user``) is here for a different reason: it IS an identity,
#: but ``usr`` is not a prefix in ``contracts/domain/v1/identifiers.json`` -- that
#: catalog is frozen at twenty-five entries and has no user aggregate -- so the sweep
#: below, which resolves each column through a contract prefix, has nothing to resolve
#: it against. Its format CHECK is asserted directly in
#: ``test_app_user_migration.py::test_the_identity_column_carries_the_contract_shaped_format_check``,
#: so excluding it here loses no coverage. When users are contracted, delete this entry.
#:
#: ``request_id``, ``created_user_uid`` and ``author_user_uid`` (``0015``) are here for the
#: same reason as ``user_uid``: ``reg`` and ``usr`` enter the catalog only with
#: ``W49-SEAL-01a``. Their format CHECKs are asserted directly in
#: ``test_accounts_migration.py::test_every_account_identity_column_carries_its_format_check``.
#: When the seal contracts both prefixes, move all four into ``prefix_by_column``.
NON_CONTRACT_IDENTITY_COLUMNS = {
    "aggregate_id",
    "author_user_uid",
    "block_id",
    "correlation_id",
    "created_user_uid",
    "request_id",
    "section_id",
    # One of the six fixed scope codes, not an opaque entity identity.
    "scope_id",
    "sequence_no",
    "stage_id",
    "user_uid",
    # `0030_executor_connections`: ``pin_id`` names a model of the provider lock
    # (``claude-opus-5``), not an entity this product mints.
    "pin_id",
    # `0018_norm_custody`: a custody target holds the prefix of whichever entity its
    # ``target_kind`` names, like ``aggregate_id``; ``ck_norm_custody_role_shape`` checks it
    # per kind.
    "target_id",
    # `0046_executor_capacity_enroll` (ADR-0026 decision 3): the name an agent process gives itself in a claim
    # (``runner_instance_id``), 8 to 64 characters of ``A-Za-z0-9_-`` -- the agent's own random string, not an
    # entity this product mints; ``ck_executor_task_claimed_by_instance_id`` checks its shape.
    "claimed_by_instance_id",
}

#: A column name that two tables use for two different identities (or for a label) cannot carry one prefix in the
#: name-keyed map inside the test below, so the table-qualified exceptions live here and the sweep consults them first.
#:
#: ``group_id`` is the Run group of an AR v3 run (``arg``) in ``ar_v3_run_group*``, the executor group (``exg``,
#: ``0047_executor_groups_rules``, ADR-0026 decision 10) in ``executor_group`` and ``executor_group_revision``, and --
#: in the four ``stage_ai_*`` tables of ``0042_comparison_stage_review`` -- a grouping label, see below.
#: ``stage_link_repair_event.revision_id`` names a stage link revision (``slk``); everywhere else ``revision_id`` is an
#: executor connection revision (``excr``).
PREFIX_BY_TABLE_COLUMN = {
    ("executor_group", "group_id"): "exg",
    ("executor_group_revision", "group_id"): "exg",
    ("stage_link_repair_event", "revision_id"): "slk",
}

#: ``stage_ai_*.group_id`` is not an entity identity: it is the stage AI's own grouping label -- ``grp:`` plus the first 24 hex
#: digits of a digest of the link items it groups (``comparison/stage_review`` and ``comparison/stage_ai/source.py``), or the
#: fixed name ``v3:final:cards`` -- bounded by ``char_length BETWEEN 1 AND 128`` in the migration and echoed by the model
#: as a string. No contract prefix exists for it and none is minted (``contracts/domain/v1/identifiers.json`` lists no such
#: identity). Qualified by table so that a future ``group_id`` elsewhere is still swept.
NON_CONTRACT_TABLE_COLUMNS = {
    ("stage_ai_unit", "group_id"),
    ("stage_ai_review", "group_id"),
    ("stage_ai_classification", "group_id"),
    ("stage_ai_synthesis", "group_id"),
}


def test_every_identity_column_carries_a_format_check(migrated_engine: Engine) -> None:
    """A CHECK per identity column, so raw SQL cannot bypass the value type.

    Matched on the constraint *definition*, not its name: a constraint named
    ``..._format`` that checks nothing would pass a name-based test.
    """
    from auditmanager.shared.identity import IDENTITY_TYPES_BY_ENTITY, pattern_for

    prefix_by_column = {
        "project_uid": "prj",
        "document_uid": "doc",
        "current_version_uid": "ver",
        "version_uid": "ver",
        "blob_id": "blob",
        "run_id": "run",
        "group_id": "arg",
        "allocated_by_run_id": "run",
        "reaudit_of_run_id": "run",
        "command_id": "cmd",
        "analysis_profile_id": "ap",
        "prompt_bundle_id": "pb",
        "norms_snapshot_id": "ns",
        "norm_document_id": "ndoc",
        "norm_paragraph_id": "npar",
        "norm_retrieval_set_id": "nrs",
        "set_blob_id": "blob",
        "catalogue_blob_id": "blob",
        "model_call_id": "mc",
        "finding_uid": "fnd",
        "finding_observation_id": "fobs",
        "canonical_observation_id": "fobs",
        "decision_id": "dec",
        "audit_event_id": "evt",
        "job_id": "job",
        "current_attempt_id": "att",
        "attempt_id": "att",
        "lease_id": "lse",
        "final_model_call_id": "mc",
        # `W54-SEAL-01`, migrations 0018 and 0019.
        "norm_custody_admission_id": "nad",
        "norm_custody_binding_id": "nbd",
        "norm_repair_call_id": "nrc",
        "worker_id": "wrk",
        # `W55A-SEAL-01`, migration 0020: the current-snapshot history.
        "event_id": "evt",
        "from_snapshot_id": "ns",
        "to_snapshot_id": "ns",
        "actor_user_uid": "usr",
        # `W59-SECTION-SEAL-01`, migration 0024: the classification's confirmer.
        "confirmed_by_user_uid": "usr",
        # `W61-DISPATCHER-01`, migration 0025: the assignment's people.
        "assignee_user_uid": "usr",
        "created_by_user_uid": "usr",
        "new_assignee_user_uid": "usr",
        "assignment_uid": "asg",
        # `W60-PRICE-LIST-01`, migration 0026: a price list's uploader, a vendor list's author.
        "uploaded_by_user_uid": "usr",
        "set_by_user_uid": "usr",
        # `W60-PRICE-LIST-01` phase B contracted the three optimisation identities.
        "price_list_id": "prl",
        "price_list_position_id": "prp",
        "vendor_list_id": "vnl",
        # `W60-OPT-PROPOSALS-01`, migration 0027: the expert who started a pass (a decision's
        # actor is ``actor_user_uid`` above).
        "started_by_user_uid": "usr",
        # `CLASSIFICATION-CORRECTION-01`, migration 0028: the expert who corrected a version's
        # classification.
        "corrected_by_user_uid": "usr",
        # `W60-OPT-PROPOSALS-01` phase B contracted the three proposal identities; the two
        # position columns of a proposal hold ``prp``.
        "optimisation_pass_id": "opp",
        "optimisation_proposal_id": "opr",
        "proposal_decision_id": "opd",
        "matched_position_id": "prp",
        "proposed_position_id": "prp",
        # `EXEC-SEAL-01`, migration 0030: the executor connections' five identities, and the
        # columns that hold them (a route names two connections, a run, call and effect freeze
        # the revision they used).
        "connection_id": "exc",
        "primary_connection_id": "exc",
        "standby_connection_id": "exc",
        "revision_id": "excr",
        "connection_revision_id": "excr",
        "secret_id": "exs",
        "probe_id": "epb",
        "route_event_id": "ert",
        # `EXEC-PULL-01`, migration 0031: a runner token, a task, and the column that names the
        # token holding a task's claim.
        "token_id": "ern",
        "claimed_by_token_id": "ern",
        "task_id": "ext",
        # `COMPARE-PERSISTED-SUMMARY-01`, migration 0035: the sheet-link history names a comparison,
        # a link and the two versions of the compared pair.
        "comparison_id": "cmp",
        "sheet_link_id": "sln",
        "source_version_uid": "ver",
        "target_version_uid": "ver",
        # B2: a summary is identified by the audit event written with it.
        "summary_id": "evt",
        # `ANALYSIS-PRESETS-01`, migration 0037: a preset and each of its revisions are identified by
        # the audit event written with them (the first revision's id is the preset's); a run records
        # the revision it started with; a preset names the executor connection (`exc`, above).
        "preset_id": "evt",
        "preset_revision_id": "evt",
        "executor_connection_id": "exc",
        # `CMP-SEAL-C0`, migration 0038 (ADR-0025 decision 2): the comparison identities and the
        # columns that hold them -- an upload batch, its set and file, an order revision, a page
        # profile, a queue item and its attempt, a journal row; the document a proposal matched, the
        # blobs a profile stores, the task a journal row waited on, and the attempt a task names.
        "comparison_upload_id": "cbt",
        "comparison_upload_set_id": "cus",
        "set_id": "cus",
        "comparison_upload_file_id": "cuf",
        "comparison_version_order_id": "cvo",
        "comparison_page_profile_id": "cpr",
        "comparison_work_id": "cq",
        "comparison_work_attempt_id": "cqa",
        "current_work_attempt_id": "cqa",
        "comparison_attempt_id": "cqa",
        "comparison_model_call_id": "cmc",
        "existing_document_uid": "doc",
        "profile_blob_id": "blob",
        "preview_blob_id": "blob",
        "thumbnail_blob_id": "blob",
        "executor_task_id": "ext",
        # `CMP-SEAL-C1`, migration 0039 (ADR-0025 decisions 2, 3, 14, 15, 21): the identities of the version
        # comparison core and the columns that hold them -- a build of the matrix, an edit, an accepted AI link, a
        # series, a transition, a sheet pair and its content-keyed result, the edit an undo reverses, the version
        # order a build or an edit is bound to, the series a queue item belongs to and the series a series restarts.
        "comparison_matrix_id": "cmx",
        "comparison_matrix_edit_id": "cme",
        "undoes_edit_id": "cme",
        "comparison_ai_link_id": "cak",
        "comparison_series_id": "cser",
        "restarted_from_series_id": "cser",
        "comparison_transition_id": "ctn",
        "comparison_sheet_pair_id": "ctp",
        "comparison_sheet_pair_result_id": "csp",
        "result_id": "csp",
        "order_id": "cvo",
        "page_version_uid": "ver",
        "other_version_uid": "ver",
        "absent_version_uid": "ver",
        "page_a_profile_id": "cpr",
        "page_b_profile_id": "cpr",
        "mask_blob_id": "blob",
        # `CMP-SEAL-C2`, migration 0040 (ADR-0025 decisions 2, 15, 19, 20): the identities of the version comparison AI,
        # specifications, reports and launch queue and the columns that hold them -- a consented AI job (which a queue item, a
        # specification comparison, a report and a launch entry name), the content-keyed pair-check answers a question and its
        # reverse question use, a question, a sheet item, a content-keyed sheet description, a specification extraction (the two
        # a comparison reads), a comparison, a report with its parts and files (and the analytic report a client report is
        # prepared from), and a launch entry; the page a description names, the page a question hints at and who consented.
        "comparison_ai_job_id": "cai",
        "comparison_ai_pair_answer_id": "cpa",
        "answer_id": "cpa",
        "reverse_answer_id": "cpa",
        "comparison_ai_pair_question_id": "cpq",
        "comparison_ai_sheet_item_id": "csi",
        "comparison_sheet_description_id": "csd",
        "comparison_spec_extraction_id": "cse",
        "extraction_a_id": "cse",
        "extraction_b_id": "cse",
        "comparison_spec_comparison_id": "cscp",
        "comparison_report_id": "crt",
        "prepared_from_report_id": "crt",
        "comparison_report_part_id": "crpt",
        "comparison_report_artifact_id": "cra",
        "comparison_launch_entry_id": "cle",
        "page_profile_id": "cpr",
        "hint_version_uid": "ver",
        "consented_by_user_uid": "usr",
        # `CMP-SEAL-C3`, migration 0041: all stage identities and their cross-row references.
        "stage_upload_id": "stu",
        "stage_upload_file_id": "suf",
        "stage_upload_candidate_id": "suc",
        "source_blob_id": "blob",
        "pdf_blob_id": "blob",
        "stage_assembly_id": "sas",
        "stage_assembly_member_id": "sam",
        "reverses_member_id": "sam",
        "stage_pair_id": "stp",
        "left_document_uid": "doc",
        "right_document_uid": "doc",
        "stage_link_revision_id": "slk",
        "base_revision_id": "slk",
        "stage_link_item_id": "sli",
        "left_profile_id": "cpr",
        "right_profile_id": "cpr",
        "stage_text_fragment_id": "stf",
        "stage_text_exclusion_id": "ste",
        "stage_text_difference_id": "std",
        "stage_text_hint_id": "sth",
        "left_fragment_id": "stf",
        "right_fragment_id": "stf",
        "source_fragment_id": "stf",
        "target_fragment_id": "stf",
        "stage_chain_run_id": "crn",
        "stage_chain_step_id": "cst",
        # `EXEC2-SEAL-1`, migration 0046 (ADR-0026 decisions 3, 4 and 7): an enrollment grant and the runner token it
        # produced, an install session and the sealed key it holds.
        "enrollment_id": "exen",
        "runner_token_id": "ern",
        "install_id": "exai",
        "key_secret_id": "exs",
        # `EXEC2-SEAL-2`, migrations 0047 and 0048 (ADR-0026 decisions 10 to 12): a group revision (a member row, a rule and a
        # Run or comparison job name it), a rule revision (a Run or job names the one that admitted it) and a routing-mode
        # change.
        "group_revision_id": "exgr",
        "executor_group_revision_id": "exgr",
        "rule_revision_id": "exrr",
        "routing_rule_revision_id": "exrr",
        "mode_event_id": "exrm",
        # `CMP-SEAL-C4`, migration 0042 (the stage review, ADR-0025): the stage AI's unit and its review, classification and
        # synthesis answers, the graphic evidence, a link repair with its events and the two link revisions it names, the run
        # a repair's recompute started, a change card with its evidence and its verdicts (a verdict can carry a previous one
        # forward), the revision a run is read at, and the durable batch of runs with its items.
        "stage_ai_unit_id": "saunit",
        "stage_ai_review_id": "sarev",
        "stage_ai_classification_id": "sacls",
        "stage_ai_synthesis_id": "sasyn",
        "stage_graphic_evidence_id": "sge",
        "source_graphic_evidence_id": "sge",
        "source_difference_id": "std",
        "stage_link_repair_id": "crp",
        "stage_link_repair_event_id": "crpe",
        "before_revision_id": "slk",
        "after_revision_id": "slk",
        "effective_link_revision_id": "slk",
        "recompute_run_id": "crn",
        "stage_change_card_id": "ccd",
        "stage_card_evidence_id": "sce",
        "stage_card_verdict_id": "cdv",
        "carried_from_verdict_id": "cdv",
        "stage_chain_batch_id": "scb",
        "stage_chain_batch_item_id": "scbi",
        # `0059_decision_memory` (`ADR-0027`): the memory's four identities and the bare identities of where a case came from
        # (no foreign key: they resolve nowhere once the project is erased). ``case_id`` is a foreign key between memory tables.
        "case_id": "dmc",
        "memory_decision_id": "dmd",
        "status_event_id": "dmw",
        "crop_id": "dmx",
        "origin_observation_id": "fobs",
        "origin_finding_uid": "fnd",
        "origin_project_uid": "prj",
        "origin_document_uid": "doc",
        "origin_version_uid": "ver",
        "origin_run_id": "run",
        "source_decision_id": "dec",
        # `0052_document_archive` (`UI-PARITY-P0G`): who archived a document (this map lacked it).
        "archived_by_user_uid": "usr",
        # `0055_work_schedule` (`UI-PARITY-P0P`): the five journals are identified by an event identity and name accounts.
        "setting_event_id": "evt",
        "plan_event_id": "evt",
        "calendar_event_id": "evt",
        "absence_event_id": "evt",
        "schedule_event_id": "evt",
        "engineer_user_uid": "usr",
    }
    assert (set(prefix_by_column.values()) | set(PREFIX_BY_TABLE_COLUMN.values())) <= {
        identity.prefix for identity in IDENTITY_TYPES_BY_ENTITY.values()
    }

    with migrated_engine.connect() as connection:
        base_tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT c.relname FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r'"
                )
            )
        }
        definitions: dict[str, list[str]] = {}
        for table, definition in connection.execute(
            text(
                "SELECT t.relname, pg_get_constraintdef(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN pg_namespace n ON n.oid = t.relnamespace "
                "WHERE n.nspname = 'public' AND c.contype = 'c'"
            )
        ):
            definitions.setdefault(table, []).append(definition)

    identity_columns = [
        (table, column)
        for table, column in _columns(migrated_engine)
        if table in base_tables
        and column.endswith(("_uid", "_id"))
        and column not in NON_CONTRACT_IDENTITY_COLUMNS
    ]
    assert len(identity_columns) >= 20, "the identity-column query found too few columns"
    # A stale table-qualified entry would silently exempt nothing today and a renamed column tomorrow.
    stale = [
        entry
        for entry in sorted(NON_CONTRACT_TABLE_COLUMNS | set(PREFIX_BY_TABLE_COLUMN))
        if entry not in set(identity_columns)
    ]
    assert stale == [], f"table-qualified entries naming no identity column: {stale}"

    missing = []
    for table, column in identity_columns:
        if (table, column) in NON_CONTRACT_TABLE_COLUMNS:
            continue
        prefix = PREFIX_BY_TABLE_COLUMN.get((table, column), prefix_by_column.get(column))
        assert prefix is not None, f"{table}.{column} has no declared prefix in this test"
        needle = pattern_for(prefix)
        if not any(
            column in definition and needle in definition
            for definition in definitions.get(table, [])
        ):
            missing.append(f"{table}.{column} (expects {needle})")
    assert missing == [], f"identity columns with no contract-pattern CHECK: {sorted(missing)}"


def test_the_current_verdict_view_reads_only_the_ledger(migrated_engine: Engine) -> None:
    """The projection must be rebuildable, so it may not read a cached column."""
    with migrated_engine.connect() as connection:
        definition = connection.execute(
            text("SELECT pg_get_viewdef('finding_current_verdict'::regclass, true)")
        ).scalar_one()
    assert "expert_decision_event" in definition
    assert "finding" in definition
    for cached in ("current_verdict_cache", "verdict_projection", "materialized"):
        assert cached not in definition
