# Task W56B-INT-RECOGNISED-REGION-PREP-01 — bind an OCR quote to its portal region

task_id: W56B-INT-RECOGNISED-REGION-PREP-01

## Outcome

A pure, unserved selector returns an exact OCR quote candidate only when the
same immutable version has a marked recognised TEXT entry, a matching portal
TEXT block, a geometry-checked region and an explicitly textless page. Tests
prove refusal of cross-version, image-description, wrong-page, mismatched
geometry and ambiguous-quote inputs.

## Depends on

- `W55B-RECOGNISED-01` — completed producer of marked OCR entries.
- `W55B-GEOMETRY-01` — completed producer of normalised portal blocks.
- `W56A-INT-RECOGNISED-CONTEXT-PREP-01` — completed fail-closed OCR artifact
  selector and flag validation, reused here.

## Frozen inputs

- base commit: `3d131d2966e0efeea7b53d9662785f253165a9a4`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- portal-block schema SHA-256: `b4e286219614dbcb892d95b40beef4ae89408650dfb27ebf6ecd399e611ede2a`;
- code-first plan SHA-256: `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- migration head: `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W55b produces marked OCR text and portal geometry, while W56a
  refuses OCR-only quotes as PDF citations. W56b plans recognised-text citations
  with region evidence but has no independent binding primitive.

### P-01 — the exact new module is absent at the frozen base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only 3d131d2966e0efeea7b53d9662785f253165a9a4 src/auditmanager/analysis/recognised`
- captured_output:
  ```text
  src/auditmanager/analysis/recognised/__init__.py
  src/auditmanager/analysis/recognised/artifact.py
  src/auditmanager/analysis/recognised/flags.py
  src/auditmanager/analysis/recognised/markdown.py
  src/auditmanager/analysis/recognised/portal.py
  ```
- interpretation: this grant adds one isolated module; it does not replace
  a registered stage or an existing OCR/PDF quote resolver.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/recognised/region_candidate.py`
- `tests/integration/analysis/recognised/test_region_candidate.py`
- `docs/program/tasks/W56B-INT-RECOGNISED-REGION-PREP-01.md`
- `docs/program/W56B-INT-RECOGNISED-REGION-PREP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, existing producer/consumer files, API
routes/UI, run executor, stage registry, composition root, root dependencies
and locks, global styles, `CURRENT_STATE.md`, provider settings, remote refs
and tags.

## Non-goals

No executable W56b profile, finding citation, OCR confidence rule, provider
request, crop analysis, model budget, DB/S3 read, persisted artifact, public
contract, W57a API/stage seal or full beta acceptance.

## Deliverables

One additive selector, focused container-free tests and a result report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/recognised/test_region_candidate.py` — all pass;
- Python compilation of the new module and test — pass;
- direct `governance_findings` from
  `tests/contract/program/test_wave_governance.py` for this task — no findings;
- `git diff --check` and exact changed-path inspection — only allowed paths.

## Integration contract

The later W56b owner may consume a `RecognisedRegionCandidate` after reading
checksum-verified same-run artifacts and the version's stored textless-page
set. It carries OCR text offsets and a normalised portal region, explicitly
marked `recognised`. It does not assert a PDF text-layer quote or authorize a
finding. The future seal owns citation schema, run pinning and publication.

## Failure/idempotency/security cases

Wrong role/version, duplicate block identity, mismatched page/type, invalid or
untrusted region, quote absent or repeated within one block, and unclassified
textless-page state refuse. Input documents are not mutated. Repeated valid
input yields the same immutable candidate.

## Rollback / feature flag

Remove the additive module and its test before wiring; no data rollback or
feature flag is needed.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: W56b seal owner binds the saved artifact references and chooses a
  public OCR citation policy after the pending model/region decisions.
