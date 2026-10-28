# AR-V3-DECISIONS-01 — expert verdicts on grounded AR v3 findings, and the norm-verification report

Lane AR-A of wave PW5. Base `9e42c18a` (`integration/ar-close-1026`), branch `agent/ar-v3-decisions-01`. Task file: [`tasks/AR-V3-DECISIONS-01.md`](tasks/AR-V3-DECISIONS-01.md) (premises P-01 to P-12). Rulings: `R-146as` (build decisions on provisional citations; overrides the review-only `R-146g`), `R-146at` (`getRunNormVerification` answers the canonical report), `R-146ba` (the labels are lane S1's switch, not touched here). Plan: [`dispatch/PRODUCTION-WAVE-PW5.md`](dispatch/PRODUCTION-WAVE-PW5.md) section 2.

Four pieces, committed whole and in this order: **(1)** the report `getRunNormVerification`; **(2)** publication of grounded findings by the terminal (with migration `0036`); **(3)** the verdict path (tests and the finding views that make a verdict decidable); **(4)** the web panel. If a later piece is not finished, the earlier ones stand alone and the remainder is listed under «Limits».

## Design

### 0. What the premise showed, and the choices it forced

* **The review artifact does not carry what a finding needs.** The sealed `ar-v3-beta-citation-review/1` Blob keeps, per provisional proposal, only the PDF evidence anchors and the norm citations; the category, the two sentences, the proposed severity and the two claimed values are not in it by design (P-02, `v3_review_artifact.py`). So the terminal cannot build a finding from the artifact alone. It rebuilds the candidates from the same saved inputs the CITE stage used (`prepare_v3_cite_preflight`: saved text layer, custody-checked retrieval set, saved reply) **and requires the rebuilt artifact to be byte-equal to the sealed one** (same SHA-256 as the CITE `StageResult`). A finding is therefore a view of exactly the sealed review plus the model's sentences, never of a different computation.
* **The publisher and the database both name a stage that a v3 Run does not have** (P-03, P-04). `publish_grounded_v3_finding` and the deferred trigger `am_verify_norm_citation_partition` require a succeeded `stage_result` named `norm_verification`; the AR v3 CITE stage is `ar_v3_citation_review` (`0033`). With the publisher alone the commit of a published v3 finding would be refused by the database. That is the one thing the database refuses, and it is why this lane takes migration `0036`.
* **No new operation, schema or field.** `appendDecision` already takes `(finding_uid, finding_observation_id)`, and every decidable provisional citation will be a finding (below), so `recordCitationVerdict` is not needed. `NormVerificationReport` and `Finding.norm_citations` already exist in the contract. The surface stays 95 / 107 / 314 and the version stays `1.8.0`; only the prose of operation descriptions changes (the way `OPT-PROJECT-ALL-SECTIONS-01` kept `1.7.0`).
* **`contracts/analysis/ar_v3_beta/v1/stage.json` is not touched** (outside the grant). Its `beta_policy.canonical_finding_publication: false` is read as the CITE stage's own output: that stage still writes only the review artifact and no finding. The terminal, a later owner, writes the findings. If the owner wants the key to read `true`, that is a change to the analysis contract, its loader and the profile seal tests, in another lane (Integration note 5).

### 1. What is published, and when

* **When.** Only in `finish_v3_review_run`, only when `select_terminal` is publishable (all four stages succeeded) and the saved CITE stage is valid. Before the Run leaves `running` the terminal does its external Blob reads (the preflight) and builds the candidates; after `running -> validating` it re-checks that the stage rows and the absence of publication rows are as before, writes the findings, and only then terminates the Run and finishes the Job. One transaction: all findings and the terminal state, or none.
* **What.** One finding per proposal that passed **both** pure gates (document gate: every PDF quote resolves; norm gate: labels, quotes, values) **and** cites only topics whose policy mode is `provisional_citation` (the list `review.provisional_proposal_ordinals` that the sealed artifact already holds). A proposal that cites a context-only topic, alone or mixed, is withheld; a proposal that failed a gate is rejected; a non-normative accepted proposal (no citations) is not a publication candidate; categories are the five normative ones (`NORMATIVE_CATEGORIES`, enforced by the writer). None of these three kinds gets a row.
* **How.** `V3PublicationCandidate` is built from the grounded candidate (category, sentences, proposed severity, evidence anchors, `GroundedNormCitation`s, the two values) and handed to `publish_grounded_v3_finding` with the set bytes read through the custody-checked port. The writer's authority query now accepts the AR v3 CITE stage as well as `norm_verification` (a `cite_stage_id` argument; the default is unchanged, so the W57a callers and tests are untouched).
* **Terminal result.** `V3ReviewTerminal` gains `published_findings`; `RunStatus.published_finding_count` is already read from the database and now counts them. `runs/executor.py` (outside the grant) still reports `published_finding_count=0` in its in-memory `ExecutionResult`; nothing reads that figure for a v3 Run.
* **Replay.** A Run is closed once, in one transaction. The existing pre-terminal guard `canonical_finding_already_published` stays: a second publication for a Run is refused.

### 2. The state of a finding that is not yet decided

`current_verdict` is `pending` (the projection of an empty ledger), `decided_severity` is absent, `proposed_severity` is the model's proposal and only that. The finding carries the AR v3 beta profile and bundle ids in its provenance, which is how a screen says «предварительная цитата, ожидает решения эксперта» (the wording and the switch that hides it are lane S1's). Nothing the server computes is a verdict, a severity decision or a compliance flag.

### 3. The verdict path

`appendDecision` as it is: `_EXPERT` at the seam (an administrator alone is `403`), `Idempotency-Key` required, the author taken from the verified subject, the append-only ledger, `accept` / `reject` / `comment`, severity only with `accept`. No new operation. A provisional citation that is not a finding (withheld, rejected, non-normative) has no target and so no verdict: by policy the context-only topics are not decidable, and a proposal that failed a gate is not a claim. The tests drive it over HTTP on a published AR v3 finding and prove each guard can fail.

### 4. `getRunNormVerification`: the source and the shape

* **Source.** The saved CITE stage and the database, together, and nothing else: `read_v3_saved_review` (the sealed artifact, its Blob read, digest and group binding rechecked) and the certified citation partitions of the Run's findings (`read_verified_citations`, now taking the CITE stage id; a succeeded stage of that id, a verified pinned set, custody counts, every quote re-found in its paragraph). The two are cross-checked: the findings of the Run are either none (a Run closed before this lane) or exactly the artifact's provisional proposals, matched one to one by content (page, quote, offsets, norm document and paragraph, quote, state). Any other count or a content difference is a refusal, never a partial answer.
* **Fields.** `run_id`, `norms_snapshot_id`, `norm_retrieval_set_id` from the Run; `status` `complete` for `published`, `partial` for `partial` (with the stage's `error_code`); `findings`: the certified partitions of the canonical observations; `withheld_by_reason`: the reasons of the artifact's `rejected_proposals` (each one must be a member of `UngroundedReason`, else the read is refused); `textless_pages` from the version.
* **Withheld by policy is not a reason.** `UngroundedReason` is a closed enum (the contract and the `0023` CHECK). Context-only or mixed proposals are withheld by the beta policy, not by a grounding failure; adding a member would change a closed enum, so they stay out of `withheld_by_reason` and remain visible as `withheld_proposal_count` in the group review. This is a limit, listed below.
* **Who and what is refused.** `R-80` is unchanged (`expert` or `admin`). A Run that is not an AR v3 beta Run answers `not_found` (the operation's description says a v1/v2 Run does); a v3 Run that is not terminal, or whose saved review fails verification, answers the typed refusal of the existing review reader (`analysis_input_invalid`), never an empty list (an empty citation SELECT is not a certificate of zero).
* **Numbers.** The wire carries no `required_value` and no `stated_value` for a v3 beta finding or partition (both are optional in the contract). They are stored (the database requires them for a normative finding, and the writer checks the first against the norm quote and the second against the PDF quote) but not served: `numeric_output_policy` is `expert_review_required` and no edition check exists. This is the single judgement call of the lane (Integration note 3); serving them later is one projection change. The model's sentences (`finding_text`, `recommendation_text`) are served, because a finding without them is not decidable, and the server does not parse them for numbers.

### 5. Migration `0036_cite_partition_v3` (22 characters)

`CREATE OR REPLACE FUNCTION am_verify_norm_citation_partition()`: `0023`'s body with `st.stage_id = 'norm_verification'` replaced by `st.stage_id IN ('norm_verification', 'ar_v3_citation_review')` (still `status = 'succeeded'`, still the pinned verified set). No table, column, CHECK, trigger or view moves. Downgrade restores `0023`'s function byte for byte and **refuses** while any certified `finding_observation` belongs to a Run whose only succeeded CITE stage is `ar_v3_citation_review` (the pattern of `0033`'s refusal). Pins that move: `scripts/recovery/schema_coverage.py` `HEAD`, `tests/support/expected_facts.json` `migration_head`, the `0036` digest in `test_downgrade_chain_round_trip.py`, the `functions` digest in `test_schema_invariant_inventory.py`, and the head sentences the prose guard reads.

### 6. Contract

Operation descriptions only (`getRunNormVerification`, the findings reads), in `contracts/api/v1/openapi.json`, its web mirror and the router; the generated client and `web/FRONTEND_LOCK.json` are regenerated (`npm --prefix web run api:generate`, then the lock). Version `1.8.0`; paths, operations, schemas and fields unchanged. If a change of a field or an enum becomes necessary, the lane stops and reports it.

### 7. The finding views

`listRunFindings` / `getFinding` for a Run of the AR v3 beta profile fill `norm_citations` from the certified partitions (failing closed with `storage_integrity_error` if the read refuses), and never `required_value` / `stated_value`. A Run of any other profile is read exactly as before.

### 8. Web

In `widgets/ar-v3-beta-review`: under each `available` member the published findings of that Run (`listRunFindings`) with the PDF quote, the norm quote and its document, the verdict badge and, for an expert, the existing record-verdict controls (one idempotency key per intent). A person without `expert` sees the findings and no buttons. No internal identifier is rendered; the existing review text and its tests stay as they are. The labels are not changed (`R-146ba`, lane S1).

## Limits stated in advance

* Context-only and mixed proposals are counted only by the group review, not by the report's `withheld_by_reason` (closed enum).
* The model's sentences may contain numbers; the server serves them as the model's text under a pending verdict and does not interpret them.
* `widgets/run-progress` still says a v3 Run publishes no finding; it is outside the grant (Integration note 6).

## Report

### Status

**All four pieces are delivered and each stands alone.** Branch `agent/ar-v3-decisions-01`, base `9e42c18a`; not pushed, not tagged, not merged. Commits in order (`git log --reverse --format='%h %s' 9e42c18a..HEAD`): the design note and task file (`f041c4b7`); **(1)** the report (`e431bbb6`, lock reseal `97039b5d`); **(2)** publication and migration `0036` (`a3a599f0`); **(3)** the verdict path and the certified citations on the finding reads (`662c877a`); **(4)** the web panel (`2194cb84`); then this report.

* **(1) `getRunNormVerification`.** Served for an AR v3 beta Run from the sealed review and the certified partitions (`runs/v3_norm_report.py`, `runs/v3_published_findings.py`); `findings/citation_reader.py` and `citation_report.py` take the certifying stage id (default unchanged). A Run of another profile is `not_found`; a v3 Run with no verified saved review answers the declared `503 dependency_unavailable` and nothing unverified.
* **(2) Publication.** `finish_v3_review_run` rebuilds the candidates (byte-equality with the sealed artifact), advances to `validating`, writes one finding per provisional proposal through `publish_grounded_v3_finding` and terminates, in one transaction. Migration `0036_cite_partition_v3` is what the database refused.
* **(3) Verdict path.** `appendDecision` reused unchanged; `listRunFindings` / `getFinding` of an AR v3 beta Run now carry the certified `norm_citations` (fail closed) and never `required_value` / `stated_value`.
* **(4) Web.** `widgets/ar-v3-beta-review` lists the findings under each available scope with the verdict controls for an expert.

### Premise result

All twelve premises (task file P-01 to P-12) held. Three findings changed the design and are recorded in «Design» section 0: the review artifact does not carry what a finding needs (so the terminal rebuilds and compares), the publisher and the deferred trigger both name a stage a v3 Run does not have (so migration `0036` and a stage parameter), and the publisher's attempt checks would refuse a Run resumed after a crash between CITE and the terminal (so the v3 stage is read at Job, not Attempt, level, which `completed_v3_call` and the final fence already prove). No STOP condition occurred: no path outside the grant was needed for the design, no closed enum was changed, no contract change beyond prose.

### Files

53 files changed (`git diff --name-only 9e42c18a..HEAD | wc -l`; a leading `*` marks a new file).

* **Migration** (1): `*db/migrations/versions/20261027_0036_cite_partition_v3.py`
* **Server (new files marked *)** (12): `src/auditmanager/api/routers/runs.py`, `src/auditmanager/bootstrap/adapters.py`, `src/auditmanager/findings/citation_publication.py`, `src/auditmanager/findings/citation_reader.py`, `src/auditmanager/findings/citation_report.py`, `src/auditmanager/findings/public.py`, `src/auditmanager/runs/v3_citations.py`, `*src/auditmanager/runs/v3_norm_report.py`, `*src/auditmanager/runs/v3_published_findings.py`, `src/auditmanager/runs/v3_review_reader.py`, `src/auditmanager/runs/v3_review_terminal.py`, `src/auditmanager/runs/v3_worker.py`
* **Contract and generated client** (7): `contracts/api/v1/openapi.json`, `web/FRONTEND_LOCK.json`, `web/openapi/openapi.json`, `web/src/shared/api/generated/client.gen.ts`, `web/src/shared/api/generated/index.ts`, `web/src/shared/api/generated/operations.gen.ts`, `web/src/shared/api/generated/types.gen.ts`
* **Pins** (3): `docs/manual-tests/PC-01_prototype.md`, `scripts/recovery/schema_coverage.py`, `tests/support/expected_facts.json`
* **Web source** (5): `web/src/widgets/ar-v3-beta-review/index.ts`, `*web/src/widgets/ar-v3-beta-review/model/may-decide.ts`, `web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.module.css`, `web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx`, `*web/src/widgets/ar-v3-beta-review/ui/run-findings.tsx`
* **Tests (Python)** (19): `tests/integration/api/conftest.py`, `tests/integration/api/test_w57a_seal_surface.py`, `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`, `tests/integration/composition/test_router_answers.py`, `*tests/integration/db/test_cite_partition_v3_migration.py`, `tests/integration/db/test_downgrade_chain_round_trip.py`, `tests/integration/db/test_schema_invariant_inventory.py`, `tests/integration/findings/test_w57a_citation_publication_offline.py`, `tests/integration/findings/test_w57a_citation_reader_offline.py`, `tests/integration/findings/test_w57a_citation_report_offline.py`, `*tests/integration/runs/test_v3_decisions_over_http.py`, `tests/integration/runs/test_v3_review_reader.py`, `tests/integration/runs/test_v3_review_terminal.py`, `tests/integration/runs/test_v3_worker_pipeline.py`, `*tests/unit/findings/test_cite_stage_ids.py`, `*tests/unit/runs/test_v3_finding_views.py`, `*tests/unit/runs/test_v3_norm_report.py`, `*tests/unit/runs/test_v3_provisional_candidates.py`, `*tests/unit/runs/test_v3_published_findings.py`
* **Tests (web)** (4): `web/tests/guards/rendered-language.guard.test.ts`, `*web/tests/unit/analysis-settings/ar-v3-beta-review-decisions.test.ts`, `web/tests/unit/analysis-settings/ar-v3-beta-review-fixtures.ts`, `web/tests/unit/styles/screens.ts`
* **Docs of the lane** (2): `*docs/program/AR-V3-DECISIONS-01.md`, `*docs/program/tasks/AR-V3-DECISIONS-01.md`

### Mutation table

Method: a scratch harness applies one text edit, runs the tests that guard it, restores the file and checks it is byte-equal again; «red» is the number of failing tests (errors of the module fixture counted). **51 mutations: 49 red; P1-14 is an equivalent mutant (explained in its row); W5 stayed green because its first assertion was too weak, so the assertion was strengthened and the mutation re-run as W5b (red). One further attempt (a syntax error in the terminal) was discarded as not a mutation.**

| id | mutation | red |
| --- | --- | ---: |
| P1-1 | report: the rejected proposals are not counted | 1 |
| P1-2 | report: a rejected reason outside `UngroundedReason` is accepted | 1 |
| P1-3 | report: the findings are not compared with the review | 1 |
| P1-4 | report: reads the v1/v2 certifying stage instead of the v3 one (unit) | 1 |
| P1-5 | wire body: a claimed number (`required_value`) is added to a citation | 1 |
| P1-6 | reader: an unknown certifying stage name is accepted | 5 |
| P1-7 | adapter: a Run of another profile is read as a v3 Run | 1 |
| P1-8 | adapter: a non-terminal Run is read | 6 |
| P1-9 | adapter: every reader failure is turned into the 503 | 1 |
| P1-10 | adapter: the report is not read in one repeatable-read read-only snapshot | 1 |
| P1-11 | router: `exclude_unset` removed (`error_code: null` on the wire) | 6 |
| P1-12 | report (HTTP): reads the v1/v2 certifying stage | 21 |
| P1-13 | report (HTTP): `withheld_by_reason` always empty | 6 |
| P1-14 | adapter (HTTP): the terminal-state guard removed | 0 (equivalent: the review reader refuses the same Runs; the guard is proved by P1-8) |
| P2-1 | migration: the stage test stays at `0023`'s (v3 stage not admitted) | 28+ |
| P2-2 | migration: `status = 'succeeded'` dropped from the stage test | 4 |
| P2-3 | migration: the downgrade refusal disabled | 1 |
| P2-4 | migration: the downgrade restores `0036`'s body, not `0035`'s | 1 |
| P2-5 | publisher: the effect must be of the current Attempt for the v3 stage too | 1 |
| P2-6 | publisher: an unknown certifying stage accepted | 4 |
| P2-7 | publisher: a non-normative category accepted | 3 |
| P2-8 | publisher: a candidate without evidence accepted | 1 |
| P2-9 | terminal: the rebuilt artifact need not equal the sealed one | 2 |
| P2-10 | terminal: the rebuilt candidate count need not equal the sealed count | 1 |
| P2-11 | terminal: the candidates are never written | 2 |
| P2-12 | terminal: no re-check of the stage rows after the transition | 1 |
| P2-13 | terminal: a second publication for a Run is not refused | 2 |
| P2-14 | terminal: the writer is called for the v1/v2 stage | 1 |
| P2-15 | terminal: a review with no provisional proposal is rebuilt anyway | 2 |
| P2-16 | candidates: every accepted normative proposal, not only the provisional ones | 2 |
| P2-17 | candidates: a proposal both provisional and withheld accepted | 1 |
| P2-18 | worker: the terminal is not given the Blob store and the document repository | 4 |
| P2-19 | reader: the findings are not re-checked after the read | 2 |
| P2-20 | candidate: the evidence page is altered (HTTP: the reader/report refuse the Run) | 16 |
| P2-21 | matcher: never refuses | 9 |
| P3-1 | finding views: any profile is read as v3 | 1 |
| P3-2 | finding views: the v1/v2 certifying stage | 66 |
| P3-3 | finding views: a refused partition becomes an empty citation list | 1 |
| P3-4 | finding views: `norm_citations` never filled | 2 |
| P3-5 | finding views: citations dropped | 2 |
| P3-6 | seam: `appendDecision` open to any role | 5 |
| P3-7 | router: a generated idempotency key instead of the caller's | 6 |
| P3-8 | router: a fixed key instead of the required header | 7 |
| W1 | web: every role may record a verdict | 2 |
| W2 | web: the findings list is not mounted | 9 |
| W3 | web: an accept defaults to the model's proposed severity | 1 |
| W4 | web: the controls are offered whatever the account holds | 1 |
| W5 | web: the verdict badge removed (first assertion too weak: the card's own attribute) | 0, then strengthened |
| W5b | web: the verdict badge removed (after strengthening) | 2 |
| W6 | web: «Отклонить» sends an accept with a severity | 1 |
| W7 | web: the norm quote is not rendered | 1 |

The guards the brief names: **the publisher refuses a candidate that failed a gate** (the gates are pure and run before; a failed or non-normative candidate cannot reach a row: P2-7, P2-8, P2-16, P2-20 and the writer's own shape guard); **non-normative category** (P2-7); **the verdict needs the expert role and a keyed request** (P3-6, P3-7, P3-8, W1, W4); **the report never turns a withheld citation into a finding** (P1-3, P2-16, P2-21 and `test_a_finding_for_a_withheld_proposal_is_refused_the_report_never_makes_one`); **the report is identical for a replay** (`test_the_report_is_the_same_on_a_replay_and_for_an_administrator`, with P1-13); **raw evidence unchanged** (`test_a_verdict_changes_no_evidence_no_citation_and_no_sentence_of_the_model`, P2-20).

### Before / after of every modified test

No assertion was removed or loosened; each change adds a member, follows a replaced mechanism, or strengthens.

| Test | Before | After |
| --- | --- | --- |
| `tests/integration/api/test_w57a_seal_surface.py::test_shipping_adapter_has_typed_refusal_without_touching_storage` | an adapter with no session raised `503 norm_verification_reader` | replaced by six tests of the served adapter: another profile is `not_found` and nothing is read; each of six non-terminal states answers the same declared `503` and reads nothing; a saved review that fails verification (both error codes) answers the same `503` with no data; any other failure is not turned into a `503`; the read is one repeatable-read read-only snapshot |
| `tests/integration/api/conftest.py` fake `get_norm_verification` | `503` for any Run | reads the Run first (`404` if absent), then the same `503` |
| `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` | `SEALED_STUB_ADDRESSED = {getRunNormVerification}` (exempt from the `404` sweep, asserted to answer `503`) | the set is empty; the operation is swept like every addressed read (an absent `run_` is `404`) |
| `tests/integration/composition/test_router_answers.py` | `SEALED_STUB_GETS` held the path (must answer `503`) | empty; the path is in the ordinary sweep and an explicit assertion says `404 not_found` |
| `tests/integration/findings/test_w57a_citation_reader_offline.py` | bind parameters `{run_id, version_uid, profile_id}` | the same plus `cite_stage_id: norm_verification` (the default is asserted) |
| `tests/integration/findings/test_w57a_citation_report_offline.py` | the stand-in reader took no stage | takes and asserts `cite_stage_id`; two tests added: the default is `norm_verification`; the v3 stage certifies when named and the v1 row does not stand in for it |
| `tests/integration/findings/test_w57a_citation_publication_offline.py` | 17 tests | the same 17 plus eight for the stage parameter and the writer's shape guard |
| `tests/integration/runs/test_v3_review_reader.py` | `publication_rows_exist` patched to `False`; case `finding`: a publication row refuses | the helper `check_run_published_findings` patched to «none»; case `finding`: a finding the review does not explain refuses; two tests added (explained findings pass and are checked on both sides of the read; findings that change during the read refuse) |
| `tests/integration/runs/test_v3_review_terminal.py` | `METRICS.provisional_citation_count = 1`; `test_success_publishes_only_review_stage` | default metrics hold `0` (nothing to publish: the same assertions plus «nothing rebuilt, nothing written»); `PROVISIONAL_METRICS` (`2`) drives eleven new tests (order rebuild / advance / publish / terminate, failures close nothing, byte-equality, count, writer arguments, second publication) |
| `tests/integration/runs/test_v3_worker_pipeline.py` | the terminal stand-in took anything | asserts the terminal is given the Blob store, the saved-text bound and the document repository |
| `tests/integration/db/test_downgrade_chain_round_trip.py` | 15 upgrade-surface digests | + the digest of `0036` (no existing one moved) |
| `tests/integration/db/test_schema_invariant_inventory.py` | `functions`: 34, `6ee1b2f0…3bd9` | 34, `6e5b1c9d…37ad` (only this family moved), comment block of the measurement |
| `tests/support/expected_facts.json`, `scripts/recovery/schema_coverage.py` | head `0035_comparison_records` | `0036_cite_partition_v3` |
| `docs/manual-tests/PC-01_prototype.md` | head sentence `0035` | `0036` |
| `web/tests/guards/rendered-language.guard.test.ts`, `web/tests/unit/styles/screens.ts`, `web/tests/unit/analysis-settings/ar-v3-beta-review-fixtures.ts` | the language guard and the contrast census did not render the findings list | additions only: five guard states over `RunFindings` (loading, refused, loaded for an expert and for an administrator, none), one `UNREACHABLE_IN_ONE_PASS` entry (the failed-write sentence), the census seeds the available scope's finding and an expert, the shared fixture gains the finding, page and account builders |

### Commands and counts

All with the lane stack's `.env` copied untracked into the worktree, `PYTHONPATH=src:$BS`, one pytest at a time; the end-to-end module and the migration tests use private databases (the probe's `prod11a_probe_*` and the suites' `a1_probe_*`, dropped by their fixtures); one hand-made `ardec_<hex>` database was dropped at the end. No docker, no network, no push, no tag.

| Command | Result |
| --- | --- |
| `pytest tests/unit/analysis tests/unit/runs tests/unit/findings tests/integration/runs tests/integration/findings tests/integration/db tests/integration/recovery` (the lane's whole battery, on the final tree of the code commits) | **2,987 passed, 71 skipped, 2 failed**, 1,052 s. The two reds are not this lane's: `tests/unit/analysis/text_profiles/test_text_profile_packages.py::test_source_files_exist_at_the_recorded_legacy_commit` (the host's legacy checkout `/root/projects/PDF-proverka` has no commit: `git show 16ba8e5d…` exits 128) and `tests/integration/runs/test_durable_effect_boundaries.py::test_provider_effect_settlement_is_bounded_and_resumable` (a stray `outcome_unknown` provider effect, `run_01M5YCJ5NB…`, created 09:55:15Z in the lane database by an earlier suite run; the same file is **20 passed** on a clean private database migrated to head) |
| the new end-to-end module `tests/integration/runs/test_v3_decisions_over_http.py` | 65 passed, about 7 s |
| `tests/unit/runs/test_v3_published_findings.py`, `test_v3_norm_report.py`, `test_v3_provisional_candidates.py`, `test_v3_finding_views.py`, `tests/unit/findings/test_cite_stage_ids.py` | 12, 9, 7, 4 and 6 passed |
| `tests/integration/db/test_cite_partition_v3_migration.py` | 10 passed, about 9 s |
| `tests/integration/runs/test_v3_review_terminal.py`, `test_v3_review_reader.py`; `tests/integration/findings/test_w57a_citation_*_offline.py`; `tests/integration/api/test_w57a_seal_surface.py` | 18, 16; 25 + 13; 12 passed |
| the existing v3 suites against the new behaviour (`test_v3_recorded_group_over_http.py`, `test_v3_saved_text_layer_probe.py`, `test_v3_cite_stage.py`, `…cite_preflight`, `…corpus_citation_bridge`, composition `test_v3_worker_registry.py`, `test_v3_pack_install.py`, `test_v3_recorded_cost_binding.py`, `test_ar_v3_group_review_route.py`) | 172 passed |
| finding- and decision-adjacent suites (`tests/integration/api/test_decision_authorship.py`, `tests/integration/decisions`, the absent/empty/listing/no-internal-identifiers/query-surface API files, `tests/integration/findings`, two `p02_journey` files, `test_every_port_implementation_is_whole.py`) | 406 passed, 4 subtests, 1,053 s |
| `tests/contract/api_v1 tests/contract/domain_p02` after piece 1 | 515 passed |
| `npx vitest run` in `web/` | 203 files, **3,095 passed** |
| `npx tsc --noEmit`; `npx eslint --quiet .` in `web/` | exit 0; exit 0 |
| `npm --prefix web run api:verify` | OK, 107 operations, contract sha256 `43f62326…f7df` |
| `pytest tests/contract` minus the three `D-220` files (`test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py`), clean committed tree | **1,174 passed, 1 failed**, 19,283 subtests, 90 s. The one red is `test_doc_prose_facts.py::test_the_scanned_docs_state_the_migration_head_this_tree_has`: `docs/program/CURRENT_STATE.md` still says `0035_comparison_records` (the integrator's sentence, integration note 1). `tests/contract/program` and `test_surface_counts_in_prose.py` are green |
| `git diff --check`; the governance one-liner on the task file | clean; prints `[]` |


### Contract and migration result

* **Contract:** `info.version` stays **`1.8.0`**; 95 paths / 107 operations / 314 schemas unchanged. The only change is the **description of `getRunNormVerification`** (router, `contracts/api/v1/openapi.json`, its mirror `web/openapi/openapi.json`); the generated client was regenerated and `web/FRONTEND_LOCK.json` resealed (`content_commit` `e431bbb6`); `npm --prefix web run api:verify` OK (contract sha256 `43f62326…f7df`). The router now dumps the report with `exclude_unset=True` so an unset `error_code` is absent, never `null`.
* **Migration:** head **`0036_cite_partition_v3`** (22 characters) on `0035_comparison_records`. Upgrade replaces `am_verify_norm_citation_partition()` (the stage test admits `norm_verification` and `ar_v3_citation_review`); downgrade refuses while a certified observation rests on no `norm_verification` stage and otherwise restores `0023`'s function byte for byte (proved on a real server at `0035`, `0036` and back). Measured: only the `functions` family of the invariant inventory moved (34 rows kept).
* **No new operation, schema, field, enum member or error code.**

### Integration notes

1. **Files that pin the migration head** (changed here): `scripts/recovery/schema_coverage.py` (`HEAD`), `tests/support/expected_facts.json` (`migration_head`), `tests/integration/db/test_downgrade_chain_round_trip.py` (digest of `0036`), `tests/integration/db/test_schema_invariant_inventory.py` (`functions` digest), `docs/manual-tests/PC-01_prototype.md` (head sentence). **Not changed (outside the grant): `docs/program/CURRENT_STATE.md`** — its sentence `migration head is **`0035_comparison_records`**` makes `tests/contract/api_v1/test_doc_prose_facts.py::test_the_scanned_docs_state_the_migration_head_this_tree_has` red on this branch until the integrator writes `0036_cite_partition_v3` there (measured: the only red of that file). No table was added, so no grant, purge or erase classification moved.
2. **Files that pin the surface counts:** none moved (95 / 107 / 314 unchanged, `1.8.0` unchanged, no prose count changed).
3. **The numeric fields (the one judgement call).** `required_value` and `stated_value` are stored (the database requires them for a normative finding; the first is checked against the norm quote and the second against the PDF quote) but **not served** for this profile: not in `listRunFindings`, `getFinding`, the report or the CSV. Reason: `numeric_output_policy: expert_review_required`, no edition check exists, and the brief says numerical conclusions stay unavailable. The model's sentences (`finding_text`, `recommendation_text`) are served, because a finding without them is not decidable, and may contain numbers in prose. If the owner wants the two values on the wire, it is one projection change in `_observation_view` and `_norm_verification_body` (tests `test_no_report_carries_a_number_the_model_claimed` and `…_finding_read_carries_the_certified_citation_and_no_number` name it).
4. **The labels of `R-146ba`** (lane S1) are untouched. The new section adds no occurrence of «предварительная цитата» or of the profile label; the existing panel text is as it was.
5. **`contracts/analysis/ar_v3_beta/v1/stage.json`** keeps `beta_policy.canonical_finding_publication: false` (outside the grant). It is read as «the CITE stage writes no finding»: the stage's only output is still the review artifact; the findings are written by the terminal. If the owner wants the key to read `true` it is a change of that contract, of `runs/v3_cite_stage_contract.py` and of the profile seal tests.
6. **A false sentence on a screen, outside the grant:** `web/src/widgets/run-progress/ui/run-progress.tsx` line 134 says «Канонические находки здесь не публикуются.» for a published AR v3 Run; it now publishes findings (when a proposal is provisional). Suggested wording: «Находки с предварительными нормативными ссылками опубликованы; решение по каждой записывает эксперт.», with the existing tests of that widget moved with it. Also the prose of `docs/program/AR-V3-BETA-*.md` that says «review-only» describes history and was not edited; `src/auditmanager/runs/executor.py` still reports `published_finding_count=0` in its in-memory `ExecutionResult` for a v3 Run (nothing reads it; `RunStatus.published_finding_count` comes from the database and is right).
7. **Other readers of published findings now meet v3 findings:** the run CSV export (works, no number column; tested), the XLSX export (answers `422 storage_integrity_error` on the synthetic test version because it has no portal companion; not caused by this lane), the version comparison's finding matching (`ComparisonAdapter.published_findings`) and the dashboard counts. None was edited.
8. **Disk and shared temp:** the lane's runs left no large pytest directory (`--basetemp` in the lane scratchpad for the last run; the earlier runs' `pytest-N` directories are the harness's own three-deep rotation). A `rm -rf /tmp/pytest-of-root/pytest-*` was refused by the permission layer as a sweep of shared scratch and was not repeated.
9. **Private databases:** one hand-made `ardec_<hex>` (22 MB, used to read the constraints and round-trip `0036`) was dropped at the end; the suites' own throw-away databases are dropped by their fixtures.

### Limits

* **Context-only and mixed proposals** are counted only by the group review (`withheld_proposal_count`), not by the report's `withheld_by_reason`: `UngroundedReason` is a closed enum (contract and the `0023` CHECK) and the beta policy's withholding is not a grounding reason.
* **The 503 is the only refusal the operation declares**, so a Run that is not terminal, a failed Run and a saved review that fails verification are one answer on the wire; the reason goes to the log (`norm verification refused for <run>: <reason>`).
* **A Run closed before this lane** has no findings although its sealed review may hold provisional proposals; the report and the group review accept that state (zero findings) and show no findings for it. No such Run exists on any stand (no pack is installed anywhere).
* **A resumed Attempt** publishes (the writer reads the v3 stage at Job level), proved at the writer and by the terminal's rebuild; it is not proved by killing a worker mid-flight.
* **The select in the web panel** is covered by the feature's own request builder tests and by the live test that an accept without a chosen severity sends nothing; the browser's `change` event itself is outside the harness (`live-render.ts` has no dispatch).
* **No live call, no recorded fixture was added** (`fixtures/recorded/ar_v3` does not exist; the recorded reply is written on first sight by the suites' helper).

### Forbidden paths are untouched

`git diff --name-only 9e42c18a..HEAD` lists the files above. None is under `contracts/domain`, `contracts/analysis`, `src/auditmanager/runs/executor.py`, `decisions/`, `exports/`, `analysis/`, `optimisation/`, `comparison/`, `access/`, `infra/`, `tests/e2e/`, a root dependency or lock file, `docs/program/CURRENT_STATE.md`, `DEBT_REGISTER.md`, a ruling or an ADR; the only migration is `0036`; `web/src` changes are under `widgets/ar-v3-beta-review` and the generated client. The commands that prove it (all print nothing):

```
git diff --name-only 9e42c18a..HEAD | grep -E '^(contracts/(domain|analysis)/|src/auditmanager/(runs/executor|decisions|exports|analysis|optimisation|comparison|access)|infra/|tests/e2e/|package(-lock)?\.json|web/package(-lock)?\.json|uv\.lock|requirements|pyproject\.toml|docs/program/(CURRENT_STATE|DEBT_REGISTER)|docs/adr)'
git diff --name-only 9e42c18a..HEAD | grep '^web/src/' | grep -v -E '^web/src/(widgets/ar-v3-beta-review|shared/api/generated)/'
git diff --name-only 9e42c18a..HEAD | grep '^db/migrations'    # only 20261027_0036_cite_partition_v3.py
```

**Two files outside the literal grant were edited, because they are pins the new web states require**: `web/tests/guards/rendered-language.guard.test.ts` and `web/tests/unit/styles/screens.ts` (the language guard and the contrast census render the widgets and fail on a branch or a rule no state reaches); the edits are additions only (see «Before / after»). The task file's allowed paths were extended with both.
