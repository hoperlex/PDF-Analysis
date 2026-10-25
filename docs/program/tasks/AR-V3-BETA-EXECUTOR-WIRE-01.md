# Task AR-V3-BETA-EXECUTOR-WIRE-01 — route reviewed v3 Runs through journal and CITE

## Outcome
A Run with the exact sealed AR v3 profile can execute through the existing worker only when the server has a reviewed six-set pack. It uses the saved-source/verified-set provider journal, reuses an already completed call after Attempt recovery, writes the review-only CITE stage, and reaches a truthful terminal without publishing canonical findings. The production registry stays empty.

## Depends on
- `AR-V3-BETA-PROVIDER-JOURNAL-01`
- `AR-V3-BETA-CITE-WRITER-01`
- `AR-V3-BETA-CITE-LEASE-01`
- `AR-V3-BETA-PROVIDER-LEASE-01`
- `AR-V3-BETA-SETTINGS-REPLAY-01`
- `AR-V3-BETA-RUN-STAGE-SEAL-01`

## Frozen inputs
- shared domain/API/analysis/events contract: `1.3.0`, unchanged
- AR v3 beta stage extension: `1.0.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `24627767c5f69593c322654c31fda13aac9f21ac`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the executor refuses either v3 profile field before starting a Job and the serving and worker composition roots install empty trusted-pack registries
### P-01 — guard and composition
- captured_at: 2026-10-26
- command: `git grep -n -E 'AR_V3_BETA_PROFILE_ID|TrustedPackRegistry.empty\(\)|ar_v3_pack_registry' 24627767c5f69593c322654c31fda13aac9f21ac -- src/auditmanager/runs/executor.py src/auditmanager/bootstrap/composition.py src/auditmanager/bootstrap/adapters.py; git grep -n -A 9 -E 'run_to_terminal\($' 24627767c5f69593c322654c31fda13aac9f21ac -- src/auditmanager/bootstrap/composition.py src/auditmanager/bootstrap/adapters.py`
- captured_output:
  ```text
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py:841:        ar_v3_pack_registry: Any = None,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py:849:        self._ar_v3_pack_registry = ar_v3_pack_registry
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py:881:            pack=(None if self._ar_v3_pack_registry is None
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py:882:                  else self._ar_v3_pack_registry.select_beta()),
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py:315:        ar_v3_pack_registry=TrustedPackRegistry.empty(),
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/runs/executor.py:98:    AR_V3_BETA_PROFILE_ID,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/runs/executor.py:869:    if (run.analysis_profile_id == str(AR_V3_BETA_PROFILE_ID)
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py:1014:            run_to_terminal(
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py-1015-                self._sessions,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py-1016-                run_id,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py-1017-                blob_store=self._blob_store,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py-1018-                adapter=self._model_adapter,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py-1019-                provider_config=self._provider_config,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py-1020-                text_profiles=self._text_profiles,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py-1021-                providers=self._providers,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py-1022-            )
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/adapters.py-1023-
  --
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py:159:        run_to_terminal(
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py-160-            sessions,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py-161-            run_id,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py-162-            blob_store=store,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py-163-            adapter=model_adapter,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py-164-            provider_config=provider_config,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py-165-            worker_id=worker_id,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py-166-            text_profiles=text_profiles.resolve,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py-167-            providers=providers.resolve,
  24627767c5f69593c322654c31fda13aac9f21ac:src/auditmanager/bootstrap/composition.py-168-        )
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 24627767c5f69593c322654c31fda13aac9f21ac with git grep against that tree (not at dispatch time). At the base, runs/executor.py imports AR_V3_BETA_PROFILE_ID (line 98) and compares run.analysis_profile_id with it at line 869; that the branch raises the v3 refusal (REQUIRED_NORM_UNAVAILABLE, 'the pinned AR v3 beta executor is not installed') comes from reading executor.py:862-878 of the base, not from the output. composition.py:315 passes TrustedPackRegistry.empty() as ar_v3_pack_registry, which adapters.py declares as a constructor parameter (841), stores (849) and reads for the pack (881-882). Neither run_to_terminal call site in the output (adapters.py:1014-1022, the carrier job of that adapter; composition.py:159-168, the worker's execute) passes a registry argument. Dispatch-time record (2026-10-23, quoted from the original section, not re-run): command `rg -n 'AR_V3_BETA_PROFILE_ID|TrustedPackRegistry.empty\(\)|run_to_terminal\(' src/auditmanager/runs/executor.py src/auditmanager/bootstrap/composition.py src/auditmanager/bootstrap/adapters.py`; captured_output was a prose summary: executor.py 869 is the v3 refusal; composition.py 315 installs an empty registry for API group start and worker composition calls `run_to_terminal` without one. Original interpretation: this integration must route the exact pair only with an injected reviewed registry while leaving production starts disabled.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/runs/carrier.py`
- `src/auditmanager/runs/v3_worker.py`
- `src/auditmanager/runs/v3_review_terminal.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `tests/integration/runs/test_v3_execution_guard.py`
- `tests/integration/runs/test_v3_review_terminal.py`
- `tests/integration/runs/test_v3_worker_pipeline.py`
- `tests/integration/composition/test_v3_worker_registry.py`
- `docs/program/tasks/AR-V3-BETA-EXECUTOR-WIRE-01.md`
- `docs/program/AR-V3-BETA-EXECUTOR-WIRE-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles, global styles
- provider transports, normative maps/source/set data, product VERSION
- `origin/main`, tag and deployment host

## Non-goals
- Installing an unapproved pack or making numerical/legal findings.
- Publishing a new API operation or the v3 review artifact to a screen; RunStatus shows the stage only.
- Claiming real PostgreSQL/S3/provider acceptance on this host.

## Deliverables
- Explicit v3 worker branch and review-only terminal policy with no v1 fallback.
- Composed empty registry for API and worker, plus injectable reviewed registry in tests.
- Recorded call/recovery/refusal tests and result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_execution_guard.py tests/integration/runs/test_v3_review_terminal.py tests/integration/runs/test_v3_worker_pipeline.py tests/integration/composition/test_v3_worker_registry.py -x --tb=short`
- expected: all pass, no migration or contract drift; handoff path check passes. Full make gate deferred by R-135.

## Integration contract
Only an exact v3 profile/bundle pair and server-installed reviewed pack can enter this branch. A completed canonical call is consumed without provider redispatch; an unresolved effect remains a durable refusal. CITE is grounded against the saved request and reply, and its StageResult gates a review-only `published` terminal with zero canonical findings. All other profiles retain their existing paths. The worker and API use their own explicitly empty registries until a later pack activation task changes both.

## Failure/idempotency/security cases
- Either mismatched v3 identity field, missing pack, stale Attempt, changed group/set, incomplete reply or failed CITE cannot publish a successful Run.
- A prior completed call of the same Job does not buy a second model call.
- A persisted failed CITE StageResult carries its stage reason to the terminal. A provider refusal before CITE uses the carrier's existing `analysis_failed` crash terminal while retaining its model-call/effect evidence; no silent fallback or model verdict.

## Rollback / feature flag
Production remains closed by `TrustedPackRegistry.empty()` at both composition roots. Revert this worker branch before pack activation; no migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: no approved six-set pack, review artifact read API or live stand acceptance
- integration notes: a later pack activation must configure identical reviewed pack bytes in API and worker
