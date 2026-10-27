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
