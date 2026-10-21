# W56A-INT-RECORDED-ARTIFACT-PREP-01 — recorded observation bytes

## Result

`build_recorded_observation_artifact` creates canonical
`analysis.text_observations` JSON bytes for a verified AR v2 recorded replay.
The payload uses artifact version `2.0.0`; it carries the saved run and
model-call IDs, registered profile/bundle/content digest, version, recorded
model and provider mode, the request/source-binding/response SHA-256 values,
source artifact references, textless-page selection and PDF page offsets.
Only accepted PDF-grounded proposals receive dense observation ordinals,
source proposal ordinals and proposed severity. Rejected proposals retain
their source ordinals and every grounding failure, alongside malformed count,
salvage and truncation flags. No finding identity or expert decision is
allocated.

The builder checks the caller-supplied opaque IDs, profile registration,
replay/source checksums, request rendering, merge consistency and PDF evidence
spans. It returns immutable bytes and Blob metadata; it does not write a Blob
or construct a StageResult. A focused test parses the resulting document with
the existing `ObservationSet.from_artifact` reader and checks the frozen
registry's `text_analysis` output role/MIME. That establishes the payload's
reader compatibility, not an end-to-end stage or DB acceptance result.

## Changed files

- `src/auditmanager/analysis/profiles/ar_v2/recorded_artifact.py`;
- `tests/integration/analysis/test_ar_v2_recorded_artifact.py`;
- `docs/program/tasks/W56A-INT-RECORDED-ARTIFACT-PREP-01.md`;
- this report.

## Checks

- `nice -n 19 ionice -c3 ../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_recorded_artifact.py` — **13 passed**. Pytest emitted only stale `/tmp/pytest-of-root/garbage-*` cleanup warnings. This includes the OCR-only refusal and existing gate-reader/registry checks.
- Combined artifact, replay, input-binder and response-pipeline tests —
  **34 passed** with the same temporary pytest cleanup warnings.
- Python AST compilation for both new Python files, direct task governance
  `[]`, six frozen SHA-256 values, owned-file whitespace and
  `git diff --check`: passed. The four owned paths were absent at captured
  base `8dac96f7`; another agent's W57a paths in the shared worktree are
  outside this task.
- No Docker, database, network or complete `make gate` under R-135.

## Contracts and limitations

No public contract, migration, registry, provider lock, v1 artifact/gate,
public boundary, executor, journal, StageResult producer, finding publisher,
dependency, composition root, global style, recording or Git ref changed.
The new version is a code-local observation payload format, not a contract
reseal or activation. StageResult compatibility still needs a durable stage
producer and contract/DB tests against its final status and artifact reference.

The replay does not retain raw malformed model elements, so diagnostics
record their count; all grounding failures provided by the response pipeline
are retained. No geometry block index is bound, so block IDs are refused.
`RunId` and `ModelCallId` must come from a durable caller and be stored with
the actual recorded call. Equal bytes are guaranteed for equal complete
inputs, including those identities, not across distinct runs.

## Integration instruction

Integrate only these four new paths. The next stage owner should publish the
returned bytes to Blob with the returned hash/size, persist the model-call
record, create a registry-valid `StageResult` and enforce run idempotency.
Keep diagnostics out of finding publication and use the separate merge stage
for `findings.merged`.
