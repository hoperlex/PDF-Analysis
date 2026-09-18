# The pre-FastAPI response baseline

Captured by session `W13-BASE`, wave 13 stage 1, against `85aaa24` (`origin/dev`).

Wave 13 retires the hand-rolled `Router` / `dispatch` / `http.py` / `multipart.py` layer and
rebuilds the twelve operations as typed FastAPI path operations — roughly 1 800 lines of a
four-times-certified surface. This directory is what that rewrite has to be *wrong against*.

**After the rewrite, the FastAPI implementation must reproduce these bytes exactly.**

## Amended 2026-09-18 by `W18-SEAL`, under owner ruling `R-5`

**Thirty-six records, not thirty-three, and five of them carry a second debt.**

Three cases were **added** -- `32-listDocuments.success`, `33-listVersions.success` and
`34-listRuns.success`. Adding an operation adds a case and a record; it changes none, so
these three carry no exception block and need none. `FIFTEEN_OPERATIONS` in
`test_response_baseline.py` moved from twelve to fifteen with them.

Five records **changed**, and they are the five already marked for `D-19`: every body
rendering a `RunStatus` now carries `cost_micros`, `cost_basis` and `model_call_count`,
the three properties `R-5` added so that `PA-01` criterion 4's cost clause can be
satisfied at all. Their `exception.debt` is now `["D-19", "D-21"]` -- a list, on all six
marked records including record 31, because a record can be moved twice and a comma inside
a sentence is not a countable thing.

**The re-capture was checked for vacuity, and here is the measurement.** `capture.py`
rewrites all thirty-six files. Comparing the directory before and after, key by key:
five records differ under `response` **and** `exception`, record 31 differs under
`exception` alone (the list format, not its content), three are new, and the remaining
twenty-seven are byte-identical. The five response diffs are three added keys each and
nothing else -- no status moved, no header moved, no existing property changed value.

A note worth keeping, because it is a real measurement rather than a design choice: the
baseline's `recorded` run reports `cost_micros: 34400` with `cost_basis: "estimated"` over
one model call. Estimated because a replayed call reports no cost of its own, so the
figure is derived -- which is exactly what the aggregate basis rule is for.

## Read this before you read a record

**These records are of the authorized surface. Amended 2026-09-18 by `W13-API`, stage 2,
in the commit that put the `T-6` dependency in front of the twelve operations.**

Every request in `records/` now presents `Authorization: Bearer w13-baseline-static-token`,
which is the credential `journey.build_apps()` configures, and is answered. None of them
pins `401` or `403`: no case here omits the credential and no case here exercises a
*caller's rights*, so an authorization answer in this corpus would mean the journey had
stopped doing what it says it does. `test_the_baseline_records_the_authenticated_era` is the
guard, and `test_the_authorization_era_check_can_fail` plants four records to show it can
reject one. **The seam's own refusals are asserted where they belong** —
`tests/integration/api/test_authorization.py` drives requests with no credential, with a
malformed one and with the wrong one.

**What this amendment did and did not change.** It added the `Authorization` header to each
record's `request.headers`, replaced the `pre_authorization` sentence and updated
`captured_through`. It changed **nothing** under `response` in any of the 33 records as they then stood: the
recapture that produced this state was run against the FastAPI implementation and the diff
is exactly three request-side lines per file. The status, every header and every body byte
are what `W13-BASE` committed — which is the claim this whole directory exists to support,
and it survives.

**Three earlier eras of this paragraph, kept so the sequence is readable.** `W13-BASE`
captured against a contract with no `securitySchemes` at all (`DEBT_REGISTER.md` D-6): every
request was unauthenticated and answered, and the corpus was explicitly *silent* about
authorization rather than asserting it. `W13-SEAL` landed the contract half of `T-6`
(`a5f4001`) and added `test_the_baseline_makes_no_authorization_claim` to keep that silence
true rather than merely old, noting that *"if stage 2 makes the journey authenticate, that
test is the one that must be changed deliberately, and this paragraph with it."* This is
that change, made in one commit with the test, as instructed.

## What is here

| | |
|---|---|
| `journey.py` | the cases, the caller, and the rules that make a response comparable |
| `capture.py` | rewrites `records/`. Run deliberately, never routinely |
| `records/*.json` | one committed record per case: status, **every** header, the body |
| `test_response_baseline.py` | re-drives the journey and requires the records to hold |

Driven the way `tests/e2e/pc01/driver.py` drives it — which, since `T-1`, is a
`starlette.testclient.TestClient` over a real `auditmanager.api.app.create_asgi_app()`,
against real PostgreSQL and real MinIO. `journey.Caller` is the one place that knows how the
transport is reached, which is why the rewrite touched one class in this directory and
nothing else. Nothing imports `IngestService`, `execute_run` or `export_run_csv`; everything
here is learned from a response.

## The paths allowed to change

**Two, as of `W17-VIEW` on 2026-09-18.** Record 31 (`D-7`) and the five records carrying a
`RunStatus` body (`D-19`). `test_exactly_the_named_records_are_marked_as_permitted_exceptions`
names them one at a time with the debt that moved each, and
`PERMITTED_EXCEPTIONS` in that file is the countable list.

### `D-19` — records 03, 04, 05, 06 and 07

**Moved at `aae0209`**, cited in each record's `exception.decided_by`. `W15-RUN` drove the
product through a browser and read *"Published findings: not reported"* and *"Started —
Finished —"* on a run that had published three findings, and *"Created 23:07:31 / Terminal
at 23:07:31"* on a run that took 9.9 seconds.

| | before `aae0209` | after |
|---|---|---|
| `StageState.started_at` / `finished_at` | absent on every stage | the real per-stage spans |
| `published_finding_count` | absent | the number of findings the same run serves |
| `diagnostic_observation_count` | absent | the ungrounded items the gate rejected |
| `created_at` vs `terminal_at` | **the same token, `{{ts_5}}`** | two values, a real duration |

All four names are declared by the frozen `RunStatus` and `StageState` and were already
serialised by `api/schemas/runs.py`; they had no producer. **Nothing was renamed, removed or
re-typed, and no status or header moved** — which is why this is a repair inside the contract
and not a reseal.

**This corpus had pinned the timestamp defect as the expectation.** Substitution is by exact
value, `created_at` and `terminal_at` *were* identical to the microsecond, and so they earned
one token between them. A record that reproduces a defect byte for byte is protecting it, and
a re-capture alone would have erased the evidence silently — so
`test_the_five_run_status_records_no_longer_pin_one_instant_for_the_whole_run` asserts against
the records that it is gone.

**The re-capture was checked for vacuity.** `capture.py` rewrites every file. Measured at
`aae0209` with `git diff --stat`: **28 came back byte-identical and exactly the 5 above
moved**, +110/-20 lines, evenly split five ways because the five bodies changed the same way.
Re-running the capture is the one thing that can make this directory vacuous, so the diff is
the evidence that it did not: a repair that had moved a sixth record would have shown here.

### `D-7` — record 31

`records/31-streamDocumentVersionContent.storage_credential_refused.json` carries an
`exception` block. **It has been taken.**

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

`test_exactly_the_named_records_are_marked_as_permitted_exceptions` makes that countable:
the marked set must be exactly the six cases `PERMITTED_EXCEPTIONS` names, each with its
debt, its citing commit and its `permitted_change`. **Every other difference is a failure of
the wave, whatever argument accompanies it.**

## The one order not pinned

`records/08-listRunFindings.success.json` and `records/12-exportRunCsv.success.json` each
carry an `unordered` block declaring **`O1`**, and they are the **only** two that do.
`test_exactly_two_records_declare_an_unordered_sequence` makes that countable, the way the
permitted exception is countable.

Both operations order published findings by `finding_uid COLLATE "C"`. A `finding_uid` is a
**fresh ULID per publication**, and `shared/identity/ulid.py` says in so many words that
monotonicity inside one millisecond is deliberately *not* promised: the domain contract
forbids deriving ordering from a ULID body, so the generator declines to supply the property
that would invite it. Two findings published in the same millisecond are separated only by
80 bits of `os.urandom`. Measured over 150 journeys against this lane: two findings shared a
millisecond in a few percent of runs, and when they did, the order was a coin flip. Pinning
the sequence was asking the system for a guarantee it does not make — which is why these two
records, and only these two, failed inside `make gate` and passed when run alone.

**What is erased, and why it cannot hide anything else.** Both sides are cut by the *same*
declared splitter into `(prefix, separator, elements, suffix)`, at the byte level — nothing
is re-parsed or re-serialised, so key order, separators, `ensure_ascii=False` and every byte
inside an element survive the cut. `prefix + separator.join(elements) + suffix` is asserted
to reassemble to the body it cut. Prefix, separator and suffix are then compared byte for
byte, and the elements are compared as a **sorted list**. Two sequences have equal sorted
lists exactly when one is a permutation of the other, so *order, and nothing else, is
erased*: a changed category, quote, offset or verdict, a dropped element, a repeated element,
a duplicated element replacing a missing one, and a changed count all still redden. Each of
those is a test, run against every permutation of the sequence rather than one.

**What is pinned instead.** The ordering *rule*, which the system does promise, asserted
against the live response rather than against a recorded sequence:
`test_the_published_findings_come_back_ascending_by_finding_uid` and
`test_the_csv_rows_come_back_ascending_by_finding_uid_then_observation_id`. A rewrite that
dropped the `ORDER BY` would leave both records green and fail both of those.

**One consequence for the substitution.** `{{finding_uid_0}}`…`{{finding_uid_2}}` are
numbered by the finding's rank in **document order** — the page and character offset of its
first evidence quote — and no longer by its place in the response. A token numbered by an
order the system does not promise is a token that names a different finding from run to run,
which is what made an order-insensitive comparison impossible before. The rank is a property
of the frozen AR fixture, it is asserted to be total, and it decides what a value is *called*,
never what any value must *be*. Cases 09, 10, 11 and 12 name their finding through the same
rank, so no record downstream depends on which finding a publication's ULIDs sorted first.

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
