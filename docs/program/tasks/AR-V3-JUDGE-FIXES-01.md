# Task AR-V3-JUDGE-FIXES-01 — fix the findings of the independent read of the AR v3 publication and the activation records

task_id: AR-V3-JUDGE-FIXES-01

## Outcome
Fix lane B of the integrator's read-out. Two code defects and six document defects that an independent read-only judge (J3) found at `93bc5037` are fixed: (1) a proposal is provisional by the paragraph its citations were grounded to, not by the label the model wrote; (2) `exportRunXlsx` reads an AR v3 beta Run's certified citations through the stage that certifies them; (3) steps 10b and 11 of the live-host instructions run in a form that works on the live stand; (4) the rollback says what it really does; (5)(6) the attestation values stop saying more than was done; (7) the activation README is current; (8) the promotion loops stop at the first refusal. Every code fix has a test written first and shown red, and a mutation table.

## Depends on
- AR-V3-DECISIONS-01
- AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01
- AR-V3-PROMOTE-01
- AR-V3-BETA-PACK-INSTALL-01

## Frozen inputs
- domain contract: `contracts/domain/v1`, unchanged
- API contract: `1.8.0`, 95 paths / 107 operations / 314 schemas, unchanged (no wire value is added: the new withheld cases use the existing `context_only_or_mixed_source` disposition)
- analysis/comparison/event contract: `contracts/analysis/ar_v3_beta/v1/stage.json`, unchanged
- migration head: `0037_analysis_presets` (unchanged; this task adds none)
- base commit: `93bc5037`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the classification at the base reads the model's label; rebinding searches every reliable paragraph of the document; the export hands the stage-blind citation reader; the live containers and the loops are as the judge described; the README and the seal sentences are stale. Each is printed below (2026-10-28, tree `93bc5037` plus the lane's own commits where stated).

### P-01 — Base and the worktree
- captured_at: 2026-10-28
- command: `git rev-parse integration/ar-close-1026 93bc5037; git log -1 --format='%h %s' 93bc5037`
- captured_output:
  ```text
  93bc5037a564c8e1c99071a4114956bdcadd7d55
  1bb15e4dbd65eb1a1cb78451c07fccf5edab4f48
  93bc5037 docs(rulings): R-146bd standing disk maintenance
  agent/ar-v3-judge-fixes-01
  ```
- interpretation: The lane starts on 93bc5037, the tip of integration/ar-close-1026 named in the brief; the first line of output is the integration tip, the second is the lane's own HEAD at capture time (which has moved on by the lane's own commits).

### P-02 — Finding 1: the classification is decided by the model's label
- captured_at: 2026-10-28
- command: `git show 93bc5037:src/auditmanager/runs/v3_citations.py | sed -n 262,283p`
- captured_output:
  ```text
      plan = plan_v3_corpus_citations(
          request, response, text_layer, block_index=block_index,
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
          else:
              withheld.append(accepted.proposal_ordinal)
      return V3BetaCitationReview(
  ```
- interpretation: At the base the proposal is classified by by_item[label_items[citation.label]].mode, with citations taken from the model's proposal (accepted.proposal.norm_citations), never from accepted.norm_citations (the grounded paragraph).

### P-03 — Finding 1: rebinding searches every reliable paragraph of the same document
- captured_at: 2026-10-28
- command: `sed -n 255,275p src/auditmanager/norms/citation_prep.py; grep -n 'rebinding_paragraphs' src/auditmanager/norms/retrieval/artifact.py`
- captured_output:
  ```text
              match = _raw_match(labelled, prepared[labelled.paragraph_id], quote)
          except _RawSpanTooLong:
              return withheld("norm_quote_absent")
          state = "verified"
          target = labelled
          if match is None:
              alternatives: list[tuple[NormParagraph, tuple[int, str]]] = []
              for item in reliable:
                  if (
                      item.document_id != labelled.document_id
                      or item.paragraph_id == labelled.paragraph_id
                  ):
                      continue
                  try:
                      found = _raw_match(item, prepared[item.paragraph_id], quote)
                  except _RawSpanTooLong:
                      continue
                  if found is not None:
                      alternatives.append((item, found))
                      if len(alternatives) > 1:
                          break
  320:            "rebinding_paragraphs": source_rows,
  ```
- interpretation: ground_norm_observation falls back to every other reliable paragraph with the same document_id; the set's rebinding_paragraphs is the list of every reliable paragraph of the mapped documents (artifact.py), not only of the paragraphs sent in the prompt part.

### P-04 — Finding 1: the repro
- captured_at: 2026-10-28
- command: `PYTHONPATH=src python -c "from auditmanager.norms.public import NormParagraph,NormCitation,NormLabelBinding,ground_norm_observation as g; A=NormParagraph('npar_A','ndoc_D','Первый абзац нормы о ширине прохода составляет не менее 1,2 м.'); B=NormParagraph('npar_B','ndoc_D','Второй абзац нормы: высота ступени не более 0,22 м для лестниц.'); r=g((A,B),(NormCitation('N1','высота ступени не более 0,22 м для лестниц'),),'0,22 м','0,22 м',('0,22 м',),label_bindings=(NormLabelBinding('N1','npar_A'),)); print(r.reason,[(c.label,c.paragraph_id,c.state) for c in r.citations])"`
- captured_output:
  ```text
  None [('N1', 'npar_B', 'rebound')]
  ```
- interpretation: The label N1 is bound to paragraph A; the quote is in paragraph B of the same document: the citation is grounded to B in state rebound. The label alone would classify this by A's item.

### P-05 — Finding 1: where the decided spans of the real map sit
- captured_at: 2026-10-28
- command: `python3 -c "import json;d=json.load(open('docs/program/ar-v3-beta/decisions.json',encoding='utf-8'));[print(i['id'],i['mode'],[(t['norm_document_id'][-6:],t['ordinal_first'],t['ordinal_last']) for t in i['targets']]) for i in d['items'] if i['id'] in ('C04','C05','C06','C07','C15','C16','C17','C18')]"`
- captured_output:
  ```text
  C04 provisional_citation [('C01BGG', 240, 248)]
  C05 context_only [('FNC87X', 489, 492)]
  C06 context_only [('C01BGG', 206, 207)]
  C07 provisional_citation [('C01BGG', 100, 100)]
  C15 context_only [('RPJF14', 390, 391)]
  C16 provisional_citation [('RPJF14', 296, 300)]
  C17 provisional_citation [('RPJF14', 345, 346)]
  C18 provisional_citation [('RPJF14', 447, 452)]
  ```
- interpretation: Scope F2 holds C04 and C07 (provisional) and C06 (context_only, ordinals 206-207) in one document (C01BGG); scope A2 holds C16-C18 (provisional) and C15 (context_only, 390-391) in RPJF14. A quote rebound inside such a document can land on the context-only text, which is sent to the model.

### P-06 — Finding 2: the export reads citations with the default certifying stage
- captured_at: 2026-10-28
- command: `git show 93bc5037:src/auditmanager/bootstrap/adapters.py | grep -n 'read_citations=read_verified_citations'; sed -n 96,99p src/auditmanager/exports/xlsx/certified_package.py; grep -n 'cite_stage_id' src/auditmanager/findings/citation_reader.py | head -5; grep -n 'norm_retrieval_set_id is not None' src/auditmanager/exports/xlsx/run_export.py`
- captured_output:
  ```text
  2154:                read_citations=read_verified_citations,
      citation_read = read_citations(
          session, run_id=identity, version_uid=run_source.version_uid,
          profile_id=profile_id,
      )
  92:       AND st.stage_id = :cite_stage_id
  202:    cite_stage_id: str = "norm_verification",
  208:    ``cite_stage_id`` names the succeeded StageResult that certifies the partitions;
  211:    if cite_stage_id not in CITE_STAGE_IDS:
  218:        "cite_stage_id": cite_stage_id,
  ```
- interpretation: The brief names findings/certified_package.py; the file is src/auditmanager/exports/xlsx/certified_package.py. The adapter hands the stage-blind reader (default norm_verification), the certified package calls it without a stage, and run_export treats any Run that pinned a retrieval set as one that cites.

### P-07 — Finding 2: the workbook projection does not read the claimed numbers
- captured_at: 2026-10-28
- command: `grep -rn 'required_value\|stated_value' src/auditmanager/exports || echo 'no match under src/auditmanager/exports'`
- captured_output:
  ```text
  no match under src/auditmanager/exports
  ```
- interpretation: Neither field appears anywhere in the export context, so no change to the export can put them in a workbook without a new read.

### P-08 — Finding 3: what the live containers have
- captured_at: 2026-10-28
- command: `grep -n '^COPY' infra/deploy/Dockerfile.api; grep -n 'ports:' infra/deploy/compose.server.yml | head -5; grep -n 'postgres:5432\|s3:9000' infra/deploy/env/alpha.env.example; grep -n 'ar-v3-pack:/run/ar-v3' infra/deploy/compose.server.yml`
- captured_output:
  ```text
  31:COPY Makefile /tmp/Makefile
  47:COPY pyproject.toml uv.lock .python-version ./
  70:COPY --from=build /app/.venv /app/.venv
  71:COPY src/ /app/src/
  72:COPY db/ /app/db/
  86:COPY contracts/ /app/contracts/
  87:COPY fixtures/recorded/ /app/fixtures/recorded/
  88:COPY docs/program/P02_LOCK.json /app/docs/program/P02_LOCK.json
  89:COPY VERSION /app/VERSION
  90:COPY release-notes/ /app/release-notes/
  91:COPY uv.lock /app/uv.lock
  92:COPY infra/deploy/serve.py /app/serve.py
  102:    # NO `ports:`. Nothing but the proxy leaves this host. The developer stack publishes
  278:    # No `ports:`. The proxy reaches 8000 and 8001 over the compose network.
  293:  # `ports:`, and not on the session volume.
  483:    ports:
  247:DATABASE_URL=postgresql+psycopg://auditmanager_alpha_app:replace-with-ALPHA_APP_DB_PASSWORD@postgres:5432/auditmanager_alpha
  250:MIGRATOR_DATABASE_URL=postgresql+psycopg://auditmanager_alpha:change-me-disposable-postgres-password@postgres:5432/auditmanager_alpha
  251:S3_ENDPOINT_URL=http://s3:9000
  277:      - ./ar-v3-pack:/run/ar-v3:ro
  358:      - ./ar-v3-pack:/run/ar-v3:ro
  ```
- interpretation: The api image has src/, db/, contracts/, fixtures/recorded/ and the P02 lock, no docs/program/ar-v3-beta; the ports: matches are comments and the proxy; live DATABASE_URL and S3_ENDPOINT_URL use the compose host names; only the pack directory is mounted, read-only.

### P-09 — Finding 4: what a missing pack does to a Run
- captured_at: 2026-10-28
- command: `grep -n 'reviewed pack is not installed' src/auditmanager/runs/executor.py; grep -n 'interrupted_reason=CRASHED_REASON\|fail_for_run' src/auditmanager/runs/carrier.py; grep -n 'remaining members refuse' docs/program/AR-V3-BETA-PACK-INSTALL-01.md`
- captured_output:
  ```text
  888:            message="the pinned AR v3 beta reviewed pack is not installed",
  507:            JobRepository().fail_for_run(session, run_id=run_id)
  517:                interrupted_reason=CRASHED_REASON,
  60:6. **Withdraw or roll back**: unset the variable in both services and restart them. New group starts then refuse again. A group already started keeps its rows and replays on its original key, but its remaining members refuse execution while no pack is installed.
  ```
- interpretation: executor.py raises required_norm_unavailable when no pack is installed; the carrier's crash path fails the Job and terminates the Run failed with the v3 reason; the install note carries the same caveat in one clause.

### P-10 — Findings 5 and 6: the sealed sentences
- captured_at: 2026-10-28
- command: `git grep -l -e 'числовые выводы недоступны' -e 'карт, векторов и сводных' 93bc5037 -- docs; git show 93bc5037:docs/program/ar-v3-beta/README.md | grep -c 'ИИ проверяет ИИ'; git show 93bc5037:docs/program/AR-V3-PROMOTE-01.md | grep -c 'ИИ проверяет ИИ'`
- captured_output:
  ```text
  93bc5037:docs/program/AR-V3-ACTIVATION-FEASIBILITY-01.md
  93bc5037:docs/program/AR-V3-PROMOTE-01.md
  93bc5037:docs/program/ar-v3-beta/README.md
  0
  1
  ```
- interpretation: At the base three documents carry the numeric phrase or the vectors phrase (the original proposal in the feasibility report, the custody-lane record in PROMOTE-01 section 6, and the README seal table); the last two numbers are the counts of the AI-to-AI clause in the README (0) and in PROMOTE-01 (1).

### P-11 — Finding 7: the README at the base
- captured_at: 2026-10-28
- command: `git show 93bc5037:docs/program/ar-v3-beta/README.md | grep -n 'not final\|fails today\|is \*\*inferred\*\*\|64 zeros'; git show 93bc5037:docs/program/ar-v3-beta/query-texts.json | grep -n 'no token count was measured'; python3 -c "import json;print(max(json.load(open('docs/program/ar-v3-beta/vectors-provenance.json'))['token_count_by_item'].values()))"`
- captured_output:
  ```text
  12:| `decisions.json` | the full decision file `ar-beta-map-decisions-v1` for C01 to C22, `synthetic: false`; the real `map_pack` tool builds six maps from it | **not final**: the six query-vector digests are the placeholder (64 zeros) |
  14:| `scopes.json` | the skeleton of `v3_pack_cli seal --scopes` | **not final**: the six `map_sha256` values are placeholders |
  40:- **Designations:** the five «СП» labels of the sheet; for D6 the reader's label of the document, `Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)`, not the short «123-ФЗ», because `map_pack validate` demands that a target's designation equals the designation of the exported rows, and the exporter writes the reader's label. This D6 string is **inferred** (see check b below).
  44:1. **`decisions.json`, `query_vectors.sha256_by_scope`: 64 zeros for each of F1 F2 A1 A2 S1 S2.** The real tool **accepts** them (it checks only that a digest is 64 lowercase hex characters), so a file with the placeholder left in would build, validate and promote. Two guards stand against that: the `comment` carries the word `PLACEHOLDER` exactly while the zeros are there (the shape test fails if the marker and the state disagree, or if the six digests are partly replaced), and `AR_V3_DECISIONS_REQUIRE_FINAL=1` makes the shape test demand real, distinct digests in `decisions.json` and real map digests in `scopes.json`. Run it before sealing; it fails today, as it should.
  8:    "estimate_method": "characters only; the tokenizer is not available on this host, so no token count was measured. Upper bound: the inference input is the text plus two special tokens, and a SentencePiece tokenizer with Cyrillic coverage produces at most one token per character, so tokens <= characters + 2. embed-texts refuses an over-long text and never truncates it",
  86
  ```
- interpretation: The README at the base still described the placeholders and the failing shape test; the query-texts description said no token count was measured while the provenance record holds measured counts, maximum 86.

### P-12 — Finding 8: the loops at the base
- captured_at: 2026-10-28
- command: `git show 93bc5037:docs/program/AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md | sed -n 22,35p`
- captured_output:
  ```text
  ```bash
  CLI="python -m auditmanager.norms.retrieval.promote_cli"
  for S in F1 F2 A1 A2 S1 S2; do
    $CLI plan bundle-$S            # must end: verdict: matched   (exit 0)
  done
  for S in F1 F2 A1 A2 S1 S2; do
    $CLI promote bundle-$S         # verified, replayed: false
    $CLI promote bundle-$S         # the replay: replayed: true, nothing changes
  done
  ```

  `plan` must print `verdict: matched` for all six before any `promote`; a differing digest prints `REFUSED [expected_digest_mismatch]` naming the artifact and writes nothing (the set id is not consumed). Stop on the first refusal and report it; do not edit a bundle. The rehearsal on the local lane took 2–5 s per promotion.

  Expected values (from the independent check): `catalogue_sha256` `4b201656…a555` identical in all six; `prompt_part_characters` F1 19,249 · F2 11,958 · A1 15,032 · A2 14,143 · S1 **21,921 (79 characters under the 22,000 cap)** · S2 18,930. A different figure means a different snapshot or build.
  ```
- interpretation: Two bare for loops: no set -e, no break, no check of the printed verdict; the prose asked to stop on the first refusal.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`.local/ar-v3-draft/pack.json` (the custody lane's sealed file) is history and is not edited; `AR-V3-PROMOTE-01.md` section 6 keeps the values that file was sealed with and section 6a carries the corrected live values; `AR-V3-ACTIVATION-FEASIBILITY-01.md` section 6 is the original proposal and is not edited.

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_citations.py`
- `src/auditmanager/runs/v3_review_artifact.py`
- `src/auditmanager/bootstrap/adapters.py`
- `tests/unit/runs/test_v3_rebound_classification.py`
- `tests/integration/runs/test_v3_review_artifact.py`
- `tests/unit/exports/test_xlsx_v3_citation_stage.py`
- `tests/integration/exports/test_xlsx_v3_run.py`
- `docs/program/AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md`
- `docs/program/AR-V3-PROMOTE-01.md`
- `docs/program/ar-v3-beta/README.md`
- `docs/program/ar-v3-beta/query-texts.json`
- `docs/program/AR-V3-JUDGE-FIXES-01.md`
- `docs/program/tasks/AR-V3-JUDGE-FIXES-01.md`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `web/**`, `infra/**`
- the section, comparison and access code
- `src/auditmanager/findings/**`, `src/auditmanager/exports/**` (read, not changed: the export seam is the composition root's reader, in `bootstrap/adapters.py` only)
- root dependency/lock files, `docs/program/CURRENT_STATE.md`, `DEBT_REGISTER.md`, the rulings, the ADRs
- `.local/ar-v3-draft/pack.json`

## Non-goals
- No change to the wire: no new withheld reason, no new error code, no new field.
- No serving of `required_value` / `stated_value`.
- No portal companion for the synthetic versions: an XLSX export of a version without one stays refused, typed.
- No run of any command on a live host, no docker, no network, no push, no tag.

## Lane resources
Tests that need PostgreSQL and the object store use the integrator's lane stack through a copy of `.local/worktrees/ar-close-1026/.env` and **private databases** that the suites create and drop (`prod11a_probe_*`); no database was created by hand. The lane stops and starts nothing.

## Deliverables
- `src/auditmanager/runs/v3_citations.py`: `index_prompt_rows`, `grounded_citations_are_provisional` (the one rule) and `plan_v3_beta_citation_review` using it.
- `src/auditmanager/runs/v3_review_artifact.py`: the artifact builder re-checks the classification with the same rule (reason `review_context_laundered`, and the new `review_citation_grounding_invalid`).
- `src/auditmanager/bootstrap/adapters.py`: `_read_citations_for_export`, the reader the Excel export is handed (stage chosen from the profile; the export use case and the public reader signature are unchanged).
- The tests of the allowed paths and the two documents of the lane.
- The three live-host documents and the activation README corrected as listed in the outcome.

## Required tests
- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/runs tests/unit/findings tests/unit/exports tests/integration/runs tests/integration/findings tests/integration/exports`
- expected: all pass on a private database (the counts are in the report); `tests/contract/program`, `tests/contract/api_v1/test_doc_prose_facts.py`, `tests/contract/api_v1/test_surface_counts_in_prose.py`, `tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py` (also with `AR_V3_DECISIONS_REQUIRE_FINAL=1`) and `git diff --check` clean on the committed tree.

## Integration contract
The integrator can rely on: an AR v3 proposal is published as a finding only if every citation was grounded to a paragraph the labelled provisional topic itself sent (a rebound citation also not where a context-only topic sends the same paragraph); the sealed review, the terminal's rebuild and the candidates are produced by the one function, so the byte-equality check of the terminal needs no change; `exportRunXlsx` of a published AR v3 Run returns the workbook with its certified citations (given the version's portal companion); no sealed pack, contract, migration or wire value changed. Runs sealed under the previous rule: none exist on any stand (no pack is installed anywhere).

## Failure/idempotency/security cases
- A rebound quote that lands on a context-only paragraph, on a paragraph no item sent, or on another topic's paragraph is withheld, never published and never re-attributed.
- An unknown label, a label that differs between the proposal and its grounding, and an unknown grounding state are refusals (`V3CorpusCitationRefused` / `review_citation_grounding_invalid`), not a quiet classification.
- The Excel export keeps its typed refusals: no portal companion is `storage_integrity_error` (`role: source.structured_companion`); a Run whose citations do not verify is `required_norm_unavailable`.

## Rollback / feature flag
Not applicable as a flag: the code change is a stricter classification (it can only withhold more) and a correct stage choice for an export that was closed. Revert the commits to restore the previous behaviour. The document rollback section of `AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md` is the pack's rollback, not this task's.

## Handoff
- changed files: see `docs/program/AR-V3-JUDGE-FIXES-01.md`
- commands/results: see the same report
- known limits: see the same report
- integration notes: see the same report
