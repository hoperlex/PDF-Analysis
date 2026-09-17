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

`records/31-streamDocumentVersionContent.storage_permission_denied.json` carries an
`exception` block and is the **only** record that does.

`StoragePermissionDeniedError` emits `permission_denied` when *our own* S3 credential is
refused by the store — the catalog code whose summary describes *"the **authenticated
subject** is not permitted"*. There is no authenticated subject in that scenario at all
(`DEBT_REGISTER.md` D-7). The owner ruled at `R-3` that the reseal gives the storage case a
code of its own, so this record's status, `error_code`, `message` and `details` all change on
purpose. **The commit that decides it is cited beside the new expectation.**

`test_exactly_one_record_is_marked_as_the_permitted_exception` makes that countable:
the marked set must be exactly this one case. **Every other difference is a failure of the
wave, whatever argument accompanies it.**

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
