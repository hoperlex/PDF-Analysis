# W59-INT-RAW-EVIDENCE-SEAL-PREP-01 — raw version evidence seal

## Result

`seal_raw_version_evidence` binds one ordered pair of immutable version byte
checksums, the comparison identity, approved link revision and every page's
deterministic raw text diff to one SHA-256. It reconstructs page text from each
supplied diff and reruns `diff_approved_pairs`; altered lines, opcodes, page
checksums and evidence digests cannot be accepted as canonical. The seal is
stable when the caller changes only input order. It is a value object, not an
approval or a stored artifact.

## Changed files

- `src/auditmanager/comparison/raw_evidence_seal.py`;
- `tests/integration/comparison/test_raw_evidence_seal.py`;
- `docs/program/tasks/W59-INT-RAW-EVIDENCE-SEAL-PREP-01.md`;
- this report.

## Checks

- Focused W59 comparison suite: **44 passed** in 0.33 s.
- Python compilation, direct task governance `[]`, frozen SHA-256 values,
  owned-file whitespace, `git diff --check` and exact changed-path proof:
  passed.
- No Docker, live DB, network or full gate under R-135.

## Contracts and limitations

No contract, migration, existing comparison module, public boundary, API/UI,
worker, dependency, composition root, global style, `CURRENT_STATE.md` or ref
changed. The caller must supply a pair read under a consistent transaction and
approved SheetLinks; this module checks exact content but cannot prove who
approved the links or whether an artifact was written once. It does not make
AI output canonical evidence or activate W59 runtime.

## Integration instruction

Integrate only the four new paths. The W59 comparison owner should persist raw
page artifacts and their seal with write-once custody, then save an AI summary
under a separate derived identity referencing this exact seal SHA-256. Pair
membership, approval revision and source reads must share a consistent DB
transaction or receive an equivalent revalidation before publication.
