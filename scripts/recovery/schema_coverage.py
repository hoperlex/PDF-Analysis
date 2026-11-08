"""The recovery tooling's closed declaration of the schema it restores and audits.

`RECOVERY-REBASE-01`. The W58 drill was written at migration head `0023`; migrations
`0024`-`0028` added eleven tables, three views, a Blob-reference column and a dozen guard
triggers, and nothing in the tooling noticed. This module is the one place that says what the
tooling believes the schema at head is, and :func:`audit_restored_schema` checks a restored
database against it with SELECT statements only. A migration that adds a table, a view, a
trigger, a sequence or a Blob-reference column therefore fails
``tests/integration/recovery/test_schema_coverage.py`` until this declaration (and, for a Blob
reference, ``blob_reference_audit``) is extended deliberately -- by a task that decides how the
restore proves the new object, or exempts it in writing here.

What each declaration is for:

* ``TABLES`` / ``EXEMPT_FROM_FINGERPRINT``: every base table is restored by ``pg_restore``.
  ``stand-fingerprint-v1`` (the frozen SQL in ``infra/deploy/copy-serve.sh``) compares the row
  count and a content digest of every table **except** those named ``norm%``; those are the
  explicit, listed exemption (the normative corpus is restored with the dump, but its parity is
  the norms import's claim, not this fingerprint's). Three of them still carry Blob references
  and are audited by ``blob_reference_audit``.
* ``TRIGGERS``: the guard triggers (``am_immutable_row``, ``am_append_only``, state and frozen
  column guards, deferred co-commit constraint triggers) are part of the data's meaning: an
  immutable table restored without its trigger is an editable one. The audit compares name,
  function, event mask and enabled state, so a trigger dropped, disabled or re-declared on a
  narrower event set is refused.
* ``SEQUENCES``: a restored sequence behind its table's rows hands out a duplicate on the next
  write; ``pg_restore`` sets them, and this proves it did.

This module never opens a transaction; the caller owns a stable read-only one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

HEAD = "0060_run_from_stage"

#: Every base table of the schema at ``HEAD`` (``relkind`` ``r``, schema ``public``).
TABLES = frozenset((
    "account_release_mark", "alembic_version", "analysis_artifact_publication", "analysis_preset_revision", "app_user", "app_user_role",
    "ar_v3_run_group", "ar_v3_run_group_member", "attempt", "audit_event", "audit_run", "blob", "command_record", "comparison_model_call", "comparison_page_profile", "comparison_sheet_link", "comparison_summary",
    "comparison_upload", "comparison_upload_file", "comparison_upload_part", "comparison_upload_set", "comparison_version_order", "comparison_work", "comparison_work_attempt",
    "comparison_ai_link", "comparison_matrix", "comparison_matrix_edit", "comparison_series", "comparison_sheet_pair",
    "comparison_sheet_pair_result", "comparison_transition",
    "comparison_ai_job", "comparison_ai_pair_answer", "comparison_ai_pair_question", "comparison_ai_sheet_item",
    "comparison_launch_entry", "comparison_launch_queue", "comparison_report", "comparison_report_artifact",
    "comparison_report_part", "comparison_sheet_description", "comparison_spec_comparison",
    "comparison_spec_extraction",
    # `0041_comparison_stage_core`: upload, pair, link, raw evidence and chain storage.
    "stage_upload", "stage_upload_file", "stage_upload_part", "stage_upload_candidate",
    "stage_assembly", "stage_assembly_member", "stage_pair", "stage_link_revision",
    "stage_link_item", "stage_text_fragment", "stage_text_exclusion",
    "stage_text_difference", "stage_text_hint", "stage_chain_run", "stage_chain_step",
    # `0042_comparison_stage_review`: stage AI units and their immutable results, graphic evidence,
    # link repairs, expert change cards and verdicts, and the durable batch. `0043`, `0044` and `0045`
    # add no table. `0046_executor_capacity_enroll` adds `executor_enrollment` and `executor_agent_install`
    # (listed beside the other executor tables below). `0047_executor_groups_rules` adds `executor_group`,
    # `executor_group_revision`, `executor_group_member`, `executor_routing_rule_revision` and
    # `executor_routing_mode_event` (`EXEC2-SEAL-2`, also listed there); `0048_dispatch_time_binding`,
    # `0049_stage_identity_checks` and `0050_viewer_role` add no table.
    "stage_ai_unit", "stage_ai_review", "stage_ai_classification", "stage_ai_synthesis",
    "stage_graphic_evidence", "stage_link_repair", "stage_link_repair_event", "stage_change_card",
    "stage_card_evidence", "stage_card_verdict", "stage_chain_batch", "stage_chain_batch_item",
    "contract_state_transition", "document",
    # `0053_document_tags` adds `document_tag` and `0054_finding_execution_status` adds `finding_execution_status`
    # (`UI-PARITY-P0H`, `UI-PARITY-P0I`); `0051` and `0052` add columns only.
    "document_tag", "finding_execution_status",
    # `0055_work_schedule` (`UI-PARITY-P0P`): five append-only journals of «График работ», each `am_immutable_row`.
    "engineer_absence_event", "schedule_plan_event", "schedule_setting_event", "work_assignment_schedule_event",
    "work_calendar_event",
    "document_version", "document_version_classification", "document_version_classification_correction",
    "execution_control", "executor_agent_install", "executor_connection", "executor_connection_revision", "executor_enrollment", "executor_group",
    "executor_group_member", "executor_group_revision", "executor_probe",
    "executor_route_event", "executor_routing_mode_event", "executor_routing_rule_revision", "executor_runner_token", "executor_secret", "executor_task", "expert_decision_event", "finding", "finding_evidence", "finding_observation",
    "finding_observation_norm_citation", "input_manifest_entry", "job", "lease", "model_call", "norm_chunk",
    "norm_chunk_build", "norm_current_snapshot", "norm_current_snapshot_event", "norm_custody_admission",
    "norm_custody_binding", "norm_document", "norm_embedding", "norm_embedding_build",
    "norm_embedding_profile", "norm_paragraph", "norm_repair_call", "norm_retrieval_set", "norms_snapshot",
    "optimisation_pass", "optimisation_proposal", "optimisation_proposal_decision", "price_list_position",
    "price_list_revision", "project", "provider_call_effect", "registration_request", "release",
    "release_revision", "stage_result", "vendor_list_entry", "vendor_list_revision", "work_assignment",
    "work_assignment_event", "worker"
))

#: Views at ``HEAD``. A view carries no rows; it is restored from the dump and checked by name.
VIEWS = frozenset((
    "executor_route_current", "finding_current_verdict", "version_classification_current",
    "version_classification_revision", "work_assignment_current",
))

#: The frozen ``stand-fingerprint-v1`` SQL selects ``c.relname NOT LIKE 'norm%'``. These are the
#: tables it does not count, listed literally so that a new ``norm*`` table (or a rename into
#: the prefix) is a visible decision and not a silent drop out of the digest comparison.
EXEMPT_FROM_FINGERPRINT = frozenset((
    "norm_chunk", "norm_chunk_build", "norm_current_snapshot", "norm_current_snapshot_event",
    "norm_custody_admission", "norm_custody_binding", "norm_document", "norm_embedding",
    "norm_embedding_build", "norm_embedding_profile", "norm_paragraph", "norm_repair_call",
    "norm_retrieval_set", "norms_snapshot",
))

#: Tables whose rows ``stand-fingerprint-v1`` counts and digests: what a restore proves equal.
FINGERPRINTED_TABLES = TABLES - EXEMPT_FROM_FINGERPRINT

#: ``(table, trigger, function, pg_trigger.tgtype)``. ``tgtype`` bits: 1 row, 2 before,
#: 4 insert, 8 delete, 16 update, 32 truncate. So 5 and 7 are AFTER and BEFORE INSERT row
#: triggers, 11 BEFORE DELETE, 19 BEFORE UPDATE, 23 BEFORE INSERT OR UPDATE, 27 BEFORE UPDATE OR DELETE (the
#: immutable and append-only guards), 31 BEFORE INSERT OR UPDATE OR DELETE, 34 BEFORE TRUNCATE.
TRIGGERS = (
    ("account_release_mark", "trg_account_release_mark", "am_guard_account_release_mark", 31),
    ("analysis_artifact_publication", "trg_analysis_artifact_frozen_guard", "am_guard_frozen_columns", 19),
    ("analysis_artifact_publication", "trg_analysis_artifact_state_guard", "am_guard_durable_effect_transition", 23),
    # `0032_ar_v3_run_group`: the group and its six members are immutable; the group's
    # co-commit check is a deferred AFTER INSERT constraint trigger (5 = ROW | INSERT).
    ("ar_v3_run_group", "trg_ar_v3_group_complete", "am_ar_v3_group_complete", 5),
    ("ar_v3_run_group", "trg_ar_v3_run_group_frozen", "am_immutable_row", 27),
    ("ar_v3_run_group_member", "trg_ar_v3_run_group_member_frozen", "am_immutable_row", 27),
    # `0037_analysis_presets`: the revisions of a preset are append-only (27 = ROW | BEFORE | DELETE |
    # UPDATE) and chained on INSERT (7 = ROW | BEFORE | INSERT); a run records its preset only with
    # the executor that preset names (an INSERT check on `audit_run`).
    ("analysis_preset_revision", "trg_analysis_preset_revision_chain", "am_check_analysis_preset_chain", 7),
    ("analysis_preset_revision", "trg_analysis_preset_revision_immutable", "am_immutable_row", 27),
    ("attempt", "trg_attempt_frozen_guard", "am_guard_frozen_columns", 19),
    ("attempt", "trg_attempt_state_guard", "am_guard_state_transition", 23),
    ("audit_event", "trg_audit_event_append_only", "am_append_only", 27),
    # `0048_dispatch_time_binding` (`EXEC2-SEAL-2`): the frozen guard of a run moved to its own function, which lets the
    # connection revision be written once, with `binding_state` pending -> bound (19 = ROW | BEFORE | UPDATE).
    ("audit_run", "trg_audit_run_frozen_guard", "am_guard_audit_run_frozen", 19),
    ("audit_run", "trg_audit_run_norm_set", "am_verify_run_norm_set", 23),
    ("audit_run", "trg_audit_run_preset_executor", "am_check_audit_run_preset", 7),
    ("audit_run", "trg_audit_run_state_guard", "am_guard_state_transition", 23),
    ("blob", "trg_blob_state_guard", "am_guard_state_transition", 23),
    ("blob", "trg_blob_write_once_guard", "am_guard_write_once_columns", 19),
    ("command_record", "trg_command_record_frozen_guard", "am_guard_frozen_columns", 19),
    ("command_record", "trg_command_record_state_guard", "am_guard_state_transition", 23),
    ("comparison_sheet_link", "trg_comparison_sheet_link_chain", "am_check_comparison_sheet_link_chain", 7),
    ("comparison_sheet_link", "trg_comparison_sheet_link_immutable", "am_immutable_row", 27),
    ("comparison_summary", "trg_comparison_summary_immutable", "am_immutable_row", 27),
    ("comparison_summary", "trg_comparison_summary_latest", "am_check_comparison_summary", 7),
    # `0038_comparison_foundation`: the comparison tables' guards. 19 = ROW | BEFORE | UPDATE (frozen,
    # write-once and state-edge guards), 7 = ROW | BEFORE | INSERT (the prepared-first, token-first,
    # chain and page checks), 27 = the immutable order revisions.
    ("comparison_model_call", "trg_comparison_model_call_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_model_call", "trg_comparison_model_call_prepared_first", "am_check_comparison_model_call_insert", 7),
    ("comparison_model_call", "trg_comparison_model_call_state_edges", "am_guard_comparison_state_edges", 19),
    ("comparison_model_call", "trg_comparison_model_call_write_once", "am_guard_write_once_columns", 19),
    ("comparison_page_profile", "trg_comparison_page_profile_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_page_profile", "trg_comparison_page_profile_page", "am_check_comparison_page_profile", 7),
    ("comparison_page_profile", "trg_comparison_page_profile_write_once", "am_guard_write_once_columns", 19),
    ("comparison_upload", "trg_comparison_upload_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_upload", "trg_comparison_upload_state_edges", "am_guard_comparison_state_edges", 19),
    ("comparison_upload_file", "trg_comparison_upload_file_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_upload_file", "trg_comparison_upload_file_state_edges", "am_guard_comparison_state_edges", 19),
    ("comparison_upload_file", "trg_comparison_upload_file_write_once", "am_guard_write_once_columns", 19),
    ("comparison_upload_part", "trg_comparison_upload_part_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_upload_part", "trg_comparison_upload_part_state_edges", "am_guard_comparison_state_edges", 19),
    ("comparison_upload_part", "trg_comparison_upload_part_token_first", "am_check_comparison_upload_part_insert", 7),
    ("comparison_upload_set", "trg_comparison_upload_set_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_upload_set", "trg_comparison_upload_set_state_edges", "am_guard_comparison_state_edges", 19),
    ("comparison_version_order", "trg_comparison_version_order_chain", "am_check_comparison_version_order_chain", 7),
    ("comparison_version_order", "trg_comparison_version_order_immutable", "am_immutable_row", 27),
    ("comparison_work", "trg_comparison_work_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_work", "trg_comparison_work_state_edges", "am_guard_comparison_state_edges", 19),
    ("comparison_work", "trg_comparison_work_write_once", "am_guard_write_once_columns", 19),
    ("comparison_work_attempt", "trg_comparison_work_attempt_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_work_attempt", "trg_comparison_work_attempt_state_edges", "am_guard_comparison_state_edges", 19),
    ("comparison_work_attempt", "trg_comparison_work_attempt_write_once", "am_guard_write_once_columns", 19),
    # `0039_comparison_core`: the guards of the version comparison core. 19 = ROW | BEFORE | UPDATE (frozen,
    # write-once and state-edge guards), 7 = ROW | BEFORE | INSERT (chain and consistency checks), 27 = the
    # append-only builds, edits and AI links.
    ("comparison_ai_link", "trg_comparison_ai_link_immutable", "am_immutable_row", 27),
    ("comparison_ai_link", "trg_comparison_ai_link_pages", "am_check_comparison_ai_link", 7),
    ("comparison_matrix", "trg_comparison_matrix_chain", "am_check_comparison_matrix_chain", 7),
    ("comparison_matrix", "trg_comparison_matrix_document", "am_check_comparison_core_document", 7),
    ("comparison_matrix", "trg_comparison_matrix_immutable", "am_immutable_row", 27),
    ("comparison_matrix_edit", "trg_comparison_matrix_edit_chain", "am_check_comparison_matrix_edit_chain", 7),
    ("comparison_matrix_edit", "trg_comparison_matrix_edit_document", "am_check_comparison_core_document", 7),
    ("comparison_matrix_edit", "trg_comparison_matrix_edit_immutable", "am_immutable_row", 27),
    ("comparison_series", "trg_comparison_series_document", "am_check_comparison_core_document", 7),
    ("comparison_series", "trg_comparison_series_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_series", "trg_comparison_series_inputs", "am_check_comparison_series", 7),
    ("comparison_series", "trg_comparison_series_state_edges", "am_guard_comparison_core_state_edges", 19),
    ("comparison_sheet_pair", "trg_comparison_sheet_pair_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_sheet_pair", "trg_comparison_sheet_pair_pages", "am_check_comparison_sheet_pair", 7),
    ("comparison_sheet_pair", "trg_comparison_sheet_pair_state_edges", "am_guard_comparison_core_state_edges", 19),
    ("comparison_sheet_pair_result", "trg_comparison_sheet_pair_result_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_sheet_pair_result", "trg_comparison_sheet_pair_result_pages", "am_check_comparison_sheet_pair_result", 7),
    ("comparison_sheet_pair_result", "trg_comparison_sheet_pair_result_write_once", "am_guard_write_once_columns", 19),
    ("comparison_transition", "trg_comparison_transition_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_transition", "trg_comparison_transition_state_edges", "am_guard_comparison_core_state_edges", 19),
    ("comparison_transition", "trg_comparison_transition_versions", "am_check_comparison_transition", 7),
    # `0040_comparison_ai_reports`: the guards of the version comparison AI, specifications, reports and launch queue.
    # 19 = ROW | BEFORE | UPDATE, 7 = ROW | BEFORE | INSERT, 27 = the append-only answers, descriptions, extractions
    # and report files.
    # `0048_dispatch_time_binding`: the admission columns are frozen; the consent guard was re-created with the
    # write-once binding exception (same name, function and mask).
    ("comparison_ai_job", "trg_comparison_ai_job_binding_pin", "am_guard_frozen_columns", 19),
    ("comparison_ai_job", "trg_comparison_ai_job_consent", "am_guard_comparison_ai_job_consent", 19),
    ("comparison_ai_job", "trg_comparison_ai_job_document", "am_check_comparison_core_document", 7),
    ("comparison_ai_job", "trg_comparison_ai_job_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_ai_job", "trg_comparison_ai_job_scope", "am_check_comparison_ai_job_scope", 7),
    ("comparison_ai_job", "trg_comparison_ai_job_state_edges", "am_guard_comparison_ai_state_edges", 19),
    ("comparison_ai_pair_answer", "trg_comparison_ai_pair_answer_immutable", "am_immutable_row", 27),
    ("comparison_ai_pair_question", "trg_comparison_ai_pair_question_document", "am_check_comparison_core_document", 7),
    ("comparison_ai_pair_question", "trg_comparison_ai_pair_question_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_ai_pair_question", "trg_comparison_ai_pair_question_pages", "am_check_comparison_ai_pair_question", 7),
    ("comparison_ai_pair_question", "trg_comparison_ai_pair_question_state_edges", "am_guard_comparison_ai_state_edges", 19),
    ("comparison_ai_sheet_item", "trg_comparison_ai_sheet_item_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_ai_sheet_item", "trg_comparison_ai_sheet_item_pair", "am_check_comparison_ai_sheet_item", 7),
    ("comparison_ai_sheet_item", "trg_comparison_ai_sheet_item_state_edges", "am_guard_comparison_ai_state_edges", 19),
    ("comparison_launch_entry", "trg_comparison_launch_entry_document", "am_check_comparison_core_document", 7),
    ("comparison_launch_entry", "trg_comparison_launch_entry_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_launch_entry", "trg_comparison_launch_entry_state_edges", "am_guard_comparison_ai_state_edges", 19),
    ("comparison_launch_queue", "trg_comparison_launch_queue_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_report", "trg_comparison_report_document", "am_check_comparison_core_document", 7),
    ("comparison_report", "trg_comparison_report_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_report", "trg_comparison_report_inputs", "am_check_comparison_report", 7),
    ("comparison_report", "trg_comparison_report_state_edges", "am_guard_comparison_ai_state_edges", 19),
    ("comparison_report_artifact", "trg_comparison_report_artifact_immutable", "am_immutable_row", 27),
    ("comparison_report_part", "trg_comparison_report_part_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_report_part", "trg_comparison_report_part_transition", "am_check_comparison_report_part", 7),
    ("comparison_sheet_description", "trg_comparison_sheet_description_immutable", "am_immutable_row", 27),
    ("comparison_sheet_description", "trg_comparison_sheet_description_subject", "am_check_comparison_sheet_description", 7),
    ("comparison_spec_comparison", "trg_comparison_spec_comparison_document", "am_check_comparison_core_document", 7),
    ("comparison_spec_comparison", "trg_comparison_spec_comparison_frozen_guard", "am_guard_frozen_columns", 19),
    ("comparison_spec_comparison", "trg_comparison_spec_comparison_inputs", "am_check_comparison_spec_comparison", 7),
    ("comparison_spec_comparison", "trg_comparison_spec_comparison_state_edges", "am_guard_comparison_ai_state_edges", 19),
    ("comparison_spec_extraction", "trg_comparison_spec_extraction_immutable", "am_immutable_row", 27),
    ("comparison_spec_extraction", "trg_comparison_spec_extraction_version", "am_check_comparison_spec_extraction", 7),
    # `0041_comparison_stage_core`: project scope, revision ordering and immutable evidence.
    ("engineer_absence_event", "trg_engineer_absence_event_immutable", "am_immutable_row", 27),
    ("schedule_plan_event", "trg_schedule_plan_event_immutable", "am_immutable_row", 27),
    ("schedule_setting_event", "trg_schedule_setting_event_immutable", "am_immutable_row", 27),
    ("stage_upload_candidate", "trg_stage_upload_candidate_scope", "am_check_stage_upload_candidate_scope", 23),
    ("stage_pair", "trg_stage_pair_project", "am_check_stage_pair_project", 23),
    ("stage_assembly_member", "trg_stage_assembly_member_scope", "am_check_stage_assembly_member", 7),
    ("stage_link_revision", "trg_stage_link_revision_chain", "am_check_stage_link_chain", 7),
    ("stage_link_item", "trg_stage_link_item_scope", "am_check_stage_link_item_scope", 7),
    ("stage_text_fragment", "trg_stage_text_fragment_scope", "am_check_stage_text_fragment_scope", 7),
    ("stage_text_exclusion", "trg_stage_text_exclusion_scope", "am_check_stage_text_evidence_scope", 7),
    ("stage_text_difference", "trg_stage_text_difference_scope", "am_check_stage_text_evidence_scope", 7),
    ("stage_text_hint", "trg_stage_text_hint_scope", "am_check_stage_text_evidence_scope", 7),
    ("stage_chain_run", "trg_stage_chain_scope", "am_check_stage_chain_scope", 23),
    ("stage_assembly", "trg_stage_assembly_immutable", "am_immutable_row", 27),
    ("stage_assembly_member", "trg_stage_assembly_member_immutable", "am_immutable_row", 27),
    ("stage_link_revision", "trg_stage_link_revision_immutable", "am_immutable_row", 27),
    ("stage_link_item", "trg_stage_link_item_immutable", "am_immutable_row", 27),
    ("stage_text_fragment", "trg_stage_text_fragment_immutable", "am_immutable_row", 27),
    ("stage_text_exclusion", "trg_stage_text_exclusion_immutable", "am_immutable_row", 27),
    ("stage_text_difference", "trg_stage_text_difference_immutable", "am_immutable_row", 27),
    ("stage_text_hint", "trg_stage_text_hint_immutable", "am_immutable_row", 27),
    ("stage_upload", "trg_stage_upload_frozen_guard", "am_guard_frozen_columns", 19),
    ("stage_upload_file", "trg_stage_upload_file_frozen_guard", "am_guard_frozen_columns", 19),
    ("stage_upload_part", "trg_stage_upload_part_frozen_guard", "am_guard_frozen_columns", 19),
    ("stage_upload_candidate", "trg_stage_upload_candidate_frozen_guard", "am_guard_frozen_columns", 19),
    ("stage_pair", "trg_stage_pair_frozen_guard", "am_guard_frozen_columns", 19),
    ("stage_chain_run", "trg_stage_chain_run_frozen_guard", "am_guard_frozen_columns", 19),
    ("stage_chain_step", "trg_stage_chain_step_frozen_guard", "am_guard_frozen_columns", 19),
    ("stage_upload_file", "trg_stage_upload_file_write_once", "am_guard_write_once_columns", 19),
    ("stage_upload_candidate", "trg_stage_upload_candidate_write_once", "am_guard_write_once_columns", 19),
    ("stage_pair", "trg_stage_pair_write_once", "am_guard_write_once_columns", 19),
    # `0042_comparison_stage_review`: 19 = ROW | BEFORE | UPDATE (frozen pins), 23 = ROW | BEFORE |
    # INSERT | UPDATE (scope checks), 27 = ROW | BEFORE | DELETE | UPDATE (the nine immutable results).
    ("stage_chain_run", "trg_stage_chain_c4_pins", "am_guard_frozen_columns", 19),
    ("stage_chain_run", "trg_stage_effective_revision", "am_check_stage_effective_revision", 23),
    ("comparison_ai_job", "trg_stage_ai_job_scope", "am_check_stage_ai_job_scope", 23),
    ("comparison_ai_job", "trg_stage_ai_job_pin", "am_guard_frozen_columns", 19),
    ("stage_ai_unit", "trg_stage_ai_unit_scope", "am_check_stage_c4_scope", 23),
    ("stage_graphic_evidence", "trg_stage_graphic_evidence_scope", "am_check_stage_c4_scope", 23),
    ("stage_link_repair", "trg_stage_link_repair_scope", "am_check_stage_c4_scope", 23),
    ("stage_change_card", "trg_stage_change_card_scope", "am_check_stage_c4_scope", 23),
    ("stage_card_evidence", "trg_stage_card_evidence_scope", "am_check_stage_c4_scope", 23),
    ("stage_card_verdict", "trg_stage_card_verdict_scope", "am_check_stage_c4_scope", 23),
    ("stage_chain_batch_item", "trg_stage_chain_batch_item_scope", "am_check_stage_c4_scope", 23),
    ("stage_link_repair_event", "trg_stage_link_repair_event_scope", "am_check_stage_c4_scope", 23),
    ("stage_ai_review", "trg_stage_ai_review_immutable", "am_immutable_row", 27),
    ("stage_ai_classification", "trg_stage_ai_classification_immutable", "am_immutable_row", 27),
    ("stage_ai_synthesis", "trg_stage_ai_synthesis_immutable", "am_immutable_row", 27),
    ("stage_graphic_evidence", "trg_stage_graphic_evidence_immutable", "am_immutable_row", 27),
    ("stage_link_repair", "trg_stage_link_repair_immutable", "am_immutable_row", 27),
    ("stage_link_repair_event", "trg_stage_link_repair_event_immutable", "am_immutable_row", 27),
    ("stage_change_card", "trg_stage_change_card_immutable", "am_immutable_row", 27),
    ("stage_card_evidence", "trg_stage_card_evidence_immutable", "am_immutable_row", 27),
    ("stage_card_verdict", "trg_stage_card_verdict_immutable", "am_immutable_row", 27),
    ("stage_ai_unit", "trg_stage_ai_unit_frozen_guard", "am_guard_frozen_columns", 19),
    ("stage_chain_batch", "trg_stage_chain_batch_frozen_guard", "am_guard_frozen_columns", 19),
    ("stage_chain_batch_item", "trg_stage_chain_batch_item_frozen_guard", "am_guard_frozen_columns", 19),
    # `0043_stage_ai_generations`: a unit's generation is pinned once written.
    ("stage_ai_unit", "trg_stage_ai_generation_pin", "am_guard_frozen_columns", 19),
    ("contract_state_transition", "trg_contract_state_transition_immutable", "am_immutable_row", 31),
    ("document_version", "trg_document_version_immutable", "am_immutable_row", 27),
    ("document_version_classification", "trg_document_version_classification_immutable", "am_immutable_row", 27),
    ("document_version_classification_correction", "trg_document_version_classification_correction_chain", "am_check_classification_correction_chain", 7),
    ("document_version_classification_correction", "trg_document_version_classification_correction_immutable", "am_immutable_row", 27),
    # `0046_executor_capacity_enroll`: the enrollment grant's identity, hash and expiry are frozen and its
    # redemption and revocation write-once; an install session's identity, host and user are frozen and its
    # observed host key, confirmed fingerprint and finish are write-once (19 = ROW | BEFORE | UPDATE).
    ("executor_agent_install", "trg_executor_agent_install_frozen_guard", "am_guard_frozen_columns", 19),
    ("executor_agent_install", "trg_executor_agent_install_write_once", "am_guard_write_once_columns", 19),
    ("executor_connection", "trg_executor_connection_frozen_guard", "am_guard_frozen_columns", 19),
    ("executor_connection", "trg_executor_connection_write_once", "am_guard_write_once_columns", 19),
    ("executor_connection_revision", "trg_executor_connection_revision_immutable", "am_immutable_row", 27),
    ("executor_enrollment", "trg_executor_enrollment_frozen_guard", "am_guard_frozen_columns", 19),
    ("executor_enrollment", "trg_executor_enrollment_write_once", "am_guard_write_once_columns", 19),
    # `0047_executor_groups_rules` (`EXEC2-SEAL-2`): a group's identity and name are frozen, its archive write-once and
    # the row is never deleted (11 = ROW | BEFORE | DELETE); a revision and a member are immutable, a revision is numbered
    # without a gap and a member is homogeneous with it and refused once the revision has the members it declared; the
    # revision commits with exactly those members (a deferred AFTER INSERT constraint trigger, 5); a rule and a
    # routing-mode event are append-only, a rule names an active group and an event is numbered without a gap
    # (7 = ROW | BEFORE | INSERT).
    ("executor_group", "trg_executor_group_frozen_guard", "am_guard_frozen_columns", 19),
    ("executor_group", "trg_executor_group_no_delete", "am_immutable_row", 11),
    ("executor_group", "trg_executor_group_write_once", "am_guard_write_once_columns", 19),
    ("executor_group_member", "trg_executor_group_member_homogeneous", "am_check_executor_group_member", 7),
    ("executor_group_member", "trg_executor_group_member_immutable", "am_immutable_row", 27),
    ("executor_group_revision", "trg_executor_group_revision_chain", "am_check_executor_group_revision", 7),
    ("executor_group_revision", "trg_executor_group_revision_has_members", "am_require_executor_group_members", 5),
    ("executor_group_revision", "trg_executor_group_revision_immutable", "am_immutable_row", 27),
    ("executor_probe", "trg_executor_probe_frozen_guard", "am_guard_frozen_columns", 19),
    ("executor_route_event", "trg_executor_route_event_append_only", "am_append_only", 27),
    ("executor_routing_mode_event", "trg_executor_routing_mode_event_append_only", "am_append_only", 27),
    ("executor_routing_mode_event", "trg_executor_routing_mode_event_number", "am_check_executor_routing_mode_event", 7),
    ("executor_routing_rule_revision", "trg_executor_routing_rule_revision_append_only", "am_append_only", 27),
    ("executor_routing_rule_revision", "trg_executor_routing_rule_revision_group", "am_check_executor_routing_rule", 7),
    ("executor_runner_token", "trg_executor_runner_token_frozen_guard", "am_guard_frozen_columns", 19),
    ("executor_runner_token", "trg_executor_runner_token_write_once", "am_guard_write_once_columns", 19),
    ("executor_secret", "trg_executor_secret_frozen_guard", "am_guard_frozen_columns", 19),
    ("executor_secret", "trg_executor_secret_write_once", "am_guard_write_once_columns", 19),
    ("executor_task", "trg_executor_task_frozen_guard", "am_guard_frozen_columns", 19),
    ("executor_task", "trg_executor_task_write_once", "am_guard_write_once_columns", 19),
    ("expert_decision_event", "trg_expert_decision_event_append_only", "am_append_only", 27),
    ("finding_evidence", "trg_finding_evidence_immutable", "am_immutable_row", 27),
    ("finding_observation", "trg_finding_observation_immutable", "am_immutable_row", 27),
    ("finding_observation", "trg_finding_observation_partition", "am_verify_norm_citation_partition", 5),
    ("finding_observation_norm_citation", "trg_finding_observation_norm_citation_guard", "am_verify_norm_citation", 7),
    ("finding_observation_norm_citation", "trg_finding_observation_norm_citation_immutable", "am_immutable_row", 27),
    ("finding_observation_norm_citation", "trg_norm_citation_partition", "am_verify_norm_citation_partition", 5),
    ("input_manifest_entry", "trg_input_manifest_entry_immutable", "am_immutable_row", 27),
    ("job", "trg_job_frozen_guard", "am_guard_frozen_columns", 19),
    ("job", "trg_job_state_guard", "am_guard_state_transition", 23),
    ("lease", "trg_lease_frozen_guard", "am_guard_frozen_columns", 19),
    ("model_call", "trg_model_call_immutable", "am_immutable_row", 27),
    ("norm_chunk", "trg_norm_chunk_no_update", "am_norm_chunk_no_update", 19),
    ("norm_chunk_build", "trg_norm_chunk_build_no_update", "am_norm_chunk_no_update", 19),
    ("norm_current_snapshot", "trg_norm_current_snapshot_guard", "am_guard_norm_current_snapshot", 31),
    ("norm_current_snapshot", "trg_norm_current_snapshot_no_truncate", "am_refuse_norm_current_snapshot_truncate", 34),
    ("norm_current_snapshot_event", "trg_norm_current_snapshot_event_designates", "am_require_current_norm_snapshot_event", 5),
    ("norm_current_snapshot_event", "trg_norm_current_snapshot_event_immutable", "am_immutable_row", 27),
    ("norm_current_snapshot_event", "trg_norm_current_snapshot_event_no_truncate", "am_refuse_norm_current_snapshot_truncate", 34),
    ("norm_current_snapshot_event", "trg_norm_current_snapshot_event_stamp", "am_stamp_norm_current_snapshot_event", 7),
    ("norm_custody_admission", "trg_norm_custody_admission_guard", "am_guard_norm_custody_admission", 31),
    ("norm_custody_binding", "trg_norm_custody_binding_guard", "am_guard_norm_custody_binding", 7),
    ("norm_custody_binding", "trg_norm_custody_binding_immutable", "am_immutable_row", 27),
    ("norm_document", "trg_norm_document_immutable", "am_immutable_row", 27),
    ("norm_embedding", "trg_norm_embedding_no_update", "am_norm_chunk_no_update", 19),
    ("norm_embedding_build", "trg_norm_embedding_build_no_update", "am_norm_chunk_no_update", 19),
    ("norm_embedding_profile", "trg_norm_embedding_profile_immutable", "am_immutable_row", 27),
    ("norm_paragraph", "trg_norm_paragraph_immutable", "am_immutable_row", 27),
    ("norm_repair_call", "trg_norm_repair_call_guard", "am_guard_norm_repair_call", 31),
    ("norm_retrieval_set", "trg_norm_retrieval_set_immutable", "am_immutable_row", 27),
    ("norm_retrieval_set", "trg_norm_retrieval_set_verified", "am_verify_norm_retrieval_set", 5),
    ("norms_snapshot", "trg_norms_snapshot_immutable", "am_immutable_row", 27),
    ("optimisation_pass", "trg_optimisation_pass_has_proposals", "am_require_optimisation_proposals", 5),
    ("optimisation_pass", "trg_optimisation_pass_immutable", "am_immutable_row", 27),
    ("optimisation_pass", "trg_optimisation_pass_scope", "am_check_optimisation_pass_scope", 7),
    ("optimisation_proposal", "trg_optimisation_proposal_immutable", "am_immutable_row", 27),
    ("optimisation_proposal", "trg_optimisation_proposal_prices", "am_check_optimisation_proposal_prices", 7),
    ("optimisation_proposal_decision", "trg_optimisation_proposal_decision_immutable", "am_immutable_row", 27),
    ("price_list_position", "trg_price_list_position_immutable", "am_immutable_row", 27),
    ("price_list_revision", "trg_price_list_revision_blob_available", "am_check_price_list_blob", 7),
    ("price_list_revision", "trg_price_list_revision_has_positions", "am_require_price_list_positions", 5),
    ("price_list_revision", "trg_price_list_revision_immutable", "am_immutable_row", 27),
    ("provider_call_effect", "trg_provider_call_effect_frozen_guard", "am_guard_frozen_columns", 19),
    ("provider_call_effect", "trg_provider_call_effect_state_guard", "am_guard_durable_effect_transition", 23),
    ("registration_request", "trg_registration_request_guard", "am_guard_registration_request", 31),
    ("release", "trg_release_append_only", "am_guard_release_append_only", 27),
    ("release_revision", "trg_release_revision_append_only", "am_guard_release_append_only", 27),
    ("vendor_list_entry", "trg_vendor_list_entry_immutable", "am_immutable_row", 27),
    ("vendor_list_revision", "trg_vendor_list_revision_has_entries", "am_require_vendor_list_entries", 5),
    ("vendor_list_revision", "trg_vendor_list_revision_immutable", "am_immutable_row", 27),
    ("work_assignment", "trg_work_assignment_has_assigned_event", "am_require_work_assignment_event", 5),
    ("work_assignment", "trg_work_assignment_immutable", "am_immutable_row", 27),
    ("work_assignment_event", "trg_work_assignment_event_immutable", "am_immutable_row", 27),
    ("work_assignment_schedule_event", "trg_work_assignment_schedule_event_immutable", "am_immutable_row", 27),
    ("work_calendar_event", "trg_work_calendar_event_immutable", "am_immutable_row", 27),
    ("worker", "trg_worker_frozen_guard", "am_guard_frozen_columns", 19),
)

#: The constraint triggers that are ``DEFERRABLE INITIALLY DEFERRED``: a parent row must
#: commit together with its children. They fire at commit, never during ``pg_restore``.
DEFERRED_TRIGGERS = frozenset((
    "trg_ar_v3_group_complete",
    "trg_executor_group_revision_has_members",
    "trg_finding_observation_partition",
    "trg_norm_citation_partition",
    "trg_norm_current_snapshot_event_designates",
    "trg_norm_retrieval_set_verified",
    "trg_optimisation_pass_has_proposals",
    "trg_price_list_revision_has_positions",
    "trg_vendor_list_revision_has_entries",
    "trg_work_assignment_has_assigned_event",
))

#: ``sequence -> (table, column)`` it numbers.
SEQUENCES = {
    "audit_event_sequence_no_seq": ("audit_event", "sequence_no"),
    "expert_decision_event_sequence_no_seq": ("expert_decision_event", "sequence_no"),
    "norm_chunk_norm_chunk_pk_seq": ("norm_chunk", "norm_chunk_pk"),
    "norm_document_norm_document_pk_seq": ("norm_document", "norm_document_pk"),
    "norm_embedding_norm_embedding_pk_seq": ("norm_embedding", "norm_embedding_pk"),
    "norm_paragraph_norm_paragraph_pk_seq": ("norm_paragraph", "norm_paragraph_pk"),
    "release_pk_seq": ("release", "pk"),
}

#: ``pg_constraint.contype -> count`` in schema ``public`` at ``HEAD``: p primary key, u unique,
#: f foreign key, c check, t constraint trigger. A restore that lost one is not the schema.
#: From the 0041 counts (c 1073, f 300, p 109, t 9, u 104): `0042_comparison_stage_review` adds twelve
#: tables and, net of the three check constraints it replaces in place, 65 checks, 44 foreign keys,
#: 12 primary keys and 19 unique constraints; `0043_stage_ai_generations` adds one check and swaps
#: one unique constraint for another; `0044_section_stats_uncapped` replaces six checks in place;
#: `0045_comparison_page_bounds` replaces seven page-number checks in place (same names, same count),
#: so no count moves; `0046_executor_capacity_enroll` adds two tables and, net of the two secret checks it
#: redefines in place, 47 checks (revision 1, task 2, runner token 6, connection 3, `executor_enrollment` 12,
#: `executor_agent_install` 23), four foreign keys (the enrollment's connection and runner token, the install's
#: connection and sealed key), two primary keys and two unique constraints (the enrollment's prefix and hash):
#: c 1186, f 348, p 123, u 125; `0047_executor_groups_rules` (`EXEC2-SEAL-2`) adds five tables and 33 checks (group 6,
#: revision 11 -- the declared member count among them --, member 4, rule 5, routing-mode event 7), four foreign keys
#: (the revision's group, the member's group revision and its connection revision, the rule's group revision), five
#: primary keys, four unique constraints (revision number, member tie-break order, rule number, event number) and one
#: constraint trigger (the deferred `trg_executor_group_revision_has_members`, contype `t`); `0048_dispatch_time_binding`
#: adds, on `audit_run` and on `comparison_ai_job`, 15 checks (7 and 8) and four foreign keys (the group and rule
#: revisions of each): c 1234, f 356, p 128, t 10, u 129 (measured on the stand at ``0048``); `0049_stage_identity_checks`
#: adds 43 identity-format checks and nothing else (`EXEC2-FIX-CMP-INVENTORY`): c 1277, the other four unchanged;
#: `0050_viewer_role` adds none. `0051`..`0054` (`UI-PARITY-P0F`..`P0I`) add c 7, f 6, p 2 (who started a run, the
#: document's archive, the tag and execution-status tables) and `0055_work_schedule` adds c 17, f 8, p 5 (the five
#: journals of «График работ»): c 1301, f 370, p 135, measured on a fresh database at ``0055`` on 2026-11-06.
#: `0056` replaces one check by a wider one under its name (no change) and `0057_decision_carryover` (`UI-B-14`) adds three
#: checks (the identity's shape, not itself, never a withdrawal) and one foreign key (the source decision): c 1304, f 371,
#: measured on a throwaway database at ``0057`` on 2026-11-07. `0058_finding_decision_origin` (`UI-A-73`) adds the same
#: three kinds to ``expert_decision_event`` (the identity's shape, not itself, only an accept or a reject) and one foreign
#: key: c 1307, f 372 measured on a throwaway database at ``0058`` on 2026-11-08. `0060_run_from_stage` (`UI-A-60`, `R-151i`)
#: adds, on ``audit_run``, four checks (the source's identity shape, not itself, the start stage, both-or-neither) and one
#: foreign key (the run whose outputs are reused): c 1311, f 373 (to be re-measured on the stand when `0059` is chained).
CONSTRAINT_COUNTS = {"c": 1311, "f": 373, "p": 135, "t": 10, "u": 129}

#: Indexes in schema ``public`` at ``HEAD`` (primary-key and unique indexes included): 386 at 0041,
#: plus 40 of 0042 (12 primary keys, 19 unique constraints, eight run indexes, one partial unique
#: index); 0043 swaps one unique index for another; 0044 and 0045 add none; 0046 adds eight (two primary keys,
#: two unique constraints, the partial unique index of one live grant per connection, the partial unique index of
#: one unfinished install per connection, and one listing index on each of the two tables); 0047 adds twelve (five primary
#: keys, four unique constraints, the partial unique index of an active group name, and one index each on the member's
#: connection and the rule's group revision); 0048 adds four (a group-revision index and a pending-work index on each of
#: `audit_run` and `comparison_ai_job`); 0049 and 0050 add none; 0051..0054 add four (the two new tables' keys and one
#: lookup each) and 0055 nine (five keys, four lookups): 463, measured at ``0055`` on 2026-11-06; `0057` adds the partial
#: index of the carried-from decision: 464, measured at ``0057`` on 2026-11-07; `0058` adds the same partial index on
#: ``expert_decision_event``: 465; `0060` adds the partial index of the run a run was started from: 466.
INDEX_COUNT = 466

#: Trigger functions that make a table immutable or append-only (the claim a restore must keep).
GUARD_FUNCTIONS = frozenset((
    "am_immutable_row", "am_append_only", "am_guard_release_append_only",
))

_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*\Z")
_MASK_NAMES = ((1, "ROW"), (2, "BEFORE"), (4, "INSERT"), (8, "DELETE"), (16, "UPDATE"),
               (32, "TRUNCATE"), (64, "INSTEAD"))

_VERSION = text("SELECT version_num FROM public.alembic_version")
_RELATIONS = text("""
    SELECT n.nspname AS schema_name, c.relname AS name, c.relkind::text AS kind,
           c.relispartition AS partition
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
       AND n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
     ORDER BY n.nspname COLLATE "C", c.relname COLLATE "C"
""")
_TRIGGER_ROWS = text("""
    SELECT n.nspname AS schema_name, c.relname AS table_name, t.tgname AS trigger_name,
           p.proname AS function_name, t.tgtype::integer AS mask,
           t.tgenabled::text AS enabled,
           (t.tgconstraint <> 0 AND t.tgdeferrable AND t.tginitdeferred) AS deferred
      FROM pg_catalog.pg_trigger t
      JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
     WHERE NOT t.tgisinternal
       AND n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
     ORDER BY c.relname COLLATE "C", t.tgname COLLATE "C"
""")
_CONSTRAINTS = text("""
    SELECT con.contype::text AS kind, count(*)::integer AS total,
           (count(*) FILTER (WHERE NOT con.convalidated))::integer AS unvalidated
      FROM pg_catalog.pg_constraint con
      JOIN pg_catalog.pg_namespace n ON n.oid = con.connamespace
     WHERE n.nspname = 'public'
     GROUP BY con.contype ORDER BY con.contype::text
""")
_INDEXES = text("""
    SELECT count(*)::integer AS total,
           (count(*) FILTER (WHERE NOT i.indisvalid OR NOT i.indisready))::integer AS unusable
      FROM pg_catalog.pg_index i
      JOIN pg_catalog.pg_class c ON c.oid = i.indrelid
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'public'
""")
_SEQUENCE_ROWS = text("""
    SELECT s.schemaname AS schema_name, s.sequencename AS name, s.last_value::bigint AS last_value
      FROM pg_catalog.pg_sequences s
     WHERE s.schemaname <> 'information_schema' AND s.schemaname !~ '^pg_'
     ORDER BY s.schemaname COLLATE "C", s.sequencename COLLATE "C"
""")


class RestoredSchemaRefused(ValueError):
    """The restored database is not the schema the recovery tooling declares for ``HEAD``."""


@dataclass(frozen=True, slots=True)
class RestoredSchemaAudit:
    tables: int
    views: int
    triggers: int
    guarded_tables: int
    sequences: tuple[tuple[str, int | None, int | None], ...]


def _rows(session: Session, statement: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in session.execute(statement).mappings()]


def _difference(label: str, declared: set[Any], found: set[Any]) -> str | None:
    if declared == found:
        return None
    return f"{label} differ: missing={sorted(declared - found)}, unknown={sorted(found - declared)}"


def mask_text(mask: int) -> str:
    """The readable event set of a ``tgtype`` (for refusal messages)."""
    return " ".join(name for bit, name in _MASK_NAMES if mask & bit) or str(mask)


def audit_restored_schema(session: Session) -> RestoredSchemaAudit:
    """Compare one consistent restored snapshot with the declaration, SELECT only.

    The result is a structural requirement check, not a data verdict: row parity is the
    stand fingerprint's claim and Blob parity is the target readback's.
    """
    versions = [row["version_num"] for row in _rows(session, _VERSION)]
    if versions != [HEAD]:
        raise RestoredSchemaRefused("migration head differs")

    relations = _rows(session, _RELATIONS)
    if any(row["schema_name"] != "public" or row["partition"] for row in relations):
        raise RestoredSchemaRefused("a relation lives outside schema public or is a partition")
    if any(row["kind"] not in ("r", "v") for row in relations):
        raise RestoredSchemaRefused("a materialised view, partitioned or foreign table exists")
    found_tables = {row["name"] for row in relations if row["kind"] == "r"}
    found_views = {row["name"] for row in relations if row["kind"] == "v"}
    problems = [message for message in (
        _difference("tables", set(TABLES), found_tables),
        _difference("views", set(VIEWS), found_views),
    ) if message]
    if problems:
        raise RestoredSchemaRefused("; ".join(problems))

    triggers = _rows(session, _TRIGGER_ROWS)
    if any(row["schema_name"] != "public" for row in triggers):
        raise RestoredSchemaRefused("a trigger lives outside schema public")
    declared = set(TRIGGERS)
    found = {(row["table_name"], row["trigger_name"], row["function_name"], row["mask"])
             for row in triggers}
    message = _difference("triggers", declared, found)
    if message:
        readable = sorted((t, n, f, mask_text(m)) for t, n, f, m in declared ^ found)
        raise RestoredSchemaRefused(f"{message}; event sets: {readable}")
    not_enabled = sorted(row["trigger_name"] for row in triggers if row["enabled"] != "O")
    if not_enabled:
        raise RestoredSchemaRefused(f"triggers are not enabled: {not_enabled}")
    not_deferred = sorted(row["trigger_name"] for row in triggers
                          if row["deferred"] != (row["trigger_name"] in DEFERRED_TRIGGERS))
    if not_deferred:
        raise RestoredSchemaRefused(f"trigger deferral differs: {not_deferred}")

    constraints = {row["kind"]: row for row in _rows(session, _CONSTRAINTS)}
    totals = {kind: row["total"] for kind, row in constraints.items()}
    if totals != CONSTRAINT_COUNTS:
        raise RestoredSchemaRefused(f"constraint counts differ: {totals} != {CONSTRAINT_COUNTS}")
    if any(row["unvalidated"] for row in constraints.values()):
        raise RestoredSchemaRefused("a constraint is not validated")
    index = _rows(session, _INDEXES)[0]
    if index["total"] != INDEX_COUNT or index["unusable"]:
        raise RestoredSchemaRefused("index count differs or an index is invalid")

    last_values = {(row["schema_name"], row["name"]): row["last_value"]
                   for row in _rows(session, _SEQUENCE_ROWS)}
    if any(schema != "public" for schema, _ in last_values):
        raise RestoredSchemaRefused("a sequence lives outside schema public")
    message = _difference("sequences", set(SEQUENCES), {name for _, name in last_values})
    if message:
        raise RestoredSchemaRefused(message)
    positions: list[tuple[str, int | None, int | None]] = []
    for name in sorted(SEQUENCES):
        table, column = SEQUENCES[name]
        if not _IDENTIFIER.fullmatch(table) or not _IDENTIFIER.fullmatch(column):
            raise RestoredSchemaRefused("declared sequence owner is not an identifier")
        highest = session.execute(
            text(f'SELECT max("{column}")::bigint FROM public."{table}"')
        ).scalar_one()
        last = last_values[("public", name)]
        if (highest or 0) > (last or 0):
            raise RestoredSchemaRefused(f"sequence {name} is behind {table}.{column}")
        positions.append((name, last, highest))

    guarded = {row["table_name"] for row in triggers if row["function_name"] in GUARD_FUNCTIONS}
    return RestoredSchemaAudit(
        len(found_tables), len(found_views), len(triggers), len(guarded), tuple(positions)
    )


__all__ = [
    "CONSTRAINT_COUNTS", "DEFERRED_TRIGGERS", "EXEMPT_FROM_FINGERPRINT", "FINGERPRINTED_TABLES",
    "GUARD_FUNCTIONS", "HEAD", "INDEX_COUNT", "RestoredSchemaAudit", "RestoredSchemaRefused",
    "SEQUENCES", "TABLES", "TRIGGERS", "VIEWS", "audit_restored_schema", "mask_text",
]
