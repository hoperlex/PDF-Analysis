# W56A-INT-RECORDING-MODEL-BIND-01 — result

`RecordedAdapter` now compares the recording's declared model ID with the
model ID of the exact request whose SHA-256 selected the file. A tampered or
missing value yields `analysis_input_invalid` with
`recording_model_mismatch`; no response is returned and no live fallback
exists. Existing recording bytes were not changed.

## Changed files

- `src/auditmanager/analysis/text/recorded.py` — model-identity guard;
- `tests/integration/analysis_text/test_provider_modes.py` — extends the
  adapter's nonretryable corpus-refusal enumeration;
- this report and `tasks/W56A-INT-RECORDING-MODEL-BIND-01.md`.

## Checks

- Recorded adapter, AR v2 request and offline replay: **39 passed**. Five
  warnings concern cleanup of stale `/tmp/pytest-of-root` directories.
- Python compilation and whitespace: pass.
- Direct governance, frozen hashes and exact path proof: recorded at integration.
- No DB, provider or complete `make gate` under R-135.

## Contracts and limits

No API/error contract, migration, provider lock, root dependency,
composition root, global style, run executor, historical recording or corpus
source changed. The guard verifies a recording's model field against its
request; it does not establish the live gateway's model identity or price.
The v2 executor still has no active recorded request/artifact path. Revert the
guard and focused test change to roll back before activation.
