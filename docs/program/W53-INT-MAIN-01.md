# W53-INT-MAIN-01 — W53 accepted and released as `v0.4.0`

**Integrator:** `pdf-analysis-62`, 2026-10-12. **Authority:** `R-85`, `R-86`, `R-87`
(`OWNER_RULINGS_2026-09-17.md` §3.29). The owner directly instructed publication of the exact
SHA `2653dbf49e9f37fa891dd6e47b396650a215542d` to `origin/main` by poll, and waived the
one-off stand copy for this publication only. The copy-before-every-migration rule applies
from W54.

## Candidate

`2653dbf` is `origin/dev` after W53-CLOSE (`3aeb75a`) plus the 0.4.0 release commit:
`VERSION`, `release-notes/0.4.0.json`, `R-85`…`R-87`, `D-153`…`D-155`, and two test pins that
now read `VERSION`. It reached `origin/main` as a fast-forward from `21eba6e`, carrying 107
commits and migration `0017_execution_queue`.

## Checks (short route, `R-87`)

- **Before publication:**
  - W53-CLOSE light acceptance (`W53-CLOSE-INT.md` §3);
  - on the release commit, `pytest tests/contract` without the three environmental `cp00`/bootstrap modules: 554 passed;
  - release web tests and guards: 99 passed;
  - the real loader `read_notes` parses 0.2.0, 0.3.0 and 0.4.0.
- **Deployment:** GitHub workflow `deploy-auto` run `38219064192` on `2653dbf` succeeded,
  including the step «Deploy and verify exact commit». That step runs `verify-deployed.sh`.
- **Live check without credentials**, on `https://audit.135.106.164.147.sslip.io`:
  - `manual-alpha-check.sh --preflight-only`: PREFLIGHT OK (five PDFs, `/` → 307 `/login`, `/login` 200, unauthenticated API 401);
  - `/login` carries `nosniff`, `X-Frame-Options: DENY`, `frame-ancestors 'none'` and `Referrer-Policy: same-origin`;
  - a cross-site POST to `/bff/v1/session` answers 303 `/login?refusal=validation`.
- **Not run:**
  - the full `make gate` (waived by `R-87`);
  - the credentialed automated acceptance: `E2E_PC01_*` is absent on this host. The owner's
    in-product check of «Журнал выполнения», «Очередь» and «Что нового 0.4.0» is the open
    manual item.
  - HSTS is absent and the stand answers HTTP/2: TLS ends at an outer terminator, which
    matches `D-144`.

## Measured identities

| Field | Value |
|---|---|
| API `build_id` | `be7bf8dae6d63d63c` (`compute_build_id()` on this tree) |
| Prompt bundle SHA-256 | `934705c04a7189f18161ea34e9b4922374dff9fec3c6bb48224398a5a468d0ba` |
| Profile bundle SHA-256 | `30053740f569ec84683f65dbd04ef7b0b1fd0a8b24ecdfb287e76533158d0553` |
| Migration head | `0017_execution_queue` |
| Tag | `v0.4.0` (annotated, object `31e69cc`) → `2653dbf` |

`web_build_id` depends on the stand's public environment, so it was not measured here.
