# GATE-REPAIR-01 — measured list (interim; the final report replaces this file)

Base `54ec23eb`, branch `agent/gate-repair-01`, lane `auditmanager-gate-repair` (PostgreSQL 57600,
S3 61400/61401). Every row below was measured on the unchanged base tree before any edit, one
pytest process at a time, `.env` sourced, `pytest -c pyproject.toml --rootdir=. -q
-p no:cacheprovider`, the status read from `$?` after a redirect to a file.

| # | scope | files | before |
|---|---|---|---|
| m1 | the downgrade chain | `tests/integration/db/test_downgrade_chain_round_trip.py` | 13 passed, rc 0 |
| m2 | every file that downgrades through `0022` (the twelve of `GATE-FIX-DB-01` plus `test_norm_citations_migration`) | `tests/integration/db/test_{accounts,app_user,execution_queue,execution_workers,norm_citations,norm_embeddings,norms_search,portal_bundles,release_notes}_migration.py`, `test_downgrade_never_loses_a_measurement`, `test_durable_analysis_effects`, `test_reviewer_display_name`, `test_run_terminal_detail_schema` | 173 passed, rc 0 |
| m3 | the files `grep -rl 0022_findings_v2 tests` names (integration side) | `analysis/test_ungrounded_reason_vocabulary.py`, `recovery/test_{blob_object_binding,copy_record_binding,offline_restore_audit,offline_restore_preflight}.py` | 57 passed, rc 0 |
| m4 | norms corpus migration | `db/test_norms_corpus_migration.py` | 20 passed, rc 0 |
| m5 | query surface | `api/test_query_surface.py`, `p02_journey/test_query_surface_over_the_corpus.py` | 46 passed, rc 0 |
| m6 | `DecisionAdapter` and the files naming it | `api/test_decision_authorship`, `test_decision_journal`, `test_listing_surface`, `test_absent_and_empty_are_not_the_same_answer`, `composition/test_every_port_implementation_is_whole`, `composition/test_router_answers`, `p02_journey/test_truncated_end_to_end` | **1 failed**, 106 passed, 1 skipped, rc 1: `test_every_wired_implementation_carries_the_whole_port[documents]` |
| m7 | error kernel, seeded corpus and their database-backed variants | `contract/shared_kernel/test_error_kernel.py`, `contract/fixtures_seeded/test_ar_v2_seeded.py`, `integration/evaluation/`, `db/test_routing_refusal_codes_migration.py`, `runs/test_the_interruption_vocabulary_is_pinned.py` | 124 passed, 32 subtests passed, rc 0 |
| m8 | `D-189` with `W55B_QA_API_PORT=28500` | `tests/integration/qa_w55b` | **1 failed**, 66 passed, rc 1: `test_p3_input_budget.py::test_a_document_exactly_at_the_budget_starts_and_one_character_less_refuses`, `ConnectionRefusedError` |
| m9 | `D-189` without the override | `tests/integration/qa_w55b` | **1 failed**, 66 passed, rc 1: `test_p3_input_budget.py::test_at_a_low_ceiling_a_start_and_a_reaudit_over_the_budget_are_refused_with_both_figures`, `ConnectionRefusedError` |
| m10 | `D-190` | `tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py` | 1 passed in 7.1 s, rc 0 (the red is a rare stall, not reproducible by rerun) |
