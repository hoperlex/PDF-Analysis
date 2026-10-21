# W56A-FREEZE-01 — blocked preflight, no implementation grant

**Status: STOPPED, not a freeze.** Captured 2026-10-15 on local
`integration/w56a` `f47c129e6d08d509ad3d2288926244afe265468b`, whose accepted W55b
ancestor is `origin/dev` `6d63802ab465a0317839c9b57abd5e90f3d91769`.
`W56A-RULE-01` is complete on the local integration line and assigns
`R-129`…`R-134`. This report does not dispatch SEAL, GENERATOR or Stage B.

**Later same-day addendum on `fd71cc32`:** `W56A-PLAN-PATH-FIX-01` corrected the
category-label grant in the plan. `W56A-PROBE-01` then sent one bounded explicit
model request through the stand's configured agent gateway. It returned a
different model and a cost inconsistent with the locked requested model, so
the stand probe failed and the remaining calls were stopped. The probe report
and spend ledger are `W56A-PROBE-01.md` and `reviews/W56A-SPEND.md`. This
supersedes only the earlier preflight statement that no network call had been
made; all preflight measurements keep their original base and meaning. The
distinct recording gateway still lacks an accessible configuration. **No
implementation grant follows.**

## 1. Freeze input status

| Input | Measured fact | Disposition |
| --- | --- | --- |
| W55b predecessor | `W55B-INT-CLOSE` is on `origin/dev`; `VERSION` is `0.6.0`, migration head `0021_portal_bundles` | Satisfied for code-first W56a planning. A `v0.7.0` release still needs the actual published/tagged predecessor or an owner-ratified history amendment. |
| W56a rulings | `W56A-RULE-01` is merged into local `integration/w56a` at this report's base; the owner log on `origin/dev` ended at `R-128` | Satisfied locally. `R-124`: one whole-wave judge then FIX. `R-126`: backend database suites run in the final gate, not each lane. |
| Frozen surface | API 47 paths / 54 operations / 123 schemas; error catalogue 24; domain candidate revision 12; `contract_version` `1.0.0-draft.1`; four pre-seal SHA-256 values are in the task definition | Satisfied as a pre-seal measurement. Only SEAL may change the shared contract and migration. |
| Proxy code and D-133 | `W48-PROXY-01` is an ancestor of W55b. `D-133` retains typed stage-message/startup-policy work after its proxy response classification fix | The SEAL, PROVIDER and WEB grants must carry the remaining D-133 behavior if still open on their base. |
| Legacy АР source | Clean `/root/projects/PDF-proverka` checkout `16ba8e5d23e4782550e79355002fde1365f682b7`; six files match `W56A-LEGACY-SOURCE-01` (§2) | Provenance available; profile author still reviews every item and excludes normative claims. |
| Advisory pin sweep | Exact integration base returned 98 lines, SHA-256 `dd6d025853316a6764b8c66856b6952408f1e43e72c01b664f01c30cd250c11b`; complete stdout in §4 | Every listed path enters SEAL's grant inventory, but only changed facts should be edited. Re-sweep if the base changes. |
| Category-label grant | The plan names `web/src/widgets/knowledge-base/ui/knowledge-base.tsx` as the SEAL label record, but that file imports `CATEGORY_LABELS` from `web/src/entities/expert-decision/model/category-labels.ts`, where the exhaustive `Record<FindingCategory, string>` lives. `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx` separately hard-codes `CATEGORY_CHOICES` | **Grant correction required before SEAL:** SEAL exclusively owns the label record's actual file. WEB owns the page's explicit choices after SEAL. Do not treat the consumer widget as the label definition. |
| Model identities | `P02_LOCK.json` has model IDs and $5/$25, $2/$10 per MTok rates but no `gateway_name`; the later `W56A-PROBE-01` stand call failed identity and rate checks | **STOP.** The plan requires passing probes on two distinct gateways before naming gateway models in the lock. |

## 2. Source and provider preflight

The six legacy digests were rechecked directly on the clean checkout; the historical
`32b9d903792b30506048a1d42b0e6b2d07aee403` to HEAD six-path diff was empty.

| Relative source path | SHA-256 |
| --- | --- |
| `prompts/disciplines/AR/finding_categories.md` | `e0591c94b2f385a837872f37f5ef32eb057131265c32283e5f732b2c1fa236ce` |
| `prompts/disciplines/AR/checklist.md` | `eccb7879023a126427fd61a0ed36237eb42bbebd4bec63c4009004247d7f3179` |
| `prompts/disciplines/AR/role.md` | `fda944f74c4a0bd7cd77339f2c2f8519f55d59e899be03da212f93d2ad432203` |
| `prompts/disciplines/AR/drawing_types.md` | `38ef910c11c71d03819a37c258933bcf4c851ac2cce31bace2681d8fde8fa45e` |
| `prompts/disciplines/AR/project_params.md` | `5d827feac80cf85760af4a1d3f8509e15defb0df771c09ea83e475e172a80f35` |
| `backend/app/data/discipline_checklists/AR.md` | `1fbede99e35e8beadbb014538af76c33fdb54a7860e72616c4a4605ee28e17a9` |

The shell environment has no `ANTHROPIC_API_KEY`, `PROXY_LLM_TOKEN`,
`PROXY_LLM_BASE_URL`, `PROXY_LLM_MODEL`, `AUDITMANAGER_MODEL_ID` or
`AUDITMANAGER_PROVIDER_MODE` value. The local ignored
`infra/deploy/env/provider.env` has one token and nonstub model entry, but its
HTTP(S) URL has **no hostname**, its provider mode is not `proxy`, and it has no
analysis model ID. Its mode is `0644`; the checked-in example instructs `0600`.
The W55b integration worktree has no such file. No separate stand-gateway
configuration is visible here. These observations concern presence and shape only;
no secret, hostname or token value was printed. No network reachability, gateway
identity or price rate is proven. No paid or network call was made. Sandbox network
reachability has therefore not been tested and must not be inferred either way.

## 3. Exact remaining work before a completed freeze

### Seeded corpus specification to confirm at completion

Build about ten byte-stable synthetic PDF portal bundles with `expected_issues.json`.
Each of the seven categories has **at least three** distinct grounded issue cases
spread over at least two bundles and **at least one** near-miss control: minimum
21 positive issues and seven controls. All positive evidence quotes must occur
verbatim in the PDF text layer; portal descriptions and recognised-only text are
never citation sources. An issue about missing content needs an explicit promise
in the supplied project set, not a norm or a generic checklist expectation.

| Category | Three required issue archetypes | Near-miss control |
| --- | --- | --- |
| `internal_contradiction` | Same room has two stated areas; the same sheet has conflicting revision dates; a room number maps to two uses in supplied tables | Different rooms may have different areas. |
| `explicit_placeholder` | Active note says «уточнить»; active table cell says «TBD»; active sheet callout says «не определено» | «Уточнение выполнено» is resolved prose, not a placeholder. |
| `dimensions` | One room length differs between plan text and schedule; one floor height differs between section text and note; one door width differs between schedule and callout | `3,00 м` and `3000 мм` describe the same dimension. |
| `layout` | Room adjacency differs between supplied plan legend and note; an entrance side differs between plan label and text; one room number has incompatible placement in two supplied schedules | Two floor plans with different, explicitly named floors may differ. |
| `facade` | Facade material differs between elevation callout and note; window count differs between elevation schedule and facade note; colour code differs between supplied facade and finish schedule | North and south facades may intentionally have different finishes. |
| `roof` | Roof slope differs between plan callout and roof note; drain count differs between plan and schedule; parapet height differs between roof detail and note | Two named roof zones may intentionally have different slopes. |
| `documentation` | Index explicitly promises a sheet absent from the supplied set; contents explicitly promises a section absent from the supplied text; one sheet identifier has incompatible titles in index and supplied header | A sheet absent from the set is not a finding if the index never promises it. |

`expected_issues.json` identifies bundle, category, issue, cited page/quote and the
distinct project statements where applicable. Controls identify their scope and
expected absence. The generator's contract tests prove byte-stable regeneration,
21/7 minimum coverage, quote validity and a failing mutation for each positive
and control. The matcher later reports over-merge and severity confusion; the
recorded baseline is measured after HARNESS, not invented in this preflight.

### Seal choices that the completed freeze must pin

- **Severity refusal:** use the existing `validation_failed` (HTTP 422) with the
  safe `constraint` classifier `severity_only_on_accept` when a non-`accept`
  decision carries severity. `accept` without severity remains wire-valid for
  v1 byte identity. SEAL must pin this code/class in the API and domain catalog;
  no separate severity error code is needed unless the integrator records a
  different explicit ruling before the seal.
- **D-133 stage failure display:** `StageState.error_code` already exists. Add
  optional `StageState.error_message` within `RunStatus.stages`, only when a
  stage has a safe, server-authored failure message; cap it at 240 characters,
  omit it for v1 successes and missing messages, and never expose proxy body,
  URL, token or raw exception text. The remaining D-133 proxy HTTP classes
  retain the already merged mappings; PROVIDER verifies each and WEB renders
  this typed stage message. Pin the schema and source of the message at SEAL.
- **Revision and migration:** the domain family (`error-codes`, `identifiers`,
  `state-machines` and their schema consts) moves as one candidate revision
  from 12 to 13 for `model_identity_mismatch`; `contract_version`
  stays `1.0.0-draft.1`. SEAL alone owns migration `0022_findings_v2` after
  `0021_portal_bundles`. It widens both category CHECKs and the ungrounded-reason
  CHECK; adds proposed severity and decision severity with its accept-only
  CHECK; backfills and constrains canonical observation identity; redefines
  `finding_current_verdict`; and widens the stored-error CHECKs
  `ck_command_record_error_code`, `ck_audit_run_terminal_reason`,
  `ck_model_call_error_code` and `ck_provider_effect_error_code`. The existing
  category/grounding constraints are `ck_finding_category`,
  `ck_finding_observation_category` and
  `ck_finding_observation_ungrounded_reason`. Pin the new severity and
  canonical-identity constraint names in the SEAL task before coding.
- **Existing registry roles:** `prepared.recognised_text` and
  `findings.merged` are already declared. SEAL specifies their v2 schema and
  profile-plan semantics in place; it does not add duplicate roles, a new
  `StageStatus`, or a changed `finding_merge.depends_on`.

1. The integrator obtains usable, separately identified recording and stand gateway
   configurations through the owner-managed secret channel. Set file permissions
   according to `provider.env.example`; do not place values in Git or this report.
2. Before spending, fix the relative price tolerance and open
   `docs/program/reviews/W56A-SPEND.md` under an explicit integrator grant. Project
   all four probe calls against the wave's $5 cap (`R-29`, `R-134`). A projection
   above $5 stops for the owner.
3. On **each** gateway, call the configured model once and the stub/default once.
   Record the response-reported concrete model and `usage.cost` rate comparison,
   without tokens or endpoint values. The configured response must match the pinned
   gateway name and rate; the default response must be concrete and distinct from
   configured and stub. An echo, fallback, missing name or mismatch stops that
   gateway. Record both signals per gateway and the actual spend.
4. Recheck the `integration/w56a` base, the `R-129`…`R-134` sequence, six legacy
   digests, `D-133`, the 98-path pin sweep and the `0.6.0` predecessor hits. The
   current hits are `tests/contract/release_notes/test_release_notes_form.py`
   lines 145–151 and `tests/integration/releases/test_release_loader.py` line 67;
   the five grep lines were captured, without truncation. Fix the v2 corpus spec,
   re-measure tolerance and private ports at this point.
5. Resolve the category-label grant drift documented in §1. Add the actual
   `web/src/entities/expert-decision/model/category-labels.ts` to SEAL's exclusive
   grant and `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`'s
   `CATEGORY_CHOICES` to WEB's. Check the shared-file handoff before dispatch.
   Only then amend this report and task to **COMPLETE**, name the final freeze SHA,
   and issue separate task files with exact `allowed_paths` from plan §§A4–A5.
   The anticipated grants are below. This table is not a current write grant.

| Future task | Exclusive file ownership after the freeze | Required handoff |
| --- | --- | --- |
| `W56A-SEAL-01` | `contracts/**`; `db/migrations/versions/<date>_0022_findings_v2.py`; API schema and generated client; direct error, catalogue, label, `P02_LOCK.json`, `P02_SEAMS.md` and expected-fact pins; **`web/src/entities/expert-decision/model/category-labels.ts`** as the actual exhaustive label record; all 98 §4 paths as an advisory grant, excluding plan §A4's W55b-only files, CSV pins and characterization records | Seal optional v2 properties and enums, deterministic merge role and profile stage plans; migration upgrade/backfill/refused downgrade and v1 byte-identity tests; no per-lane DB suite or `make gate` under `R-102`/`R-126`. |
| `W56A-GENERATOR-01` | `tools/fixtures/seeded/**`, `fixtures/evaluation/ar_v2/**` corpus/manifests, `tests/contract/fixtures_seeded/**` | After SEAL; byte-stable PDF/bundle/expected-issues regeneration and a mutation self-test for each seeded issue/control. |
| `W56A-PROVIDER-01` | `analysis/text/{proxy,live,adapter,config,lock}.py`, then named `bootstrap/settings.py`, `runs/{executor,public}.py`, `bootstrap/adapters.py` stage-message seams and tests in plan §A4 B1 | From SEAL's merge; model mismatch is a typed failed stage; D-133 message; v1 recordings untouched. |
| `W56A-PROFILES-01` | New `analysis/profiles/**`, other named `analysis/text/**`, `runs/{repository,commands,scope,executor}.py`, `findings/grounding.py`, `bootstrap/{adapters,settings,composition}.py`, `tests/conftest.py`, provider env example and readiness, tests in §A4 B2 | From PROVIDER's merge; run-row stage plan, current-profile re-audit, marked recognised context, source provenance/exclusions, v1 identity. |
| `W56A-MERGE-01` | New `analysis/stages/finding_merge.py`, named stage/public exports, `runs/executor.py`, `findings/{publication,queries,artifacts,public,__init__}.py`, `bootstrap/adapters.py`, tests in §A4 B3 | From PROFILES' merge; connected components, canonical observation, member lineage, grounded-only publication. |
| `W56A-DECIDE-01` | `decisions/**`, named decision router/adapter and finding query, `exports/**`, the exact CSV pins and record 12 listed in §A4 B4 | From MERGE's merge; expert-decided severity, cleared on non-accept, two appended CSV columns. |
| `W56A-HARNESS-01` | `tools/evaluation/**`, `tests/integration/evaluation/**`, `tests/contract/evaluation/**`, v2 recordings/baseline and spend ledger | From DECIDE's merge; red mutation proof, no-regression evaluation and live cap. |
| `W56A-WEB-01` | Finding, decision, knowledge-base and run widgets/entities/pages, including **`web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`** and its explicit `CATEGORY_CHOICES`; their named tests, rendered-language entry and journey manifest entry in §A4 B6. SEAL's category-label record is excluded from WEB's grant | From HARNESS' merge; proposed versus decided severity, merged members and profile shown. |

`bootstrap/adapters.py`, `runs/executor.py`, `findings/queries.py` and
`web/tests/guards/rendered-language.guard.test.ts` are sequential handoffs in
plan §A5, never simultaneous writers. Integrator owns `CURRENT_STATE.md`, refs,
tags, the stand and `.local/**`; the SEAL pin inventory does not itself grant
an implementation lane those integrator paths. A later recorded-only rehearsal,
release notes, one whole-wave judge, FIX and final gate follow the ordered lanes.
The plan's W56b drawings, critic, region evidence and chunking remain outside W56a.

## 4. Complete pin-sweep output on `f47c129e`

Command (exit 0):
`/root/projects/PDF-Analysis/.venv/bin/python tools/plan/pin_sweep.py reseal-surface migration table error-code`.
The stdout has 98 lines and SHA-256
`dd6d025853316a6764b8c66856b6952408f1e43e72c01b664f01c30cd250c11b`.

```text
contracts/api/v1/openapi.json	error-code: catalogue; reseal-surface: catalogue
contracts/domain/v1/error-codes.json	error-code: catalogue
db/migrations/versions/**	migration: catalogue; table: catalogue
docs/manual-tests/PC-01_prototype.md	migration: catalogue; migration: prose
docs/manual-tests/README.md	migration: prose
docs/program/ALPHA_ROADMAP.md	error-code: live claims; error-code: prose; migration: live claims; reseal-surface: live claims; reseal-surface: prose; table: live claims
docs/program/CONTRACT_PIN_REGISTRY.md	error-code: registry; migration: registry; reseal-surface: registry; table: registry
docs/program/CURRENT_STATE.md	error-code: live claims; error-code: prose; migration: live claims; migration: prose; reseal-surface: live claims; reseal-surface: prose; table: live claims
docs/program/P02_SEAMS.md	error-code: live claims; migration: live claims; migration: prose; reseal-surface: live claims; reseal-surface: prose; table: live claims
infra/deploy/README.md	reseal-surface: catalogue
infra/deploy/compose.server.yml	table: catalogue
infra/deploy/deploy.sh	table: catalogue
infra/deploy/proxy/nginx.conf	reseal-surface: catalogue; reseal-surface: prose
infra/deploy/reset.sh	table: catalogue
infra/deploy/serve.py	reseal-surface: catalogue; reseal-surface: pattern
src/auditmanager/api/README.md	reseal-surface: catalogue
src/auditmanager/api/app.py	reseal-surface: catalogue; reseal-surface: live claim; reseal-surface: pattern
src/auditmanager/api/health.py	reseal-surface: live claim
src/auditmanager/api/routers/__init__.py	reseal-surface: pattern
src/auditmanager/api/routers/blocks.py	reseal-surface: live claim
src/auditmanager/api/routers/errors.py	migration: live claim
src/auditmanager/documents/refusals.py	migration: live claim
src/auditmanager/ingest/pdf_reader.py	reseal-surface: pattern
src/auditmanager/norms/__main__.py	migration: live claim
src/auditmanager/norms/bundle/__init__.py	migration: pattern
src/auditmanager/norms/bundle/copy_record.py	migration: live claim; migration: pattern
src/auditmanager/norms/bundle/export.py	migration: pattern
src/auditmanager/norms/bundle/manifest.py	migration: pattern; reseal-surface: pattern
src/auditmanager/norms/bundle/stand.py	migration: live claim; migration: pattern
src/auditmanager/shared/db/__init__.py	migration: pattern
src/auditmanager/shared/db/check.py	migration: live claim
src/auditmanager/shared/db/errors.py	migration: live claim
src/auditmanager/shared/db/migrations.py	migration: live claim; migration: pattern
src/auditmanager/shared/db/schema.py	migration: live claim
src/auditmanager/shared/statemachine/topology.py	migration: live claim
src/auditmanager/storage/check.py	migration: live claim
tests/contract/api_v1/test_doc_prose_facts.py	error-code: pattern; migration: catalogue; migration: migration-application-head; migration: pattern; reseal-surface: pattern; reseal-surface: surface-doc-prose-triple
tests/contract/api_v1/test_openapi_conformance.py	reseal-surface: pattern; reseal-surface: surface-conformance-operation-count; reseal-surface: surface-conformance-operation-set; reseal-surface: surface-conformance-schema-count; reseal-surface: surface-conformance-schema-set
tests/contract/api_v1/test_surface_counts_in_prose.py	reseal-surface: pattern
tests/contract/domain_p02/test_contract_vocabulary.py	error-code: error-migration-domain-count; error-code: pattern; migration: pattern
tests/contract/domain_p02/test_openapi_document.py	error-code: error-openapi-enum-count; error-code: pattern; reseal-surface: pattern
tests/contract/domain_p02/test_seam_register.py	reseal-surface: pattern
tests/contract/test_cp00_candidate.py	error-code: pattern; migration: pattern
tests/contract/test_proxy_rate_limits.py	table: pattern
tests/contract/tools/test_pin_sweep.py	migration: pattern; reseal-surface: pattern
tests/e2e/pc01/journey/manifest.json	reseal-surface: catalogue
tests/e2e/pc01/test_acceptance.py	reseal-surface: pattern; reseal-surface: surface-e2e-composition
tests/integration/api/driver.py	reseal-surface: pattern
tests/integration/api/test_authorization.py	reseal-surface: pattern
tests/integration/api/test_envelope_screen_rules.py	error-code: error-screen-source-count; error-code: pattern
tests/integration/api/test_operation_surface.py	reseal-surface: pattern; reseal-surface: surface-path-and-operation-count; reseal-surface: surface-router-and-document-count; reseal-surface: surface-router-count
tests/integration/api/test_role_register.py	reseal-surface: pattern
tests/integration/api/test_router_and_body_rules.py	reseal-surface: pattern; reseal-surface: surface-router-operation-id-count; reseal-surface: surface-router-route-count-control
tests/integration/api/test_served_document_and_health_plane.py	reseal-surface: pattern; reseal-surface: surface-served-operation-count; reseal-surface: surface-served-path-count; reseal-surface: surface-served-schema-count
tests/integration/composition/test_api_token_channel.py	reseal-surface: pattern; reseal-surface: surface-composition-token-case
tests/integration/composition/test_bundle_transport_refusals.py	migration: pattern
tests/integration/composition/test_composition_root.py	reseal-surface: pattern; reseal-surface: surface-composition-proxy; reseal-surface: surface-composition-recorded
tests/integration/composition/test_deployed_stack_probe.py	table: pattern
tests/integration/composition/test_norms_worker_image_contract.py	error-code: pattern
tests/integration/composition/test_proxy_config_follows_checkout.py	table: pattern
tests/integration/composition/test_reset_rehearsal_counts_base_tables.py	table: catalogue; table: pattern
tests/integration/composition/test_reset_script_refusals.py	table: pattern
tests/integration/composition/test_session_register_volume.py	table: catalogue
tests/integration/composition/test_stand_copy_refusals.py	migration: pattern
tests/integration/db/test_accounts_migration.py	migration: pattern
tests/integration/db/test_durable_analysis_effects.py	migration: pattern
tests/integration/db/test_migration_lifecycle.py	migration: catalogue; migration: pattern; table: pattern
tests/integration/db/test_release_notes_migration.py	migration: pattern
tests/integration/db/test_schema_shape.py	table: catalogue; table: pattern
tests/integration/foundation/test_cross_provider_publication.py	migration: pattern
tests/integration/norms/bundle/conftest.py	migration: pattern
tests/integration/norms/bundle/support.py	migration: pattern
tests/integration/norms/bundle/test_bundle_postgres.py	migration: pattern
tests/integration/norms/bundle/test_contents.py	reseal-surface: pattern
tests/integration/norms/bundle/test_copy_record.py	migration: pattern
tests/integration/norms/bundle/test_manifest.py	migration: pattern
tests/integration/p02_journey/journey.py	table: catalogue; table: pattern
tests/integration/p02_journey/test_extractor_divergence.py	error-code: pattern
tests/support/expected_facts.json	error-code: expected facts (error_catalog.api_codes, error_catalog.stored_vocabulary); migration: expected facts (migration_head); reseal-surface: expected facts (surface.path_count, surface.operations, surface.schema_names); table: expected facts (no table field; review alongside schema)
tests/support/expected_facts.py	migration: pattern; reseal-surface: pattern
web/FRONTEND_LOCK.json	error-code: catalogue; reseal-surface: catalogue
web/openapi/openapi.json	error-code: catalogue; reseal-surface: catalogue
web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx	reseal-surface: live claim
web/src/app/bff/v1/[...path]/route.ts	reseal-surface: live claim
web/src/entities/audit-run/model/terminal-reason.ts	error-code: pattern
web/src/entities/execution/model/presentation.ts	error-code: pattern
web/src/shared/api/catalog-message.ts	error-code: pattern
web/src/shared/api/errors.ts	error-code: pattern
web/src/shared/api/generated/**	error-code: catalogue; reseal-surface: catalogue
web/src/shared/api/generated/operations.gen.ts	reseal-surface: pattern
web/src/shared/api/generated/types.gen.ts	error-code: pattern
web/tests/contract/catalog-message.contract.test.ts	error-code: pattern
web/tests/contract/pc01-error-codes.contract.test.ts	error-code: pattern
web/tests/contract/seam-operations.contract.test.ts	error-code: error-frontend-contract-enum-count; error-code: pattern; reseal-surface: pattern
web/tests/contract/terminal-reason-sentences.contract.test.ts	error-code: pattern
web/tests/guards/frontend-lock.guard.test.ts	error-code: catalogue; reseal-surface: catalogue; reseal-surface: pattern; reseal-surface: surface-frontend-lock-operations; reseal-surface: surface-frontend-lock-paths; reseal-surface: surface-frontend-lock-schemas
web/tests/unit/api/failure-surface.test.ts	error-code: error-frontend-failure-enum-count; error-code: pattern
web/tests/unit/screens/run-terminal-reason.test.ts	error-code: pattern
```

## 5. Checks and handoff

At this preflight, the accepted W55b and local W56a refs were read, four contract
digests matched their task values, the legacy checkout was clean and its six
digests matched the recovered-source addendum, and the pin sweep returned 0.
The exact predecessor-version grep returned the five lines identified in §3.
The task and this report are the only files owned by this branch. Document
checks on the staged candidate:

| Command | Result |
| --- | --- |
| `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/program/test_wave_governance.py` | 93 passed, exit 0. An earlier task-field syntax failure was corrected before this final run. |
| `git diff --cached --check` | Exit 0. |
| `git diff --cached --name-only` | Exactly `docs/program/W56A-FREEZE-01.md` and `docs/program/tasks/W56A-FREEZE-01.md`. |

No API, domain, analysis, migration, dependency, composition-root or global-style
file is changed by this preflight. The unresolved gateway probes are a hard
freeze stop. The implementation and release sequence remains with the
integrator; this report confers no publication authority.
