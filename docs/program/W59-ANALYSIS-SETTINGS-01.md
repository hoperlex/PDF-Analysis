# W59-ANALYSIS-SETTINGS-01 — section profiles proven by recorded runs and listed in «Настройки анализа»

**Base:** `121ef2ce` (task freeze on `origin/dev` `c4cbc026`), branch
`agent/w59-analysis-settings-01`, isolated worktree `w59-analysis-settings`, lane PostgreSQL
57520 / MinIO 61120–61121 (`auditmanager-w59-analysis-settings`). **Status:** development
candidate under `R-135`; no full gate, no live journey, no provider call, no push, merge into
another branch or tag.

## Phase A — section-profile runs in recorded mode

### Result

A version classified to АИ (`AI`), ПЗ (`PS`), ПОС (`POS`) or ТХ (`TX`) now runs end to end in
`recorded` mode with its own profile: the run pins the section's `analysis_profile_id` and
`prompt_bundle_id`, `text_analysis` sends that profile's prompt bundle, the recorded reply is
parsed by the v1 stage, the gate grounds it and the findings are published. Before this,
`W59-SECTION-SEAL-01` recorded the risk that only AR had a recording, so every
section-routed recorded run failed at `text_analysis`.

### How the recorded adapter finds a section recording

Recordings were, and still are, keyed by `request_sha256`: the checksum of the exact request
body, which includes the profile's system prompt. A section profile therefore already has
its own key, different from AR's and from every other section's. What the adapter lacked
was a place to look: `RecordedAdapter()` read `fixtures/recorded/text_analysis/` only, and
the phase-A paths do not include the composition root. The minimal change is in
`src/auditmanager/analysis/text/recorded.py`:

- `RecordedAdapter()` **without** a directory — what the composition root serves in recorded
  mode and what `python -m auditmanager.analysis.text` uses — searches the canonical
  directory and then each sub-directory of `fixtures/recorded/sections/` in name order
  (plain files and `_`/`.` names skipped). `RecordedAdapter(directory)` reads that directory
  alone, exactly as before, so every variant and every existing suite is unchanged.
- A key present in two searched directories is refused as `recording_ambiguous`
  (`analysis_input_invalid`, not retryable) instead of being answered by directory order.
  The other five reasons are untouched; a missing key is still `recording_missing`.
- `recording_dir` still names the canonical directory; the new `recording_dirs` names
  everything searched.
- `recording_document` takes an optional `origin` mapping, written only when given and
  refused if it names `provider_mode` or `mode`. Without it the document has the same eight
  keys as before, so the AR builder's `--check` still reports `fixtures match`.

AR is byte-identical: its key exists only in the canonical directory, so the same file
answers with the same response (`test_the_served_adapter_answers_ar_exactly_as_the_canonical_directory`
compares the two `ModelResponse`s), and the AR routed run still reproduces the corpus run.

### The synthetic recordings

`fixtures/recorded/sections/<code_lower>/<request_sha256>.json`, one per section, built by
`fixtures/recorded/sections/build_fixtures.py` (`--check` reports drift and stale files):

| Section | Key | Observations |
|---|---|---|
| АИ `AI` | `a03cfde3…04bf8f` | 1 — window-filling placeholder |
| ПЗ `PS` | `5dad5c5f…2411f3` | 1 — fire-resistance contradiction |
| ПОС `POS` | `9fd79951…f8ea15` | 1 — evacuation-exit contradiction |
| ТХ `TX` | `e1dcf36b…99c6df` | 2 — fire resistance + placeholder |

Each request is the section profile's bundle over the committed AR corpus text layer
(`fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json`), which is what the
pinned extractor produces from the PDF the run suites seed. The replies are **authored by
hand**: each file has `origin.kind: synthetic`, a statement that no model produced the reply
and that it is not field evidence for the profile's review, the task, section, both
identities, the bundle's `content_sha256` and the profile status; every `finding_text` opens
with «Синтетический ответ (<раздел>), не результат вызова модели»; usage and latency are
authored. No file carries a provider mode; the adapter's class constant stamps `recorded`.
`fixtures/recorded/sections/README.md` says all of this beside the files.

### Registry

`RegisteredTextProfile` gains `source: TextProfileSource | None` (default `None`): the
package's validated `source` block — repository, commit and `(path, sha256)` files — kept
instead of discarded after validation. Builtin AR has none (its prompt was written in this
repository). Phase B lists it.

### Tests

- `tests/integration/runs/test_w59_section_profile_recorded.py` (lane containers, 7 cases):
  for each of AI, PS, POS, TX — classify (stage `P`) → `start_audit_run` with the registry's
  table → the run pins the section's pair → `execute_run` with `RecordedAdapter()` and the
  registry's resolver → `published`, all four PC-01 stages `succeeded`, the persisted
  `text_analysis` metrics carry the section's `prompt_bundle_sha256`,
  `analysis_profile_sha256` and the recording's key, and the published findings are exactly
  the recording's observations under the section's pair in `recorded` mode; `PB` → refused
  (`required_norm_unavailable`, `analysis_profile`), unclassified → refused
  (`version_classification`), no run either way; a PS run over the AI directory alone ends
  `failed` with `recording_missing`, and over the AI file renamed to the PS key with
  `recording_key_mismatch`, with no finding published.
- `tests/integration/sections/test_section_recordings.py` (container-free, 16 cases): one
  synthetic recording per section keyed to its own request; the five requests (AR + four)
  pairwise distinct; builder `--check` clean; the served adapter answers AR as the
  canonical directory does and answers each section, the canonical directory alone does
  not; KJ (no recording) fails `recording_missing`; the AI recording never answers the PS
  request; one key in two searched directories → `recording_ambiguous`; `origin` cannot carry
  a mode; the registry keeps every package's `source`.

### Checks run (phase A)

Interpreter `PY=/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python`,
`$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`, lane containers up
via `make up` / `make migrate` (head `0024_version_classification`).

| Command (paths) | Result |
|---|---|
| `tests/integration/runs/test_w59_routed_execution.py` (before any change) | 3 passed, exit 0 |
| `tests/integration/runs/test_w59_section_profile_recorded.py` | 7 passed, exit 0 |
| `tests/integration/sections` | 79 passed, exit 0 |
| `tests/integration/sections tests/integration/runs/test_w59_section_profile_recorded.py tests/integration/runs/test_w59_routed_execution.py tests/integration/runs/test_full_chain.py tests/integration/runs/test_terminal_detail_says_which_dependency.py tests/integration/analysis_text tests/unit/analysis` | 423 passed, exit 0 |
| `tests/contract/architecture tests/contract/domain_p02 tests/contract/provider tests/contract/analysis_packages` | 202 passed, exit 0 |
| `build_fixtures.py --check` for `text_analysis` and `sections` | `fixtures match` ×2 |
| `git diff --check` | clean |

Mutation probes on commit `439580da` (each applied in-tree, run against the two new modules,
then restored with `git checkout`):

| Mutation | Result |
|---|---|
| served adapter reads the canonical directory only | 10 failed |
| ambiguity refusal removed (first match wins) | 1 failed |
| an explicit directory also searches the section directories | 8 failed |
| registry drops the `source` block | 1 failed |

## Phase B — «Настройки анализа»

Started from `1049367e` (`integration/night-1020` = `origin/dev`, surface 51/58/147) on the
integrator's go; the operation was accepted as proposed. `a50dafd4` (a task freeze, docs only)
was merged after it.

### Surface

| | before | after |
|---|---|---|
| paths / operations / schemas | 51 / 58 / 147 | 52 / 59 / 153 |
| API error codes / migration head | 25 / `0024_version_classification` | unchanged |

`listAnalysisProfiles` — `GET /analysis/profiles`, new tag `analysis`, any one role
(`role:admin|expert`), no parameter, no body, so no `422` (it joins
`INPUT_LESS_OPERATIONS`). `200 AnalysisProfileList {items}`: exactly fifteen
`AnalysisProfileListItem {section_code, section_name, profile}` in the project-structure order
(`S-5`: АР, АИ, ПЗ, ПОС, ТХ, КЖ, КМ, ОВ, ВК, ПТ, ЭОМ, СС, ИТП, ГП, ПБ), `profile` an
`AnalysisProfileSummary {analysis_profile_id, prompt_bundle_id, profile_version, status,
prompt_bundle_sha256, content_sha256, source}` or `null`; `status` is
`AnalysisProfileStatus` (`builtin`, `draft`, `reviewed`); `source` is
`AnalysisProfileSource {repository, commit, files: AnalysisProfileSourceFile[] {path,
sha256}}` or `null` (builtin AR). Six schemas. The contract's `info.description` gains a
reseal paragraph; `contract_version` does not move.

### Backend

- `api/schemas/models.py` — the six models; `api/routers/ports.py` —
  `AnalysisProfilePort.list_analysis_profiles()`; `api/routers/analysis_profiles.py` — the
  route; `api/routers/__init__.py` — the eighteenth router module, optional port
  `analysis_profiles`; `api/security.py` — `listAnalysisProfiles: _ANY_ROLE`.
- `bootstrap/adapters.py` — `AnalysisProfileAdapter(registry, section_names=...)` maps the
  composition root's registry **once**, at construction (the registry is immutable for the
  process): rows in `PROJECT_STRUCTURE_ORDER`, names from `sections.public.section_names()`,
  a section the catalogue cannot name fails start-up. No session, no store.
  `bootstrap/composition.py` passes the same `text_profiles` run start routes through.
- `analysis/text/profile_registry.py` — `PROJECT_STRUCTURE_ORDER` (checked equal to the
  fifteen codes at import, and to the web's literal by
  `tests/integration/sections/test_section_recordings.py`).

### Web

- `/analysis-settings` graduates from the `RoutePlaceholder` stub to a read-only table:
  `_pages/analysis-settings` (loading, Russian refusal with correlation id, «Обновить»),
  `widgets/analysis-profile-table` (one row per section: abbreviation and name, «версия
  X.Y.Z», status, the prompt-bundle hash shortened; «Подробнее» holds both identities, both
  hashes in full and the source — «Перенесён из прежней системы: репозиторий …, коммит …»
  with every file and its hash, or «Написан в этом приложении…»; ПБ «профиль не создан.
  Прогон версии этого раздела будет отклонён.»), `entities/analysis-profile` (query options,
  labels: `builtin` «встроенный», `draft` «черновик, требует экспертной проверки»,
  `reviewed` «проверен экспертом», an unknown status said to be unknown).
- New query root `analysis` (`queryKeys.analysis.profiles()`), recorded in
  `web/docs/PC01_UI_SEAM.md` §6. The screen registry row is unchanged (`session`,
  `any-role` — the role set is exactly admin|expert).
- Guards moved with the screen: `prepared-sections.guard` and `r66-navigation` hold it as a
  built screen; `rendered-language.guard` seeds the registry; the contrast census renders
  the table; the journey manifest declares `listAnalysisProfiles` for the screen.

### Reseal files

`contracts/api/v1/openapi.json`, byte-identical `web/openapi/openapi.json` (SHA-256
`2147d56515b4b96b8682e430a5833ba603f67dfae8ed0299fcf47bf97d5647e2`), regenerated
`web/src/shared/api/generated/**`, `web/FRONTEND_LOCK.json` (both digests, the four generated
files, 52/59/153), `tests/support/expected_facts.json`, the register entries in
`tests/contract/domain_p02/test_openapi_document.py`, `tests/integration/api/
{test_authorization,test_role_register}.py`, `tests/integration/composition/
{test_every_port_implementation_is_whole,test_an_absent_parent_is_not_an_empty_page}.py`,
the prose-guard mutation strings, and the surface prose in `P02_SEAMS.md`,
`ALPHA_ROADMAP.md`, `infra/deploy/{README.md,proxy/nginx.conf,serve.py}`,
`api/{README.md,app.py,health.py}`, `api/routers/{declarations,errors}.py`, the BFF
`route.ts` and `shared/api/authorization.ts`; `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`
A09 describes the screen. `CONTRACT_PIN_REGISTRY.md` needed no change (no needle moved).
`docs/program/CURRENT_STATE.md` is the integrator's and still states 51/58/147.

### Checks run (phase B)

| Command | Result |
|---|---|
| `npm --prefix web ci` (once) | exit 0 |
| `npm --prefix web run api:generate` / `api:verify` | 59 operations, contract SHA-256 `2147d565…5647e2`, `--check: OK` |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `vitest run tests/guards tests/contract tests/unit/analysis-settings tests/unit/api tests/unit/qa_w50/r66-navigation.test.ts tests/unit/styles tests/unit/screens/routes.test.ts tests/unit/shell` | 46 files, 728 passed |
| `pytest tests/contract` (whole directory) | 1057 passed; failures listed below, none from this change |
| `pytest tests/e2e/test_pc01_journey_conformance.py` | 87 passed |
| lane containers: `tests/integration/composition/test_analysis_profiles_over_http.py` | 4 passed |
| lane containers: `tests/integration/api/{test_authorization,test_role_register,test_served_document_and_health_plane,test_operation_surface,test_router_and_body_rules}.py`, `tests/integration/composition/{test_every_port_implementation_is_whole,test_an_absent_parent_is_not_an_empty_page,test_composition_root,test_api_token_channel,test_the_served_application_routes_by_section,test_router_answers}.py` | 164 passed, 1 skipped, 1 failed (pre-existing, below) |
| `tests/integration/sections tests/unit/analysis` | 110 passed |

`tests/contract` failures, none caused here: `test_doc_prose_facts::test_the_scanned_docs_state_the_contract_surface_this_tree_has`
(`CURRENT_STATE.md` still says 51/58/147 — integrator-owned, moves at integration);
`test_cp00_candidate.py` (49 failed + 126 errors, git-sandbox/CP-00 records),
`test_cp00_final_state.py` ×3 (CP-00 tag/manifest history), `test_validate_bootstrap.py` ×21
(`jsonschema` absent from the runtime interpreter), `test_alpha_acceptance_command.py` ×1
(run on the uncommitted tree: "checkout содержит незакоммиченные изменения"), and the two
known reds `test_error_kernel::test_there_are_twenty_four`,
`test_ar_v2_seeded::test_seeded_categories_equal_the_sealed_api_enum`. The integration
failure `test_every_port_implementation_is_whole::test_pre_decide_adapter_refuses_a_severity_instead_of_dropping_it`
is in `DecisionAdapter`, which this task does not touch.

Mutation probes (applied, run, restored with `git checkout`):

| Mutation | Result |
|---|---|
| «Подробнее» → `Details` in the table | `rendered-language.guard` 2 failed, naming `[analysis-settings]` |
| draft label shortened to «черновик» | `analysis-settings.test.ts` 2 failed |
| adapter lists the codes alphabetically | composition test 1 failed |
| adapter gives ПБ the AR profile | composition test 1 failed |
| `listAnalysisProfiles` admin-only | `test_role_register` 3 failed |

## Risks and limits

- The section recordings answer **one document**: the AR corpus PDF the suites seed. Any
  other document classified to these sections still fails `recording_missing` in recorded
  mode — explicitly, as before. Nine sections with packages (EOM, GP, ITP, KJ, KM, OV, PT,
  SS, VK) still have no recording.
- The replies are synthetic. Passing proves routing, parsing, grounding and publication,
  not the quality of any profile. They never count as evidence for a profile becoming
  `reviewed`.
- `infra/deploy/Dockerfile.api` copies all of `fixtures/recorded/`, so the image carries the
  section recordings; its comment still names only `text_analysis/**` (outside this task's
  paths).
- Editing a section's `system_prompt.md` orphans its recording; the builder's `--check` and
  `test_the_builder_reports_no_drift` catch it.

- The settings page lists what the server holds; it cannot show a profile's prompt text
  (not in the contract) and offers no editing, by the task's non-goals.
- `required_norm_unavailable` still carries the `analysis_profile` refusal for ПБ (the seal's
  accepted overload); the page says «профиль не создан» from `profile: null`, not from it.
- If `W57B-NORMS-CATALOGUE-XLSX-01` integrates first, both reseals add paths and schemas to the
  same files; see the integrator instructions.

## Integrator instructions

1. Merge `agent/w59-analysis-settings-01` (phases A and B are one slice). If
   `integration/night-1020` holds the norms reseal by then, keep both sides' paths and
   schemas in `contracts/api/v1/openapi.json` and re-derive everything else (mirror copy,
   `api:generate`, `api:verify`, `FRONTEND_LOCK.json`, `expected_facts.json`, every
   surface-count prose line and the two prose-guard mutation strings), then rerun
   `tests/contract`.
2. `CURRENT_STATE.md`: surface **52 paths / 59 operations / 153 schemas** (before the norms
   reseal), head unchanged `0024_version_classification`, error catalogue 25; «Настройки
   анализа» is a built screen; section-profile runs work in recorded mode for АИ, ПЗ, ПОС, ТХ
   on the AR corpus document only, with synthetic recordings.
3. Register as debt: the nine package sections without recordings; synthetic recordings
   are not field evidence; the `Dockerfile.api` comment naming only `text_analysis/**`.
4. Before the final gate: the live journey visits `/analysis-settings` and must now see
   `GET /analysis/profiles`.

## Hotspot proof

Phase A changed only its five paths and the two docs files. Phase B changed paths inside the
task's allowed list only: `contracts/api/v1/**`, `src/auditmanager/api/**`,
`src/auditmanager/bootstrap/**`, `src/auditmanager/analysis/text/profile_registry.py`,
`tests/support/**`, `tests/contract/**`, `tests/integration/api/**`,
`tests/integration/composition/**`, `tests/integration/sections/**`, `tests/e2e/pc01/**`,
`web/openapi/**`, `web/FRONTEND_LOCK.json`, `web/src/shared/api/**`, `web/src/entities/**`,
`web/src/widgets/**`, `web/src/_pages/analysis-settings/**`,
`web/src/app/analysis-settings/**`, `web/src/app/bff/v1/[...path]/route.ts`, `web/tests/**`,
`web/docs/**`, `docs/program/{P02_SEAMS,ALPHA_ROADMAP}.md`, `docs/manual-tests/**`,
`infra/deploy/{README.md,proxy/nginx.conf,serve.py}` and this report. Not touched:
migrations, `pyproject.toml`, `uv.lock`, `web/package*.json`, `web/src/_app/providers.tsx`,
global styles, `src/auditmanager/analysis/text/profiles/**`, `web/src/shared/config/**`,
`CURRENT_STATE.md`, `CONTRACT_PIN_REGISTRY.md` (no needle moved), refs, tags, the stand.
