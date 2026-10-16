# W56B-INT-TEXT-BYTES-PREP-01 — supplied TEXT source bytes

Base: `origin/dev` candidate 41 at
`6f1307412c94de45e67ffdeba71506dc5a0aa8fb`.

`check_supplied_text_window_bytes` verifies a supplied canonical
`prepared.text_layer` JSON payload against its Blob reference's exact SHA-256,
size, role and media type. It refuses a foreign version, malformed source
metadata, page coordinates or disagreement with the supplied frozen page
count. It then invokes the existing complete page partition under an explicit
document-text character ceiling, preserving Unicode offsets and blank pages.

## Checks

- Focused source-byte, chunk and reply-cohort suites: **35 passed**.
- Python compilation, direct task governance, frozen SHA-256 readback,
  whitespace and exact four-path proof: passed at handoff.
- No Docker, PostgreSQL, S3, proxy, paid call or complete gate was run.

## Contracts and limits

No contract, migration, registry, provider, API/UI, composition, dependency or
served runtime change. This function verifies **supplied** values only. A
future caller must prove the `ArtifactRef` came from this Run's successful
saved StageResult, bound the Blob read, retain current Attempt authority,
derive the character ceiling from an approved budget and journal each call.
The function does not select a model, calculate cost or publish evidence.

Rollback is removal of this additive module/test before wiring; no data
migration or flag is needed.

Only these four paths change:

- `src/auditmanager/analysis/text/source_bytes.py`;
- `tests/integration/analysis_text/test_source_bytes.py`;
- `docs/program/tasks/W56B-INT-TEXT-BYTES-PREP-01.md`;
- this report.

The integrator can cherry-pick the exact local commit after checking frozen
surfaces and direct handoff. Real saved Run/Attempt and Blob acceptance is
still required before W56b stage activation.
