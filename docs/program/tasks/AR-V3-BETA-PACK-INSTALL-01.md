# Task AR-V3-BETA-PACK-INSTALL-01 — install the reviewed AR v3 beta pack without a code change

task_id: AR-V3-BETA-PACK-INSTALL-01
status: completed in development candidate (lane branch `agent/ar-v3-beta-pack-install-01`; database acceptance and the deploy pass-through are open, see Handoff)

## Outcome

Production can install a reviewed AR v3 beta pack by configuration alone. Both composition roots load a sealed manifest named by `AR_V3_BETA_PACK_MANIFEST` into the `TrustedPackRegistry`. With the variable unset or blank the registry stays empty, exactly as before: group starts refuse with `DEPENDENCY_UNAVAILABLE / ar_v3_trusted_pack`. A variable that names a missing, unreadable, non-regular, symlinked, oversized, malformed, tampered, wrongly ordered or unresolvable manifest refuses process start with a typed `ConfigurationError`; the empty registry is never a fallback for it. An operator CLI (`python -m auditmanager.runs.v3_pack_cli`) seals a manifest from six already-verified retrieval sets and verifies one offline with the server's own loader.

## Depends on

- `AR-V3-BETA-SIX-RUN-02` — completed `TrustedPack`, `TrustedPackRegistry` and the atomic six-Run group.
- `AR-V3-BETA-EXECUTE-PREFLIGHT-01` — completed current-Attempt check of the persisted pack against the registry.
- `AR-V3-BETA-GROUP-API-SEAL-01` — completed group review read; the registries were still empty.
- `AR-SET-PROMOTION-01` — completed verified-set custody read (`select_verified_retrieval_set`).

## Frozen inputs

- domain/API/analysis/events contract family: `1.4.0`, unchanged; no OpenAPI, error-code or schema change.
- migration head: `0032_ar_v3_run_group`, unchanged; `VERSION` `0.8.0`, unchanged.
- `TrustedPack.sha256` (`format: ar-v3-beta-reviewed-pack/1`), `TrustedPackRegistry.select_beta`, `_validate_pack` and `select_verified_retrieval_set` semantics: read-only inputs, not edited.
- manifest format `ar-v3-beta-reviewed-pack-manifest/1`, frozen by the orchestrator (see the report).
- base commit: `354a9092c48a5d5f37fe8fe3de60af4b4dff7c88`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the composition roots hard-code the empty registry and nothing in `src`, `infra` or the `Makefile` reads a manifest variable

### P-01 — the two hard-coded empty registries

- captured_at: 2026-10-26
- command: `git grep -n 'TrustedPackRegistry.empty()' 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- src/auditmanager/bootstrap/composition.py`
- captured_output:
  ```text
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/bootstrap/composition.py:157:    ar_v3_pack_registry = TrustedPackRegistry.empty()
  354a9092c48a5d5f37fe8fe3de60af4b4dff7c88:src/auditmanager/bootstrap/composition.py:294:    ar_v3_pack_registry = TrustedPackRegistry.empty()
  ```
- interpretation: `build_worker_runtime` (line 157) and `build_application` (line 294) each build an empty registry; neither can install a pack. Says nothing about tests, which inject registries directly.

### P-02 — no installer, loader or variable exists

- captured_at: 2026-10-26
- command: `git grep -n 'AR_V3_BETA_PACK_MANIFEST' 354a9092c48a5d5f37fe8fe3de60af4b4dff7c88 -- src infra Makefile; echo "exit=$?"`
- captured_output:
  ```text
  exit=1
  ```
- interpretation: no match (`git grep` exit 1) in code, deploy files or the Makefile at the base: the variable is new and the deploy pass-through does not exist yet.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/v3_pack_manifest.py`
- `src/auditmanager/runs/v3_pack_cli.py`
- `src/auditmanager/runs/public.py`
- `src/auditmanager/bootstrap/composition.py`
- `tests/integration/runs/test_v3_pack_manifest.py`
- `tests/integration/composition/test_v3_pack_install.py`
- `tests/integration/composition/test_v3_worker_registry.py`
- `tests/integration/db/test_ar_v3_pack_seal.py`
- `docs/program/tasks/AR-V3-BETA-PACK-INSTALL-01.md`
- `docs/program/AR-V3-BETA-PACK-INSTALL-01.md`

The only edit to `composition.py` is the import, one private helper `_ar_v3_pack_registry` that translates `PackManifestRefused` into `ConfigurationError`, and the two call sites that replace `TrustedPackRegistry.empty()`. `test_v3_worker_registry.py` is allowed but unchanged; it is the proof that the existing registry hand-over still holds.

## Forbidden hotspots

Everything else, especially `contracts/**`, `db/migrations/**`, `infra/**`, the `Makefile`, root dependency/lock files, `src/auditmanager/runs/executor.py`, `src/auditmanager/runs/v3_group.py`, `src/auditmanager/norms/**`, global styles and `web/**`.

## Non-goals

No reviewer is named, no review is performed or inferred, and no manifest for the real snapshot is sealed. No change to how a group is started, how a pack is validated at start or at execution, or to any API. No compose/env pass-through, no bind mount, no `.env.example` entry (all under `infra/**`, an integrator action). No import of the norms stand, no set promotion, no provider call, no migration. A manifest is not a signature: the digest detects an edited file, not a forger who holds the file (see Failure cases).

## Deliverables

- `v3_pack_manifest.py`: `parse_manifest`, `seal_manifest`, `load_manifest`, `load_trusted_pack_registry`, `read_regular_file`, `PackManifestRefused` (stable reason tokens), `ReviewAttestation`, `ParsedPackManifest`; exported through `runs/public.py`.
- `v3_pack_cli.py`: `verify` (offline) and `seal` (read-only transaction, injectable database access, atomic 0600 write, no overwrite without `--force`).
- Composition wiring in both roots.
- Container-free tests and one collectable database acceptance module.
- Report with the operator runbook.

## Required tests

- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_pack_manifest.py tests/integration/composition/test_v3_pack_install.py tests/integration/composition/test_v3_worker_registry.py -x`
- expected: all pass without a database, container or network (the composition cases build their own dummy environment).
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_execution_guard.py tests/integration/runs/test_v3_worker_pipeline.py tests/integration/db/test_ar_v3_pack_seal.py --collect-only -q`
- expected: collects cleanly; the database module is written but not run by this lane.
- `python -m auditmanager.runs.v3_pack_cli verify --manifest <sealed fixture>` exits 0 and a tampered copy exits 2; `git diff --check`; the governance check of this file prints `[]`; `python -m compileall -q src/auditmanager/runs src/auditmanager/bootstrap`. Full `make gate` is deferred by `R-135`; touching the composition root makes it a once-per-lane gate item for the integrator (AGENTS.md section 8, case 3).

## Integration contract

Provider: `auditmanager.runs.public` exposes `PACK_MANIFEST_ENV`, `PackManifestRefused`, `ReviewAttestation`, `ParsedPackManifest`, `load_trusted_pack_registry`, `parse_manifest`, `seal_manifest`. Consumers: the two composition roots (this task) and the CLI.

Behaviour the integrator can rely on: `AR_V3_BETA_PACK_MANIFEST` unset or blank gives `TrustedPackRegistry.empty()` in the API and the worker; set, it must name a regular, non-symlink file of at most 64 KiB whose JSON has exactly the frozen keys, whose `pack_sha256` equals the recomputed `TrustedPack.sha256`, whose six scopes are ordered `F1,F2,A1,A2,S1,S2` with six distinct map SHA-256 values and six distinct set ids, whose review strings are non-empty with a calendar `reviewed_at`, and which `TrustedPackRegistry.select_beta()` accepts; otherwise the process refuses to start with `ConfigurationError` carrying the reason token. The API and the worker must receive the same file: a worker holding a different pack refuses execution of a group the API accepted (existing preflight behaviour).

## Failure/idempotency/security cases

- The attestation is a record of a human decision. Presence and shape are checked; approval is never inferred, and no default reviewer exists anywhere in the code.
- `pack_sha256` binds the manifest to its own content. It is tamper evidence against an edit, not a signature: whoever can write the file and recompute the digest can install a pack. Custody of the file and of the host is the trust boundary; the read-only mount in the runbook is the control.
- The refusal text names a reason token and the object or field at fault, never a value read from the file and never the path. The CLI prints the reviewer as a JSON string so a newline cannot forge a second summary line.
- The loader opens with `O_NOFOLLOW | O_NONBLOCK`, decides the type by `fstat` on the opened descriptor, and reads at most 64 KiB + 1 byte, so a symlink, FIFO, directory or growing file cannot hang or exhaust the process. A symlinked directory on the way (a bind mount) is accepted; only the final component is.
- Duplicate JSON keys, `NaN`, a BOM and nesting bombs are refused as `manifest_not_json`; the last of two equal keys never wins.
- `seal` writes beside the target with `O_EXCL` and mode 0600, fsyncs, re-reads the temporary file with the loader, then publishes by `link` (fails if the target exists, no check-then-write window) or by `replace` with `--force`. A refusal leaves no target and no temporary file. It reads the database in one `SET TRANSACTION READ ONLY` transaction and never writes.
- Replaying the same `seal` is idempotent in content: the same sets give byte-identical output.
- Known limit: `builder_version` is checked for presence only here; `select_verified_retrieval_set` refuses a wrong value at every group start, and `seal` obtains it from the same call.

## Rollback / feature flag

Unset `AR_V3_BETA_PACK_MANIFEST` and restart the API and the worker: the registry is empty and group starts refuse again; or forward-revert the commit. No data, migration or contract is involved. Groups already started keep their rows; their execution refuses while no pack is installed (existing behaviour).

## Handoff

- changed files: `v3_pack_manifest.py`, `v3_pack_cli.py`, `runs/public.py`, `bootstrap/composition.py`, three test modules, this file and the report.
- commands/results: see the report; the container-free suite passes, the database module is collected only.
- known limits: database acceptance (`tests/integration/db/test_ar_v3_pack_seal.py`) not run; deploy pass-through under `infra/**` not done; the real six-map/six-set pack and its reviewer attestation do not exist yet.
- integration notes: merge after the lane's base; run the database module on a lane with PostgreSQL; add the compose pass-through and read-only mount as a separate infra slot; the composition-root edit puts this lane in the once-per-lane gate set.
