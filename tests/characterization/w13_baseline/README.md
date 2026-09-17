# The pre-FastAPI response baseline

Captured by session `W13-BASE`, wave 13 stage 1, against `85aaa24` (`origin/dev`).

Wave 13 retires the hand-rolled `Router` / `dispatch` / `http.py` / `multipart.py` layer and
rebuilds the twelve operations as typed FastAPI path operations — roughly 1 800 lines of a
four-times-certified surface. This directory is what that rewrite has to be *wrong against*.

**After the rewrite, the FastAPI implementation must reproduce these bytes exactly.**

## Read this before you read a record

**This is a picture of the surface as it was BEFORE the `T-6` reseal.**

Every request in `records/` is **unauthenticated, and is answered**. The contract carried no
`securitySchemes` at all when this was captured (`DEBT_REGISTER.md` D-6), so there is no
401 anywhere here and no operation asks for a token. When wave 13 adds the authorization
dependency of `T-6` in front of all twelve operations, **every operation's unauthenticated
behaviour changes** — and that is not a difference this baseline is claiming should not
happen. It is a difference this baseline has nothing to say about.

Read a record as: *this is what the operation answered when it was allowed to answer.* The
comparison suite drives the journey through whatever satisfies the dependency at the time;
what it pins is the answer, not the absence of a gate in front of it.

**Amended 2026-09-18, `W13-SEAL`, stage 0b.** The contract half of `T-6` has now landed:
`contracts/api/v1/openapi.json` declares one `http`/`bearer` scheme at its root and all
twelve operations declare `401` and `403` (`a5f4001`). The *implementation* half has not —
stage 2 (`W13-API`) writes the dependency — so the records below are unchanged and every
request in them is still unauthenticated and still answered.

The paragraph above therefore stayed true, and it is now the kind of true that has to be
kept rather than assumed: a reader arriving after the seam exists could take 33 records of
answered unauthenticated requests as the surface's *expected* unauthenticated behaviour,
which is exactly backwards. `test_the_baseline_makes_no_authorization_claim` is what keeps
it honest — no record carries an `Authorization` header, none answers `401`, and every one
declares `pre_authorization`. If stage 2 makes the journey authenticate, that test is the
one that must be changed deliberately, and this paragraph with it.

## What is here

| | |
|---|---|
| `journey.py` | the cases, the caller, and the rules that make a response comparable |
| `capture.py` | rewrites `records/`. Run deliberately, never routinely |
| `records/*.json` | one committed record per case: status, **every** header, the body |
| `test_response_baseline.py` | re-drives the journey and requires the records to hold |

Driven the way `tests/e2e/pc01/driver.py` drives it: `Request.build` plus `dispatch`, over a
real `auditmanager.api.app.create_app()`, against real PostgreSQL and real MinIO. Nothing
imports `IngestService`, `execute_run` or `export_run_csv`; everything here is learned from a
response.

## The one path allowed to change

`records/31-streamDocumentVersionContent.storage_credential_refused.json` carries an
`exception` block and is the **only** record that does. **It has been taken.**

As captured, `StoragePermissionDeniedError` emitted `permission_denied` when *our own* S3
credential was refused by the store — the catalog code whose summary describes *"the
**authenticated subject** is not permitted"*. There is no authenticated subject in that
scenario at all (`DEBT_REGISTER.md` D-7). The owner ruled at `R-3` that the reseal gives the
storage case a code of its own, and `W13-SEAL` did so at **`e6d0a6a`**, cited in the record's
`exception.decided_by`:

| | before `e6d0a6a` | after |
|---|---|---|
| status | `403` | `500` — the fault is the server's, and a 4xx blamed the caller |
| `error_code` | `permission_denied` | `dependency_credential_refused` |
| `details` | `aggregate_type`, `required_capability` | `dependency` |
| `retryable` | `false` | `false` |

The class was renamed to `StorageCredentialRefusedError` with its code, and this record's
file name with it — `31-` is unchanged, so "record 31" still finds it.

The record is compared byte for byte against the new expectation exactly as before: being the
permitted exception never made it unwatched, it made the change require a citation.

`test_exactly_one_record_is_marked_as_the_permitted_exception` makes that countable:
the marked set must be exactly this one case. **Every other difference is a failure of the
wave, whatever argument accompanies it.**

## How a response is made comparable, and what that does not hide

A response carries values that cannot repeat: ULID identities, database timestamps, the
correlation id the edge assigns. Each is replaced by a `{{token}}`, and a value earns one in
exactly one of two ways:

1. **the journey already knows it** — it supplied the value, or read it from an earlier
   response in the same journey (`project_uid`, `version_uid`, `run_id`, `finding_uid`, the
   opaque cursor, the decision timestamp the CSV repeats). Substitution is **by exact value**;
2. **it sits under a declared field name and matches a pinned format** — `TIMESTAMP_FIELDS`
   and `GENERATED_ID_FIELDS` in `journey.py` name them one at a time, and
   `TIMESTAMP_FORMAT` / `CORRELATION_FORMAT` are literal patterns written out there. The
   value is checked against its pattern *first*, then replaced by exact value.

**Nothing is substituted by scanning a body for things that look generated.** So a changed
key order, a changed separator, a dropped field, a renamed property, a different message, a
moved constraint name, a different status or a missing header is a byte difference and the
comparison reddens. The token list in each record is the complete, enumerated statement of
what was *not* pinned.

Two values get a rule rather than a literal, and both are stated in the record:

- **`Content-Length`** is tokenised unconditionally. It is a function of the body, the body
  is compared byte for byte, and the comparison separately asserts
  `Content-Length == str(len(body))`. Pinning the number as well would only restate the body
  comparison, and would redden for a token whose replacement is a different length.
- **`X-Correlation-Id`, when the request supplies none.** It is checked against the pinned
  `^cid-[0-9a-f]{32}$` before being tokenised. When a request *does* supply one, the value is
  a literal in the record and the echo is pinned exactly
  (`07-getRunStatus.correlation_supplied`).

Every expectation here is a literal. Not one is computed from the module it checks —
`OPERATING_CONSTRAINTS.md` §12 records three instances of that failure in this programme.

## Fixtures

No bytes were added to `fixtures/synthetic/ar/**` or `fixtures/validation/PC-02/**`; both are
frozen evidence. The four negative-envelope fixtures are **read** from the AR corpus, and the
two size-boundary bodies are built in process by `journey.sized_multipart` — which is the tool
`tests/integration/ingest/test_size_guard_boundary.py` already argues for, since every oversize
fixture in the repository is over *both* guards and so never reaches the envelope's.

The streamed document body is recorded as `fixtures/synthetic/ar/ar_baseline.pdf` with its
pinned sha256 and length rather than copied in, so this directory holds no duplicate of frozen
evidence.

## Re-capturing

`capture.py` rewrites every record. It is committed so the baseline can be re-measured
deliberately and so a reader can see exactly how it was produced. **Re-running it against a
changed implementation makes the comparison vacuous** — that is the one thing this directory
exists to prevent. If a record has to move, move it in a commit that says which decision moved
it and cites the commit that took that decision.

## Lifetime

This directory is wave 13's safety net and nothing else. It comes out when the wave ends and
`W13-CONF`'s conformance gate plus the migrated suites are the standing guard.
