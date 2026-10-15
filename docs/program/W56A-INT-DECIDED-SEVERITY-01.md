# W56A-INT-DECIDED-SEVERITY-01 — expert decided severity

## Result

An expert `accept` can append `severity` to the 0022 decision ledger. The
ledger rejects severity on any other event before an idempotency claim and
requires a canonical observation with a non-null proposed severity for this
optional v2 path. Legacy decisions without severity keep their original
payload fingerprint and omit the optional wire property. The independent
Python fold mirrors the database view: a comment preserves decided severity;
reject or revoke clears it. Decision history, journal, finding list/detail
and adapter responses carry the stored value without substituting the model
proposal.

## Checks

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/decisions/test_v2_severity_semantics.py`: **7 passed**.
- Python compilation, direct task governance (`[]`) and `git diff --check`:
  passed.
- The three PostgreSQL tests in `test_v2_severity_db.py` were added but could
  not run: this worktree has no `DATABASE_URL`; the integration harness fails
  setup rather than skipping.
- Full `make gate` deferred under R-135.

## Contracts and limits

No contract, migration, provider lock, root dependency or composition root
changed. The optional 0022 fields and CHECKs were already sealed. The
non-null proposal plus canonical identity is a fail-closed current guard for
the v2 decision path; it is not proof of an activated v2 profile. The later
runtime activation still needs explicit profile authorization and publication
of canonical identities. Database view/fold equivalence and SQL CHECK
translation must be confirmed on isolated PostgreSQL.

## Integration instruction

Run `tests/integration/decisions/test_v2_severity_db.py` against an isolated
database migrated through 0022. Then run the CSV severity integration test
and wire the recorded-only v2 publisher so it assigns the canonical
observation in the same publication transaction. Keep legacy requests without
severity byte-compatible.

## Ownership proof

Only the decision ledger, projection, journal, decision and finding mappers
in `bootstrap/adapters.py`, two focused tests, this report and its task file
were changed. `contracts/**`, migrations, exports, public API routers,
provider lock, root dependency/lock files, composition root, global styles,
stand and Git refs were untouched by this task.
