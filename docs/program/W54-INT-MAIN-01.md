# W54-INT-MAIN-01 — W54 + W55a code released as `v0.5.0` (P2 and P3 together)

**Integrator:** `pdf-analysis-29`, 2026-10-13.
**Authority:** the owner's direct poll on 2026-10-13: "publish `23fd729dbb06c642be0588017f6b195305e2e53e`", "release as v0.5.0 as is". `R-102` (one full gate before main), `R-110` (no stand copy while the stand holds test data only).

## Candidate and gate

- **SHA:** `23fd729`, a fast-forward of `origin/main` from `2653dbf` (`v0.4.0`) carrying 97 commits.
- **Migrations:** `0018_norm_custody`, `0019_execution_workers` and `0020_norms_search`.
- **New compose service:** `worker`.
- **Gate:** literal `GATE OK` on this exact SHA (`W55A-INT-GATE-01.md`): battery 4765 passed, foundation 35, Vitest 1941.
- **Version:** `VERSION` 0.5.0, and the 0.5.0 notes describe W54. W55a's «Нормы» ships too. It shows "no current snapshot" until the corpus import (P4); its 0.6.0 notes come with P4.

## Publication

- **Push and deploy.** The remote `main` was re-read before the push (`2653dbf`), and the fast-forward was proven. The exact SHA was pushed, and the remote was read back as `23fd729`. Deploy workflow `deploy-auto` run `38356461757` (06:23:56–06:26:14Z) succeeded, including «Deploy and verify exact commit».
- **Live checks without credentials** on `https://audit.135.106.164.147.sslip.io`:
  - `manual-alpha-check.sh --preflight-only`: PREFLIGHT OK.
  - `/`, `/norms`, `/workers` and `/queue` all answer 307 to `/login?next=…` for a guest.
  - `/api/v1/system/version` and `/api/v1/norms/search` answer 401 without a token.
  - The security headers are present.
- **Tag:** `v0.5.0` (annotated object `b5ebb39`) → `23fd729`.

## Not done here

- **No stand copy** (`R-110`; the stand holds generated test data, `R-109`).
- **`verify-objects` and the D-144 probe** need the copy key, which the owner has not installed. They remain open.
- **The credentialed in-product check** has not run: the worker online in «Исполнители», a run completing through the worker, and «Что нового» showing 0.5.0. `E2E_PC01_*` is absent on this host, so this is the owner's.
- **P4** (the corpus import) and the corpus operations are still ahead: the paid repairs need the owner's proxy key; the build needs about 14 h of night windows.
