# W56A-INT-RECORDED-RESPONSE-BRIDGE-01 — offline response bridge

## Result

`replay_recorded_response` joins the verified AR v2 input binder, the concrete
offline `RecordedAdapter` and the existing `finish_response` step. It requires
caller-supplied saved request, fixture model and source-binding identities,
checks them before the adapter read, and recomputes the source-binding digest
from the bound artifact references and request key. The concrete adapter
itself checks the recording's declared request and model. Successful replay
returns an immutable typed result with request, source-binding and response
SHA-256 values and the full `FinishedV2Response`: PDF-only accepted evidence,
rejected quote diagnostics and dense merge preparation.

The bridge invokes `complete` exactly once. A missing or mismatched recording
propagates the existing typed refusal without a fallback. It does not create
or update a call journal, StageResult, finding, run state or database row.

## Changed files

- `src/auditmanager/analysis/profiles/ar_v2/recorded_response.py`;
- `tests/integration/analysis/test_ar_v2_recorded_response.py`;
- `docs/program/tasks/W56A-INT-RECORDED-RESPONSE-BRIDGE-01.md`;
- this report.

## Checks

- `nice -n 19 ionice -c3 ../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_recorded_response.py` — **7 passed**. Pytest emitted only old `/tmp/pytest-of-root/garbage-*` cleanup warnings.
- Combined recorded response, recorded input and response-pipeline suite —
  **21 passed** with the same temporary pytest cleanup warnings.
- Python AST compilation for both new Python files, six frozen SHA-256 checks,
  direct task governance `[]`, owned-file whitespace and `git diff --check`:
  passed. All four owned paths were absent from the captured base; other
  agents' new paths in the shared worktree are outside this task.
- No Docker, database, network or complete `make gate` under R-135.

## Contracts and limitations

No public contract, migration, provider lock, existing adapter/binder/finisher,
run executor, call journal, publisher, root dependency, composition root,
global style, historical recording or Git ref is changed. Active v1 behavior
is unchanged and recorded AR v2 runtime remains off.

`RecordedV2Input` must come from the verified saved-run source reader. This
bridge compares the caller's expected identities but cannot independently
authenticate the saved execution context or persist them. The caller must
retain all three checksums, diagnostic partition and call provenance durably,
enforce run-level idempotency and keep OCR non-citable. The present bridge
does not add geometry block IDs or publish findings.

## Integration instruction

Integrate only the four new task paths. A later owned executor task should
source expected identities from its durable execution context, call this
bridge once with a concrete `RecordedAdapter`, persist the response and
diagnostics with the call/stage record, then invoke separately owned
publication logic. No live model or price is inferred from `fixture/` IDs.
