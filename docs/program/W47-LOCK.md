# `W47-LOCK` — `R-50` and `R-51`, one stream

Brief: `docs/program/dispatch/W47-A2-DISPATCH.md`. Base `45d784f`, branch `agent/w47-lock`,
worktree `/root/w47pass`, lane `gate-w47b`.

This page is written as the work lands, not after it, so a restart loses nothing but the
step in progress.

## 1. `R-50`, the field — the Python half

`IssueTokenResponse` gains `is_default_credential`, required. The value is the account's
own column, read in the statement that authenticated the password and passed through
unchanged:

- `api/security.py`: `IssuedCredential` gains the field, with **no default** — the same
  rule `Subject.token_epoch` and `Subject.display_label` are held to, and for the same
  reason: the value a caller would assume is the permissive one. `TokenSigner.issue` takes
  it as a required keyword and puts it on the returned record and **not into the payload**.
- `bootstrap/adapters.py`: both mint sites read `record.is_default_credential` — the record
  `authenticate` returned, and the record the `change_password` UPDATE returned (which
  clears the column in the same statement, so `false` there is the write's doing).
- `api/routers/auth.py`: both operations answer the port's value.

**Why not in the credential's payload**, which would have been the other shape: the seam
decides the refusal (§2) from the account's row on every guarded request, so a copy in the
payload would be a second and older answer to the question that decides whether a request is
refused. It would also have forced `am2` → `am3` (see `_FORMAT`'s own note), signing every
holder out, and it would have left a pre-deploy credential on a default password claiming
not to be on one.

Tests: `tests/integration/auth/test_the_exchange_over_real_users.py` — a flagged account
reads `true`, a created account reads `false` (the control that makes the first mean
something), and a password change turns it off in the same answer, confirmed by the next
exchange so that the answer is the row and not a constant.

## 2. `R-50`, the reseal — four documents, one commit

`contracts/api/v1/openapi.json`, the regenerated client, `web/openapi/openapi.json` and
`web/FRONTEND_LOCK.json`, in one commit, because a lock that trails its contract by a commit
is a window in which the frontend reads a digest the backend does not serve (`D-18`).

- contract sha256 `78eccd9e…` → `ffcf3c0c…`; mirror verified equal to it before the gate ran.
- **The counts do not move: 17 / 20 / 61, catalog 22.** A property on an existing schema adds
  no schema. `tests/contract/api_v1/test_surface_counts_in_prose.py` reads the reseal's own
  paragraph against the live document and agrees.
- `contracts/domain/v1/**` untouched; `db/migrations/**` untouched, head still
  `0011_document_section`.
