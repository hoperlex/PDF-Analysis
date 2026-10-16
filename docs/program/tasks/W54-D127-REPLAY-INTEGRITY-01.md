# Task W54-D127-REPLAY-INTEGRITY-01 — verify persisted windows on an embedding-build replay

task_id: W54-D127-REPLAY-INTEGRITY-01

## Outcome

An exact `ensure_build` replay accepts an existing completed build only when its stored window metadata still hashes to the completion-row digest and retains the declared chunk/window counts.

## Depends on

- `W54-EMBED-01` — completed embedding repository, full-window validation and computed-key digest.
- `W54-SNAPSHOT-01` — completed stored chunk subject and reliability-aware profile.

## Frozen inputs

- base commit: `4efd756c67b5160aeca3dbc58903f72df6c93636`
- Published development candidate 26 is the exact base.
- Domain candidate revision 14; API 48 paths / 55 operations / 131 schemas; error catalogue 25; migration head `0023_norm_citations`.
- API `contracts/api/v1/openapi.json` SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
- Analysis stage registry `contracts/analysis/v1/stage-registry.json` SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`.
- Domain, comparison and event contracts unchanged by this task.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `ensure_build` recomputes `stored_build_digest` only after a new insertion, and returns an existing build after comparing the supplied digest to the completion row.
- captured_at: 2026-10-16
- command: `git show 4efd756c67b5160aeca3dbc58903f72df6c93636:src/auditmanager/norms/embedding_repository.py | sed -n '363,374p'`
- captured_output:
  ```text
        expected = (chunk_total, digest.windows, digest.hexdigest())
        if stored is not None:
            actual = (int(stored.chunk_count), int(stored.window_count), stored.embedding_set_sha256)
            if actual != expected:
                raise NormEmbeddingConflict(
                    f"embedding build {snapshot_id}/{chunking_profile}/{embedding_profile} "
                    f"already exists with {actual!r}, requested {expected!r}"
                )
            return self._result(snapshot_id, chunking_profile, embedding_profile, expected, False)

        self._session.execute(
            _INSERT_BUILD,
  ```
- interpretation: a replay never reads its persisted windows, so deletion or corruption of a stored row can be silently accepted; the transaction-local streamed digest reader already exists.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/embedding_repository.py`
- `tests/integration/norms/embedding/test_repository_offline.py`
- `docs/program/tasks/W54-D127-REPLAY-INTEGRITY-01.md`
- `docs/program/W54-D127-REPLAY-INTEGRITY-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, dependency and lock files, composition root, API/UI, shared fixtures, `CURRENT_STATE.md`, the source corpus, publication refs and tags.

## Non-goals

- No new embedding profile, tokenizer, vector format, schema, build job or production corpus operation.
- No guarantee against direct out-of-band DB deletion after a successful read; qualification and export continue to run their own checks. Vector-byte rehashing is outside the documented metadata digest.

## Deliverables

- Streamed stored-window digest/count verification on an existing-build replay.
- A focused test that first demonstrates a missing persisted window is accepted, then passes after the repair.
- Evidence report naming file scope, tests and the remaining live-DB limit.

## Required tests

- Run `PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/integration/norms/embedding/test_repository_offline.py -p no:cacheprovider` without PostgreSQL/S3.
- Run direct task governance and `git diff --check`.
- Do not run Docker, a database or the full gate while the W55b gate owns the host resource slot.

## Integration contract

The integrator may cherry-pick the one clean source commit. A replay now streams all persisted rows and compares digest and counts to the supplied/completion identity. An existing complete build still returns `created=False`; new build insertion behavior is unchanged. Full PostgreSQL and corpus checks remain integrator work after the resource window opens.

## Failure/idempotency/security cases

- Missing, mutated or extra persisted windows cause `NormEmbeddingConflict`, and no completion is claimed.
- The repository never commits; caller rollback semantics remain.
- No corpus bytes or credentials enter task evidence.

## Rollback / feature flag

- Revert this isolated repository/test commit; no schema or feature flag is changed.

## Handoff

- Changed files, commands/results, limitations and exact commit are in the report.
