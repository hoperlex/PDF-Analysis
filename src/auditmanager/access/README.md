# `access` boundary

Identity/session/object authorization policies and ports. Server-side, fail-closed.

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.

## The access journal

Every `access.*` event is one row of the append-only `audit_event` table, written by `audit.py` in the transaction of
the change it describes: sign-in succeeded, sign-in blocked (a refusal that started a cooling-off period), password
changed, password reset, role granted, role revoked and, since contract 1.36.0, sessions ended. The payload holds
identities, a role, a source word, one boolean and one count and nothing else.

`journal.py` reads it back and writes nothing: `read_access_events` is `listAuthEvents` (newest first, the cursor an
event's own identity) and `last_sign_in_times` is `Account.last_sign_in_at` (the latest `sign_in_succeeded` of each
account named, in one statement). The seam's per-request standing read (`get_account`) does not touch the journal.

`AccountRepository.end_sessions` is `endUserSessions`: it raises `token_epoch` (the mechanism archive, reset and a
role change already use) and journals `access.sessions_ended` in the same transaction. Not oneself; an archived or
missing account is `not_found`. The idempotency key is claimed by the composition root's adapter in the same
transaction (command type `end_user_sessions`, kept by the purge with the other account-side receipts).
