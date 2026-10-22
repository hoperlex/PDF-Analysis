# AR-SET-PROMOTION-01 — result report

## Result

The unserved promotion service now assembles a retrieval candidate for one caller-pinned snapshot/build and reviewed map, compares independent proof digests and expected canonical artifact hashes, and persists a mismatch as an immutable rejected row. Each write/admission/finalization re-runs read-only preparation against the pinned DB facts and requires the exact candidate, so a hand-constructed or stale `PreparedPromotion` is not authority. Matching bytes are admitted through the existing two-role custody outbox; after dispatch, finalization re-reads both saved objects and inserts the verified set plus both bindings in one database transaction. A preflight of 0023's verified identity key refuses a different `set_id` before new admission or Blob read. Exact retries preserve `set_id`; a changed map, digest, admission or Blob refuses. The public read port returns only an exact verified row with confirmed available custody. Run INSERT has an additive nullable set pin, and the optional frozen-input digest includes the set SHA only when passed explicitly.

This is persistence groundwork, not a v3 runtime activation. It accepts a caller-supplied scope map and never assumes one global 22-document set. The budget evidence `efe765ba` showed the all-22 prompt refused at 76–88k characters against the 22k cap; scope-bound Run selection and contract remain separate. The existing 0023 UNIQUE verified identity is `(map_sha256, norms_snapshot_id, chunking_profile, embedding_profile, builder_version)`. Six scope groups therefore need six distinct scope-specific map digests, or a separately owned schema seal; one global map digest cannot yield six verified sets under this schema.

## Changed files

- `src/auditmanager/norms/retrieval/promotion.py` — preparation, refusal, admission, finalization and exact selection.
- `src/auditmanager/norms/retrieval/promotion_repository.py` — specialized immutable set SQL and verified-custody read.
- `src/auditmanager/norms/public.py` — cross-context promotion port.
- `src/auditmanager/runs/repository.py` — nullable INSERT pin and `RunRow` readback.
- `src/auditmanager/runs/commands.py` — optional set digest in future frozen input.
- `tests/integration/norms/retrieval/test_promotion.py` — offline order, mismatch, replay, manifest, Blob-byte and forged-comparison checks.
- `tests/integration/norms/custody/test_retrieval_set_promotion.py` — synthetic real PostgreSQL/S3 two-object acceptance, including rejected row, dispatch and verified read.
- `tests/integration/runs/test_retrieval_set_persistence.py` — Run INSERT pin and digest compatibility.
- `docs/program/tasks/AR-SET-PROMOTION-01.md` — task grant, frozen base, lane resources and cleanup.
- `docs/program/AR-SET-PROMOTION-01.md` — this result report.

## Checks

- `pytest -c pyproject.toml --rootdir=. -q tests/contract/api_v1/test_w57a_citation_contract.py tests/integration/norms/retrieval tests/integration/runs/test_retrieval_set_persistence.py tests/contract/program`: **136 passed** (offline).
- `pytest -c pyproject.toml --rootdir=. --collect-only -q tests/integration/norms/custody/test_retrieval_set_promotion.py`: **1 collected**; actual DB/Blob execution pending assigned lane.
- `python -m compileall -q` for changed Python: passed.
- `git diff --check`: passed.
- Whole `make gate`: integrator owns it under `R-135`; not run in this branch.

## DB/Blob lane

Assigned only to this task: instance `auditmanager-ar-set-promotion-01`, PostgreSQL `57741`, S3 API `61542`, S3 console `61543`, database `auditmanager_ar_set_promotion_01`, bucket `auditmanager-ar-set-promotion-01`. The test uses one synthetic document/chunk/window and two tiny JSON objects; the 674-document import is excluded. Before any start on 2026-10-22, `df -B1 .` showed 5,974,142,976 bytes free, below the 6144 MiB gate margin. The lane remains stopped until the integrator completes the gate and approves capacity. A temporary ignored `.env` and `.venv` symlink belong solely to this worktree and must be removed after the test. Only task-owned volumes may be removed, after recording evidence; no other lane may be touched.

## Contracts and limitations

- No frozen contract or migration changes; contract remains `1.0.0`, migration head `0031`, storage uses existing `0023` schema.
- No reviewed owner map or real normative qualification is asserted. The real DB/Blob test is synthetic mechanics only and explicitly substitutes W57 preparation; the production write path re-runs the real reader. A caller must run preparation and persistence under a consistent database read transaction for the named snapshot/build.
- The served v1/v2 start/re-audit commands still create NULL set pins and their frozen digest stays byte-identical. A later scoped v3 runtime task must choose the verified set for its requested scope, include its SHA in frozen input, and dispatch only after commit.
- A later scoped runtime must give each group a distinct reviewed map digest under 0023. Reusing one global digest for all six groups conflicts with the immutable verified identity key; adding scope/composition columns requires a separate owned migration/contract task.
- Custody's confirmed admission is the durable outbox. External object writes occur only in its existing dispatcher, outside the DB transaction. Verified set and both bindings are one transaction; rollback leaves admissions available for reconciliation.

## Integration and rollback

Cherry-pick the final candidate commit into the integration branch, run the real DB/Blob acceptance and full gate before any publication. Do not activate v3 runtime until the scope-bound contract and reviewed map are owned. Roll back by reverting this additive code commit; existing immutable `0023` rows remain as evidence. The temporary lane can be stopped and its exact named volumes removed after checks; keep all other lane resources intact.

## Hotspot audit

No changes to `contracts/**`, `db/migrations/**`, root dependency/lock files, bootstrap/composition root, `web/**`, global styles, refs, tags or deployment stand. The changed source, tests and docs are the task's allowed paths; the temporary ignored lane files are separately recorded in its addendum and are not committed.
