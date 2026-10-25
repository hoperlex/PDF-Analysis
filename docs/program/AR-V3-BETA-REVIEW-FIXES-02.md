# AR-V3-BETA-REVIEW-FIXES-02 — judges' findings on the pack loader, the set tool and the map builder

**Task:** [AR-V3-BETA-REVIEW-FIXES-02](tasks/AR-V3-BETA-REVIEW-FIXES-02.md). **Base:** `809d5c733a92e62a6979103c5771b546d1217c03` (`integration/ar-close-1026`). **Date:** 2026-10-26 UTC. Development only; nothing merged or pushed, no `GATE OK` claimed.

Two independent judges read `v3_pack_manifest.py`, `promote_cli.py` and `map_pack.py` and reported findings A to D. Each was re-proved on the base tree first (the snippets and their output are in the task file); all four reproduced, so all four were fixed.

## What changed

| Finding | Reproduced | Fix | Guards |
| --- | --- | --- | --- |
| **A** the request's targets and vectors are not bound to the reviewed map | yes: same map bytes, spans widened by one paragraph: 5 prompt rows became 8, the set digest changed, `load_bundle` accepted both | `load_bundle` parses `map.json` (`json.loads`, equal to its own canonical encoding, as the library does) and requires, per item id, exactly the map's `(norm_document_id, ordinal_first, ordinal_last)` spans in the request; the order of one item's spans is free, their number and values are not. A map with `synthetic: true`, without a boolean flag, or that the binding cannot read is refused. Reasons `map_invalid`, `map_synthetic`, `request_items_differ_from_map`, `request_targets_differ_from_map`; exit 2, no runner built, nothing written. The map format already carries per-item targets (`items[].targets[]`), so no format change was needed and none was made | `test_promote_cli.py` (46 new cases), `test_map_pack.py` (3 contract tests holding the set tool to what `map_pack` writes), `test_promote_cli_db.py::test_a_request_whose_spans_differ_from_the_reviewed_map_writes_nothing` |
| **B** a trailing newline passes as an opaque id | yes: `ndoc_<ULID>\n` and `nrs_<ULID>\n` parse; `map_pack._ident` accepts them | `ids.py`: `fullmatch` in the identity check, the prefix probe and `pattern_for`. `map_pack._ident` and the set tool's `set_id` check refuse a line break themselves | `tests/unit/shared/test_opaque_id_exactness.py` (every one of the identity types), `test_map_pack.py`, `test_promote_cli.py`, manifest case `set_id_trailing_newline` |
| **C** `builder_version` not pre-checked; a lone surrogate escapes | yes: `totally-wrong-builder` loads and `select_beta()` returns the pack while `select_verified_retrieval_set` refuses it; `"x\ud800"` ends as `UnicodeEncodeError` in `pack.sha256` or in the attestation fields on the status route | `_scope` compares `builder_version` with `SET_BUILDER_VERSION` (one new export in `norms/public.py`): `builder_version_mismatch`. An iterative walk refuses any string or key without a UTF-8 form: `manifest_string_encoding`, in `parse_manifest`, in `seal_manifest` (before `pack.sha256` encodes) and, as `spec_value`, in the seal scopes file | 3 rows added to the refusal table (42 to 45), 10 dedicated non-UTF-8 tests and 2 scopes-file cases in `test_v3_pack_manifest.py` (97 to 112); `test_ar_v3_pack_status_route.py` sealed an unselectable builder and now uses the real one |
| **D** `write_pack` not atomic; tracebacks instead of typed refusals; exit-status text | yes: dangling-symlink `pack-summary.json` left six maps and a following `output_exists`; 5,000-digit integer: `ValueError`; 500,000-deep `[`: `RecursionError`; `os.listdir` `OSError`: traceback | `write_pack` looks at every target with `lstat`, creates exclusively, and on any failure or interrupt removes the files and directories it created (never a stranger's file). `_load_json` catches `ValueError` without re-labelling a duplicate key. `promote_cli`: `RecursionError`, `OSError` from `listdir`, a NUL byte in the path are `request_invalid` / `bundle_unreadable`. The exit-status text now names SIGTERM, SIGKILL and the OOM killer and says a re-run is idempotent | `test_map_pack.py` (dangling x3, mid-write failure x4, stranger's file, huge integer, duplicate key), `test_promote_cli.py` (nesting, listdir, NUL, text) |

## Mutations (one edit, run the named file with the new guards, observe red, revert; `git status` clean after each)

| Guard | Mutation | First red |
| --- | --- | --- |
| B shared parser | `.fullmatch(value)` back to `.match(value)` in `OpaqueId.__init__` | `test_every_identity_type_refuses_a_trailing_newline` (3 red) and manifest `[set_id_trailing_newline]` |
| B prefix probe | `_PREFIX_RE.fullmatch(head)` to `.match(head)` | `test_a_wrong_prefix_followed_by_a_newline_is_a_format_error_not_a_prefix_error` |
| B map tool | line-break test removed from `map_pack._ident` | `test_an_identity_with_a_line_break_is_refused_without_relying_on_the_shared_parser` |
| B set tool | `"\n" in set_id` test removed | `test_the_set_id_check_does_not_depend_on_the_shared_parser_alone` |
| C builder | builder comparison replaced by `if False` | `[builder_version_unknown]`, `[builder_version_previous_release]` |
| C parse | `_require_utf8_text(document)` removed from `parse_manifest` | `test_a_string_that_is_not_utf8_text_is_refused_with_its_own_reason[hashed_scope_field]` (and 7 more) |
| C seal | the two `_require_utf8_text(asdict(...))` calls removed | `test_sealing_refuses_a_string_that_is_not_utf8_text` |
| C scopes file | `encode` check removed from `_nonempty` | `[lone_surrogate_in_profile]`, `[lone_surrogate_in_scope]` |
| A binding | `_bind_request_to_map` call removed | 6 `test_targets_that_differ_from_the_reviewed_map_are_refused` cases, 3 item cases, the CLI tests, the contract test `..._spans_widened_by_one_paragraph`, and against real PostgreSQL `plan` exits 0 for a narrowed span (`assert 0 == 2`) |
| A spans | the per-item span comparison made vacuous | the same six span cases |
| A items | the item-set comparison replaced by `if False` | the three `test_request_items_that_are_not_the_maps_items_are_refused` cases |
| A synthetic | `synthetic is True` test replaced by `if False` | `test_a_synthetic_map_is_never_promoted`, contract `..._a_synthetic_map_that_this_tool_wrote` |
| A flag required | `synthetic is not False` relaxed to `is True` | `[no synthetic flag]`, `[a synthetic flag that is text]`, `[a null synthetic flag]` |
| A canonical | canonical-equality test dropped | `[not in canonical form]`, `[padded with a newline]` |
| D request nesting | the `RecursionError` clause removed | `test_a_deeply_nested_request_is_a_refusal_not_a_recursion_error` |
| D listdir | `except OSError` made unreachable | `test_a_bundle_directory_that_cannot_be_listed_is_a_refusal` |
| D NUL path | `ValueError` dropped from the `lstat` guard | `test_a_bundle_path_with_a_nul_byte_is_a_refusal` |
| D text | "SIGTERM, SIGKILL or the out-of-memory killer" removed | `test_the_exit_status_text_names_the_signals_that_leave_admissions_behind` |
| D lexists | `os.path.lexists` replaced by `Path.exists` | the three `test_a_dangling_symlink_in_the_output_...` cases |
| D rollback files / dirs | the unlink loop / the rmdir loop removed | all four mid-write cases / the two new-directory cases |
| D stranger's file | `created.append` moved before the exclusive create | `test_a_file_that_appears_between_the_check_and_the_create_is_never_removed` |
| D `ValueError` | JSON guard back to `JSONDecodeError` | `test_a_5000_digit_integer_is_a_typed_refusal_in_every_input_file` |
| D relabelling | `except MapPackRefused: raise` removed | `test_duplicate_json_keys_and_non_finite_numbers_are_refused`, `test_a_duplicate_key_keeps_its_own_code_...` |
| D interrupt | rollback narrowed from `BaseException` to `OSError` | the two `interrupt` cases |

With the shared parser reverted (B, first row) the map-tool and set-tool tests stay green: that is the requirement that the tools do not depend on the shared fix alone.

## Verification

Run from the lane directory with the repository `.venv` linked in, `PYTHONPATH=src:<bootstrap site-packages>` and `-c pyproject.toml --rootdir=. -p no:cacheprovider`.

- `test_opaque_id_exactness.py` 4 passed; `test_v3_pack_manifest.py` 112 passed (base 97); `test_promote_cli.py` 107 passed (base 61); `tests/contract/norm_map` 117 passed (base 102); `test_v3_pack_install.py`, `test_v3_worker_registry.py`, `test_ar_v3_pack_status_route.py`, `tests/contract/architecture` passed.
- Against the already-running integration stack, throwaway database and bucket per test, nothing in `auditmanager_ar_close` touched: `test_promote_cli_db.py` 12 passed (11 + the new spans test), `test_ar_v3_pack_seal.py` 3 passed, `test_ar_v3_run_group.py` 5 passed. The DB seed's map had to gain `synthetic: false` and the item's target span so that it is a map the command accepts; the digests are computed, none is pinned.
- All 120 non-DB test files that import `shared.identity` (outside `tests/integration/db`): 1,352 passed; the 712 errors and one of the three failures are database or object-store set-up (no `DATABASE_URL`, `S3_*`); the other two failures, in `test_v2_recorded_durable_stage.py`, fail on the base `ids.py` as well (a fake session without `.mappings()` meeting `jobs/repository.py`), not caused by this lane.
- The whole `tests/contract`, `git diff --check` and the governance check of the task file: see the final answer.

## Statements in earlier reports that this task makes stale (not edited here)

- `AR-V3-BETA-PACK-INSTALL-01.md`: "`builder_version` is checked for presence only at load" (now `builder_version_mismatch`); its token list lacks `builder_version_mismatch` and `manifest_string_encoding`; test counts (97 is now 112).
- `AR-V3-BETA-SET-TOOL-01.md`: the `map.json` description needs per-item `targets` (`norm_document_id`, `ordinal_first`, `ordinal_last`) and a boolean `synthetic: false`; the refusal-reason list lacks `map_invalid`, `map_synthetic`, `request_items_differ_from_map`, `request_targets_differ_from_map`; "Unclassified faults ... after it, everything is exit 3" is not true for SIGTERM, SIGKILL and the OOM killer (the docstring now says so); runbook step 4 should add that the command itself now checks the request's spans against the map.
- `AR-V3-BETA-MAP-TOOL-01.md`: `output_exists` also covers a dangling symlink and a failed write now leaves nothing; 102 tests are now 117.

## Limits and integrator notes

- `candidate.py` is untouched: a caller other than this tool still has to bind spans to the map itself. The binding does not check query vectors; their digests are the reviewer's recomputation (set-tool runbook, step 4).
- `map_pack`'s rollback does not survive a SIGKILL in the middle of a write; the leftover then needs a manual removal and a re-run says `output_exists`.
- A real promotion now needs a map in the shape `map_pack` writes with `synthetic: false`; a hand-made map with only `mapped_document_ids` and `items[].id` (the shape the earlier tests used) is refused as `map_invalid`.
- Merge after the integration branch tip `809d5c73`; the `norms/public.py` export and the `ids.py` change touch shared modules, but both are additive or tightening. On a database lane re-run the three DB files above. A pack manifest sealed earlier by hand with a wrong builder, or with non-UTF-8 text, no longer loads: re-seal it.
- Debt register rows were not touched (forbidden path).

## Hotspot audit

Changed paths are the allowed paths of the task, including the one extra test path it names. `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files, `src/auditmanager/bootstrap/**`, `candidate.py`, `promotion.py`, the rest of the norms library, `web/**`, `DEBT_REGISTER.md` and `CURRENT_STATE.md` are untouched. The lane's `.env` and `.venv` link are untracked and ignored.
