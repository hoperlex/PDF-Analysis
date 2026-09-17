# `W13-API` dispatch prompt — the twelve operations, natively under FastAPI

Stage 2 of wave 13, and the largest single piece of work in this road. **Starts only after
`W13-SEAL` (stage 0b) has landed**, because the reseal changes `components.schemas.ErrorCode`
— measured: that schema enumerates the codes and its own description says it is *"exactly the
key set of `contracts/domain/v1/error-codes.json`"*, so a twenty-first code moves it and your
models with it.

---

## What you are for

`ADR-0002`, `TECHNOLOGY_BASELINE.md`, `ARCHITECTURE_BIBLE.md` P-05 and
`PROTOTYPE_PROFILE.md` §2 have named FastAPI since the bootstrap. The lock never carried it,
`B6` wrote ~100 stdlib lines instead, and `api/README.md` described that absence as a
deliberate decision until the owner corrected it. **A lane-level pin set cannot overrule an
ADR.** You build what the architecture has said all along.

Measured at `6c4b236`: `wc -l src/auditmanager/api/routers/*.py src/auditmanager/api/schemas/*.py`
= **2 511 lines**, of which **639 are kept** (`ports.py` 233, `errors.py` 196, the two
`__init__.py` 114 + 96) and **1 872 are replaced**.

**The `Port` protocols are why this is a transport change and not a rewrite of the
application.** `routers/ports.py` declares `ProjectPort`, `DocumentPort`, `RunPort`,
`FindingPort`, `DecisionPort`, `CsvExportPort`, plus the `UploadedDocument` and
`AppendedDecision` result protocols. **The handlers keep calling exactly the same ports.**
Nothing under `src/auditmanager/{ingest,runs,findings,decisions,exports,storage,analysis}/**`
changes, and if you find yourself wanting to change one, stop: that is a finding, not a step.

## What you build

- **Pydantic models for the 43 `components.schemas`**, named exactly as the contract's keys,
  with `extra="forbid"` wherever the contract refuses unknown fields. The response baseline
  pins `additionalProperties` refusals on **all four** write bodies, including the multipart
  one where it is an undeclared *part*.
- **Twelve typed path operations** mounted at `/api/v1`, carrying the contract's
  `operationId`, tags, parameters, status codes and response headers. Twelve, not thirteen —
  `web/tests/contract/openapi-drift.contract.test.ts` counts them.
- **The authorization dependency** in front of all twelve, raising `authentication_required`,
  with the alpha's static-token implementation behind it. Nothing about roles or subjects.
- **The health plane on its own port**, outside `/api/v1` and outside the authorized surface,
  so a health check needs no credential.
- **`X-Correlation-Id`** assigned when absent and echoed when supplied; the body cap; the two
  size guards kept distinct; the Range response; the CSV's exact bytes and headers.

## The single highest-risk item, and it is not the models

**Every failure is rendered by `envelope_response` and nothing else.**

FastAPI's own `RequestValidationError` and `HTTPException` bodies must never reach a client.
Exception handlers map them onto the catalog, **preserving the constraint names the
certifications pin** — `pdf_magic_bytes`, `byte_size <= 26214400`, `not_encrypted`,
`every_page_has_extractable_text`, the page-count bound, `plain_base_name`, `non_empty`,
`char_length <= 255`.

Four certifications and the response baseline assert *which rule refused*, not merely that
something did. A FastAPI default body that leaks through is not a cosmetic difference: it is
a criterion-10 regression wearing a 422.

## The response baseline is your specification

`tests/characterization/w13_baseline/` holds **33 records** captured from the certified
implementation by `W13-BASE`. **Your implementation must reproduce those bytes exactly.**

**Exactly one record may differ**, `records/31-streamDocumentVersionContent.storage_permission_denied.json`,
and only by the decision `DEBT_REGISTER.md` D-7 records — which `W13-SEAL` has now made. A
test requires the marked set to be exactly one. **Every other difference is a failure of this
stage, whatever argument accompanies it.** That sentence was written before the corpus
existed, deliberately, because a safety net with an unnamed exception is one somebody talks
past at the end of a long wave.

Authorization is the known exception to the baseline's *scope*, not to its bytes: every
request in it is unauthenticated and answered, because it predates `T-6`. The corpus README
says so. Do not let that become a licence for a second undeclared difference.

### One finding from `W13-BASE` that will bite a Pydantic model

**`startRun` with the same idempotency key and a payload differing only by `provider_mode` is
a replay, not a conflict** — 202 with the original run, byte for byte. At the command layer
a different payload raises `idempotency_key_reuse`; at the transport the property is
normalised away before the fingerprint, because `RunAdapter.start_run` refuses a disagreeing
mode and otherwise forwards the configured one.

So a model that defaults `provider_mode` differently, or forwards `None` where the current
parser forwards the configured value, **moves a request between baseline cases `04`, `05` and
`05b`.** All three are pinned.

## The 21 coupled test files

`grep -rln "api.routers\|Request.build" tests/` = 21. They split into two kinds and are not
treated the same way:

- **`tests/e2e/pc01/driver.py` is cheap.** Every call funnels through one `request()` method,
  so the driver becomes an ASGI test client in one place.
- **`tests/integration/api/*` is not.** It tests helpers like `require_idempotency_key` and
  `resolve_correlation_id` directly, and those helpers change shape. **Those tests are
  rewritten, not re-pointed**, and each must still assert *which rule refused*.

`httpx` 0.28.1 is pinned in the test group for exactly this — `starlette.testclient` imports
it, and the environment carried `httpx2`, a different distribution, until `W13-PIN`.

## Discipline

**Every behaviour you keep needs a test that reddens without it.** The baseline gives you most
of that for free; where it does not, write the guard.

**Pin expected values as literals.** `OPERATING_CONSTRAINTS.md` §12 records three instances of
the opposite failing here — a test importing the constant it checks, a test deriving its input
from one, and a grep matching one of two spellings.

`make mutation-copy MUT=/root/w13api-mut`, and **baseline the unmutated copy before trusting
any red**.

**Commit, then gate.** `make gate` refuses a checkout that changes *during* the run.

## Constraints

You own `src/auditmanager/api/**`, the 21 coupled test files, and your review. You do **not**
touch `contracts/**` (`W13-SEAL` owns it this wave), the six ports' *callers* under the other
`src/` packages, or `web/**`. `W13-CONF` is building the conformance gate beside you and owns
`tests/contract/api_v1/**`.

No new dependency beyond what `W13-PIN` landed. No tag, no push, no merge to `main`.

**Check every premise here against the tree.** Twelve stale premises are on record, most in
briefs written by the integrator who wrote this one — one of them last week invented a design
dilemma that did not exist, and another said "26 MiB" of a 25 MiB limit.

## Report

`docs/program/reviews/W13-API.md`: HEAD on arrival; the baseline's 33 records reproduced, with
the one permitted difference named and its deciding commit cited; how FastAPI's own error
bodies are prevented from reaching a client, and the test that proves it; which of the 21 test
files were re-pointed and which rewritten, and why each; anything false in this brief; elapsed
wall-clock.
