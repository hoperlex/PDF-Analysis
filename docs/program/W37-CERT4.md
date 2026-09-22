# W37-CERT4 — PA-01 re-certified at `b0e5c07`

- **Task:** `W37-CERT4`. Re-certify `PA-01` against the tree at `b0e5c07`.
- **Record:** `artifacts/checkpoints/PA-01/certification-b0e5c07.json`, superseding `certification-ac7c348.json`.
- **Worktree:** `/root/w37cert4`, branch `agent/w37-cert4`, head on arrival `b0e5c07`.
- **Gate lane:** `gate-w37b` — POSTGRES_PORT 56160, S3_API_PORT 59760, S3_CONSOLE_PORT 59761, POSTGRES_DB `audit_w37b`, S3_BUCKET `auditmanager-gate-w37b`.
- **Logs:** `/root/w37-logs/cert4-*`.
- **This session writes two files and no code.** It repairs nothing it finds.

## Status

OPEN — this file was committed before the first measurement, per the dispatch, so that a
session that dies leaves its evidence. Sections below are filled as each verdict is produced.

## 1. The answer

*pending*

## 2. Stacks driven

*pending*

## 3. The ten verdicts

### Criterion 1 — `deploy.sh` from a clean clone + the served schema conforms

> *"`deploy.sh` brings the stack up from a clean clone on a machine that has never run it, and
> the schema the running app serves conforms to the frozen `contracts/api/v1/openapi.json` —
> the same check the gate runs, re-run against the deployed process rather than against a
> build artifact"* — `ALPHA_ROADMAP.md` §5, read from the file.

**Second clause: HOLDS.** The schema the *running process* serves, fetched over HTTP from
`http://127.0.0.1:31500/api/v1/openapi.json` (68402 bytes), compared against
`contracts/api/v1/openapi.json` by the gate's own engine
(`tests/contract/api_v1/openapi_conformance.py`, `surface()` then `differences()`):
**0 differences**, 16 operations on both sides, 13 paths and 48 schemas on both sides.

The two documents are **not** byte-identical and cannot be — `infra/deploy/verify-deployed.sh`
explains at length why the served document is generated and the frozen one is written by hand.
Canonical digests: served `b65177b5…`, frozen `de213e7e…`. Conformance is the declared
normalization, not equality.

**Anti-vacuity, against the served document itself** — three plants, three reds, one green
control:

| plant | differences |
|---|---|
| delete `/auth/token` from the served document | 1 |
| `POST /projects` response `201` → `299` | 2 |
| an extra key on schema `AnalysisProfileId` | 1 |
| *control: unmutated* | **0** |

So the comparison behind this clause can fail, and does, on a semantic change to the served
document. `make mutation-copy` was not needed: the subject here is a JSON document fetched over
HTTP, and mutating the fetched copy is the stronger test — it mutates what the *process served*,
not what the tree contains.

**First clause: not driven as the criterion writes it.** See the verdict below.

**Verdict: `cannot be established, because R-1`.** No machine here has never run this stack.
`deploy.sh` can be driven, and was (below), but the clause says *a machine that has never run
it*, and this host has run it since wave 14. `cannot be established` is not a synonym for
`fails`, and the half that could be measured holds.

### Criterion 2 — TLS, and a request carrying no token refused **by the application**

> *"the browser reaches the app over TLS, and a request carrying no token is refused with
> `authentication_required` **from the application**, not by the proxy — shown for an operation
> of each kind, so the dependency is proved to be in front of all twelve rather than in front of
> the one that was tried"* — `ALPHA_ROADMAP.md` §5.

**First clause — TLS: NOT ESTABLISHED.** Measured inside the running proxy container, not from
the tree: `docker exec auditmanager-w19a-proxy-1` shows `/etc/nginx/conf.d/` holding exactly one
file, `default.conf`, with exactly one listen directive, `listen 8080;`. `docker port` publishes
`8080/tcp -> 127.0.0.1:31500`. There is an **inert** TLS path in the tree —
`infra/deploy/proxy/tls-server.conf` (`listen 8443 ssl`), `compose.tls.yml`, `enable-tls.sh` —
and it is not loaded by the running container. There is no host name and no certificate. `R-1`.

**Second clause — HOLDS, and this is the verdict that moved.** The previous record
(`ac7c348`) recorded this clause as holding *with a named qualification*, `W30CERT3-1`: the
published origin carried a second, credential-free path to all fifteen operations through
`/bff/v1`. **That is repaired at `b0e5c07`, measured rather than inherited.**

All **sixteen** declared operations driven over HTTP through the published origin
`http://127.0.0.1:31500`, on **both** surfaces, in six credential conditions each
(`/root/w37-logs/cert4-criterion2.json`, `/root/w37-logs/cert4-auth.log`):

| condition | result over the 15 guarded operations |
|---|---|
| `/api/v1`, no `Authorization` header | **15/15** `401 authentication_required` |
| `/api/v1`, a forged `am1.` credential with a wrong tag | **15/15** `401 authentication_required` |
| `/api/v1`, a credential that is not even the right shape | **15/15** `401 authentication_required` |
| `/bff/v1`, no session cookie | **15/15** `401 authentication_required` |
| `/bff/v1`, a cookie naming no live session | **15/15** `401 authentication_required` |
| *positive control:* `/api/v1` with a credential minted by the stand | **15/15** reached the operation (200 / 404 / 422, never 401) |

The positive control is what makes the other five rows mean something: the same fifteen requests,
same paths, same bodies, differing only in the credential, are **not** refused. So the 401 is the
seam and not a routing miss.

`issueToken` — the one operation in `UNAUTHENTICATED_OPERATIONS`, and the one operation the
contract publishes with an empty security requirement — answers `200` without a credential on
`/api/v1`, which is the register working. On `/bff/v1` it answers `404 not_found`: the browser
tier refuses to forward the exchange at all, so a minted token cannot be returned to a page.

**Refused by the application, not by the proxy — proved by removing the proxy.** Both readings
below bypass nginx entirely, from inside the containers:

- `docker exec auditmanager-w19a-api-1` → `http://127.0.0.1:8000/projects` → `401`,
  `{"error_code": "authentication_required"}` in a full `ErrorEnvelope`.
- `docker exec auditmanager-w19a-web-1` → `http://127.0.0.1:3000/bff/v1/projects` → `401`,
  `authentication_required`, `correlation_id` `web-…`.

**Verdict: `cannot be established, because R-1`** — unchanged, and for the first clause only.
There is no TLS, no host and no certificate on this host. The second clause is stronger than it
has ever been recorded and is stated above in full.

## 4. Findings

*pending*

## 5. Spend

*pending*

## 6. False premises in the dispatch brief

*pending*

## 7. Gate

*pending*
