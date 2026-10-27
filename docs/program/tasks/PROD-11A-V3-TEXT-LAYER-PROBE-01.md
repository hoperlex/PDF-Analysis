# Task PROD-11A-V3-TEXT-LAYER-PROBE-01 — does a v3 Run leave the saved text layer that АР optimisation reads

task_id: PROD-11A-V3-TEXT-LAYER-PROBE-01
status: completed in development candidate; verdict UNSAFE (see the report)

## Outcome

A measured answer, committed as a test, to the question of `D-222` / `PROD-11a`: after `PROD-11` an АР version can start only the AR v3 group, and `optimisation/project_match.py` (`_newest_published`) and `optimisation/section_specification.py` (`_read_source`) take the saved page text of the newest **published** Run of the version. Does a v3 Run, driven to its terminal state through the production worker entry point, (1) reach the state those readers accept and (2) leave a saved text layer that `saved_page_text` returns? One new test module states the measured facts; the report carries the table and one of three verdicts: `SAFE`, `UNSAFE`, `UNKNOWN`. No change under `src/`, `db/`, `contracts/`, `infra/` or `web/`.

## Depends on

- `PRODUCTION-READINESS-PLAN-01` item `PROD-11a`, `ADR-0024` section 2 (correction of 2026-10-26), `D-222` — completed documents.
- `PROD-10-AR-V2-EXTRACT-01` finding 2 — completed (the task that found the dependency).

## Frozen inputs

- domain contract: not_applicable
- API contract: unchanged (`contracts/**` is not touched)
- analysis/comparison/event contract: not_applicable
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `0e663fd0e608fcf5f79075ea71713c24ddf027e5` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the two readers, the production text-layer reader, the executor's v3 branch and its required stages, the cost check, the existing v3 fixtures and the schema at head were re-read at the base commit; they match the plan, with three findings that the plan did not name (no existing test drives a v3 Run on a database; the stock recorded composition cannot pass the v3 cost check; the stage CHECK does not admit the CITE stage)

### P-01 — the two readers and the production text-layer reader

- captured_at: 2026-10-26
- command: `sed -n 207,216p src/auditmanager/optimisation/project_match.py; sed -n 521,541p src/auditmanager/optimisation/section_specification.py; sed -n 3039,3050p src/auditmanager/bootstrap/adapters.py; sed -n 3060,3070p src/auditmanager/bootstrap/adapters.py`
- captured_output:
  ```text
  def _newest_published(reader: SavedTextReader, session: Session, version_uid: str) -> str | None:
      runs = tuple(reader.runs_newest_first(session, version_uid=version_uid))
      for run in runs:
          if not isinstance(run, RunCandidate) or not isinstance(run.state, str):
              raise _integrity("a run candidate is malformed")
          try:
              RunId.parse(run.run_id)
          except (IdentityError, TypeError):
              raise _integrity("a run candidate is malformed") from None
      return next((run.run_id for run in runs if run.state == RUN_STATE_PUBLISHED), None)

  def _read_source(
      session: Session,
      reader: SavedTextReader,
      version: CurrentVersionPlacementRecord,
      positions: tuple[PriceListPositionRecord, ...] | None,
  ) -> tuple[SectionSource, tuple[SectionRow, ...], tuple[RowMatch, ...]]:
      source = _source(version, SOURCE_STATE_READY)
      version_uid = str(version.version_uid)
      run_id = _newest_published(reader, session, version_uid)
      if run_id is None:
          return replace(source, state=SOURCE_STATE_ANALYSIS_MISSING), (), ()
      source = replace(source, run_id=run_id)
      supplied = reader.saved_page_text(
          session, run_id=run_id, version_uid=version_uid, page_count=version.page_count
      )
      if supplied is None:
          return replace(source, state=SOURCE_STATE_TEXT_UNAVAILABLE), (), ()
      text = _checked_text(supplied, run_id=run_id, page_count=version.page_count)
      extraction = extract_specification(version_uid=version_uid, pages=text.pages)
      source = replace(
          source,

          from auditmanager.comparison.public import SavedPageText
          from auditmanager.runs import RunRepository

          stages = [
              row for row in RunRepository().stage_results(session, run_id)
              if row.stage_id == self._SOURCE_STAGE
          ]
          if len(stages) != 1 or stages[0].status != "succeeded":
              return None
          references = [a for a in stages[0].artifacts if a.get("role") == ROLE_TEXT_LAYER]
          if len(references) != 1:
              raise DomainError(

                  text_layer_ref=ArtifactRef(**dict(reference)),
                  supplied_bytes=payload,
              )
          except (SuppliedTextSourceRefused, TypeError, ValueError):
              raise DomainError(
                  ErrorCode.STORAGE_INTEGRITY_ERROR,
                  blob_id=str(reference.get("blob_id")),
                  role=ROLE_TEXT_LAYER,
                  expected_sha256=str(reference.get("sha256")),
              ) from None
          return SavedPageText(
  ```
- interpretation: matches the plan. The readers need (a) a Run of the version whose state is exactly `published` and (b) a `source_preparation` stage result that is `succeeded` with exactly one text-layer artifact whose bytes verify. Nothing else (no finding row) is read. `_SOURCE_STAGE` is `"source_preparation"` (line 3018). The served classes `_SpecificationTextReader` and `_ProposalTextReader` both delegate to this `_AnalysisReader.saved_page_text`.

### P-02 — the executor's v3 branch, the required stages and the cost check

- captured_at: 2026-10-26
- command: `rg -n "deterministic = \(" -A12 src/auditmanager/runs/executor.py | head -16; sed -n 1088,1097p src/auditmanager/runs/executor.py; sed -n 21,25p src/auditmanager/runs/v3_review_terminal.py; rg -n "def _check_completed_cost" -A12 src/auditmanager/runs/v3_worker.py`
- captured_output:
  ```text
  1034:    deterministic = (
  1035-        (
  1036-            "source_preparation",
  1037-            (ROLE_SOURCE_DOCUMENT, ROLE_SOURCE_MARKDOWN, ROLE_SOURCE_STRUCTURED_COMPANION),
  1038-        ),
  1039-        # `W55B-GEOMETRY-01`: the block list, when the version has one, is normalised into
  1040-        # `geometry.portal_blocks` and its IMAGE blocks are cut as crops.
  1041-        (
  1042-            "page_geometry_extraction",
  1043-            (ROLE_PAGE_INVENTORY, ROLE_TEXT_LAYER, ROLE_SOURCE_STRUCTURED_COMPANION),
  1044-        ),
  1045-        ("document_context_build", (ROLE_BLOCK_INDEX, ROLE_TEXT_LAYER)),
  1046-    )
      if v3_exact:
          # The last deterministic artifact binding holds the Lease row until
          # commit. The v3 request and reply readers do external Blob I/O without
          # that lock, and the journal commits each intent before its effect.
          session.commit()
          from auditmanager.runs.v3_review_terminal import finish_v3_review_run
          from auditmanager.runs.v3_worker import run_v3_worker_chain

          if halted:
              terminal = finish_v3_review_run(
  _REQUIRED = (
      "source_preparation", "page_geometry_extraction",
      "document_context_build", "ar_v3_citation_review",
  )
  59:def _check_completed_cost(call: object, ceiling_usd: float) -> None:
  60-    basis = getattr(call, "cost_basis", None)
  61-    micros = getattr(call, "cost_micros", None)
  62-    if basis == "unmetered" and micros == 0:
  63-        return
  64-    if basis not in {"measured", "estimated"} or type(micros) is not int or micros < 0:
  65-        raise DomainError(
  66-            ErrorCode.ANALYSIS_INPUT_INVALID,
  67-            message="a metered AR v3 call has no verifiable cost amount",
  68-            stage_id="text_analysis", reason="v3_metered_cost_unknown",
  69-        )
  70-    if micros > ceiling_usd * 1_000_000:
  71-        raise _budget_exceeded()
  ```
- interpretation: a v3 Run executes the same three deterministic stages as every other Run, **before** the v3 branch, so `source_preparation` and its text-layer artifact exist for it by construction. The v3 terminal needs those three plus `ar_v3_citation_review` and publishes only when all four succeeded. After the provider call a v3 call without a verifiable cost refuses before CITE.

### P-03 — the existing v3 fixtures: none drives a v3 Run on a database

- captured_at: 2026-10-26
- command: `git grep -l -E "ar_v3|startArV3BetaGroup|v3_group" 0e663fd0 -- tests/integration | wc -l; git grep -n -E "execute_run\(|run_to_terminal\(" 0e663fd0 -- tests/integration/runs/test_v3_execution_guard.py tests/integration/runs/test_v3_worker_pipeline.py tests/integration/composition/test_v3_worker_registry.py; rg -n "class FakeRuns|class Runs|class Jobs|monkeypatch.setattr\(v3_worker" tests/integration/runs/test_v3_cite_stage.py tests/integration/runs/test_v3_worker_pipeline.py`
- captured_output:
  ```text
  51
  tests/integration/composition/test_v3_worker_registry.py:30:    def run_to_terminal(*args, **kwargs):
  tests/integration/composition/test_v3_worker_registry.py:54:    carrier.run_to_terminal(
  tests/integration/runs/test_v3_execution_guard.py:95:        execute_run(
  tests/integration/runs/test_v3_execution_guard.py:121:        execute_run(
  tests/integration/runs/test_v3_execution_guard.py:132:        execute_run(
  tests/integration/runs/test_v3_worker_pipeline.py:266:    result = executor.execute_run(
  tests/integration/runs/test_v3_cite_stage.py:34:class FakeRuns:
  tests/integration/runs/test_v3_worker_pipeline.py:27:class Jobs:
  tests/integration/runs/test_v3_worker_pipeline.py:48:class Runs:
  tests/integration/runs/test_v3_worker_pipeline.py:84:    monkeypatch.setattr(v3_worker, "dispatch_v3_provider_call", dispatch)
  tests/integration/runs/test_v3_worker_pipeline.py:85:    monkeypatch.setattr(v3_worker, "run_v3_cite_stage", cite)
  tests/integration/runs/test_v3_worker_pipeline.py:265:    result = executor.execute_run(
  ```
- interpretation: 51 test files name the v3 group; the only `execute_run`/`run_to_terminal` calls among the v3 tests are an early-guard probe, a stubbed chain (`dispatch`, `cite`, `finish` replaced) and a registry-forwarding fake. The CITE writer is tested against `FakeRuns`/`FakeJobs`. The one database test of the group (`tests/integration/db/test_ar_v3_run_group.py`) claims members and resolves their pins and stops there, with fake blob rows. **There is no existing driver that takes the six Runs to terminal; this lane composes one from the production entry points inside its single test module** (`start_ar_v3_group`, `run_to_terminal`, the served reader), which the allowed paths permit.

### P-04 — the stack, and the schema at head

- captured_at: 2026-10-26
- command: `read-only SELECTs on the lane database (DATABASE_URL of the lane .env); rg -n "ar_v3_citation_review" db | wc -l`
- captured_output:
  ```text
  select: alembic_version -> [('0032_ar_v3_run_group',)]
  select: norms_snapshot -> [(0,)]
  select: norm_retrieval_set -> [(0,)]
  select: ar_v3_run_group -> [(0,)]
  select: pg_constraint where conname = 'ck_stage_ -> [("CHECK ((stage_id = ANY (ARRAY['source_preparation'::text, 'page_geometry_extraction'::text, 'document_context_build'::text, 'text_analysis'::text, 'block_analysis'::text, 'finding_merge'::text, 'finding_review'::text, 'finding_correction'::text, 'norm_verification'::text])))",)]
  0
  ```
- interpretation: the lane database is at head and holds no norms and no pack, so a reviewed pack cannot be read from it; the probe seeds a synthetic one into its own throw-away database. At head `ck_stage_result_stage_id` admits nine stage ids, and no file under `db/` mentions `ar_v3_citation_review`. The lane database itself is only read here; the probe never writes to it.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/integration/runs/test_v3_saved_text_layer_probe.py`
- `docs/program/tasks/PROD-11A-V3-TEXT-LAYER-PROBE-01.md`
- `docs/program/PROD-11A-V3-TEXT-LAYER-PROBE-01.md`

## Lane resources

- foundation_instance: the integrator's lane stack (`ar-close-1026`), not stopped, reset or written to by this lane
- postgres_db: a throw-away database `prod11a_probe_<random>` created on that server by the test, migrated by the literal migration command, dropped at the end
- s3_bucket: the lane bucket; objects are content-addressed and left in place, as in every other suite of `tests/integration/runs`

## Forbidden hotspots
- `src/**`, `db/**`, `contracts/**`, `infra/**`, `web/**` (this is a measurement)
- root dependency/lock files, composition roots, global styles
- `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs (the integrator records the verdict in `D-222`)

## Non-goals

- No fix: the migration that would widen the CHECK, the recorded-composition cost seam and any change to the readers belong to their own slots.
- No live provider call, no credential, no cost: the model answer is a recorded replay of an empty reply.
- No claim about the content of a real reviewed pack: it is installed by data (`D-204`) that no code can supply.

## Deliverables

- `tests/integration/runs/test_v3_saved_text_layer_probe.py`
- this task file and `docs/program/PROD-11A-V3-TEXT-LAYER-PROBE-01.md` (table, mutation table, verdict, integration notes)

## Required tests

- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/runs/test_v3_saved_text_layer_probe.py`
- expected: `15 passed`

## Integration contract

The module states the measured facts as assertions (fact 1 to fact 9 in the report). A later change that alters one of them turns the module red **on purpose**: in particular, a migration that admits `ar_v3_citation_review` flips the schema facts and the four facts that follow from them, which is the integrator's signal that `D-222` can be closed (checked, see mutation M14 in the report). The module needs the lane stack's PostgreSQL server (it creates and drops its own database, so `CREATEDB` is required) and its bucket.

## Failure/idempotency/security cases

- The throw-away database name is checked before the only DDL the module runs (the what-if widening); a test shows the check refuses the lane database.
- The module holds no credential and the recorded adapter holds no client; Python-level connections are checked to be loopback; the check is shown to be able to fail.
- A failed drive still drops the database (`finally`).

## Rollback / feature flag

Not applicable: a test and two documents; nothing changes behaviour.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report
- integration notes: see the report
