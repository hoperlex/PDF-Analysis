# CMP-C4-RUNTIME-SEAMS-01 — shared cancellation seam

The Stage AI runtime needs to cancel a job in the same transaction as its full chain. `cancel_in_session` delegates to the existing shared command, role, edge and idempotency logic through `_steer_in_session`; the standalone `cancel` remains its session-owning wrapper. The internal `cancel_stage_review_ai` receipt is classified for product recovery.

No contract, migration or provider-call policy changed. Focused shared AI command checks and the Stage AI lane's recorded cancel replay provide implementation evidence; full acceptance remains deferred by the owner.

Proven provider failures now retain bounded dispatch metadata on `CallFailed`: class, auth/quota/rate-limit/request kind, HTTP status and retry-after. HTTP402 and known insufficient-quota429 envelopes are definite refusals;401/403 are auth. Ambiguous5xx outcomes remain `OutcomeUnknown`, never automatically resent. No raw body or credential is added to an envelope/journal. Checks:54 shared state edges,64 caller,29 local fake-HTTP adapter and5 refusal-metadata cases passed.
