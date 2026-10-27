# Task AR-V3-ACTIVATION-PREP-01 — decision file, query texts and seal skeleton for the AR v3 beta

task_id: AR-V3-ACTIVATION-PREP-01
status: completed in development candidate (lane AR-B, part 1 of wave PW5; authoring, no database)

## Outcome

The inputs the integrator needs for steps 4 to 9 of the AR v3 activation exist as files in `docs/program/ar-v3-beta/`: the full decision file for C01 to C22 (`decisions.json`, with the query-vector digests left as a marked placeholder), the 22 query texts with their SHA-256 (`query-texts.json`), the skeleton of the `seal` scopes file (`scopes.json`), the scope definitions (`scope-definitions.json`) and a README with the «exclude → context_only» mapping note, the attestation wording and the order of the remaining steps. The real `map_pack` accepts the decision file; a shape test proves 22 distinct items, the 14/8 split, sorted targets, NFC texts and that every guard can fail.

## Depends on

- `AR-V3-ACTIVATION-FEASIBILITY-01` — completed; section 3 is the spec, section 6 the attestation wording, section 8 steps 3 and 7 the plan.
- `AR-V3-BETA-MAP-TOOL-01` — completed; the decision schema and `map_pack`.
- `AR-V3-BETA-SPANS-MEASURE-01` — completed; the measured spans, their paragraph ids and digests.
- `AR-NORM-MAP-APPROVAL-PREP-01` — completed; the decision sheet.
- `AR-V3-BETA-PACK-INSTALL-01` — completed; `v3_pack_cli`.
- `AR-V3-BETA-SET-TOOL-01` — completed; `promote_cli`.

## Frozen inputs

- domain contract: unchanged
- API contract: `1.8.0`, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0035_comparison_records`, unchanged
- base commit: `b32c64f3` (`integration/ar-close-1026`)
- rulings `R-146ba` and `R-146bb` (`docs/program/OWNER_RULINGS_2026-09-17.md`); accepted risks `A-10` and `A-11` (`docs/program/PRODUCTION-READINESS-PLAN-01.md`)
- beta policy `src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.json` (eight `context_only` items, which a decision may not upgrade)
- snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`; frozen embedding profile `bge-m3-dense-v1`, revision `5617a9f61b028005a4858fdac845db406aefb181`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the topic labels of the 22 items live on a commit outside this tree; the policy has 14 provisional and 8 context-only items; the real map tool accepts zero digests and refuses a missing paragraph file; the seal reader refuses non-hex map digests; the D6 label the exporter writes is 61 characters; the proposal has 20 distinct spans; no paragraph rows exist in this lane

### P-01 — the topic labels are on `281a5418`, which is not an ancestor of this tree

- captured_at: 2026-10-27
- command: `git show 281a5418:docs/program/AR-NORM-MAP-DISCOVERY-01.md | grep -c '^| C[0-9][0-9] |' ; git merge-base --is-ancestor 281a5418 HEAD ; echo "ancestor exit=$?"`
- captured_output:
  ```text
  22
  ancestor exit=1
  ```
- interpretation: the commit is in the shared repository and has the 22 candidate rows; it is read with `git show` and not merged, so the query texts cite it by SHA.

### P-02 — the beta policy fixes the split the integrator ordered

- captured_at: 2026-10-27
- command: `python3 -c "import json;d=json.load(open('src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.json',encoding='utf-8'));print([i['id'] for i in d['items'] if i['mode']=='context_only'], sum(i['mode']=='provisional_citation' for i in d['items']))"`
- captured_output:
  ```text
  ['C05', 'C06', 'C08', 'C09', 'C10', 'C15', 'C21', 'C22'] 14
  ```
- interpretation: eight `context_only` items (which the tool refuses to upgrade) and 14 provisional ones.

### P-03 — the real map tool accepts the decision file, zero vector digests included

- captured_at: 2026-10-27
- command: `PYTHONPATH=src:$BS .venv/bin/python -c "from pathlib import Path; from auditmanager.analysis.profiles.ar_v3.norm_map import map_pack as m; x=m.build_scope_maps(m.parse_decisions(Path('docs/program/ar-v3-beta/decisions.json').read_bytes())); print([s.scope_id for s in x.maps], len({s.sha256 for s in x.maps}), x.review)"`
- captured_output:
  ```text
  ['F1', 'F2', 'A1', 'A2', 'S1', 'S2'] 6 None
  ```
- interpretation: with `BS` the bootstrap site-packages of the repository virtualenv. Six maps, six distinct digests, no review block. It also shows that the tool does not refuse 64 zeros as a query-vector digest, so a file with the placeholder left in would build; the shape test is the guard.

### P-04 — the CLI refuses only the missing paragraph rows

- captured_at: 2026-10-27
- command: `PYTHONPATH=src:$BS .venv/bin/python -m auditmanager.analysis.profiles.ar_v3.norm_map.map_pack build --decisions docs/program/ar-v3-beta/decisions.json --paragraphs /nonexistent/paragraphs.json --out /nonexistent/pack ; echo "exit=$?"`
- captured_output:
  ```text
  REFUSED: file_unreadable:paragraphs.json
  exit=2
  ```
- interpretation: `build` parses and builds the decisions first, then reads the paragraph file; the refusal is the file, not a decision defect. The paragraph-dependent checks (ids, designations, reliability, the 22,000-character cap) wait for the database export.

### P-05 — the seal reader refuses the skeleton because of its placeholders only

- captured_at: 2026-10-27
- command: `PYTHONPATH=src:$BS .venv/bin/python -m auditmanager.runs.v3_pack_cli seal --scopes docs/program/ar-v3-beta/scopes.json --reviewer x --capacity x --reviewed-at 2026-10-27 --decision-ref x --scope-statement x --out /nonexistent/pack.json ; echo "exit=$?"`
- captured_output:
  ```text
  v3-pack REFUSED spec_value: every map_sha256 must be a lowercase SHA-256
  exit=2
  ```
- interpretation: refused before any database is reached; the shape test also shows that six distinct hex digests make `_read_spec` accept the rest of the skeleton.

### P-06 — the D6 label the exporter writes has 61 characters

- captured_at: 2026-10-27
- command: `python3 -c "print(len('Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)'))"`
- captured_output:
  ```text
  61
  ```
- interpretation: the string is the label that `tests/unit/norms/test_reader_designation.py` derives from the D6 slug; `AR-V3-BETA-SPANS-MEASURE-01` measured the exporter's D6 label as 61 characters. Equal length and equal source, not a read of the database: the integrator checks the label at the export (README, check b).

### P-07 — the proposal has 20 distinct spans and this lane has no paragraph rows

- captured_at: 2026-10-27
- command: `python3 -c "import json;d=json.load(open('docs/program/ar-v3-beta/spans.proposal.json'));print(len({(c['norm_document_id'],c['ordinal_first'],c['ordinal_last']) for i in d['items'] for c in i['candidates']}))" ; ls .local/ar-v3-draft ; echo "ls exit=$?"`
- captured_output:
  ```text
  20
  ls: cannot access '.local/ar-v3-draft': No such file or directory
  ls exit=2
  ```
- interpretation: the decisions use 19 of the 20 spans (C22 takes 289 to 300), so the export for the comparison with the earlier read uses the proposal's 20; there is no paragraph file in the lane, so nothing dependent on rows can run here.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/ar-v3-beta/**`
- `docs/program/AR-V3-ACTIVATION-PREP-01.md`
- `docs/program/tasks/AR-V3-ACTIVATION-PREP-01.md`
- `tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py`

## Forbidden hotspots

All of `src/**`, `contracts/**`, `db/**`, `infra/**`, `web/**`, `scripts/**`, every other path under `tests/**` and `docs/program/**` (so also `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md` and `docs/program/OWNER_RULINGS_*.md`), the existing `docs/program/ar-v3-beta/spans.proposal.json` (new files only in that directory), the migration head, root dependency/lock files, the composition root, global styles, any corpus text in git, `origin/main`, tags, other worktrees. No container, database, network or download; no process killed.

## Non-goals

No vector, no map digest, no pack, no promotion, no seal, no attestation is produced. No `edition_evidence` is fetched or invented. No `review` block. No expert decision is simulated: every decision is the AI integrator's under `R-146ba` and the files say so. The paragraph export, the weights and the database are the integrator's steps.

## Deliverables

- `docs/program/ar-v3-beta/decisions.json`, `query-texts.json`, `scopes.json`, `scope-definitions.json`, `README.md`;
- `tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py` (53 pass, 1 skipped unless `AR_V3_DECISIONS_REQUIRE_FINAL=1`);
- the report `docs/program/AR-V3-ACTIVATION-PREP-01.md` and this task file.

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py`
- expected: 53 passed, 1 skipped; with `AR_V3_DECISIONS_REQUIRE_FINAL=1` the skipped test runs and fails until the placeholders are replaced.
- governance: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-ACTIVATION-PREP-01.md',encoding='utf-8').read())))"` — expected `[]`.
- prose guards: the same pytest invocation over `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` — expected green apart from failures present at the base (named in the handoff).
- `git diff --check` clean; only the allowed paths changed.

## Integration contract

The integrator reads the README of `docs/program/ar-v3-beta/` and the report. `decisions.json` is the input of `map_pack build`; `query-texts.json` of `embed-texts`; `scopes.json` of `v3_pack_cli seal` once its six `map_sha256` are filled. Two placeholders are open: the six vector digests of `decisions.json` and the six map digests of `scopes.json`. Nothing imports these files; no runtime code reads them.

## Failure/idempotency/security cases

No corpus text is in any file: they hold ids, ordinals, digests and authored text; the query texts contain no digit and no quotation. No file claims that an edition is current or that a human checked a norm (the shape test refuses such wording). The placeholder cannot be sealed by accident: the digests of `scopes.json` are not hex and `seal` refuses them; the zero digests of `decisions.json` are accepted by the tool and are guarded by the marker rule and by `AR_V3_DECISIONS_REQUIRE_FINAL=1`.

## Rollback / feature flag

Not applicable: new documents and one test. Revert the commits to remove them.

## Handoff

- changed files: the five files in `docs/program/ar-v3-beta/`, the shape test, the report and this task file (all new)
- commands/results: see the report; the shape test prints 53 passed, 1 skipped; governance prints `[]`
- known limits: the paragraph-dependent checks of `map_pack` did not run (no database); the D6 designation is inferred; the query texts were not tried against vectors; no expert reviewed anything
- integration notes: merge-independent (new paths only); open questions are in section 5 of the report
