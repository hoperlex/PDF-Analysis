# AR-V3-BETA-SET-TOOL-01 — promote one reviewed retrieval set from the command line

**Task:** [AR-V3-BETA-SET-TOOL-01](tasks/AR-V3-BETA-SET-TOOL-01.md). **Date:** 2026-10-26 UTC. **Development base:** `354a9092c48a5d5f37fe8fe3de60af4b4dff7c88`.

## Result

`python -m auditmanager.norms.retrieval.promote_cli {new-id,plan,promote}` is the first caller of the W57a promotion library outside tests. It keeps the library's two-person check as two commands. `plan` prepares the candidate in one `REPEATABLE READ READ ONLY` transaction and prints its digests; it writes nothing and never opens the object store. `promote` needs the reviewer's `expected_set_sha256` and `expected_catalogue_sha256` in the bundle, re-prepares, and only on equality admits both artifacts, runs the existing custody dispatcher and finalizes (both saved Blobs re-read, then the immutable set row and both bindings in one transaction). The same command with the same `set_id` is an exact replay. Nothing else in `src/` changed: the tool adds one module, no SQL of its own, no contract, migration, route or composition-root entry.

It has not promoted a real set. The six `nrs_` sets of the AR v3 beta pack still need their six reviewed maps and an independent reviewer; this tool is what they will be created with.

## Bundle format

A bundle directory holds exactly two regular files; any other entry, a symlink (directory or file), a FIFO or an oversize file is refused.

- `map.json` — the reviewed canonical map bytes (at most 10,000,000 bytes). Hashed exactly as stored, never re-serialised; `map_sha256` is its SHA-256. The library requires it to be canonical JSON carrying `norms_snapshot_id`, `reviewed_content_key`, `embedding_build`, `mapped_document_ids` and `items` (`id` each). Since `AR-V3-BETA-REVIEW-FIXES-02`/`-03` the command also reads the map and requires: a boolean `synthetic` that is false; per item the exact reviewed spans `(norm_document_id, ordinal_first, ordinal_last)` (`request_targets_differ_from_map`, `request_items_differ_from_map`); per mapped document the one `designation` its targets carry, equal to the request's label (`request_designations_differ_from_map`); and a `norms_snapshot_id` equal to the request's (`request_snapshot_differs_from_map`). A map written by `map_pack build` always has all of these; a hand-made one without per-target `designation` or `norms_snapshot_id` is `map_invalid`.
- `request.json` — strict JSON (at most 4,000,000 bytes; duplicate keys, unknown keys and non-integer ordinals refused):

```json
{
  "format": "ar-set-promotion-request-v1",
  "set_id": "nrs_<ULID>",
  "snapshot_id": "ns_<ULID>",
  "reviewed_content_key": "<the map's reviewed_content_key>",
  "embedding_build": "bge-m3-dense-v1:characters-v2:1200",
  "chunking_profile": "characters-v2:1200",
  "independently_checked_source_digest": "<64 hex>",
  "independently_checked_embedding_digest": "<64 hex>",
  "designations": [{"document_id": "ndoc_<ULID>", "slug": "<stored slug>", "designation": "<reviewed label>"}],
  "items": [{
    "item_id": "<the map's item id>",
    "query_vector_base64": "<1024 big-endian float32, unit length, base64>",
    "provenance": {"query_text_sha256": "<64 hex>", "query_vector_sha256": "<64 hex>"},
    "targets": [{"document_id": "ndoc_<ULID>", "ordinal_first": 0, "ordinal_last": 3}]
  }],
  "expected_set_sha256": "<64 hex, promote only>",
  "expected_catalogue_sha256": "<64 hex, promote only>"
}
```

The vector uses the repository's own representation (`auditmanager.norms.embedding.vectors`: float32, big-endian, base64) and `query_vector_sha256` is the SHA-256 of those bytes, the same digest type as `norm_embedding.embedding_sha256`; the command refuses a vector that does not hash to it. `query_text_sha256` is recorded and printed by `plan` for the reviewer; the tool cannot check it, it has no query text. The two `expected_*` keys come together or not at all; `plan` accepts a bundle without them, `promote` refuses one without them (`expected_digests_required`). `DATABASE_URL` and `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET` come from the process environment through the application's own constructors.

## Operator runbook (one set)

```bash
cd <repository>                       # PYTHONPATH=src and .venv/bin/python below
export PYTHONPATH=src
set -a; . ./.env; set +a              # or export DATABASE_URL and S3_* from the stand's own file
CLI=".venv/bin/python -m auditmanager.norms.retrieval.promote_cli"
```

1. **Mint the identity once.** `$CLI new-id` prints a fresh `nrs_…`. Put it in `request.json` as `set_id` and keep it for every retry of this map; never mint a second id for the same map.
2. **Assemble the bundle** (`map.json`, `request.json` without the two `expected_*` keys) in an empty directory. The proof digests are the reviewer's: copy them from the verified W54 bundle manifest and import report, not from the database being qualified.
3. **Plan.** `$CLI plan <bundle>` exits 0 and prints, among others:
   `map_sha256`, `source_proof_digest`, `embedding_proof_digest`, `set_sha256`, `set_size_bytes`, `catalogue_sha256`, `catalogue_size_bytes`, `prompt_part_characters`, one `item: <id> query_text_sha256=… query_vector_sha256=… targets=<doc>:<first>-<last>,…` line per item, one `designation: <doc> "<label>"` line per mapped document, and `verdict: not_compared`. Nothing was written. It reads one consistent snapshot without taking locks, so it may run while the stand is live.
4. **The independent reviewer recomputes** (a second person or at least a second checkout and database; the tool offers no way to copy step 3's output into the bundle):
   - `sha256sum map.json` equals `map_sha256`, and the map's items, mapped documents, target spans and branch decisions are the ones approved.
   - `source_proof_digest` and `embedding_proof_digest` equal the snapshot content digest and the embedding-set digest of the verified bundle (otherwise `plan` exits 2 with `source digest differs from independent proof` or `embedding set digest differs from expected`).
   - Each `query_vector_sha256` equals the digest of the vector re-encoded from the frozen BGE-M3 image for the approved query text (`query_text_sha256`), each `targets=` equals the approved spans, and each `designation:` label is the norm the approved map names for that document (a wrong label would attribute the citation to another norm even though the map digest is unchanged).
   - Their own build of the set and catalogue from the same snapshot and map yields the same `set_sha256`, `catalogue_sha256` and `prompt_part_characters`. Only then do they write their digests into `expected_set_sha256` and `expected_catalogue_sha256`.
5. **Optional check.** `$CLI plan <bundle>` again now ends with `verdict: matched` (exit 0). A differing digest prints the candidate and exits 2 with `REFUSED [expected_digest_mismatch]` naming the differing artifact; nothing was written and the `set_id` is not consumed.
6. **Promote.** `$CLI promote <bundle>` re-prepares and compares, refuses while any admission outside this set is pending, admits both artifacts in one transaction, dispatches, finalizes. Success exits 0 and prints `promote: verified`, `set_id`, `replayed: false`, both digests and both Blob ids.
7. **Verify.** `$CLI promote <bundle>` again prints `replayed: true` and changes nothing. In SQL: `SELECT state, observed_set_sha256, observed_catalogue_sha256 FROM norm_retrieval_set WHERE norm_retrieval_set_id = '<set_id>';` is `verified` with the reviewer's digests, and `SELECT role, blob_id FROM norm_custody_binding WHERE target_id = '<set_id>';` returns two rows.

### Exit status and what a failed state looks like

| Exit | stderr starts | Meaning | What to do |
| --- | --- | --- | --- |
| 0 | — | verified (`replayed: false`) or exact replay (`true`); `plan`: computed, and any supplied expectation matches | nothing |
| 2 | `plan|promote: REFUSED [reason]: …` | nothing was written by this invocation | fix the cause; the same `set_id` is still free |
| 3 | `promote: UNCERTAIN [reason]: …` then `set_id:`, `state:`, `next:` | an admission or dispatch step may exist; no verified row is claimed | run the printed `next:` command (it is the same command) |

Refusal reasons: `bundle_unreadable`, `bundle_layout`, `bundle_oversize` (files); `request_invalid`, `query_vector_digest_mismatch`, `expected_digests_required` (request); `map_invalid`, `map_synthetic`, `request_items_differ_from_map`, `request_targets_differ_from_map`, `request_designations_differ_from_map`, `request_snapshot_differs_from_map` (the request does not match the reviewed map); `expected_digest_mismatch`; `foreign_pending_admissions` (another admission is pending: the dispatcher takes any due admission, so let its owner finish it or requeue it first); `promotion_refused`, `candidate_refused`, `qualification_read_refused`, `window_read_refused`, … (the library's own message, for example an unknown map digest, a stale preparation, a verified identity that already belongs to another set); custody classifiers such as `slot_reuse` (the same `set_id` was admitted before with other bytes: the map or the snapshot changed, mint a new id only if the change is intended); `blob_store_unavailable` and `database_unavailable` (settings or reachability, before anything was written).

Uncertain reasons:

- `admission_uncertain` — the admission transaction ended unclassified (for example a lost connection at commit). Re-run.
- `interrupted` — the process was stopped (Ctrl-C) or a dispatch step failed after admission. Re-run: the same admissions are replayed, never duplicated, and the dispatcher continues from the last durable step.
- `dispatch_unsettled` — after dispatch an admission is not `confirmed`: `pending` is a retry scheduled after 30 s, 5 min, 30 min or 2 h, so wait and re-run; `poisoned` (five failed tries) needs a requeue first; `none` means every admission of the slot was rejected (a byte or media-type mismatch): read `last_failure` and do not retry blindly.
- `finalize_refused` — a Blob could not be re-read or differs from the candidate. Re-run once the store is healthy; a persistent difference is a custody incident for `custody reconcile`.

To see a failed state: `SELECT norm_custody_admission_id, role, state, attempt_count, available_at, last_failure FROM norm_custody_admission WHERE target_id = '<set_id>' ORDER BY created_at;`. To requeue exactly this set's poisoned admissions (the runbook form of what the test `test_a_poisoned_admission_is_reported_and_completes_after_the_documented_requeue` does):

```python
from auditmanager.norms.public import NORM_CATALOGUE, NORM_RETRIEVAL_SET, report, requeue
from auditmanager.shared.db import session_scope

with session_scope() as session:
    ids = [a.admission_id for role in (NORM_RETRIEVAL_SET, NORM_CATALOGUE)
           for a in report(session, role=role, targets=["<set_id>"]).poisoned]
    print(requeue(session, ids))
```

Then re-run `promote`. Never edit `map.json` or `request.json` between a failed run and its re-run: changed bytes either mismatch the reviewer's digests or are refused as `slot_reuse`. Never mint a second `set_id` to "get round" a refusal: 0023 allows one verified set per `(map_sha256, snapshot, chunking profile, embedding profile, builder version)` and the command refuses the twin (`already belongs to another set`).

## What was run

All on the lane's private stack (`auditmanager-ar-set-tool`, PostgreSQL 17.11 + pgvector at `127.0.0.1:58610`, MinIO at `127.0.0.1:62110`, migration head `0032_ar_v3_run_group`), `make up`, `make migrate`, `make check-services` printing `FOUNDATION-CHECK OK check-services`.

- `pytest tests/integration/norms/retrieval/test_promote_cli.py` — **61 passed** (offline, fake runner).
- `pytest tests/integration/norms/custody/test_promote_cli_db.py` — **11 passed** (real PostgreSQL and S3).
- `pytest tests/integration/norms/retrieval tests/integration/norms/custody -k "promotion or promote"` — **84 passed**, which includes the 12 existing promotion tests (`test_promotion.py`, `test_retrieval_set_promotion.py`).
- The governance check of the task file prints `[]`; `python -m compileall` and `git diff --check` pass.
- Not run (R-135): `make gate`, the whole contract battery, the frontend suite, any live journey.

The DB tests do not substitute preparation. They seed one snapshot (one document, two reliable paragraphs, one chunk, one embedding window, a confirmed source-PDF binding) so the real readers, set builder and catalogue builder produce the bytes, and they cover: `plan` writes nothing (row counts of the set, admission, binding, Blob and audit tables and the bucket listing unchanged) and runs `repeatable read` / `read only` (an INSERT inside it is refused by PostgreSQL); `promote` publishes two Blobs and one verified set with two bindings, then replays exactly, and a twin `set_id` is refused; a mismatched expected digest exits 2 with no admission, row or object and the corrected digests then promote under the same `set_id`; a process lost mid-publication (`KeyboardInterrupt`) exits 3 and the re-run completes with two admissions only; a counted failed try leaves the admission pending (exit 3) until it is due; a poisoned admission is reported, requeued and completes; a foreign pending admission refuses before this set's admission; a wrong independent source or embedding proof refuses `plan` and `promote` with the library's message and nothing written; and the default runner is built from the environment names.

### Mutation proofs

Each guard was mutated in place (a one-line textual change to `promote_cli.py`), the named test files run, then the file restored (`git status` clean after each). The run was repeated on the final source. All 45 mutations turned the run red:

| Guard (mutation) | Red test |
| --- | --- |
| duplicate JSON keys accepted (`if False:` for the key-count check) | `test_request_json_must_be_strict[duplicate key]` |
| unknown keys accepted (`unknown = []`) / missing keys accepted (`missing = []`) | the `unknown …` and `missing top-level key` cases of `test_each_malformed_request_is_refused_with_its_reason` |
| format, expectations-together, `expected_digests_required`, `set_id` parse, uppercase digest, boolean/negative/float ordinal, empty list removed or loosened | the matching case of `test_each_malformed_request_is_refused_with_its_reason` (`wrong format`, `set id is not an nrs identity`, `proof digest is not lowercase sha256`, `boolean ordinal`, `negative ordinal`, `empty items`), `test_a_plan_bundle_may_omit_the_expectations_but_never_one_of_them`, `test_promote_requires_the_reviewers_expected_digests` and `test_request_json_must_be_strict[float]` |
| non-unit vector accepted; vector digest not compared; vector error escapes untyped | `vector is not unit length`; `vector bytes do not match…`, `test_a_changed_vector_is_caught_…`; `vector is not base64` |
| directory entries not checked; `lstat` → `stat`; `O_NOFOLLOW` dropped; `S_ISREG`/`S_ISDIR` dropped; read limit off by one | `test_the_bundle_directory_holds_exactly_the_two_files`, `test_symlinks_are_refused_…`, `test_a_fifo_…`, `test_oversize_files_are_refused` |
| `O_NONBLOCK` dropped (FIFO open blocks) | `test_a_fifo_in_place_of_a_file_is_refused_not_waited_on` fails through its 5 s alarm instead of hanging |
| invalid UTF-8 replaced instead of refused | `test_invalid_utf8_is_refused` |
| source serves another set or role (`_Source.open`); manifest names other sets/kinds/anchors (`_Manifest.declared`) | `test_the_source_serves_…`, `test_the_manifest_names_only_…` |
| `plan` ignores a differing digest; `plan` opens the store; `plan` reports a verdict without expectations; bundle always `compared`; provenance lines dropped or wrong | `test_plan_reports_a_matching_verdict_…`, `test_plan_prints_…` |
| `promote` continues past a differing digest | `test_a_mismatched_expected_digest_refuses_with_no_admission` |
| typed admit refusal made uncertain; unclassified admit failure made refused; unsettled admissions do not stop finalize; finalize refusal unclassified; `KeyboardInterrupt` not caught after admission (pytest aborts with `KeyboardInterrupt`); re-run command unquoted; replay flag always false | the `test_a_typed_refusal_while_admitting_…`, `test_an_unclassified_failure_…`, `test_an_admission_that_is_not_confirmed_…`, `test_a_finalize_refusal_…`, `test_an_interrupted_dispatch_is_uncertain_…`, `test_the_rerun_command_quotes_…`, `test_an_exact_replay_is_reported_as_replayed` |
| `plan` not `REPEATABLE READ READ ONLY` (`execution_options={}`) | `test_plan_runs_in_one_repeatable_read_read_only_transaction` |
| foreign pending admissions tolerated; own pending admissions counted as foreign | `test_a_foreign_pending_admission_refuses_…`; `test_an_interrupted_dispatch_exits_3_and_the_rerun_completes_…` |
| `settle` reports every role confirmed; poisoned hint no longer names `requeue` | `test_a_failed_try_leaves_the_admission_pending_…`; `test_a_poisoned_admission_is_reported_…` |

## Design notes and limits

- **The dispatcher is global.** `CustodyDispatcher.dispatch()` claims any due `pending` admission (premise P-03). The command refuses with `foreign_pending_admissions` before it admits anything while another admission is pending, and its source raises for any admission that is not this set's, so a foreign admission is never given our bytes. A race with another admitter between the check and the dispatch is not excluded; run it while no other custody work runs. A role/target-scoped dispatcher in `norms/custody` would remove the limit and is a library change outside this task.
- **The custody source is recomputed, not staged.** After an interruption the re-run recomputes the candidate from the same snapshot and bundle, and the dispatcher verifies the SHA-256 of the staged bytes against what the admission declared. No file outside the database is trusted.
- **No rejected row.** On a digest mismatch the command does not call `record_rejection`: that row would consume the `set_id` and block the corrected digests.
- **Independence is procedural.** The command cannot know that the reviewer computed the digests independently; it only refuses to take them from `plan`'s output automatically and re-derives the candidate before every admission.
- **`requeue` has no command.** The runbook uses the public `report` and `requeue` functions.
- **Scale is untested.** The tool was not run against the 674-document snapshot (it lives in another lane). The readers replay the whole build's window metadata (61,573 windows there), and `promote` prepares three times (read-only, admission, finalization), so cost grows with the corpus; measure it on the first real set.
- **Unclassified faults.** A fault before the admission transaction (a bug, not a refusal) propagates as a traceback with exit 1 and nothing written; after it, everything is exit 3.
- **Lane cleanup.** After the checks `make down` stops this lane's three containers and removes the network. Its two named volumes, `auditmanager-ar-set-tool-postgres-data` (about 70 MB) and `auditmanager-ar-set-tool-s3-data` (a few kB), remain for the integrator to remove by exact name; no other lane's container or volume was touched.

## Hotspot audit

Changed paths are exactly the task's allowed paths: the new module, the two new test files, this report and the task file. `src/auditmanager/norms/__main__.py`, the promotion library, `custody/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, dependency and lock files, `src/auditmanager/bootstrap/**`, `src/auditmanager/runs/**` and `web/**` are untouched. The lane's `.env` and `.venv` symlink are untracked and ignored.
