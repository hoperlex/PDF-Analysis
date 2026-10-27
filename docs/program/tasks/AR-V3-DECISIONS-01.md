# Task AR-V3-DECISIONS-01 — expert verdicts on grounded AR v3 findings and the norm-verification report

task_id: AR-V3-DECISIONS-01

## Outcome
Lane AR-A of wave PW5 (`R-146as`, `R-146at`; supersedes the review-only `R-146g`). On the recorded composition the AR v3 terminal publishes, for every proposal that passed both pure gates and cites only provisional topics, the grounded finding through `findings/citation_publication.py`; an expert records a verdict with the existing `appendDecision`; `getRunNormVerification` answers the canonical `NormVerificationReport` from the saved CITE stage instead of `dependency_unavailable`; the group-review panel lists the findings with verdict controls. Numerical conclusions stay unavailable; no live call; the model text is never a decision. Design and report: [`../AR-V3-DECISIONS-01.md`](../AR-V3-DECISIONS-01.md).

## Depends on
- AR-V3-BETA-RUN-REVIEW-BOUNDARY-01
- AR-V3-BETA-GROUP-REVIEW-SCREEN-01
- CONTRACT-1-8-0-01
- COMPARE-PERSISTED-SUMMARY-01

## Frozen inputs
- domain contract: `contracts/domain/v1`, error catalogue unchanged
- API contract: `1.8.0`, 95 paths / 107 operations / 314 schemas (descriptions only may change)
- analysis/comparison/event contract: `contracts/analysis/ar_v3_beta/v1/stage.json` unchanged
- migration head: `0035_comparison_records` at the start; this lane takes `0036_cite_partition_v3`
- base commit: `9e42c18a`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `db/migrations/versions/20261027_0036_cite_partition_v3.py`
- enumerator_owner: AR-V3-DECISIONS-01
- totality_query: `ls db/migrations/versions | tail -3; python -m alembic --config db/migrations/alembic.ini heads`

## Captured premise evidence
- premise: the terminal publishes no finding row; the publisher and a deferred database trigger both require a stage named norm_verification that an AR v3 Run does not have; getRunNormVerification is a refusing stub; appendDecision, the report schema and Finding.norm_citations already exist; the files that pin the head and the surface are the ones listed in P-12. One consequence found: migration 0036 is needed (P-04) and the numeric fields stay off the wire.

### P-01 — Base, head, versions
- captured_at: 2026-10-27
- command: `git rev-parse HEAD; git branch --show-current; cat VERSION; grep -m1 '"version"' contracts/api/v1/openapi.json; ls db/migrations/versions | grep -v pycache | tail -1; python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));s=d['surface'];print(d['migration_head'],d['contract_version'],s['path_count'],len(s['operations']),len(s['schema_names']))"`
- captured_output:
  ```text
  9e42c18ae68c5025020474ef8839223d3d889538
  agent/ar-v3-decisions-01
  0.9.0
      "version": "1.8.0",
  20261027_0035_comparison_records.py
  0035_comparison_records 1.8.0 95 107 314
  ```
- interpretation: The lane starts on 9e42c18a, contract 1.8.0, migration head 0035_comparison_records, product version 0.9.0 and the sealed surface in expected_facts.json.

### P-02 — The terminal publishes no finding row today
- captured_at: 2026-10-27
- command: `grep -n 'no finding row is written\|publication_rows_exist\|canonical_finding_already_published\|_REQUIRED = ' -A0 src/auditmanager/runs/v3_review_terminal.py; grep -n 'canonical_finding_publication' contracts/analysis/ar_v3_beta/v1/stage.json src/auditmanager/runs/v3_cite_stage_contract.py`
- captured_output:
  ```text
  10:from auditmanager.findings.public import TerminalSelection, publication_rows_exist, select_terminal
  --
  21:_REQUIRED = (
  --
  67:    publishes only the already verified CITE review; no finding row is written.
  --
  83:    if publication_rows_exist(session, authority.run_id):
  84:        raise _refuse("canonical_finding_already_published")
  --
  117:            or publication_rows_exist(session, authority.run_id)):
  contracts/analysis/ar_v3_beta/v1/stage.json:35:    "canonical_finding_publication": false
  src/auditmanager/runs/v3_cite_stage_contract.py:85:                "scenario", "numeric_output_policy", "canonical_finding_publication",
  src/auditmanager/runs/v3_cite_stage_contract.py:107:                "canonical_finding_publication": False,
  ```
- interpretation: The terminal writes no finding and refuses when one exists; the CITE stage contract (an analysis contract, outside this lane) reads canonical_finding_publication false. The key is read here as describing the CITE stage output, which stays the review artifact.

### P-03 — The grounded publisher and what it requires of the Run
- captured_at: 2026-10-27
- command: `grep -n 'NORMATIVE_CATEGORIES\|class V3PublicationCandidate\|stage_id = .norm_verification.\|stage_id = .text_analysis.\|run_state\|def publish_grounded_v3_finding' src/auditmanager/findings/citation_publication.py`
- captured_output:
  ```text
  26:NORMATIVE_CATEGORIES = frozenset({
  41:class V3PublicationCandidate:
  64:           r.norm_retrieval_set_id, r.state AS run_state,
  83:       AND mc.run_id = r.run_id AND mc.stage_id = 'text_analysis'
  86:       AND pe.attempt_id = a.attempt_id AND pe.stage_id = 'text_analysis'
  88:       AND st.stage_id = 'norm_verification'
  230:def publish_grounded_v3_finding(
  243:            or candidate.category not in NORMATIVE_CATEGORIES
  253:        row["run_state"] != "validating"
  ```
- interpretation: The writer is transaction-scoped, restricted to the five normative categories, needs the Run in validating and a succeeded stage_result named norm_verification. The AR v3 CITE stage is named ar_v3_citation_review, so the authority query refuses it.

### P-04 — The database refuses a certified partition without a norm_verification stage (head 0035)
- captured_at: 2026-10-27
- command: `PGPASSWORD=local-disposable-postgres-password psql -h 127.0.0.1 -p 58640 -U auditmanager_local -d ardec_1733cf3c4552 -At -c "select pg_get_functiondef('am_verify_norm_citation_partition'::regproc)" | sed -n '20,32p'`
- captured_output:
  ```text
                      USING ERRCODE = 'AM001';
              END IF;
              IF certified_count IS NOT NULL AND NOT EXISTS (
                  SELECT 1 FROM audit_run r
                  JOIN norm_retrieval_set s
                    ON s.norm_retrieval_set_id = r.norm_retrieval_set_id
                   AND s.norms_snapshot_id = r.norms_snapshot_id
                   AND s.state = 'verified'
                  JOIN stage_result st ON st.run_id = r.run_id
                   AND st.stage_id = 'norm_verification' AND st.status = 'succeeded'
                  WHERE r.run_id = observation_run
              ) THEN
                  RAISE EXCEPTION 'state_transition_not_allowed: certified citation partition needs succeeded CITE stage and pinned verified set'
  ```
- interpretation: am_verify_norm_citation_partition (deferred constraint trigger on finding_observation and finding_observation_norm_citation) requires st.stage_id = norm_verification AND succeeded. A v3 beta Run has no such row, so the commit of a published v3 finding is refused: migration 0036 replaces the function.

### P-05 — Constraints of finding, finding_observation, finding_evidence, citations at head 0035
- captured_at: 2026-10-27
- command: `cat /tmp/claude-0/-root-projects-PDF-Analysis/16441722-42ee-458c-b74f-e08cf340d7b7/scratchpad/p_constraints.txt`
- captured_output:
  ```text
  == finding
  CHECK ((allocated_by_run_id ~ '^run_[0-9A-HJKMNP-TV-Z]{26}$'::text))  -- ck_finding_allocated_by_run_id_format
  CHECK (((canonical_observation_id IS NULL) OR (canonical_observation_id ~ '^fobs_[0-9A-HJKMNP-TV-Z]{26}$'::text)))  -- ck_finding_canonical_observation_id
  CHECK ((category = ANY (ARRAY['internal_contradiction'::text, 'explicit_placeholder'::text, 'dimensions'::text, 'layout'::text, 'facade'::text, 'roof'::text, 'documentation'::text, 'evacuation'::text, 'fire_safety'::text, 'accessibility'::text, 'insulation'::text, 'sound'::text])))  -- ck_finding_category
  CHECK ((finding_uid ~ '^fnd_[0-9A-HJKMNP-TV-Z]{26}$'::text))  -- ck_finding_finding_uid_format
  CHECK ((project_uid ~ '^prj_[0-9A-HJKMNP-TV-Z]{26}$'::text))  -- ck_finding_project_uid_format
  CHECK ((version_uid ~ '^ver_[0-9A-HJKMNP-TV-Z]{26}$'::text))  -- ck_finding_version_uid_format
  FOREIGN KEY (allocated_by_run_id) REFERENCES audit_run(run_id)  -- finding_allocated_by_run_id_fkey
  PRIMARY KEY (finding_uid)  -- finding_pkey
  FOREIGN KEY (project_uid) REFERENCES project(project_uid)  -- finding_project_uid_fkey
  FOREIGN KEY (version_uid) REFERENCES document_version(version_uid)  -- finding_version_uid_fkey
  FOREIGN KEY (finding_uid, canonical_observation_id) REFERENCES finding_observation(finding_uid, finding_observation_id)  -- fk_finding_canonical_observation
  == finding_observation
  CHECK ((analysis_profile_id ~ '^ap_[0-9A-HJKMNP-TV-Z]{26}$'::text))  -- ck_finding_observation_analysis_profile_id_format
  CHECK ((category = ANY (ARRAY['internal_contradiction'::text, 'explicit_placeholder'::text, 'dimensions'::text, 'layout'::text, 'facade'::text, 'roof'::text, 'documentation'::text, 'evacuation'::text, 'fire_safety'::text, 'accessibility'::text, 'insulation'::text, 'sound'::text])))  -- ck_finding_observation_category
  CHECK (((finding_uid IS NULL) OR (finding_uid ~ '^fnd_[0-9A-HJKMNP-TV-Z]{26}$'::text)))  -- ck_finding_observation_finding_uid_format
  CHECK (((grounded = (finding_uid IS NOT NULL)) AND (grounded = (ungrounded_reason IS NULL))))  -- ck_finding_observation_grounding
  CHECK ((finding_observation_id ~ '^fobs_[0-9A-HJKMNP-TV-Z]{26}$'::text))  -- ck_finding_observation_id_format
  CHECK (((model_call_id IS NULL) OR (model_call_id ~ '^mc_[0-9A-HJKMNP-TV-Z]{26}$'::text)))  -- ck_finding_observation_model_call_id_format
  CHECK ((((category = ANY (ARRAY['evacuation'::text, 'fire_safety'::text, 'accessibility'::text, 'insulation'::text, 'sound'::text])) AND ((NOT grounded) OR ((norm_citation_count IS NOT NULL) AND ((norm_citation_count >= 1) AND (norm_citation_count <= 5)) AND (required_value IS NOT NULL)))) OR ((category <> ALL (ARRAY['evacuation'::text, 'fire_safety'::text, 'accessibility'::text, 'insulation'::text, 'sound'::text])) 
  CHECK (((norm_citation_count IS NULL) OR (grounded AND (finding_uid IS NOT NULL) AND ((norm_citation_count >= 0) AND (norm_citation_count <= 5)))))  -- ck_finding_observation_norm_partition
  CHECK ((((required_value IS NULL) = (stated_value IS NULL)) AND ((required_value IS NULL) OR ((char_length(required_value) >= 1) AND (char_length(required_value) <= 200))) AND ((stated_value IS NULL) OR ((char_length(stated_value) >= 1) AND (char_length(stated_value) <= 200)))))  -- ck_finding_observation_norm_values
  CHECK ((prompt_bundle_id ~ '^pb_[0-9A-HJKMNP-TV-Z]{26}$'::text))  -- ck_finding_observation_prompt_bundle_id_format
  CHECK (((proposed_severity IS NULL) OR (proposed_severity = ANY (ARRAY['critical'::text, 'economic'::text, 'operational'::text, 'recommendation'::text, 'check_adjacent'::text]))))  -- ck_finding_observation_proposed_severity
  CHECK ((provider_mode = ANY (ARRAY['live'::text, 'recorded'::text])))  -- ck_finding_observation_provider_mode
  CHECK ((run_id ~ '^run_[0-9A-HJKMNP-TV-Z]{26}$'::text))  -- ck_finding_observation_run_id_format
  CHECK ((stage_id = ANY (ARRAY['source_preparation'::text, 'page_geometry_extraction'::text, 'document_context_build'::text, 'text_analysis'::text, 'block_analysis'::text, 'finding_merge'::text, 'finding_review'::text, 'finding_correction'::text, 'norm_verification'::text])))  -- ck_finding_observation_stage_id
  CHECK ((((char_length(finding_text) >= 1) AND (char_length(finding_text) <= 4000)) AND ((char_length(recommendation_text) >= 1) AND (char_length(recommendation_text) <= 4000))))  -- ck_finding_observation_text_length
  CHECK (((ungrounded_reason IS NULL) OR (ungrounded_reason = ANY (ARRAY['quotation_absent'::text, 'quotation_on_different_page'::text, 'span_outside_page'::text, 'span_outside_block'::text, 'span_length_mismatch'::text, 'quote_in_recognised_text'::text, 'norm_label_unknown'::text, 'norm_quote_too_short'::text, 'norm_quote_ambiguous'::text, 'norm_quote_absent'::text, 'norm_value_not_in_quote'::text, 'stated_value_not_i
  FOREIGN KEY (finding_uid) REFERENCES finding(finding_uid)  -- finding_observation_finding_uid_fkey
  FOREIGN KEY (model_call_id) REFERENCES model_call(model_call_id)  -- finding_observation_model_call_id_fkey
  PRIMARY KEY (finding_observation_id)  -- finding_observation_pkey
  FOREIGN KEY (run_id) REFERENCES audit_run(run_id)  -- finding_observation_run_id_fkey
  UNIQUE (finding_uid, finding_observation_id)  -- uq_finding_observation_finding_id
  trg_finding_observation_immutable : CREATE TRIGGER trg_finding_observation_immutable BEFORE DELETE OR UPDATE ON public.finding_observation FOR EACH ROW EXECUTE FUNCTION am_immutable_row()
  trg_finding_observation_partition : CREATE CONSTRAINT TRIGGER trg_finding_observation_partition AFTER INSERT ON public.finding_observation DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION am_verify_norm_citation_partition()
  == finding_evidence
  CHECK (((block_id IS NULL) OR (block_id ~ '^b_[0-9]{6}$'::text)))  -- ck_finding_evidence_block_id
  CHECK ((evidence_ordinal >= 0))  -- ck_finding_evidence_evidence_ordinal
  CHECK ((finding_observation_id ~ '^fobs_[0-9A-HJKMNP-TV-Z]{26}$'::text))  -- ck_finding_evidence_observation_id_format
  CHECK ((page_number >= 1))  -- ck_finding_evidence_page_number
  CHECK (((char_length(quote) >= 1) AND (char_length(quote) <= 2000)))  -- ck_finding_evidence_quote_length
  CHECK (((char_start >= 0) AND (char_end > char_start)))  -- ck_finding_evidence_span
  CHECK (((char_end - char_start) = char_length(quote)))  -- ck_finding_evidence_span_matches_quote
  FOREIGN KEY (finding_observation_id) REFERENCES finding_observation(finding_observation_id)  -- finding_evidence_finding_observation_id_fkey
  PRIMARY KEY (finding_observation_id, evidence_ordinal)  -- pk_finding_evidence
  trg_finding_evidence_immutable : CREATE TRIGGER trg_finding_evidence_immutable BEFORE DELETE OR UPDATE ON public.finding_evidence FOR EACH ROW EXECUTE FUNCTION am_immutable_row()
  == finding_observation_norm_citation
  CHECK (((finding_observation_id ~ '^fobs_[0-9A-HJKMNP-TV-Z]{26}$'::text) AND (run_id ~ '^run_[0-9A-HJKMNP-TV-Z]{26}$'::text) AND (norms_snapshot_id ~ '^ns_[0-9A-HJKMNP-TV-Z]{26}$'::text) AND (norm_retrieval_set_id ~ '^nrs_[0-9A-HJKMNP-TV-Z]{26}$'::text) AND (norm_document_id ~ '^ndoc_[0-9A-HJKMNP-TV-Z]{26}$'::text) AND (norm_paragraph_id ~ '^npar_[0-9A-HJKMNP-TV-Z]{26}$'::text)))  -- ck_finding_observation_norm_citat
  CHECK (((citation_ordinal >= 1) AND (citation_ordinal <= 5)))  -- ck_finding_observation_norm_citation_ordinal
  CHECK ((((char_length(quote) >= 20) AND (char_length(quote) <= 4000)) AND (char_length = char_length(quote)) AND (char_start >= 0)))  -- ck_finding_observation_norm_citation_quote
  CHECK ((state = ANY (ARRAY['verified'::text, 'rebound'::text])))  -- ck_finding_observation_norm_citation_state
  FOREIGN KEY (finding_observation_id) REFERENCES finding_observation(finding_observation_id)  -- finding_observation_norm_citation_finding_observation_id_fkey
  FOREIGN KEY (norm_document_id) REFERENCES norm_document(norm_document_id)  -- finding_observation_norm_citation_norm_document_id_fkey
  FOREIGN KEY (norm_paragraph_id) REFERENCES norm_paragraph(norm_paragraph_id)  -- finding_observation_norm_citation_norm_paragraph_id_fkey
  FOREIGN KEY (norm_retrieval_set_id) REFERENCES norm_retrieval_set(norm_retrieval_set_id)  -- finding_observation_norm_citation_norm_retrieval_set_id_fkey
  FOREIGN KEY (norms_snapshot_id) REFERENCES norms_snapshot(norms_snapshot_id)  -- finding_observation_norm_citation_norms_snapshot_id_fkey
  FOREIGN KEY (run_id) REFERENCES audit_run(run_id)  -- finding_observation_norm_citation_run_id_fkey
  PRIMARY KEY (finding_observation_id, citation_ordinal)  -- pk_finding_observation_norm_citation
  trg_finding_observation_norm_citation_guard : CREATE TRIGGER trg_finding_observation_norm_citation_guard BEFORE INSERT ON public.finding_observation_norm_citation FOR EACH ROW EXECUTE FUNCTION am_verify_norm_citation()
  trg_finding_observation_norm_citation_immutable : CREATE TRIGGER trg_finding_observation_norm_citation_immutable BEFORE DELETE OR UPDATE ON public.finding_observation_norm_citation FOR EACH ROW EXECUTE FUNCTION am_immutable_row()
  trg_norm_citation_partition : CREATE CONSTRAINT TRIGGER trg_norm_citation_partition AFTER INSERT ON public.finding_observation_norm_citation DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION am_verify_norm_citation_partition()
  ```
- interpretation: Quoted from a fresh database migrated to 0035. finding_observation.stage_id admits text_analysis (what the publisher writes); norm category shape requires 1..5 citations and required_value; the ungrounded reasons are a closed list (not touched).

### P-06 — Contract schemas and handlers named by the brief
- captured_at: 2026-10-27
- command: `grep -n '^class NormVerificationReport\|^class NormFindingVerification\|^class ArV3BetaGroupReview\b\|^class ArV3BetaGroupReviewMember\|^class AppendDecisionRequest\|^class UngroundedReason' src/auditmanager/api/schemas/models.py; grep -n 'def get_norm_verification' -A8 src/auditmanager/bootstrap/adapters.py | head -12; grep -n 'getRunNormVerification' -B3 src/auditmanager/api/routers/runs.py | head -8`
- captured_output:
  ```text
  1123:class ArV3BetaGroupReviewMember(_Object):
  1133:class ArV3BetaGroupReview(_Object):
  1550:class UngroundedReason(str, enum.Enum):
  1671:class NormFindingVerification(_Object):
  1677:class NormVerificationReport(_Object):
  1822:class AppendDecisionRequest(_Object):
  1151:    def get_norm_verification(self, *, run_id: str) -> models.NormVerificationReport:
  1152-        """Refuse until a reader proves the 0023 partition and the pinned set.
  1153-
  1154-        An empty citation SELECT is not a certificate of zero. CITE will replace this
  1155-        seam after it checks stage success and every canonical/member partition.
  1156-        """
  1157-        raise DomainError(
  1158-            ErrorCode.DEPENDENCY_UNAVAILABLE,
  1159-            dependency="norm_verification_reader",
  83-
  84-    @router.get(
  85-        "/runs/{run_id}/norm-verification",
  86:        operation_id="getRunNormVerification",
  ```
- interpretation: The report schema is closed and already carries run_id, norms_snapshot_id, norm_retrieval_set_id, status, findings, withheld_by_reason (keys: UngroundedReason), textless_pages, error_code. The handler is a refusing stub (dependency_unavailable / norm_verification_reader).

### P-07 — The decision path that exists
- captured_at: 2026-10-27
- command: `grep -n 'appendDecision' src/auditmanager/api/security.py src/auditmanager/api/routers/decisions.py | head -6; grep -n '"appendDecision"' src/auditmanager/api/security.py; grep -n 'def append_decision_under_key\|def record_decision\|def _check_severity_target' src/auditmanager/decisions/ledger.py`
- captured_output:
  ```text
  src/auditmanager/api/security.py:302:#: event is written only by a complete profile" hold by construction: ``appendDecision``
  src/auditmanager/api/security.py:433:        "appendDecision": _EXPERT,
  src/auditmanager/api/routers/decisions.py:1:"""``appendDecision``, ``listDecisionHistory`` and ``listDecisions``."""
  src/auditmanager/api/routers/decisions.py:46:        operation_id="appendDecision",
  433:        "appendDecision": _EXPERT,
  135:def _check_severity_target(
  276:def record_decision(
  450:def append_decision_under_key(
  ```
- interpretation: appendDecision is expert-only (admin alone is 403), keyed by Idempotency-Key through CommandRepository, and takes (finding_uid, finding_observation_id). It needs a published finding; a provisional citation that is not a finding has no target.

### P-08 — Recorded v3 fixtures and tests that drive the six Runs
- captured_at: 2026-10-27
- command: `grep -rl 'ar_v3' tests/integration fixtures --exclude-dir=__pycache__ | wc -l; ls fixtures/recorded; grep -rl 'ar_v3' fixtures | head -3; ls tests/integration/runs | grep v3_ | tr '\n' ' '`
- captured_output:
  ```text
  58
  comparison
  sections
  sections_widen
  text_analysis
  test_v3_cite_preflight.py test_v3_cite_stage.py test_v3_corpus_citation_bridge.py test_v3_cost_refusal.py test_v3_execution_guard.py test_v3_execution_request.py test_v3_group_review.py test_v3_group_start_queues_the_runs.py test_v3_pack_manifest.py test_v3_provider_call.py test_v3_recorded_cost_binding.py test_v3_recorded_group_over_http.py test_v3_reply_custody.py test_v3_review_artifact.py test_v3_review_reader.py test_v3_review_terminal.py test_v3_saved_text_layer_probe.py test_v3_worker_pipeline.py 
  ```
- interpretation: No fixtures/recorded/ar_v3 directory exists. The six-Run drive is a test-side recorded reply written on first sight (test_v3_recorded_group_over_http.py, test_v3_saved_text_layer_probe.py); this lane reuses those drivers and adds no committed fixture.

### P-09 — Docs of the beta and the runbook
- captured_at: 2026-10-27
- command: `ls docs/program/AR-V3-BETA-*.md | wc -l; ls docs/program/AR-V3-BETA-ACTIVATION-RUNBOOK-01.md; grep -n 'Numerical findings' docs/program/AR-V3-BETA-ACTIVATION-RUNBOOK-01.md`
- captured_output:
  ```text
  46
  docs/program/AR-V3-BETA-ACTIVATION-RUNBOOK-01.md
  39:- Numerical findings stay unavailable until an expert decision and an edition check exist; nothing here creates one.
  ```
- interpretation: The runbook states: numerical findings stay unavailable until an expert decision and an edition check exist; nothing in the runbook creates one.

### P-10 — The rulings that bind the lane
- captured_at: 2026-10-27
- command: `grep -n -o '^| `R-146\(g\|as\|at\|ba\)` | \*[^*]*\*[^|]\{0,220\}' docs/program/OWNER_RULINGS_2026-09-17.md`
- captured_output:
  ```text
  1765:| `R-146g` | **Analysis path for АР.** Chosen: «Только v3 (нормативный путь)». The production АР product is the six-Run reviewed-pack path (`AR-V3-BETA-*`): provisional citations that «требует проверки эксперта», no numerical conclusio
  1803:| `R-146as` | *АР v3 decisions.* Chosen: «Да, строить решения по предварительным цитатам» (overrides `R-146g` review-only): an expert can record a verdict on a provisional citation, the grounded publisher (`findings/citation_publication.py`) serves dec
  1804:| `R-146at` | *`getRunNormVerification`.* Chosen: «Реализовать» (follows `R-146as`): the operation answers the canonical norm-verification report instead of `dependency_unavailable`. 
  1811:| `R-146ba` | *Human review of the sections and of АР v3 during the beta.* The owner wrote: «Проверки человеком не будет на бета. Оставляем риск, индикацию убираем временно. АР v3 запускаем по нормам без реальной проверки экспертом, надеюсь на твой профессионализм». Poll answers: remove the pr
  ```
- interpretation: R-146as overrides the review-only R-146g (decisions on provisional citations, the grounded publisher, a contract and migration slot); R-146at implements getRunNormVerification; R-146ba removes the labels for the beta and is lane S1 (not this lane).

### P-11 — Tests that pin the refusing stub (they must change with the report)
- captured_at: 2026-10-27
- command: `grep -rn 'norm_verification_reader' tests --include=*.py | cut -c1-170`
- captured_output:
  ```text
  tests/integration/api/test_w57a_seal_surface.py:26:    assert caught.value.detail_fields == {'dependency': 'norm_verification_reader'}
  tests/integration/api/conftest.py:843:            ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="norm_verification_reader"
  tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py:193:#: ``dependency: norm_verification_reader``) until the CITE reader; it belongs here.
  ```
- interpretation: Three test files pin the 503 stub; each is modified in this lane with a before/after in the report.

### P-12 — Files that pin the migration head and the surface counts
- captured_at: 2026-10-27
- command: `grep -rl --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=.venv '0035_comparison_records' . | grep -v 'docs/program/tasks/' | sort | tr '\n' ' '; echo; python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'))['surface'];print(d['path_count'],len(d['operations']),len(d['schema_names']))" | cut -c1-200`
- captured_output:
  ```text
  ./contracts/api/v1/openapi.json ./contracts/api/v1/README.md ./db/migrations/versions/20261027_0035_comparison_records.py ./docs/manual-tests/PC-01_prototype.md ./docs/program/COMPARE-PERSISTED-SUMMARY-01.md ./docs/program/CONTRACT-1-8-0-01.md ./docs/program/CURRENT_STATE.md ./docs/program/DEBT_REGISTER.md ./docs/program/P02_SEAMS.md ./scripts/recovery/product_purge.py ./scripts/recovery/schema_coverage.py ./src/auditmanager/comparison/sheet_links.py ./tests/integration/comparison/test_comparison_summary_db.py ./tests/integration/comparison/test_sheet_pairing_db.py ./tests/integration/db/test_comparison_records_migration.py ./tests/integration/db/test_comparison_summary_migration.py ./tests/integration/db/test_downgrade_chain_round_trip.py ./tests/integration/db/test_migration_lifecycle.py ./tests/integration/db/test_schema_invariant_inventory.py ./tests/integration/db/test_schema_shape.py ./tests/integration/recovery/test_comparison_records_purge_and_erase.py ./tests/integration/recovery/test_grant_classification.py ./tests/integration/recovery/test_product_purge.py ./tests/integration/recovery/test_synthetic_drill_compare.py ./tests/integration/recovery/test_synthetic_drill_seed.py ./tests/support/expected_facts.json ./tests/unit/comparison/test_comparison_records_migration_text.py ./web/openapi/openapi.json 
  95 107 314
  ```
- interpretation: The files that name the head, as found by the same search COMPARE-PERSISTED-SUMMARY-01 used. The surface counts do not move in this lane (no operation, schema or field is added).

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_*.py`
- `src/auditmanager/findings/**`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/**`
- `contracts/api/v1/openapi.json`
- `contracts/api/v1/README.md`
- `web/openapi/openapi.json`
- `web/src/shared/api/generated/**`
- `web/FRONTEND_LOCK.json`
- `db/migrations/versions/20261027_0036_cite_partition_v3.py`
- `scripts/recovery/schema_coverage.py`
- `tests/support/expected_facts.json`
- `tests/unit/runs/**`
- `tests/unit/findings/**`
- `tests/integration/runs/**`
- `tests/integration/findings/**`
- `tests/integration/db/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `tests/contract/api_v1/**`
- `web/src/widgets/ar-v3-beta-review/**`
- `web/src/entities/finding/**`
- `web/tests/unit/analysis-settings/**`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/AR-V3-DECISIONS-01.md`
- `docs/program/tasks/AR-V3-DECISIONS-01.md`

## Lane resources
- foundation_instance: `auditmanager-ar-close` (the integrator's lane stack, shared read-only; this lane writes only to private databases it creates and drops)
- postgres_port: `58640`
- s3_api_port: `62140`
- s3_console_port: `62141`
- postgres_db: private `ardec_<hex>` databases created and dropped by the lane (never `auditmanager_ar_close`)
- s3_bucket: `auditmanager-ar-close` (objects written by the suites' own fixtures only)

## Forbidden hotspots
- the section profile packages, optimisation, comparison, other web areas
- `contracts/analysis/**`, `contracts/domain/**`
- root dependency/lock files
- `tests/e2e/pc01/journey/manifest.json`
- `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, the rulings, the ADRs
- `src/auditmanager/runs/executor.py`, `src/auditmanager/decisions/**`, `src/auditmanager/exports/**`
- the labels of `R-146ba` (lane S1)

## Non-goals
- no live provider call, no model dispatch, no new recording
- no numerical conclusion on the wire, no edition check
- no new operation, schema, field or enum member
- no change to the beta policy (context-only topics stay withheld)
- no change to the labels, to the exports, to `widgets/run-progress`

## Deliverables
- the report `getRunNormVerification`
- publication of grounded findings by the AR v3 terminal and migration `0036`
- the verdict path proved over HTTP on a published v3 finding
- the web panel
- `docs/program/AR-V3-DECISIONS-01.md` and this file

## Required tests
- command: `pytest -q tests/unit/analysis tests/integration/runs tests/integration/findings tests/integration/db tests/contract` (minus the three `D-220` files), one pytest at a time on the lane stack with a private database
- expected: green; every guard has a recorded mutation that turns a named test red

## Integration contract
The integrator can rely on: terminal state, run count and the six-Run group unchanged; a published v3 Run now has 0..n finding rows equal to its provisional proposals; `getRunNormVerification` answers the canonical report or a typed refusal; `appendDecision` works on those findings; surface 95 / 107 / 314 and contract `1.8.0` unchanged; head `0036_cite_partition_v3`.

## Failure/idempotency/security cases
- a candidate that failed a gate, a non-normative category, a context-only or mixed proposal: no row
- a rebuilt review that differs from the sealed one: the terminal refuses before the Run transition
- a second publication for a Run: refused
- a verdict by a non-expert, without a key, on a withheld proposal: refused or impossible
- a report over a Run with a finding that matches no provisional proposal: refused

## Rollback / feature flag
Behaviour changes only for AR v3 beta Runs, which need an installed reviewed pack (none is installed on any stand). Rollback: revert the commits; `alembic downgrade 0035_comparison_records` is refused while a certified v3 finding exists (restore a backup instead).

## Handoff
- changed files: see the report `docs/program/AR-V3-DECISIONS-01.md` section «Files»
- commands/results: see the report section «Commands and counts»
- known limits: see the report section «Limits»
- integration notes: see the report section «Integration notes»
