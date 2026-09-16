# `W10-API` review — mutation sweep of the API boundary and the shared kernel

Session `W10-API`. Worktree `/root/w10api`, branch `agent/w10-api`.

## Provisioning

`HEAD` on arrival: **`e08da85`** — *docs: the wave 10 dispatch — five parallel sweeps of
the rule surface*, the tip of `origin/dev`. The brief names `fb30e96` as the base; `e08da85`
is its child and carries only the dispatch documents, so the `src/` and `tests/` surface is
identical to the stated base. Not a discrepancy that changes anything, but recorded.

Surface read: `src/auditmanager/api/**`, `src/auditmanager/shared/**`,
`src/auditmanager/bootstrap/**` — 5 209 lines by `wc -l`, exactly as the brief states.

Instance `gate-w10c`, `POSTGRES_PORT=55610`, `S3_API_PORT=59210`, `S3_CONSOLE_PORT=59211`,
`POSTGRES_DB=audit_w10c`, bucket `auditmanager-gate-w10c`. `.env` copied from `.env.example`
and set to exactly that instance; never committed.

## Baseline

`make gate` on arrival, worktree clean: the canonical battery reports **816 passed, 5 skipped,
116 subtests passed** in 192 s. Exactly the figure the brief states. Measured with

```
cd /root/w10api && set -a && . ./.env && set +a
.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q tests \
  --ignore=tests/contract --ignore=tests/checkpoint
```

against tree `6c2c49f` with no working-tree modifications.

A first attempt to read this figure out of `make gate` reported *3 failed, 813 passed*. That
was not this worktree. The five wave-10 streams are subagents of one parent session and so
share one scratchpad directory; `W10-RUN` had written its own `gate-baseline.log` over mine.
The surviving lines named instance `gate-w10d`, ports `55620`/`59220` and `rootdir:
/root/w10run`. **No stream should redirect a log to the shared scratchpad under a generic
name.** This session's own logs live in `/root/w10api-work/`.

## Method

`src/` is copied to `/root/w10api-mut/`, with `contracts/`, `docs/`, `fixtures/` and `db/`
symlinked in — `analysis.text.lock` resolves `docs/program/P02_LOCK.json` from `parents[4]`
of its own module file, so a copy without `docs/` fails before reaching any assertion. Each
mutation is applied to a freshly re-copied `src/`, and every run collects
`/root/w10api-work/probe_test.py` first:

```python
assert auditmanager.__file__.startswith("/root/w10api-mut/"), auditmanager.__file__
```

so a result from a run that imported the worktree's own `src/` is a failure, not a false
green. The worktree's `src/` is never written.

Before any run, all 77 mutations were checked to apply exactly once and to change the file
text — the `frozenset() or frozenset({...})` mistake, which evaluates to the real set and
mutates nothing — and each was read back against its intended meaning.

## Finding 1 — the brief says seven forbidden shapes. There are six.

`_FORBIDDEN` in `shared/errors/envelope.py` is a six-tuple: *a URL*, *a filesystem path*,
*an S3-style object key*, *a credential*, *SQL*, *a stack frame*. The module docstring lists
five (it omits the S3 key). The brief says seven, twice. **Six.** Nothing depends on the
count, but a sweep briefed to find seven rules will look for one that is not there.

## Finding 2 — the detail-value screen, which `B6` paid for, had no test at all

`build()` screens `details` **values** against the same six patterns as a message. The
comment on that loop records why it exists: `B6`'s `additionalProperties` refusal echoed the
caller's own property name into `details.field`, so a property named `/etc/passwd` came back
inside the envelope. The key was declared safe; the value was raw caller input.

Neutering the loop — iterating `()` instead of `_FORBIDDEN`, so no value is ever screened —
leaves the canonical battery at **816 passed, 5 skipped**. `UnsafeDetailValue` appears
nowhere in `tests/` at all; the only references in the repository are its own definition,
its `raise`, and its export.

This is the finding the wave exists for: a screening loop on a security surface, reading as
coverage, that no test in the gate can distinguish from a deleted one.

## Finding 3 — `_MAX_DETAILS = 16` is unreddenable *by construction*

No test is owed here and none was written. `checked` is built only from keys that passed
`key not in allowed`, so it can never hold more keys than the reported code declares in
`safe_detail_keys`. Measured across all twenty codes:

| code | declared safe keys |
|---|---|
| `storage_integrity_error` | 4 |
| `required_norm_unavailable` | 4 |
| `validation_failed`, `state_transition_not_allowed`, `unsupported_contract_version`, `stale_attempt` | 3 |
| the other fourteen | 0–2 |

The maximum is **4**. `len(checked) > 16` cannot be true for any code in the closed enum, so
the branch is unreachable without editing the catalog — which is product code this session
does not write. The mutation `_MAX_DETAILS = 100000` is green for that reason and not
because a guard is missing.

(The check also sits *after* the loop rather than inside it, so even a catalog that declared
seventeen safe keys would screen all seventeen values before counting them. Noted, not a
defect: nothing can reach it.)

## Finding 4 — the message screen could not say which rule refused

The one gate test over the message screen,
`tests/integration/api/test_error_envelope.py::test_a_message_carrying_an_address_is_refused_by_the_screen`,
asserts `pytest.raises(UnsafeMessage)` over three sentences and nothing more. Two of the
three match two patterns each:

| sentence | patterns it matches |
|---|---|
| `could not read /var/lib/audit/objects/ab/cd.pdf` | *a filesystem path*, *an S3-style object key* |
| `GET https://minio.internal/audit-b6 failed` | *a URL* |
| `SELECT blob_id FROM blob WHERE state = 'available'` | *SQL* |

The screen iterates in order and raises on the first match, so the S3 rule is never the
rule that fires and could be deleted with the suite still green. *Credential* and *stack
frame* are not exercised by any gate test. (`tests/contract/shared_kernel/test_error_kernel.py`
does cover five of the six, but `make gate` runs
`tests --ignore=tests/contract --ignore=tests/checkpoint` — it is quarantined CP-00 evidence
and not part of the gate.)

## The guard written

`tests/integration/api/test_envelope_screen_rules.py`, 20 tests. Each forbidden shape gets a
value checked to match **exactly one** pattern, asserted through both the message screen and
the detail-value screen, and the assertion is on **the phrase naming the rule**, not on the
exception class — `UnsafeMessage` is raised by all six rules and by the length rule alike.

| shape | value pinned | reason phrase pinned |
|---|---|---|
| a URL | `https://minio.internal/audit-b6` | `a URL` |
| a filesystem path | `the object at /var/lib/audit/ was refused` | `a filesystem path` |
| a filesystem path (Windows) | `C:\Windows\System32` | `a filesystem path` |
| an S3-style object key | `bucket/prefix/object.pdf` | `an S3-style object key` |
| a credential | `api_key=sk-ant-abc123` | `a credential` |
| SQL | `SELECT id FROM blob` | `SQL` |
| a stack frame | `File "s3.py", line 3` | `a stack frame` |

Nothing imports `_FORBIDDEN`, `_MAX_MESSAGE` or `_MAX_DETAIL_VALUE`. The length ceilings are
asserted at the boundary against written numbers — 512 accepted / 513 refused, 256 accepted /
257 refused. **No independent authority declares either number**: the frozen OpenAPI document
carries no length for `message`, and the error catalog carries none for a detail value. That
is stated rather than papered over; the literals still redden when a constant drifts, which is
the property that matters.

### Red and green, per mutation

Each mutation applied to `/root/w10api-mut2/src`, **read back** to confirm the new text is
present and the old text gone, and the guard run against it:

| mutation | guard tests that reddened |
|---|---|
| `_FORBIDDEN` *a URL* → never-matching | `…_and_named[url]`, `…_under_a_declared_key[url]` |
| *a filesystem path* → never-matching | both `[posix_path]` and both `[windows_path]` — 4 |
| *an S3-style object key* → never-matching | `…_and_named[s3_key]`, `…_under_a_declared_key[s3_key]` |
| *a credential* → never-matching | `…_and_named[credential]`, `…_under_a_declared_key[credential]` |
| *SQL* → never-matching | `…_and_named[sql]`, `…_under_a_declared_key[sql]` |
| *a stack frame* → never-matching | `…_and_named[stack_frame]`, `…_under_a_declared_key[stack_frame]` |
| `_MAX_MESSAGE` 512 → 100000 | `test_a_message_of_512_characters_is_accepted_and_513_is_not` |
| `_MAX_DETAIL_VALUE` 256 → 100000 | `test_a_detail_value_of_256_characters_is_accepted_and_257_is_not` |
| detail-value screen → `for … in ()` | all **7** `…_under_a_declared_key[*]` cases, and no message case |
| scalar check → `if False:` | `test_a_non_scalar_detail_value_is_refused` |

Each mutation reddens exactly the cases written for it and no others, and the suite is green
on unmutated source.

## Sweep table — `shared/errors/envelope.py`, all 14 rules

Every mutation applied to a fresh copy, read back, then Phase A
(`tests/integration/{api,composition,shared_kernel}`, `-x`) and, if Phase A was green,
Phase B — the **whole canonical battery**, `tests --ignore=tests/contract
--ignore=tests/checkpoint`. A green line below means all 816 tests passed with the rule
neutered.

| # | rule mutated | mutation | result | what reddened |
|---|---|---|---|---|
| E1 | `_FORBIDDEN` *a URL* | pattern → never-matching | **RED** | `test_error_envelope.py::test_a_message_carrying_an_address_is_refused_by_the_screen` |
| E2 | `_FORBIDDEN` *a filesystem path* | pattern → never-matching | **GREEN** | nothing — 816 passed |
| E3 | `_FORBIDDEN` *an S3-style object key* | pattern → never-matching | **GREEN** | nothing — 816 passed |
| E4 | `_FORBIDDEN` *a credential* | pattern → never-matching | **GREEN** | nothing — 816 passed |
| E5 | `_FORBIDDEN` *SQL* | pattern → never-matching | **RED** | `…::test_a_message_carrying_an_address_is_refused_by_the_screen` |
| E6 | `_FORBIDDEN` *a stack frame* | pattern → never-matching | **GREEN** | nothing — 816 passed |
| E8 | `_MAX_MESSAGE = 512` | → `100000` | **GREEN** | nothing — 816 passed |
| E9 | `_MAX_DETAIL_VALUE = 256` | → `100000` | **GREEN** | nothing — 816 passed |
| E10 | `_MAX_DETAILS = 16` | → `100000` | **GREEN** | nothing — **unreachable by construction**, see Finding 3 |
| E11 | detail-**value** screen | `for … in ()` | **GREEN** | nothing — 816 passed |
| E12 | `safe_detail_keys` allowlist | `if False:` | **RED** | `…::test_a_domain_error_detail_outside_the_catalog_is_refused_not_dropped` |
| E13 | detail scalar check | `if False:` | **GREEN** | nothing — 816 passed |
| E14 | `retryable` from catalog | `return not …` | **RED** | `test_database_refusals.py::test_am001_a_non_initial_insert_becomes_the_typed_code` |
| E15 | default message = `code.summary` | → a constant | **GREEN** | nothing — 816 passed |

**Four of the fourteen reddened. Nine are unguarded and reachable. One is unreachable.**

### Finding 5 — the path rule and the S3 rule mask each other

This is why E2 and E3 are *both* green, and it is the thing worth carrying forward. The
one gate test sends `could not read /var/lib/audit/objects/ab/cd.pdf`, which matches **both**
patterns. The screen raises on the first match, so:

* delete the path rule → the S3 rule still matches that sentence → `UnsafeMessage` still
  raised → green;
* delete the S3 rule → the path rule matches first anyway → green.

Either rule can be removed from a security screen with the full battery passing. Only
removing *both* would be noticed. A value matching exactly one pattern is the only kind that
can tell them apart, which is why the guard uses one.

**Answering the brief's question directly** — *which of the forbidden shapes can no test
redden?* Four of the six: **a filesystem path, an S3-style object key, a credential, a stack
frame**. Only *a URL* and *SQL* were reddenable. (`tests/contract` covers five of six, but it
is quarantined out of `make gate` and is red before any wave starts, so it guards nothing
the gate would catch.)

### The guard, extended

`test_envelope_screen_rules.py` now carries 24 tests and covers **all nine reachable greens**:
E2, E3, E4, E6 (one-shape-per-value, reason phrase asserted), E8, E9 (boundary literals),
E11 (the whole detail-value screen), E13 (scalar), E15 (default message).

E15's guard is pinned against `contracts/domain/v1/error-codes.json`, read from the **test
file's** own location rather than the module's — the independent authority
`shared/errors/catalog.py` itself names ("the contract is the authority … never restates a
value the contract owns"). It also pins the catalog at **20 codes**, so a code added or
removed reddens rather than quietly narrowing the loop. E15 reddens
`test_every_code_defaults_to_its_declared_summary`.

E12 and E14 already redden against the existing suite, so no test was added for them.

## Sweep table — `api/routers/multipart.py`

| # | rule mutated | mutation | result | what reddened |
|---|---|---|---|---|
| M1 | `MAX_BODY = 26 MiB` | → 26 GiB | **see below** | nothing asserted — the run was killed |
| M2 | `multipart/form-data` media-type check | `if False:` | **GREEN** | nothing — 816 passed |
| M3 | `parsed.is_multipart()` boundary check | `if False:` | **GREEN** | nothing — 816 passed |
| M4 | part carries a name | `if False:` | **GREEN** | nothing — 816 passed |
| M5 | part is not repeated | `if False:` | **GREEN** | nothing — 816 passed |
| M6 | undeclared part refused | `raise …` → `pass` | **GREEN** | nothing — 816 passed |
| M7 | a `file` part is required | `if False:` | **GREEN** | nothing — 816 passed |
| M8 | the `file` part needs a filename | `if False:` | **GREEN** | nothing — 816 passed |

**All seven refusing branches of the multipart reader are unguarded.** The module's own
docstring calls it "deliberately strict, because a lenient multipart reader is a security
surface" — and every one of those refusals could be deleted with the battery green. The
three tests that mention multipart (`test_journey`, `test_schema_conformance`,
`test_no_internal_identifiers`) all send *well-formed* bodies; they exercise the happy path
and never a refusal.

### Finding 6 — M1 is not a red, it is an out-of-memory kill

`tests/integration/ingest/test_size_guard_boundary.py` is the one test that names `MAX_BODY`,
and it sizes its payload from the constants it is testing:

```python
BODY_TARGET = (MAX_BYTES + MAX_BODY) // 2
```

With `MAX_BODY` mutated to 26 GiB that is ≈ 13 GiB, so the suite tries to allocate 13 GiB and
the process dies at 70 % of the battery with no failure and no summary line. The harness saw
a non-zero exit and recorded RED; there is no assertion behind it.

This is wave 9's mistake in a new form. The file is careful — `test_the_window_between_the_two_guards_is_open`
asserts `MAX_BYTES < BODY_TARGET < MAX_BODY`, which genuinely catches the limit being
*lowered* to the envelope's. But because the payload is derived from the limit, the limit
being *raised* is not a red test; it is an unbounded allocation. **`MAX_BODY` itself has no
test pinning it.** Not a product defect — a measurement artefact and a gap, reported as both.

## The second guard — `tests/integration/api/test_multipart_rules.py`

19 tests, one per refusing branch, asserting **`details["constraint"]`** — the rule — rather
than `details["field"]`. The field cannot identify the rule here: `file` is the field for
four different rules (`part_name`, `required`, `filename`, `max_bytes`) and `Content-Type`
for two (`media_type`, `boundary`). All bodies are built in the test; nothing is read from
either frozen corpus.

| mutation | guard tests that reddened |
|---|---|
| `MAX_BODY` → 26 GiB | `…_one_byte_over_the_limit_is_refused_as_max_bytes`, `…_checked_before_the_body_is_parsed` |
| media-type check off | both `…_refused_as_media_type` cases |
| boundary check off | `…_with_no_boundary_is_refused_as_boundary` |
| part-name check off | both `…_refused_as_part_name` cases |
| repeated-part check off | `…_refused_as_unique_part`, `…_absent_from_the_envelope[repeated_part_name]` |
| undeclared part → `pass` | `…_refused_as_additional_properties`, `…_absent_from_the_envelope[unknown_part_name]` |
| file part required off | `…_no_file_part_is_refused_as_required` |
| filename required off | both `…_refused_as_filename` cases |

The transport limit is pinned as the literal **27262976** and exercised at
`TRANSPORT_LIMIT + 1`, so the mutated run allocates 27 MB rather than 13 GiB and **fails as a
test instead of dying as a process**. No independent authority declares 26 MiB — the frozen
OpenAPI declares the *document* maximum, which is the envelope's 25 MiB `ENV-SIZE`, a
different limit — so the number is pinned here and that is stated rather than implied.

Two branches that read as defensive programming turned out to be reachable and are now
covered: a `file` part that is itself `multipart/mixed` decodes to `None` rather than to
bytes (`constraint: encoding`), and a `display_title` part carrying invalid UTF-8 (also
`constraint: encoding`, distinguished by `field`).

The suite also pins the thing `B6` paid for from this end: an `additionalProperties` refusal
over a part named `/etc/passwd`, and a `unique_part` refusal over a repeated filename, must
not reflect that text back inside the envelope. Nothing checked that before.

## Sweep table — `routers/idempotency.py`, `routers/correlation.py`

| # | rule mutated | mutation | result | what reddened |
|---|---|---|---|---|
| I1 | `Idempotency-Key` required | `if False:` | **RED** | `test_journey.py::test_a_write_without_the_header_is_refused_before_anything_happens` |
| I2 | key character class | pattern → `^[\s\S]*$` | **RED** | `test_no_internal_identifiers.py::test_an_error_envelope_leaks_nothing_either` |
| I3 | key **length** `{0,127}` | → `{0,100000}` | **GREEN** | nothing — 816 passed |
| I4 | bad path identity → `not_found` | → `validation_failed` | **RED** | `test_error_envelope.py::test_an_unknown_identity_is_not_found_and_reveals_nothing` |
| I5 | header name | → `X-Idempotency` | **RED** | `test_journey.py::test_the_ingest_path_publishes_an_immutable_version` |
| C1 | correlation pattern | → `^[\s\S]*$` | **RED** | `test_error_envelope.py::test_an_unusable_correlation_id_is_replaced_not_reflected` |
| C2 | honour a supplied id | `if False:` | **RED** | `test_error_envelope.py::test_a_supplied_correlation_id_is_echoed` |
| C3 | assigned id is **unique** | `token_hex(16)` → a constant | **GREEN** | nothing — 816 passed |

This layer is in much better shape than the two before it: six of eight reddened. The
brief's steer — *"wave 8 found the rest of criterion 9 lives in a `UNIQUE` constraint rather
than in a pre-read; ask the same question of this layer"* — did not reproduce here. The
header rules themselves are guarded.

### Finding 7 — the key's character class is guarded, its length is not

`_KEY_PATTERN` is `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`, and the module says it is "exactly
`#/components/schemas/IdempotencyKey`". Widening the repetition bound to `{0,100000}` leaves
the battery green: no test sends a key longer than the bound. The frozen document declares
`"maxLength": 128`, so an authority exists and the guard pins against it.

### Finding 8 — an assigned correlation id was never required to be different

Every existing assertion — the header is present on every response, the body matches the
header, a supplied id is echoed, an unusable one is replaced — holds exactly as well when
`new_correlation_id()` returns the same constant for every request. Replacing
`secrets.token_hex(16)` with `"cid-constant"` leaves all 816 tests green. A correlation id
addresses one diagnostic record; if two requests share one, it addresses neither.

## The third guard — `tests/integration/api/test_header_rules.py`

9 tests.

| mutation | guard tests that reddened |
|---|---|
| key length `{0,127}` → `{0,100000}` | `…_129_characters_is_refused_by_the_pattern_rule`, `…_never_echoed_back` |
| `token_hex(16)` → a constant | `…_two_hundred_generated_ids_are_all_distinct`, `…_assigned_different_ones` |
| key required off | `…_refused_as_required_not_as_pattern` |
| key character class widened | `…_129_characters_is_refused_by_the_pattern_rule`, `…_never_echoed_back` |
| supplied id ignored | `…_a_supplied_id_is_still_preferred_over_an_assigned_one` |

The length case is pinned at **128 accepted / 129 refused** against
`contracts/api/v1/openapi.json`, read from the test file's own location — the frozen document
declares `maxLength: 128`, `minLength: 1` and the pattern, and the suite asserts all three, so
the module drifting away from the contract is a red test rather than a private agreement.
The refusal asserts `constraint == "pattern"` rather than the field: `require_idempotency_key`
answers `field: "Idempotency-Key"` for **both** its branches, and `required` and `pattern` are
only distinguishable by the constraint.

The uniqueness guard also pins the two ways it could be satisfied dishonestly — an assigned id
must still match the frozen `CorrelationId` pattern and stay within 128 characters, and a
supplied id must still win.

*(sweep of `schemas`, `errors`, `http`, `identity`, `bootstrap`, `db`, `statemachine`
continues)*
