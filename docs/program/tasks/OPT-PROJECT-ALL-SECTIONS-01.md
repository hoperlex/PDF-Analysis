# Task OPT-PROJECT-ALL-SECTIONS-01 — «Спецификация и цены» and «Предложения» for a version confirmed in any of the fifteen sections

task_id: OPT-PROJECT-ALL-SECTIONS-01
status: completed in development candidate (2026-10-27). First session STOPPED at the premise (P-05, P-06: the pass trigger pins AR in the database); the integrator granted the migration slot (option A of the stop report) and the lane built it. See the report.

## Outcome

«Спецификация и цены» (`getSpecificationPrices`) and «Предложения» (`startOptimisationPass` and the passes' screens) accept a version whose current classification is any of the 15 sections, instead of `AR` only: the guard `src/auditmanager/optimisation/project_match.py:281` is replaced by the version's own section, the effective vendor list is read for that section, the two web filters go, the stale `uploadDocument` text and the 409 reason list are repaired in the same contract reseal, and `section_not_ar` stays in the enum, documented as «no longer produced for a confirmed section».

History. The premise (P-01..P-10) was captured first and **differed from the brief on one point that the brief itself says to stop on**: the database trigger `am_check_optimisation_pass_scope` refuses any pass over a non-AR version (P-05, P-06). The lane stopped and reported. The integrator then decided **option A** and gave this lane, for this wave, the migration slot (`0034`), the head pins, the domain catalogue prose, the web copy files named below and the dashboard sentence (`getDashboardSummary` said «fourteen» sections); everything else of PW4 section 4 stays as written. P-11 and P-12 were captured for the migration after the grant.

## Depends on

- `W60-OPT-MATCH-01`, `W60-OPT-PROPOSALS-01` — completed (the modules changed).
- `W59-SECTION-SEAL-01` — completed (the classification the guard reads).
- `PROD-11A-V3-TEXT-LAYER-PROBE-01`, `PROD-11B-V3-STAGE-ID-MIGRATION-01` — completed (the saved text of an AR version exists after a v3 Run publishes).

## Frozen inputs

- domain contract: `contracts/domain/v1/error-codes.json` names `section_not_ar` in prose (line 189); prose edited, nothing else
- API contract: `contracts/api/v1/openapi.json` 1.7.0 (92 paths, 104 operations, 301 schemas); prose edited, version stays 1.7.0
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id` at the base; this task moves it to `0034_pass_scope_all_sections` (granted by the integrator)
- base commit: `6075df889beef40084d337f03d2a072349fc9620` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: OPT-PROJECT-ALL-SECTIONS-01 (the only task that touches the migration head in PW4 until lane B, which the integrator sequences after it)
- totality_query: `PYTHONPATH=src:$BS .venv/bin/python -c "from auditmanager.shared.db.migrations import head_revision, revision_walk; print(head_revision()); print(revision_walk()[-3:])"`

## Captured premise evidence

- premise: the guard, the callers, the vendor-list keying, the section-blindness of the matcher and the contract places are as the brief says; one fact is not: a database trigger pins a pass to AR (P-05, P-06), so «Предложения» for another section needs a migration (granted, P-11, P-12). Blocks P-01..P-10 are the base-tree output captured before any change; they are not re-run.

### P-01 — the guard and every caller of `SECTION_AR` / `section_not_ar`
- captured_at: 2026-10-27
- command: `grep -rnE "SECTION_AR|section_not_ar|STATE_SECTION_NOT_AR" src web/src tests --exclude-dir=__pycache__ --exclude-dir=node_modules`
- captured_output:
  ```text
  src/auditmanager/api/routers/optimisation_proposals.py:112:            "`version_unclassified`, `section_not_ar`, `price_list_missing`, "
  src/auditmanager/api/routers/specification_prices.py:12:error**: ``200`` with one ``state`` -- ``version_unclassified``, ``section_not_ar``,
  src/auditmanager/api/routers/specification_prices.py:72:            "(`version_unclassified`, `section_not_ar`, `price_list_missing`, "
  src/auditmanager/api/schemas/models.py:2998:    The states are checked in order -- ``version_unclassified``, ``section_not_ar``,
  src/auditmanager/api/schemas/models.py:3011:        "section_not_ar",
  src/auditmanager/optimisation/proposals/commands.py:48:    SECTION_AR,
  src/auditmanager/optimisation/proposals/commands.py:221:        if entry.section_code == SECTION_AR
  src/auditmanager/optimisation/proposals/policy.py:20:read's own states (``version_unclassified``, ``section_not_ar``, ``price_list_missing``,
  src/auditmanager/optimisation/proposals/policy.py:35:    STATE_SECTION_NOT_AR,
  src/auditmanager/optimisation/proposals/policy.py:95:    STATE_SECTION_NOT_AR,
  src/auditmanager/optimisation/project_match.py:52:    "SECTION_AR",
  src/auditmanager/optimisation/project_match.py:57:    "STATE_SECTION_NOT_AR",
  src/auditmanager/optimisation/project_match.py:69:SECTION_AR: Final[str] = "AR"
  src/auditmanager/optimisation/project_match.py:75:STATE_SECTION_NOT_AR: Final[str] = "section_not_ar"
  src/auditmanager/optimisation/project_match.py:84:    STATE_SECTION_NOT_AR,
  src/auditmanager/optimisation/project_match.py:281:    if classification.section_code != SECTION_AR:
  src/auditmanager/optimisation/project_match.py:282:        return replace(answer, state=STATE_SECTION_NOT_AR)
  web/src/features/start-ar-v3-group/model/start-failure.ts:34:  | 'section_not_ar'
  web/src/features/start-ar-v3-group/model/start-failure.ts:64:  'section_not_ar',
  web/src/features/start-ar-v3-group/model/start-failure.ts:118:        kind: 'section_not_ar',
  web/src/widgets/specification-prices/ui/specification-prices-section.tsx:11: * it would only answer `section_not_ar` for.
  web/src/entities/specification-price/model/presentation.ts:25:  section_not_ar:
  web/src/entities/optimisation-proposal/model/failure.ts:20:  section_not_ar:
  web/src/shared/api/generated/operations.gen.ts:1178: * «Спецификация и цены»: the specification rows of the document set's current version, read deterministically from its newest published run's saved text layer, each matched to the project's current price-list revision as `matched`, `ambiguous` or `unmatched` with its reason (code or mark first, then the normalised name, in the same unit; never a fuzzy guess). The version must be classified as section `AR`. A precondition that does not hold is `state` (`version_unclassified`, `section_not_ar`, `price_list_missing`, `analysis_missing`, `text_unavailable`, `specification_too_large`) with the facts read so far; a path naming no such set is `404`. A price and an amount appear only on a matched row with a numeric quantity; totals are per currency over those rows only, with every other row counted by its reason. Rows are paged (`offset`, `limit`, `next_offset`); counts and totals cover every row. Nothing is written. Any one role, `role:admin|expert`.
  web/src/shared/api/generated/operations.gen.ts:2545: * Start the optimisation pass of the document set's current AR version. The pass pins the version, its newest published run and that run's saved text layer, the project's current price-list revision and the effective AR vendor list (the project's own, else the administrator's), reads the specification, matches it against the price list and stores the deterministic proposals `cheaper_analog`: for a row matched to exactly one position, another position of the same revision in the same unit and currency, with a lower unit price, from a vendor on the list, of the same kind of product (at most three per row). The saving is `(current − proposed) × quantity` and is absent when the row's quantity is not a plain number. `expert` is required (`admin` alone is `permission_denied`). A precondition that is not met is `409 conflict` with `conflict_reason` `version_unclassified`, `section_not_ar`, `price_list_missing`, `analysis_missing`, `text_unavailable`, `specification_too_large` or `vendor_list_missing` and nothing is written, not even the key; an unknown project or a set of another project is `404`. An exact repeat of the `Idempotency-Key` answers the stored pass, the same key for another set or caller is `409 idempotency_key_reuse`, and a new key over exactly the same inputs answers the pass already stored instead of writing a second one.
  web/src/shared/api/generated/types.gen.ts:3074: * The states are checked in order -- ``version_unclassified``, ``section_not_ar``,
  web/src/shared/api/generated/types.gen.ts:3089:  state: "ready" | "version_unclassified" | "section_not_ar" | "price_list_missing" | "analysis_missing" | "text_unavailable" | "specification_too_large";
  tests/integration/optimisation/test_project_match.py:30:    STATE_SECTION_NOT_AR,
  tests/integration/optimisation/test_project_match.py:248:    assert (result.state, result.project_stage, result.section_code) == (STATE_SECTION_NOT_AR, "R", "KJ")
  tests/integration/optimisation/proposals/test_passes.py:183:    _refused_pass(unit, factory, cast, world, "section_not_ar")
  tests/integration/composition/test_optimisation_proposals_over_http.py:7:``version_unclassified``, ``section_not_ar`` (a second set), ``price_list_missing``,
  tests/integration/composition/test_optimisation_proposals_over_http.py:270:        "section_not_ar",
  tests/integration/composition/test_specification_prices_over_http.py:13:A second set classified ``KJ`` is ``section_not_ar``; a set of another project is ``404``;
  tests/integration/composition/test_specification_prices_over_http.py:211:    assert (body["state"], body["section_code"], body["rows"]) == ("section_not_ar", "KJ", None)
  tests/e2e/pc01/journey/README.md:523:their own, since a pass over the journey's own ПБ set is refused `section_not_ar`. Since
  tests/e2e/pc01/journey/manifest.json:933:        "section is answered `section_not_ar`), and the specification and the passes read the saved page text of",
  tests/e2e/pc01/journey/manifest.json:4330:          "over a set of another section is refused (`409`, `conflict_reason` `section_not_ar`), so the step is bound",
  ```
- interpretation: The server guard is one line, `project_match.py:281`; its constant is imported by exactly one other module (`proposals/commands.py:48`, used at `:221` to pick the AR vendor list). `section_not_ar` is a member of the `SpecificationPrices.state` enum (`models.py:3011`, `types.gen.ts:3089`) and of the pass refusal reasons (`proposals/policy.py:95`). The web names it in `failure.ts`, `presentation.ts` and the rendered-language guard. Matches the brief.


### P-02 — the files that name the guard's reason
- captured_at: 2026-10-27
- command: `grep -rl "section_not_ar" . --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=.venv | grep -v tasks/OPT-PROJECT-ALL-SECTIONS-01.md | sort`
- captured_output:
  ```text
  ./contracts/api/v1/openapi.json
  ./contracts/domain/v1/error-codes.json
  ./docs/program/dispatch/PRODUCTION-WAVE-PW4.md
  ./docs/program/PROD-10B-JOURNEY-REBASE-01.md
  ./docs/program/ROADMAP-GAP-2026-10-27.md
  ./docs/program/tasks/PROD-10B-JOURNEY-REBASE-01.md
  ./docs/program/tasks/ROADMAP-GAP-2026-10-27.md
  ./docs/program/W60-OPT-MATCH-01.md
  ./docs/program/W60-OPT-PROPOSALS-01.md
  ./src/auditmanager/api/routers/optimisation_proposals.py
  ./src/auditmanager/api/routers/specification_prices.py
  ./src/auditmanager/api/schemas/models.py
  ./src/auditmanager/optimisation/project_match.py
  ./src/auditmanager/optimisation/proposals/policy.py
  ./tests/e2e/pc01/journey/manifest.json
  ./tests/e2e/pc01/journey/README.md
  ./tests/integration/composition/test_optimisation_proposals_over_http.py
  ./tests/integration/composition/test_specification_prices_over_http.py
  ./tests/integration/optimisation/proposals/test_passes.py
  ./web/openapi/openapi.json
  ./web/src/entities/optimisation-proposal/model/failure.ts
  ./web/src/entities/specification-price/model/presentation.ts
  ./web/src/features/start-ar-v3-group/model/start-failure.ts
  ./web/src/shared/api/generated/operations.gen.ts
  ./web/src/shared/api/generated/types.gen.ts
  ./web/src/widgets/specification-prices/ui/specification-prices-section.tsx
  ./web/tests/guards/rendered-language.guard.test.ts
  ./web/tests/unit/analysis-settings/ar-v3-group-start-failure.test.ts
  ./web/tests/unit/optimisation-proposals/failure.test.ts
  ```
- interpretation: 29 files, not the 24 the brief counts (the brief's count did not include the seven documents under `docs/program/` that quote it, or `contracts/domain/v1/error-codes.json`). `contracts/domain/v1/error-codes.json` (line 189) carries the reason list of `startOptimisationPass` in the domain catalogue: a second contract file whose prose would need the same repair.


### P-03 — vendor lists are per section (all fifteen); price lists are per project
- captured_at: 2026-10-27
- command: `grep -n "section_code     text NOT NULL\|ck_vendor_list_revision_section_code\|section_code            text NULL\|UNIQUE NULLS NOT DISTINCT (project_uid, section_code" db/migrations/versions/20261020_0026_price_lists.py; grep -n "All fifteen sections' vendor lists\|for section in SECTION_ORDER" src/auditmanager/optimisation/queries.py`
- captured_output:
  ```text
  253:            section_code            text NULL,
  335:            section_code     text NOT NULL,
  346:                UNIQUE NULLS NOT DISTINCT (project_uid, section_code, revision_number),
  357:            CONSTRAINT ck_vendor_list_revision_section_code
  181:    """All fifteen sections' vendor lists as they apply to one project, in section order."""
  188:    for section in SECTION_ORDER:
  219:    return tuple((section, latest.get(section)) for section in SECTION_ORDER)
  ```
- interpretation: `vendor_list_revision.section_code` is NOT NULL and held to the fifteen sections, one revision series per (project or global, section); `getEffectiveVendorLists` answers all fifteen. The price list is one per project (`price_list_revision.project_uid`), its positions carry an optional `section_code`, and neither the matcher nor the generator reads it. So the read side needs no new data.


### P-04 — the matcher, the generator and the extractor do not know the section
- captured_at: 2026-10-27
- command: `grep -nwE "section|sections|section_code|SECTION" src/auditmanager/optimisation/matching.py src/auditmanager/optimisation/proposals/generator.py src/auditmanager/optimisation/specification.py; echo "grep exit status: $?"`
- captured_output:
  ```text
  grep exit status: 1
  ```
- interpretation: No line of the three modules mentions a section (grep finds nothing, exit status 1): the extraction (Form-7 header found in plain text), the matching and the cheaper-analog rule are pure functions of page text, price-list positions and a vendor list, identical for every section. The AR assumptions of the optimisation context are exactly `project_match.py:281`, `proposals/commands.py:221` and the database trigger of P-05.


### P-05 — THE DATABASE REFUSES A PASS OVER ANY VERSION BUT AR (migration 0027, replaced in 0028)
- captured_at: 2026-10-27
- command: `grep -n "c.section_code = 'AR'\|l.section_code = 'AR'\|CREATE OR REPLACE FUNCTION am_check_optimisation_pass_scope\|CREATE FUNCTION am_check_optimisation_pass_scope" db/migrations/versions/20261020_0027_optimisation_proposals.py db/migrations/versions/20261020_0028_classification_corrections.py; grep -rl --include='*.py' "am_check_optimisation_pass_scope" db/migrations/versions`
- captured_output:
  ```text
  db/migrations/versions/20261020_0027_optimisation_proposals.py:219:        CREATE FUNCTION am_check_optimisation_pass_scope() RETURNS trigger
  db/migrations/versions/20261020_0027_optimisation_proposals.py:235:                  AND c.section_code = 'AR'
  db/migrations/versions/20261020_0027_optimisation_proposals.py:237:                  AND l.section_code = 'AR'
  db/migrations/versions/20261020_0028_classification_corrections.py:98:        CREATE OR REPLACE FUNCTION am_check_optimisation_pass_scope() RETURNS trigger
  db/migrations/versions/20261020_0028_classification_corrections.py:114:                  AND c.section_code = 'AR'
  db/migrations/versions/20261020_0028_classification_corrections.py:116:                  AND l.section_code = 'AR'
  db/migrations/versions/20261020_0027_optimisation_proposals.py
  db/migrations/versions/20261020_0028_classification_corrections.py
  ```
- interpretation: `trg_optimisation_pass_scope` (BEFORE INSERT on `optimisation_pass`) requires the version's current classification to be `AR` **and** the pinned vendor list to be an `AR` list; otherwise it raises `AM001` (`state_transition_not_allowed`). The function was created in `0027` and replaced in `0028` (only the relation the classification is read from changed); no later migration touches it, so it is the function at head `0033`. This is a database invariant, not an application guard: lifting `project_match.py:281` and `commands.py:221` alone makes `startOptimisationPass` fail at the INSERT (P-06). Changing it is a migration.


### P-06 — the probe: with the two Python-side AR assumptions lifted, the INSERT is refused by PostgreSQL
- captured_at: 2026-10-27
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider -s tests/integration/optimisation/proposals/test_zz_probe_pass_scope.py`
- captured_output:
  ```text
  sqlalchemy.exc.DatabaseError: (psycopg.DatabaseError) state_transition_not_allowed: optimisation pass
  opp_01M5X0KQVR6WGV819CTVTGM4QS does not pin one AR version of its project with that version's run, a price list of
  the project and an AR vendor list in force for it
  HINT:  A pass is written by auditmanager.optimisation.proposals from one consistent read.
  CONTEXT:  PL/pgSQL function am_check_optimisation_pass_scope() line 23 at RAISE
  [SQL: INSERT INTO optimisation_pass (optimisation_pass_id, project_uid, document_uid, version_uid, run_id, ...
  1 failed in 2.38s
  ```
  The output above is an excerpt (line breaks added, nothing else changed). The probe was a temporary, untracked file in the lane's worktree (deleted after the run; the tree is clean). Its body, on the stock `tests/integration/optimisation/proposals/conftest.py` fixtures (real PostgreSQL clone and MinIO):
  ```text
  def test_probe(unit, factory, store, cast, world, monkeypatch):
      classify(unit, cast, world, "PB")                 # version confirmed as ПБ
      upload(store, factory, cast, PRICE_LIST, "prices-1")
      global_vendors(unit, cast, section="PB")          # a PB global vendor list
      monkeypatch.setattr(project_match, "SECTION_AR", "PB")   # lift guard line 281 only
      monkeypatch.setattr(commands, "SECTION_AR", "PB")        # pick the PB vendor list (line 221)
      unit(start_optimisation_pass, project_uid=world.project, document_uid=world.document,
           idempotency_key="probe-1", actor_uid=cast.expert, reader=published_reader(world))
  ```
- interpretation: the read half («Спецификация и цены») never writes and is not affected; the write half (`startOptimisationPass`, «Предложения») cannot work for a ПБ version without changing the trigger function, i.e. without a migration. The brief says to STOP in that case (and its decision rule 3 says «No migration»).


### P-07 — the saved text layer is the same for every section (read side)
- captured_at: 2026-10-27
- command: `grep -nE "_SOURCE_STAGE|ROLE_TEXT_LAYER|class _AnalysisReader|class _SpecificationTextReader" src/auditmanager/bootstrap/adapters.py | head -12; sed -n 52,60p src/auditmanager/runs/repository.py`
- captured_output:
  ```text
  3074:class _AnalysisReader:
  3077:    _SOURCE_STAGE = "source_preparation"
  3093:            ROLE_TEXT_LAYER,
  3103:            if row.stage_id == self._SOURCE_STAGE
  3107:        references = [a for a in stages[0].artifacts if a.get("role") == ROLE_TEXT_LAYER]
  3126:                role=ROLE_TEXT_LAYER,
  3252:class _SpecificationTextReader:
  #: The four stages PC-01 drives, in the order the registry's ``depends_on`` declares.
  #: Read by the executor and by terminal selection; not a second registry, just the
  #: PC-01 subset of one.
  PC01_STAGES: Final[tuple[str, ...]] = (
      "source_preparation",
      "page_geometry_extraction",
      "document_context_build",
      "text_analysis",
  )
  ```
- interpretation: `_SpecificationTextReader.saved_page_text` reads the `source_preparation` stage result of the newest published Run and its `text_layer` artifact, whatever the Run's profile; every non-AR section Run drives `PC01_STAGES`, whose first stage is `source_preparation`, so a published section Run leaves exactly the layer the AR readers read. Not measured here on a driven section Run (the lane stopped before building); the AR v3 measurement is `tests/integration/runs/test_v3_saved_text_layer_probe.py` (fact 7: readers answer `ready` on the published group). The 14 recorded section replies were all built over the AR corpus layer `fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json`, which the lane's own HTTP test already notes has **no specification table**; the synthetic Form-7 set `fixtures/synthetic/ar_specification/` has a recording only for the AR request, so a positive ПБ/ОВ case with a real section Run would need a new recording under `fixtures/recorded/sections/**`, which this lane may not write; the existing idiom (a fake `SavedTextReader` returning Form-7 pages) covers it.


### P-08 — the contract places that state the AR-only rule (descriptions only)
- captured_at: 2026-10-27
- command: `python3 -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print(d['info']['version']);w=lambda o,p='':[w(v,p+'/'+k) for k,v in o.items()] if isinstance(o,dict) else [w(v,p+'['+str(i)+']') for i,v in enumerate(o)] if isinstance(o,list) else (print(p) if isinstance(o,str) and 'section_not_ar' in o else None);w(d)"`
- captured_output:
  ```text
  1.7.0
  /info/description
  /paths//projects/{project_uid}/documents/{document_uid}/specification-prices/get/description
  /paths//projects/{project_uid}/documents/{document_uid}/optimisation-passes/post/description
  /components/schemas/SpecificationPrices/properties/state/enum[2]
  /components/schemas/SpecificationPrices/description
  ```
- interpretation: Version `1.7.0`. `section_not_ar` is named in `info.description` (the `W60-OPT-MATCH-01` and `W60-OPT-PROPOSALS-01` reseal paragraphs), in the descriptions of `getSpecificationPrices` and `startOptimisationPass`, in the `SpecificationPrices.description` and as `SpecificationPrices.state` enum member 2. `uploadDocument`'s description still says «The analysis is built for AR (architectural solutions) text and is applied to any uploaded document» (`D-110`, closed by `W59-SECTION-SEAL-01`). All are prose except the enum member, which stays.


### P-09 — how a prose-only contract change was sealed last time (version policy)
- captured_at: 2026-10-27
- command: `git log --format='%h %ad %s' --date=short -4 -- contracts/api/v1/openapi.json; git show --stat --format='%h %s' 22c1df66 | head -12`
- captured_output:
  ```text
  b7e5fdf1 2026-10-26 PROD-11 stage 2b (contract version, proposed 1.7.0): shared contract_version 1.6.0 -> 1.7.0 across the families, served constants, fixtures, edge bodies and tests
  22c1df66 2026-10-26 PROD-11 stage 2a (contract content): AnalysisProfileStatus loses builtin; reviewed described as it is (D-223)
  d81a14f3 2026-10-26 Seal executor choice OpenAPI content
  b02f680e 2026-10-26 Seal AR v3 beta pack status OpenAPI content
  22c1df66 PROD-11 stage 2a (contract content): AnalysisProfileStatus loses builtin; reviewed described as it is (D-223)

   contracts/api/v1/openapi.json                     |  7 +++----
   src/auditmanager/api/routers/analysis_profiles.py | 13 +++++++------
   src/auditmanager/api/schemas/models.py            | 11 ++++++-----
   web/openapi/openapi.json                          |  7 +++----
   4 files changed, 19 insertions(+), 19 deletions(-)
  ```
- interpretation: The previous prose-only change (`22c1df66`, stage 2a) touched `contracts/api/v1/openapi.json`, `web/openapi/openapi.json`, the router and model text, and did **not** move the version; the version moved in a separate commit (`b7e5fdf1`) only because an enum member was removed. The W60 reseal paragraphs end «no error code is added and contract_version does not move». `tests/contract/api_v1/test_openapi_conformance.py` drops `description` (normalisation N4), so prose is outside the conformance gate; the web client carries the prose in `operations.gen.ts`/`types.gen.ts`, so `api:generate` and `FRONTEND_LOCK.json` move with any prose change.


### P-10 — the journey the integrator owns depends on the AR-only rule (not this lane's paths)
- captured_at: 2026-10-27
- command: `grep -n "section_not_ar" tests/e2e/pc01/journey/manifest.json tests/e2e/pc01/journey/README.md`
- captured_output:
  ```text
  tests/e2e/pc01/journey/manifest.json:933:        "section is answered `section_not_ar`), and the specification and the passes read the saved page text of",
  tests/e2e/pc01/journey/manifest.json:4330:          "over a set of another section is refused (`409`, `conflict_reason` `section_not_ar`), so the step is bound",
  tests/e2e/pc01/journey/README.md:523:their own, since a pass over the journey's own ПБ set is refused `section_not_ar`. Since
  ```
- interpretation: The static journey manifest binds 33 steps to an АР set as `pending_v3_activation` precisely because «a set of another section is answered `section_not_ar`». Once the optimisation tab accepts every section those steps could run on the journey's ПБ set. That is a follow-up in `tests/e2e/**`, outside this lane's allowed paths.

### P-11 — the style of the last migration, read before writing 0034
- captured_at: 2026-10-27
- command: `sed -n 1,3p db/migrations/versions/20261026_0033_ar_v3_cite_stage_id.py; grep -nE "^revision|^down_revision|^def (upgrade|downgrade)|raise RuntimeError|0033 downgrade refused" db/migrations/versions/20261026_0033_ar_v3_cite_stage_id.py`
- captured_output:
  ```text
  """Admit the AR v3 citation-review stage id in ``stage_result``.

  Revision ID: 0033_ar_v3_cite_stage_id
  52:revision: str = "0033_ar_v3_cite_stage_id"
  53:down_revision: str | None = "0032_ar_v3_run_group"
  87:def upgrade() -> None:
  91:def downgrade() -> None:
  97:        raise RuntimeError(
  98:            "0033 downgrade refused: a stage_result row carries ar_v3_citation_review; "
  ```
- interpretation: the pattern 0034 follows: a module docstring with the revision ids, the reason and what it leaves alone; `upgrade()` one statement; `downgrade()` reads the data first and raises `RuntimeError("00NN downgrade refused: …")` while a row would be orphaned, otherwise restores the previous text exactly; a test file per migration (`tests/integration/db/test_ar_v3_cite_stage_id_migration.py`) and a unit text test.

### P-12 — the revision id cannot be the 40 characters the grant named
- captured_at: 2026-10-27
- command: `env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -c "import os;from sqlalchemy import create_engine,text;e=create_engine(os.environ['DATABASE_URL']);print(e.connect().execute(text(\"select table_name, column_name, character_maximum_length, data_type from information_schema.columns where table_name='alembic_version'\")).all())"; awk -F'"' '/^revision/ {print length($2), $2}' db/migrations/versions/*.py | sort -rn | head -3`
- captured_output:
  ```text
  [('alembic_version', 'version_num', 32, 'character varying')]
  32 0015_accounts_roles_registration
  31 0028_classification_corrections
  29 0014_durable_analysis_effects
  ```
- interpretation: `alembic_version.version_num` is `varchar(32)` and the longest existing revision id is exactly 32 characters. The id the integrator named, `0034_optimisation_pass_scope_all_sections`, is 40 and could not be stored (the stamp after the upgrade would fail). The revision is `0034_pass_scope_all_sections` (28), the file `20261027_0034_pass_scope_all_sections.py`; `tests/unit/sections/test_pass_scope_migration_text.py` holds `len(revision) <= 32`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `db/migrations/versions/20261027_0034_pass_scope_all_sections.py`
- `scripts/recovery/schema_coverage.py`
- `tests/support/expected_facts.json`
- `src/auditmanager/optimisation/**`
- `src/auditmanager/api/routers/specification_prices.py`
- `src/auditmanager/api/routers/optimisation_proposals.py`
- `src/auditmanager/api/schemas/models.py`
- `contracts/api/v1/openapi.json`
- `contracts/domain/v1/error-codes.json`
- `web/openapi/openapi.json`
- `web/src/shared/api/generated/**`
- `web/FRONTEND_LOCK.json`
- `web/src/widgets/specification-prices/**`
- `web/src/widgets/optimisation-proposals/**`
- `web/src/entities/specification-price/**`
- `web/src/entities/optimisation-proposal/**`
- `web/src/features/start-optimisation-pass/**`
- `web/tests/unit/specification-prices/**`
- `web/tests/unit/optimisation-proposals/**`
- `tests/unit/optimisation/**`
- `tests/unit/sections/test_pass_scope_migration_text.py`
- `tests/integration/optimisation/**`
- `tests/integration/composition/test_specification_prices_over_http.py`
- `tests/integration/composition/test_optimisation_proposals_over_http.py`
- `tests/integration/db/test_pass_scope_migration.py`
- `tests/integration/db/test_downgrade_chain_round_trip.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/runs/test_section_run_text_layer_is_what_optimisation_reads.py`
- `docs/program/CURRENT_STATE.md`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/tasks/OPT-PROJECT-ALL-SECTIONS-01.md`
- `docs/program/OPT-PROJECT-ALL-SECTIONS-01.md`

## Lane resources

The lane stack is the integrator's (`ar-close-1026/.env`, copied untracked); database tests use a private database (`optall_<hex>`, created and dropped by a script outside git).

## Forbidden hotspots

- any migration other than `0034` and any schema, enum or column change
- `bootstrap/**`, `analysis/**`, `runs/**`, `comparison/**`
- `web/src/entities/project/**`, `web/src/widgets/dashboard/**`, the other web areas, the root lock files
- `tests/e2e/**` (the 33 journey steps `pending_v3_activation` stay as they are), `fixtures/recorded/sections/**`, `tests/support/**` other than `expected_facts.json`
- `DEBT_REGISTER.md`, the rulings, the ADRs (`CURRENT_STATE.md` only for the migration head sentence, as granted)

## Non-goals

- no new category, state, enum member or schema shape; no removal of `section_not_ar` from the enum
- no section-specific reading of a specification table (decision rule 2 of the brief); the extraction of a real section run's Form-7 table is **not** measured and is listed as a limit
- no recording under `fixtures/recorded/sections/**`; no model call, no norm, no change of the AR v3 path

## Deliverables

- migration `0034` with its unit and database tests and the moved head pins
- the server change, the contract prose and its regenerated client and lock, the web copy and filters, and the tests of each
- this task file and `docs/program/OPT-PROJECT-ALL-SECTIONS-01.md` (files, mutation table, before/after of modified tests, commands with counts, limits)

## Required tests

- command: `PYTHONPATH=src:$BS python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/OPT-PROJECT-ALL-SECTIONS-01.md',encoding='utf-8').read())))"`
- expected: `[]`

## Integration contract

Provider: `getSpecificationPrices` and `startOptimisationPass` accept a version an expert confirmed in any of the fifteen sections; a pass pins the effective vendor list of that section and the database holds the same equality (`0034`). `section_not_ar` is never produced and stays in the enum. Contract 1.7.0, prose only. Consumer: the web screens offer every classified set. Migration head `0034_pass_scope_all_sections`; lane B (`0034` reserved in PW4 section 8) becomes `0035`.

## Failure/idempotency/security cases

- a pass whose version and vendor list are of different sections must be refused by the database even if the application is wrong (`tests/integration/db/test_pass_scope_migration.py`); the downgrade must refuse while a non-AR pass exists; a stored pass is never revalidated

## Rollback / feature flag

No feature flag. Rollback of the code is a revert; `alembic downgrade 0033_ar_v3_cite_stage_id` restores `0028`'s function byte for byte and **refuses** while a pass pins a vendor list of a section other than AR (restore a backup instead).

## Handoff

- changed files: see `git diff --name-only 6075df88..HEAD` in the report
- commands/results: see the report
- known limits: extraction of a real section run's Form-7 table is not measured (no recorded section fixture contains a table); the 33 journey steps stay pending
- integration notes: see the report
