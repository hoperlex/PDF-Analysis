# CMP wave C0 — report to the integrator of `origin/dev`

Integrator of the CMP waves: `pdf-analysis-12` (formerly `pdf-analysis-4d`). Branch `integration/compare-modules`, tip
`94695e8e` (base `origin/dev` `10432537`, merged at `c86ae7b0`). Plan `docs/program/dispatch/COMPARE-MODULES-PLAN.md`,
ADR `docs/architecture/adr/ADR-0025-comparison-modules.md` (with the 2026-10-27 addendum), wave brief
`docs/program/dispatch/CMP-WAVE-C0.md`.

## Facts after the wave
- Contract `1.9.0`, 115 paths / 130 operations / 351 schemas, 27 error codes (no new code); migration head
  `0038_comparison_foundation`; `VERSION` unchanged (`0.9.0`; no release note in this wave).
- New dependencies: `numpy==2.5.4`, `opencv-python-headless==4.14.0.94`, `reportlab==5.1.0` (licences and bundled
  libraries in `docs/program/CMP-SEAL-C0.md`; images grow ≈ 230 MB; the OpenCV wheel bundles OpenSSL 1.1.1k).
- Module flag `ProductVersion.comparison_modules` (`none` by default) — enabling needs `AUDITMANAGER_COMPARISON_MODULES`
  on api and worker (PROD-05b).

## Lanes merged (each report under `docs/program/<ID>.md`)
CMP-ORIGINAL-READ-01, CMP-ADR-01, CMP-FIXTURES-01, CMP-MEASURE-01A, CMP-SEAL-C0, CMP-VERSION-MARK-01,
CMP-STORAGE-PARTS-01, CMP-WORK-01, CMP-INGEST-ZIP-01, CMP-EXEC-IMAGES-01, CMP-PROFILE-01, CMP-SPEND-01,
CMP-PROFILE-QUEUE-01, CMP-INGEST-01, CMP-C0-FIX-01, CMP-INGEST-02; integrator commits `34dcf9a1` (worker hand-over of
the comparison queue) and `94695e8e` (stub list after the merges).

## Granted change in `jobs/` (your grant, conditions met)
`JobRepository._hold_connection_limit`, constant `_CONNECTION_HAS_OTHER_ACTIVE_RUN` in
`src/auditmanager/jobs/repository.py`: the existing EXISTS over active jobs of the connection, plus `OR EXISTS` over
`comparison_model_call` rows in `prepared`/`sent` whose attempt is `created`/`leased`/`running` on the same connection.
Exact before/after SQL in `docs/program/CMP-SPEND-01.md`; EXEC-PAR-QUEUE-01 tests unmodified and green; mutation M17a.

## Verification on the merged tree (light acceptance, R-70)
- `tests/contract` minus the three `D-220` files: green (1307 at the seal; re-run per lane).
- Unit: `tests/unit/comparison`, `workers`, `executors`: 1214+ passed (per merge).
- Integration on an isolated stack of the integration tree: composition, recovery, comparison, ingest
  comparison_pdf/comparison_batch, documents, storage, executors — **3533 passed, 20 skipped, 11 failed**; the 11 are
  all in `tests/integration/comparison/profile_queue` and pass 18/18 on a fresh database: those tests assume no
  claimable Run exists in the database (the comparison queue yields to Runs by design). Test isolation fix is the
  first item of the next FIX slot.
- No complete `make gate` (moved to debt by the owner, `Q-CMP-11`); no web journey (the only web change is the
  comparison-only mark; web lint/typecheck/vitest green in that lane).

## Open items
- Owner: the ZIP security review (ADR-0025 decision 12) was stopped by a model safety classifier before any probe;
  path to be chosen by the owner; `__MACOSX/` refusal; confirmation of the A-2 widening to drawing images.
- Next seal (SEAL-C1) also amends the contract prose you listed (registration caps, run-CSV apostrophe rule, preset
  error words, D-246/D-251/D-253), registers the reasons of `comparison_zip_*` and of INGEST-01 §6, adds a read for the
  «Сравнение» block of «Очередь» and a field for «После подготовки сравнить все соседние версии».
- Debts to open from D-260: `_NEXT_JOB` dispatch hint does not see comparison calls; five pickers without the
  comparison-only mark; the ZIP security review; acts of the batch lane not in `audit_event`; module `none` keeps
  drive/sweep items queued and blocks project erase until cancel.
