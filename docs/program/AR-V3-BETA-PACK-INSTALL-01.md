# AR-V3-BETA-PACK-INSTALL-01 — install the reviewed pack by configuration

Until now nothing could put a `TrustedPack` into a running server: both composition roots built `TrustedPackRegistry.empty()`, so every group start refused. This task adds the installer. An operator seals a manifest from six verified retrieval sets, the file is mounted into the API and the worker, and `AR_V3_BETA_PACK_MANIFEST` names it. No code change is needed to install, replace or withdraw a pack.

**Not done here and an integrator action:** the deploy compose/env pass-through under `infra/**` (the variable on the `api` and `worker` services, a read-only mount of the file into both, and an `alpha.env.example` entry). This lane may not edit `infra/**`; until that slot lands, the variable can only be set where the process environment is set directly. Also not done: sealing the real pack. No reviewer, ruling or real six-map set exists in this lane, and none was invented.

## What the server does with the variable

| `AR_V3_BETA_PACK_MANIFEST` | Result in the API and in the worker |
| --- | --- |
| unset, empty or blank | empty registry (as before); group starts refuse `DEPENDENCY_UNAVAILABLE / ar_v3_trusted_pack` |
| names an acceptable manifest | registry holds that one pack; `select_beta()` returns it |
| names anything else | process refuses to start: `ConfigurationError` with a reason token |

Blank counts as unset because every optional variable in `settings.py` reads that way and a compose pass-through of an unset host variable yields an empty string. Only the empty registry can result, which is the most restrictive state.

## Manifest (`ar-v3-beta-reviewed-pack-manifest/1`)

UTF-8 JSON object with exactly the keys `format`, `analysis_profile_id`, `prompt_bundle_id`, `pack_sha256`, `review` (`reviewer`, `capacity`, `reviewed_at`, `decision_ref`, `scope_statement`) and `scopes`: six objects in the order `F1,F2,A1,A2,S1,S2`, each with exactly `scope_id`, `map_sha256`, `snapshot_id`, `reviewed_content_key`, `embedding_build`, `builder_version`, `chunking_profile`, `set_id`, `set_sha256`. `seal` writes it canonically (`sort_keys`, `ensure_ascii=False`, compact separators, no trailing newline); the loader accepts any JSON with these keys and checks meaning, not byte form.

The loader refuses, each with its own token: `manifest_missing`, `manifest_not_regular_file` (directory, FIFO, final-component symlink), `manifest_unreadable`, `manifest_too_large` (over 64 KiB), `manifest_not_json` (not UTF-8, BOM, duplicate key, `NaN`, nesting bomb), `manifest_keys` (unknown or missing key at any level), `manifest_format`, `manifest_value` (non-string, blank, non-lowercase-SHA, bad `set_id`, `reviewed_at` not a calendar date, `embedding_build` not `bge-m3-dense-v1:<chunking_profile>`), `scope_count`, `scope_id_duplicate`, `scope_order`, `scope_map_duplicate`, `scope_set_duplicate`, `pack_digest_mismatch` (`pack_sha256` differs from the digest recomputed over the scopes) and `pack_refused` (`select_beta()` refused: unresolved profile pair, snapshot differing from the profile). The review block is a record of a human decision; its presence and shape are checked, approval is never inferred.

## Operator runbook

Prerequisite: the six retrieval sets are promoted and verified, and a person with the authority has reviewed the maps and recorded the decision (ruling or ticket). The CLI performs no approval.

1. **Scopes file** (`scopes.json`): the pinned profile pair and the six scope identities, without set ids, in this order.

   ```json
   {
     "analysis_profile_id": "ap_01M5M28ZCDD8VPSP1BTAEW92YE",
     "prompt_bundle_id": "pb_01M5M28ZCDVCR37BX1884JGSPM",
     "scopes": [
       {"scope_id": "F1", "map_sha256": "<64 hex>", "snapshot_id": "ns_01M59N8QNBVN91ACA2HCE6VE74",
        "reviewed_content_key": "<norms_snapshot.content_key>",
        "embedding_build": "bge-m3-dense-v1:<chunking_profile>",
        "builder_version": "norm-retrieval-set-prep-v1", "chunking_profile": "<as promoted>"}
     ]
   }
   ```

   Repeat the scope object for `F2`, `A1`, `A2`, `S1`, `S2`, in that order, with six different map SHA-256 values.

2. **Seal**, on a host that can reach the database holding the promoted sets. Prefer the environment variable to `--database-url`, which would show the password in the process list.

   ```text
   DATABASE_URL=postgresql+psycopg://... PYTHONPATH=src .venv/bin/python -m auditmanager.runs.v3_pack_cli seal \
     --scopes scopes.json --reviewer "<name>" --capacity expert --reviewed-at YYYY-MM-DD \
     --decision-ref "<ruling or ticket id>" --scope-statement "<what was reviewed>" --out ar-v3-pack.json
   ```

   It asks the database, in one read-only transaction, which verified set each identity selects; any scope without exactly one verified set refuses with `scope_unverified` and nothing is written. The file is written with mode 0600; an existing `--out` is refused without `--force`. Exit 0 prints `v3-pack SEALED pack_sha256=... scopes=... maps=... reviewer=...`.

3. **Verify** offline, on any host with the code: `PYTHONPATH=src .venv/bin/python -m auditmanager.runs.v3_pack_cli verify --manifest ar-v3-pack.json`. Exit 0 prints one `v3-pack OK ...` line; exit 2 prints `v3-pack REFUSED <reason>` on stderr. Give the printed `pack_sha256` to the reviewer so the decision refers to the digest the server will use.

4. **Install** (needs the infra slot): copy the file to the host, make it readable by the container user (uid 10001; the file holds identities, digests and the review record, no credential, so 0644 is fine), mount it read-only into **both** the `api` and the `worker` service, and set `AR_V3_BETA_PACK_MANIFEST` to the in-container path in both. The two must see the same file; a worker holding a different pack refuses to execute a group the API accepted.

5. **Restart** the API and the worker. The file is read once, at start. A refused manifest stops the container with `ConfigurationError: AR_V3_BETA_PACK_MANIFEST names a reviewed-pack manifest the server refuses: <reason>`; correct the file and restart. As a check inside a container: `docker compose exec api python -m auditmanager.runs.v3_pack_cli verify --manifest <in-container path>`.

6. **Withdraw or roll back**: unset the variable in both services and restart them. New group starts then refuse again. A group already started keeps its rows and replays on its original key, but its remaining members refuse execution while no pack is installed.

## Verification (lane branch, base `354a9092`)

All with `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider`; no container, database or network.

- `tests/integration/runs/test_v3_pack_manifest.py`: **97 passed** (round trip, canonical bytes, Russian text, 42 refusal cases each asserting its own reason token, non-manifest bytes, duplicate key, size limit, file types, errno, and the CLI with a fake database: seal, overwrite, race, unverified scope, malformed scopes file, verify, subprocess exit status).
- `tests/integration/composition/test_v3_pack_install.py` + `test_v3_worker_registry.py`: **18 passed** (16 new: both roots, unset/blank/good/four bad manifests, same pack in both).
- Wider composition-root regression with a dummy environment (`DATABASE_URL`, `S3_*` set to unreachable values): the three files above plus `test_the_served_application_routes_by_section.py`, `test_the_served_application_always_passes_a_budget.py`, `test_api_token_channel.py`, `test_composition_root.py`: **161 passed**.
- `test_v3_execution_guard.py` + `test_v3_worker_pipeline.py`: 20 collected, **20 passed**. `tests/integration/db/test_ar_v3_pack_seal.py`: 3 collected, not run (needs PostgreSQL).
- `verify` on a sealed fixture exits 0; on a copy with one `set_sha256` changed exits 2 with `pack_digest_mismatch`. `git diff --check`, governance check of the task file (`[]`) and `compileall` pass. `tests/contract/api_v1/test_doc_prose_facts.py` and `test_surface_counts_in_prose.py`: 77 passed.

### Mutation probes (each: change, run the two focused modules with `-x`, observe red, revert)

| Mutation | First red |
| --- | --- |
| digest comparison replaced by `if False` | `test_each_refusal_has_its_own_reason[digest_tampered_scope]` |
| `O_NOFOLLOW` removed | `test_a_symlink_to_a_valid_manifest_refuses` |
| duplicate-map check disabled | `[map_sha_duplicated]` |
| composition returns the empty registry on refusal | `test_a_variable_that_names_a_bad_manifest_refuses_the_start[missing-application]` |
| scope-order check disabled | `[scope_ids_reordered]` |
| size limits removed (parse, `st_size`, read loop) | `test_an_oversized_manifest_is_refused_before_it_is_parsed` |
| blank variable no longer means unset | `test_no_variable_is_the_empty_registry[]` |
| duplicate JSON keys accepted | `[duplicate_key]` |
| CLI publishes with `replace` instead of `link` | `test_seal_writes_the_manifest_the_server_loads` |
| CLI file mode 0644 | `test_seal_writes_the_manifest_the_server_loads` |
| CLI trusts a set answered for another identity | `test_seal_refuses_a_set_answered_for_another_identity` |
| `reviewed_at` calendar check removed | `[reviewed_at_not_a_date]` |
| `embedding_build` pairing check removed | `[embedding_build_mismatch]` |
| `select_beta()` validation skipped in the loader | `test_sealing_refuses_what_the_loader_would_refuse` |
| `seal` does not self-validate | same test |
| CLI skips the existing-target pre-check | `test_seal_refuses_to_overwrite_without_force_and_replaces_with_it` |
| CLI scopes-file order not checked | `[reordered]` |
| unknown root keys accepted | `[root_unknown_key]` |

## Known limits

- The database module `test_ar_v3_pack_seal.py` is unrun: it reuses the norm half of the `test_ar_v3_run_group.py` seed and asserts that `seal` pins exactly the seeded verified sets, refuses a scope without one, and reads inside a read-only transaction. Run it on a PostgreSQL lane.
- `pack_sha256` is tamper evidence, not a signature (see the task file). Custody of the file is the control; mount it read-only.
- `builder_version` is checked for presence only at load; a wrong value is refused at every group start by `select_verified_retrieval_set`, and `seal` takes it from that same call.
- A successful start prints nothing about the installed pack; `verify` inside the container is the confirmation. A startup log line would be a composition-root change beyond this task's single permitted edit.
- Pre-existing, not touched: `tests/contract/architecture/test_alr05_boundaries.py` reports two deep imports in `src/auditmanager/workers/__main__.py`, and `governed_task_findings()` reports 17 older task files with `PREMISE_OUTPUT_REQUIRED`; neither includes this lane's files.

## Integration notes

Merge after base `354a9092`; no ordering constraint with other lanes beyond `composition.py` and `runs/public.py`, which this lane edits minimally (an import, one private helper, two call sites; an import block and `__all__` entries). The composition-root edit places this lane in the once-per-lane complete-gate set (AGENTS.md section 8, case 3), deferred by `R-135`. Contracts, migrations, `infra/**` and the executor are unchanged. No beta acceptance is claimed.
