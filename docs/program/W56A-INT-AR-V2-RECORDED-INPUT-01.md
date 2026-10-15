# W56A-INT-AR-V2-RECORDED-INPUT-01 — recorded input binding

## Result

`prepare_recorded_v2_input` is a pure, additive seam between the existing
artifact reader, W55b OCR selector and AR v2 offline request builder. It
requires the persisted version UID, textless-page list, two independently
sourced `ArtifactRef` values and the actual SHA-256 values returned by
`read_artifact`. It checks artifact role, version identity, canonical bytes,
read digest and declared byte size before using either document. Its result
retains the PDF text-layer reference, exact page offsets, selected uncitable
OCR context, recognised-artifact reference, request SHA-256 and a separate
source-binding SHA-256 over the version UID, artifact references, textless-page
selection and request SHA-256.

Only OCR TEXT on stored textless pages reaches the request. OCR on a textful
page and portal IMAGE descriptions stay out. The same sources yield the same
request and binding keys. Changed rendered PDF or OCR text changes the request
key. Changed unrendered artifact metadata can leave the request key unchanged
but changes the source-binding key; the runtime must retain both.
Multiple OCR TEXT blocks on one page produce the explicit
`multiple_text_blocks_for_page` refusal. The present request renderer accepts
only one OCR context item per page; a later owner must review a lossless
representation before enabling that input shape.

## Changed files

- `src/auditmanager/analysis/profiles/ar_v2/recorded_input.py`;
- `tests/integration/analysis/test_ar_v2_recorded_input.py`;
- this report and `tasks/W56A-INT-AR-V2-RECORDED-INPUT-01.md`.

## Checks

- Python compilation: passed for both new Python files.
- Direct task governance: `[]`; six frozen SHA-256 values match the task;
  whitespace and `git diff --check`: passed.
- Exact owned-path proof: these four paths were absent from frozen HEAD and are
  the only paths this task added. Other agents have separate untracked files
  in the shared worktree; none is a path owned by this task.
- `nice -n 19 ionice -c3 ../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_recorded_input.py` — **10 passed** in the integrator's focused run.
- Docker, database, network and complete `make gate`: not run under R-135.

## Contracts and limitations

No public contract, migration, provider lock, existing selector/request/adapter,
run executor, finding publisher, dependency, composition root, global style,
historical recording, corpus source or Git ref changed. Existing v1 behavior
is unchanged; no AR v2 runtime stage is activated.

The caller must obtain `ArtifactRef` from the persisted stage and
`read_sha256` from verified Blob reads. This pure binder cannot authenticate
a caller-created reference, verify the recognised artifact's separate
`results_sha256` against source markdown bytes, or prove a model-call ledger
exists. It cannot publish findings or apply a run-level idempotency rule.

## Integration instruction

Integrate only the four task-owned new paths. A later executor owner should
source the version and artifact references independently, pass the returned
request and page provenance into durable recorded call/stage wiring, and
persist both request and source-binding checksums before invoking
`RecordedAdapter`. Keep OCR
non-citable and resolve the multi-block representation before claiming broad
portal coverage. Rollback before activation is removal of this module.
