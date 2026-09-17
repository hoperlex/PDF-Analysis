# W15-AUTH — the credential the browser never sent

**Session** `W15-AUTH` · **branch** `agent/w15-auth` · **worktree** `/root/w15auth`
**HEAD on arrival** `700022f` (`merge(W14-PKG): the image, the single origin and the wipe`),
the tip of `origin/dev` at provisioning.

This file is opened before the first edit, per the dispatch, and filled as the work lands.

## 0. The blocker, as measured on arrival

- `grep -rn "Authorization\|Bearer\|credentials" web/src` → no match. The frontend sends
  no credential on any of the twelve operations.
- `web/src/shared/api/transport.ts` sets exactly `Accept`, `Idempotency-Key`,
  `X-Correlation-Id` and (for JSON bodies) `Content-Type`.
- Against wave 14's running stack, reused rather than rebuilt:
  `curl http://127.0.0.1:31480/api/v1/projects` → **401**, body
  `{"error_code": "authentication_required", ...}`.
- Baseline before any edit: `npx vitest run` in `web/` → **35 files, 440 passed**.

Sections 1–8 follow as the work is done.
