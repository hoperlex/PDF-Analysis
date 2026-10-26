# Task AR-V3-BETA-ACCEPT-RECORDED-01 — the recorded AR v3 beta group, driven over HTTP the way a reviewer drives it

task_id: AR-V3-BETA-ACCEPT-RECORDED-01
status: completed in development candidate (see the report)

## Outcome

One integration module, `tests/integration/runs/test_v3_recorded_group_over_http.py`, that on a private migrated database installs a sealed synthetic pack through the composition root (`AR_V3_BETA_PACK_MANIFEST`), builds the stock recorded application (`build_application`, only the model answer stood in), starts the AR v3 beta group over HTTP (`startArV3BetaGroup`), carries the six Runs to `published` on the application's own carrier and asserts what a reviewer reads from `getArV3BetaGroup`, `getArV3BetaGroupReview` and `getArV3BetaPackStatus`: six scope outcomes with the right labels; provisional citations that carry the expert-review label; no numerical conclusion anywhere; a review that agrees with the group; an idempotent second start; the typed refusals for an empty registry, a non-expert and an anonymous caller; a review that says `pending` before the Runs finish and `available` after. It is the recorded half of `AR-V3-BETA-ACCEPT-01`; the live half needs the activation data (`D-204`) and is not this lane.

It also measures a **gap in the product** that the probe could not see because it never started a group over HTTP: the start leaves the six Runs `created` with no Job, and nothing in a served process carries them (P-04, fact 5).

## Depends on

- `PROD-11A-V3-TEXT-LAYER-PROBE-01` — completed (the driver and the pack helpers this lane reuses).
- `PROD-11B-V3-STAGE-ID-MIGRATION-01` — completed (migration `0033`: without it the CITE row is refused by the database).
- `PROD-11C-RECORDED-COST-01` — completed (the stock recorded binding is unmetered for the sealed v3 pair: without it every recorded Run ends `analysis_input_invalid`).
- `AR-V3-BETA-GROUP-API-SEAL-01`, `AR-V3-BETA-PACK-STATUS-API-01`, `AR-V3-BETA-PACK-INSTALL-01` — completed (the four operations and the sealed manifest loader).

## Frozen inputs

- domain contract: not_applicable
- API contract: unchanged (`contracts/**` is not touched); the module reads `contracts/api/v1/openapi.json` and `contracts/domain/v1/error-codes.json` as its expectations
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id`, unchanged
- base commit: `b0644fd3` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the PW3 dispatch says the probe drives the six Runs through the service layer, that nothing drives them over HTTP, and names what to capture: the probe's driver and pack construction, the route handlers and error codes of the four operations, the beta citation policy, and the carrier used by `run_to_terminal`; it adds that if the product has no way to carry a Run over HTTP without a worker process the lane says so and drives the carrier at the probe's seam. Re-read at the base commit: the probe, the four operations and the policy are as described; the carrier part differs in a way that matters (P-04): the HTTP start neither queues the Runs nor enqueues a Job, so the product offers no HTTP-side way to carry them, only the in-process seam `RunAdapter.submit_existing` -> `carrier.submit` -> `run_to_terminal`.

### P-01 — the probe's driver and pack construction

- captured_at: 2026-10-26
- command: `rg -n "^def (_publish_source|_seed_norms|_drop|_database_url|_require_loopback|_require_probe_database)|^class _RecordOnFirstSight|^def probe_database|^QUOTE|^PROFILE_ID|^BUNDLE_ID" tests/integration/runs/test_v3_saved_text_layer_probe.py; rg -n "run_to_terminal\(factory" tests/integration/runs/test_v3_saved_text_layer_probe.py`
- captured_output:
  ```text
  113:PROFILE_ID = "ap_01M5M28ZCDD8VPSP1BTAEW92YE"
  114:BUNDLE_ID = "pb_01M5M28ZCDVCR37BX1884JGSPM"
  117:QUOTE = "Test normative paragraph."
  125:def _database_url() -> str:
  132:def _drop(maintenance: Engine, name: str) -> None:
  143:def probe_database() -> Iterator[str]:
  220:def _publish_source(
  295:def _seed_norms(session: Session, store: Any, source: Source, actor: str) -> TrustedPack:
  425:class _RecordOnFirstSight(RecordedAdapter):
  635:def _require_probe_database(name: str) -> None:
  640:def _require_loopback(peers: list[str]) -> None:
  678:            run_to_terminal(factory, member.run_id, blob_store=store, adapter=adapter,
  740:            run_to_terminal(factory, started.run_id, blob_store=store,
  ```
  and the baseline of the probe before any change: `18 passed in 24.19s`.
- interpretation: the probe seeds a throw-away database (`probe_database`, prefix `prod11a_probe_`), a published AR version (`_publish_source`), six synthetic canonical sets with real bytes and custody rows (`_seed_norms`, returns the `TrustedPack`) and a replay that writes its reply on first sight (`_RecordOnFirstSight`). It calls `run_to_terminal` directly on `created` Runs. A test module is not importable by name under `--import-mode=importlib`, so the new module loads the probe by explicit path (the mechanism `conftest.py` uses for the harness) and binds only the helpers it needs; the probe is not edited. The synthetic paragraph text (`QUOTE`) has no number, which matters for P-06.

### P-02 — the four operations, their roles and their error codes

- captured_at: 2026-10-26
- command: `rg -n "operation_id=|\"/ar-v3-beta" src/auditmanager/api/routers/ar_v3_groups.py; rg -n "\"(startArV3BetaGroup|getArV3BetaGroup|getArV3BetaGroupReview|getArV3BetaPackStatus)\":" src/auditmanager/api/security.py`, then the contract: `python3` over `contracts/api/v1/openapi.json` (`paths` containing `ar-v3`, `info.version`) and `contracts/domain/v1/error-codes.json` (`codes[...].http`, `.retryable`)
- captured_output:
  ```text
  18:        "/ar-v3-beta/groups",
  19:        operation_id="startArV3BetaGroup",
  38:        "/ar-v3-beta/groups/{group_id}",
  39:        operation_id="getArV3BetaGroup",
  55:        "/ar-v3-beta/groups/{group_id}/review",
  56:        operation_id="getArV3BetaGroupReview",
  72:        "/ar-v3-beta/pack",
  73:        operation_id="getArV3BetaPackStatus",
  359:        "getArV3BetaGroup": _ANY_ROLE,
  360:        "getArV3BetaGroupReview": _ANY_ROLE,
  361:        "getArV3BetaPackStatus": _ANY_ROLE,
  423:        "startArV3BetaGroup": _EXPERT,
  POST /ar-v3-beta/groups startArV3BetaGroup ['202', '401', '403', '404', '409', '422', '500', '503']
  GET /ar-v3-beta/groups/{group_id} getArV3BetaGroup ['200', '401', '403', '404', '500', '503']
  GET /ar-v3-beta/groups/{group_id}/review getArV3BetaGroupReview ['200', '401', '403', '404', '500', '503']
  GET /ar-v3-beta/pack getArV3BetaPackStatus ['200', '401', '403', '500', '503']
  info.version 1.6.0
  dependency_unavailable 503 True
  permission_denied 403 False
  authentication_required 401 False
  validation_failed 422 False
  idempotency_key_reuse 409 False
  ```
- interpretation: only the start needs the `expert` role; the three reads take either role. The empty-registry refusal the code raises is `dependency_unavailable` with `dependency: ar_v3_trusted_pack` (`runs/v3_group.py`), which the contract maps to `503` and `retryable: true`; a non-expert is `permission_denied` `403`. The module takes the status and the retryability from the contract files, not from the code under test.

### P-03 — the beta citation policy

- captured_at: 2026-10-26
- command: `rg -n "C05/C06" docs/program/AR-BETA-CITATION-REVIEW-GATE-01.md; sed -n 232,248p src/auditmanager/runs/v3_citations.py`
- captured_output:
  ```text
  5:... Grounded proposals citing only the 14 provisional topics are returned as **review-only proposal ordinals**. Proposals citing C05/C06/C08/C09/C10/C15/C21/C22, including a mix with a provisional label, are withheld. The returned beta type has no normative publication-candidate field; neither an LLM answer nor this gate creates an expert decision or numeric conclusion.
      )
      by_item = {item.item_id: item for item in policy.group(request.scope_id)}
      provisional: list[int] = []
      withheld: list[int] = []
      for accepted in plan.evaluation.grounding.accepted:
          if not accepted.norm_citations:
              continue
          citations = accepted.proposal.norm_citations
          if citations is None:
              raise V3CorpusCitationRefused("beta_normative_citations_missing")
          try:
              modes = tuple(by_item[label_items[citation.label]].mode
                            for citation in citations)
          except KeyError as exc:
              raise V3CorpusCitationRefused("beta_citation_label_invalid") from exc
          if all(mode == "provisional_citation" for mode in modes):
              provisional.append(accepted.proposal_ordinal)
  ```
  and `runs/v3_review_artifact.py` writes `"review_status": "requires_expert_review"` on every topic.
- interpretation: the eight context-only items are written out in the module from this document, not read from code. The wire carries the machine value `requires_expert_review`; the Russian label «требует проверки эксперта» is rendered by the web widget (`web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx`, one fixed sentence per topic), so the module asserts the wire value (decided by the lane, see below).

### P-04 — the carrier, and what the HTTP start leaves behind

- captured_at: 2026-10-26
- command: `rg -n "No Job or provider call" src/auditmanager/runs/v3_group.py; rg -n "JobRepository|advance\(|\.submit\(|enqueue" src/auditmanager/runs/v3_group.py src/auditmanager/api/routers/ar_v3_groups.py; sed -n 80,98p src/auditmanager/jobs/repository.py | grep -n "j.state = 'queued'\|r.state IN"; rg -n "def submit_existing" -A3 src/auditmanager/bootstrap/adapters.py; rg -n "configure_runner|DurableCarrier\(|ReclaimingCarrier\(" src/auditmanager/bootstrap/composition.py; rg -n "STRANDED_STATES\s*[:=]" src/auditmanager/runs/reconciliation.py`
- captured_output:
  ```text
  5:The caller owns the transaction. No Job or provider call is made here.
  11:    "WHERE j.state = 'queued' AND r.state IN ('queued', 'running') "
  1102:    def submit_existing(self, run_id: str) -> None:
  1103-        """Wake execution for a durable re-audit accepted in another command."""
  1104-        self._carrier.submit(self._job(run_id))
  334:        ReclaimingCarrier(sessions) if resolved.execution_role == "api"
  335:        else DurableCarrier(sessions)
  367:        carrier.configure_runner(run_adapter._job)
  71:STRANDED_STATES: Final[tuple[str, ...]] = ("running",)
  ```
  (the second `rg` printed nothing: `v3_group.py` and the router contain no `JobRepository`, no `advance(`, no `.submit(` and no `enqueue`). Then the measurement of the new module's first draft, same instrument, after `POST /ar-v3-beta/groups` and before any carry:
  `states_after_start = F1..S2 all "created"`, `after_start = {"groups": 1, "runs": 6, "jobs": 0}`, `next_queued_run_after_start = null`.
- interpretation: `RunAdapter.start_ar_v3_group` (adapters.py 884-897) writes the group and six `created` Runs in one transaction and returns; unlike `start_run` it does not `advance(created -> queued)`, does not `enqueue` a Job and does not `carrier.submit`. The serving carrier's poller (`DurableCarrier._poll`) runs `JobRepository.next_queued_run`, whose query needs a `queued` Job of a `queued` or `running` Run, and the startup reconciliation touches only `running` Runs. So in a served process nothing carries the six Runs: they stay `created`, and the group review reads six `pending` for ever. The web hook says «six queued Runs, six new queued jobs» (`web/src/features/start-ar-v3-group/model/use-start-ar-v3-group.ts`), which is the intent, not the fact. The only product seam that carries an already-accepted Run in-process is `RunAdapter.submit_existing(run_id)` -> `carrier.submit(self._job(run_id))` -> `run_to_terminal`, on a `DurableCarrier` that is not started (`start` belongs to the serving lifespan; an unstarted one runs a submitted job on its thread pool, and `carrier.drain` waits for it). That is what the module uses, and fact 5 pins the gap.

### P-05 — the composition seam the module builds on

- captured_at: 2026-10-26
- command: `rg -n "def build_application|_build_provider\(|RunAdapter\(|ar_v3_installed_pack|build_router\(|ar_v3_groups=" src/auditmanager/bootstrap/composition.py | head -12; rg -n "def create_asgi_app" -A4 src/auditmanager/api/app.py`
- captured_output:
  ```text
  77:def _ar_v3_installed_pack(env: dict[str, str]) -> ParsedPackManifest | None:
  103:    return _registry_of(_ar_v3_installed_pack(env))
  193:    model_adapter, provider_config, _profile_id, _bundle_id, providers = _build_provider(
  237:def build_application(
  288:    model_adapter, provider_config, profile_id, bundle_id, providers = _build_provider(
  338:    ar_v3_installed_pack = _ar_v3_installed_pack(env)
  339:    run_adapter = RunAdapter(
  362:        ar_v3_pack_registry=_registry_of(ar_v3_installed_pack),
  364:        ar_v3_installed_pack=ar_v3_installed_pack,
  369:    router = build_router(
  373:        ar_v3_groups=run_adapter,
  484:def _build_provider(
  153:def create_asgi_app(
  154-    environ: dict[str, str] | None = None,
  155-    *,
  156-    application: Application | None = None,
  157-) -> FastAPI:
  ```
- interpretation: `build_application(environ=...)` is the stock composition: `_build_provider` (the recorded branch with PROD-11C's unmetered replay binding), `load_text_profiles`, `DurableCarrier`, the sealed-manifest loader and `RunAdapter` are all its own. The module patches only two names for the duration of the call: `_build_provider` (to swap the adapter for the replay and keep the stock `call` binding) and `RunAdapter` (a subclass that keeps its instance so `submit_existing` can be called). The application is served by `create_asgi_app` through a `TestClient` (no lifespan).

### P-06 — what a grounded normative proposal needs

- captured_at: 2026-10-26
- command: the module's first draft with the probe's own reply and `QUOTE`, one observation with `required_value` `1,4 м`, the review's rejected proposals read through `read_v3_saved_review`; then `rg -n "norm_value_not_in_quote|stated_value_not_in_evidence" src/auditmanager/norms/citation_prep.py`
- captured_output:
  ```text
  [[{'proposal_ordinal': 0, 'reason': 'norm_value_not_in_quote'}], ... six scopes, the same ...]
  295:        return withheld("norm_value_not_in_quote")
  297:        return withheld("stated_value_not_in_evidence")
  ```
- interpretation: a normative category (here `evacuation`) must carry `norm_citations`, a `required_value` and a `stated_value`; the required value must occur in the cited norm quote and the stated value in the PDF evidence quote, otherwise the proposal is rejected. The probe's synthetic paragraph has no number, so a numeric proposal over it is rejected. To produce a **grounded** numeric proposal the module sets `QUOTE` on its own copy of the probe (the seed reads the global when called) to a sentence that contains `1,4 м`, and cites a quote of page 7 of the baseline PDF that contains `1,2 м`. A second proposal states `9,9 м`, which is not on the page: rejected, visible only as a count.

## Decisions (taken by the lane; the owner asked for no questions)

- decided by the lane: the Runs are carried with `RunAdapter.submit_existing` on the application's own unstarted `DurableCarrier` (P-04), not by the probe's direct `run_to_terminal` call, because that is the product's own carrier path and it uses the adapter's own providers, text profiles and pack registry; the poller cannot be used until the product queues the group's Runs.
- decided by the lane: the gap is pinned as a measured fact (fact 5) with a docstring that says what to do when it is fixed, rather than worked around silently or left unasserted. It is reported to the integrator as a candidate debt row; the lane may not touch `src/**` or the register.
- decided by the lane: «`ready` after they finish» in the dispatch is the contract's `available` (`review_state`: `pending`, `failed`, `verification_refused`, `available`); there is no `ready` value on the wire.
- decided by the lane: «the review label from the beta policy» is asserted as the wire value `requires_expert_review` on every topic; the Russian sentence is the widget's and the module does not read web sources.
- decided by the lane: «no numerical conclusion field anywhere in the answers» is five checks: every key of every answer is one the contract declares for these schemas (so an injected property is red), no key is a conclusion-shaped name, no number is a float, the model's own prose and severity never appear, and the numbers of the reply appear only inside the two verbatim quote fields (`quote`, `raw_quote`), which are the PDF's and the norm's own words.
- decided by the lane: the empty-registry refusal is asserted on a second application built from the same database without a manifest, which is how a server without the pack behaves; the admin-only and the role-less accounts are the two non-experts; an anonymous start and a start that names a pack or a scope are added because the contract declares `401` and `422` for the operation.
- decided by the lane: the module loads the probe by explicit path and binds only helper names; it reuses the probe's `probe_database` fixture (so its database is named `prod11a_probe_*`) rather than copying it.
- decided by the lane: everything is measured once in a module-scoped fixture, because the suite's autouse `_no_network` fixture refuses new sockets during a test body and a `TestClient` needs a socket pair; the tests read the captured exchanges, the way the probe does.
- decided by the lane: accounts for the HTTP seam are created in the private database with the access repositories (not `provisioned_credential`, which writes into the shared lane database).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths
- `tests/integration/runs/test_v3_recorded_group_over_http.py`
- `docs/program/tasks/AR-V3-BETA-ACCEPT-RECORDED-01.md`
- `docs/program/AR-V3-BETA-ACCEPT-RECORDED-01.md`

## Lane resources

- foundation_instance: the integrator's lane stack (`ar-close-1026`), not stopped, reset or written to by this lane
- postgres_db: one throw-away database per run of the module (`prod11a_probe_*`, created and dropped by the probe's fixture); none left behind
- s3_bucket: the lane bucket (content-addressed objects only)

## Forbidden hotspots
- `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, root dependency/lock files, global styles
- `tests/integration/runs/test_v3_saved_text_layer_probe.py` and every other existing test
- documents other than the two deliverables, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals
- No live provider call, no cost measurement, no activation (`D-204`, `PROD-12`): the live half of `AR-V3-BETA-ACCEPT-01`.
- No fix of the gap in P-04: the product is not touched.
- No browser and no web assertion.

## Deliverables
- the new module (55 tests), this task file and `docs/program/AR-V3-BETA-ACCEPT-RECORDED-01.md` (premise, mutation table, commands with counts, integration notes, the gap)

## Required tests
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/runs/test_v3_recorded_group_over_http.py`
- expected: `55 passed`; the probe `tests/integration/runs/test_v3_saved_text_layer_probe.py` still `18 passed`

## Integration contract

The integrator merges with `--no-ff`. The module needs the lane stack (`DATABASE_URL`, the S3 variables) and no other service. After the merge it is the recorded acceptance of the group over HTTP. **Fact 5 is a deliberate red-on-fix:** when the product starts queueing the group's Runs (advance `created -> queued` and enqueue a Job in the start's transaction, or an equivalent poller), `test_the_http_start_leaves_the_six_runs_created_and_unqueued_for_the_serving_poller` turns red (and with it the facts that read the state right after the start); the carry step then becomes the serving poller, started by the lifespan, and those facts are flipped. The module changes no code path.

## Failure/idempotency/security cases
- empty registry: `503 dependency_unavailable` (`dependency: ar_v3_trusted_pack`), nothing created
- an administrator and an account with no role: `403 permission_denied` (`required_capability: role:expert`), nothing created; no credential: `401`
- a body that names a pack digest or scopes: `422 validation_failed` (`additionalProperties`), nothing created
- the same key and body: `202`, the same group and Runs, no new row, no new provider request, also after the Runs finished; the same key with another version: `409 idempotency_key_reuse`, nothing created
- a read while the first Run is at the provider: one `running`, five `created`, six `pending`

## Rollback / feature flag
Not applicable: one new test module and two documents; reverting the lane removes them.

## Handoff

- changed files: see the report
- commands/results: see the report
- known limits: see the report
- integration notes: see the report
