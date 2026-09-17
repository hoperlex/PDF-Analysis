# W16-ERR — three error mappings that told a caller something untrue

**Session** `W16-ERR`. **Worktree** `/root/w16err`, branch `agent/w16-err` off `origin/dev`.
**HEAD on arrival** `315de25` — *"merge: the clean-lane breaker, and the two infra lines
W15-AUTH stopped at"*. **Started** 2026-09-17T23:03Z. Disk at start: `/` 89% used, 13G free.

## 0 — the settled shape, confirmed before anything was touched

The brief asserts that `dependency_credential_refused` — the 21st code, owner ruling `R-3`,
settling `D-7` — already exists everywhere and that nothing this wave needs a catalog change.
**Confirmed, measured, not assumed:**

| where | measurement |
| --- | --- |
| catalog | `contracts/domain/v1/error-codes.json` — 21 codes; `dependency_credential_refused` = `http` 500, `retryable` false, category `dependency`, `safe_detail_keys` exactly `["dependency"]` |
| revision note | round 6 carries `R-3` of 2026-09-17 and names `D-7`; `status: draft_candidate`, `frozen: false` |
| envelope schema | `contracts/domain/v1/error-envelope.schema.json:35`, `:353` |
| enum | `src/auditmanager/shared/errors/codes.py:32`; `src/auditmanager/api/schemas/models.py:235` |
| OpenAPI | `contracts/api/v1/openapi.json:1206` (and the 403/500 prose at `:930`, `:1050`) |
| migration | `db/migrations/versions/20260910_0002_pc01_schema.py:88` |
| storage | `src/auditmanager/storage/errors.py:167` — `StorageCredentialRefusedError.code` |

So no reseal, no owner decision, no `contracts/` byte is needed. **`contracts/` was not touched.**

Command used: `python3 -c "import json; d=json.load(open('contracts/domain/v1/error-codes.json')); print(len(d['codes']))"` → `21`.

## 2.1 — a refused model-proxy credential was pinned retryable

**Measured before touching it.** `src/auditmanager/analysis/text/proxy.py:222` — the brief's
line number is exact. The mapping read:

```python
    if exc.code == 401:
        return DomainError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            message="the model proxy refused the token",
        )
```

The catalog pins `dependency_unavailable` `"retryable": true`, `"http": 503`, and its summary
says *transiently* unavailable. So a proxy that rejected our credential answered as a service
that would work in a minute.

**Envelope before and after**, both produced from the tree rather than written by hand
(`PYTHONPATH=src .venv/bin/python -c ...` building the `DomainError` and rendering
`.envelope(...)`):

| | before | after |
| --- | --- | --- |
| HTTP | **503** | **500** |
| `error_code` | `dependency_unavailable` | `dependency_credential_refused` |
| `retryable` | **`true`** | **`false`** |
| `details` | *(absent)* | `{"dependency": "model_provider"}` |
| `message` | "the model proxy refused the token" | "the model proxy refused the configured credential" |

`dependency` carries `DEPENDENCY_NAME` (`= "model_provider"`, `analysis/text/config.py:36`) —
the same stable class-name vocabulary `live.py` and `recorded.py` already use and the one
`R-3`'s catalog note asks for, so an operator reading a `dependency_credential_refused`
envelope can tell the blob store's refusal from the model proxy's.

**Which test reddened when I reverted the change.** Mutated the mapping in place back to
`DEPENDENCY_UNAVAILABLE` with the old message (`tests/` cannot ride in a `make mutation-copy`
tree — `D-10` — so this was in place, then `git checkout --`). **Two went red:**

- `tests/integration/analysis_text/test_proxy_adapter.py::TestFailuresMapToTheCatalog::test_each_documented_status_lands_on_its_code[401-payload0-dependency_credential_refused]`
- `tests/integration/analysis_text/test_proxy_adapter.py::TestFailuresMapToTheCatalog::test_a_refused_credential_never_tells_the_caller_to_retry` — new this wave

`2 failed, 26 passed`; reverted, `28 passed`. The pre-existing parametrised row asserted only
the *code*, which is a name. The lie was the `retryable` flag beside it, so the new test pins
the rendered envelope — `retryable is False`, `http_status == 500`, and the `dependency` detail.

**On the alpha.** `R-4` permits real client PDFs on the alpha and `R-1`'s open items include
whether the model proxy is reachable from the alpha host at all. A misconfigured proxy
credential there is a likely first failure, and this mapping is what the operator sees.

## 2.2 — a server fault answered as the caller's validation error

**Measured before touching it.** `src/auditmanager/storage/errors.py:112` —
`class StorageBucketMissingError(StorageConfigurationError)`, and that parent carries
`code = "validation_failed"` at line 107. Both line numbers exact. It is reachable well beyond
a startup probe: `S3BlobStore._translate` returns it for `_NO_BUCKET_CODES` (`s3.py:421`) and
for a bucket-scoped 404 (`s3.py:434`), so any `get`/`put`/`head` can raise it into
`domain_error_from_storage` and out as an envelope.

**The choice, argued from the catalog's own summaries.** All twenty-one were read; the full
argument is now in the class docstring. In short: `validation_failed` describes the *request*,
and there is no request defect. `not_found` is *"the addressed aggregate does not exist"* — a
bucket is not an aggregate of this domain, and a 404 would read as a normal empty result and
hide the fault. `dependency_unavailable` is `retryable: true` and means *transiently*
unavailable; this class's own first paragraph refutes it (retrying never creates a bucket), and
taking it would be the exact untruth 2.1 came to remove. `dependency_credential_refused` means
a dependency *refused the application's own credential* — nothing was refused here, the store
answered and the bucket was absent, and borrowing it would repeat `D-7`'s mistake in the act of
citing it. `storage_integrity_error` requires a comparison; nothing was compared.

What is left is **`internal_error`**, and it is not a shrug. `internal_mapping` rule 1 declares
it in the catalog's own words: *"An internal analysis stage code, **adapter code** or worker
code that has no declared mapping in this catalog is reported externally as internal_error."*
This is an adapter code with no declared mapping. 500, not retryable, category `internal` —
*"an unclassified server fault"* — is true of a missing bucket in every particular.

**Envelope before and after** (rendered through `domain_error_from_storage`, from the tree):

| | before | after |
| --- | --- | --- |
| HTTP | **422** | **500** |
| `error_code` | `validation_failed` | `internal_error` |
| `retryable` | `false` | `false` |
| `details` | `{"field": "S3_BUCKET", "constraint": "must_exist"}` | *(absent)* |
| `message` | "The request or payload violates a declared schema, enum, format or invariant…" | "An unclassified server fault. The envelope still carries a stable code and correlation id…" |

The class was **reparented onto `StorageError`** rather than left as a `StorageConfigurationError`
overriding its parent's code — a subclass of a class meaning `validation_failed` that means
something else is the same confusion `R-3`'s own docstring refused one layer down. Nothing in
`src/` depended on that `isinstance`: the only other uses of `StorageConfigurationError` are
`S3StorageSettings.from_env`, which is untouched.

`field` and `constraint` are still accepted and still on the raised exception — so `S3_BUCKET`
still reaches the logs, and `s3.py`'s two call sites (which this session does not own) needed
no edit. They no longer reach the envelope: `internal_error` declares `safe_detail_keys: []`
and `domain_error_from_storage` narrows every detail to the reported code's own list. That is
where `R-3` put the offending environment variable too — behind `correlation_id`, per the
catalog's own safety rule.

**Which test reddened when I reverted the change.** Mutated in place back to
`StorageBucketMissingError(StorageConfigurationError)` with the parent's code. **Two went red:**

- `tests/integration/storage/test_unavailable.py::test_a_missing_bucket_is_a_typed_configuration_failure` — the pre-existing test, amended
- `tests/integration/storage/test_unavailable.py::test_a_missing_bucket_is_never_answered_as_the_callers_validation_error` — new this wave, and it pins the **envelope**, because the envelope is what told the lie

`2 failed, 11 passed`; reverted, `13 passed`.

**The boundary I stopped at.** A dedicated 22nd code — a *dependency misconfigured* code,
distinct from a refused credential — would say more to an operator than `internal_error` does,
and I think the register should carry it as a candidate. **I did not take it and I am not
proposing a reseal this wave.** `internal_mapping` rule 4 settles whose call it is, in its own
words: *"Giving a recurring internal reason its own stable external code is a deliberate change
to this catalog under the versioning policy, not an edge-local or provider-local decision."*
That is the owner's. `internal_error` is strictly more truthful than the 422 it replaces and is
the catalog's declared destination meanwhile, so this is not a bad fit forced to close a row.

## 2.3 — `D-3` and `D-4`, re-measured before anything was touched

### `D-4` — "an empty digest reaches an operator-facing envelope": **already closed. No change made.**

The register states two things. Measured separately:

1. *"Against an unstamped object, `inspect` yields `sha256=\"\"`"* — **still true.**
   `src/auditmanager/storage/s3.py:408`: `sha256=recorded_sha or ""`.
2. *"and `verify_version` emits `actual_sha256=\"\"`"* — **no longer true.**
   `src/auditmanager/ingest/reconciliation.py:287` now guards it explicitly, ahead of the
   comparison that used to fire, and raises `validation_failed` with
   `{aggregate_type: Blob, field: sha256, constraint: "recorded on every published object"}`.
   The code's own comment names the defect it is there to prevent: *"Reporting this as an
   integrity failure would put `actual_sha256=\"\"` into an operator's envelope."*

So the reachable half is closed, and it was closed by the wave-12/13 rewrite exactly as the
brief suspected. **It already has a guard**, which I ran rather than assumed:
`tests/integration/ingest/test_reconciliation_reads_the_bytes.py::test_a_version_whose_object_records_no_digest_is_not_an_integrity_verdict`
— 1 passed. It asserts the debt's own words back at it:
`assert "actual_sha256" not in envelope.details` and `assert "" not in set(envelope.details.values())`.

**One residual, and it is not the one `D-4` names.**
`src/auditmanager/storage/blob_repository.py:260` still reads
`actual_sha256=existing.sha256 or ""`, which would put an empty digest in a
`storage_integrity_error` envelope. I judged it **latent, not live**: `_assert_same_content` is
reached only for a row in `available` or `verifying` (`blob_repository.py:182`); the migration's
`ck_blob_available_is_verified` forbids a NULL `sha256` on `available`; and the only insert path
writes `verified.sha256`, which is never empty. The `or ""` is type-narrowing for a
`str | None` column, not a live defect. **I did not change it** — `blob_repository.py` is not a
file this session owns (STEP 4), and there is no defect behind the change. Recommend `D-4` be
**re-scoped to that line and kept**, rather than closed outright.

### `D-3` — `_record`'s `cost_basis` default: **still latent. No change made. The register's own text is stale.**

The register says: *"`analysis/text/stage.py`: `cost_basis: str = \"estimated\"`. … **Latent, not
live** — one call site exists and passes it explicitly."*

Measured (`grep -n "_record(" src/auditmanager/analysis/text/stage.py`):

- the default is still there, `stage.py:417`;
- there are **two** call sites now, not one: `stage.py:260` and `stage.py:292`;
- `:292` (the success path) passes it explicitly;
- **`:260` (the budget-overrun path) does not** — it takes the default.

So the register's count is out of date and the row understates the shape. But the **verdict
still holds**, and this is the part worth being careful about: the overrun call site passes
`cost_usd=overrun`, where `overrun = pin.cost_usd(input_tokens=…, output_tokens=…)` — a figure
computed from the pin's price table, never the provider's reported cost. For *that* figure
`"estimated"` is the correct basis. The defaulted value is right; it is right **by coincidence
rather than by statement**, which is precisely the latency `W11-FIX` flagged and correctly
declined to act on.

Two further notes so the row can be judged without re-deriving this:

- the `"cost_basis"` in the metrics dict beside it (`stage.py:279`) computes
  `"measured" if response.reported_cost_usd is not None else "estimated"`, but it describes a
  **different figure** — `cost_meter.spent_usd`, not `overrun`. The two are not in conflict.
- **`D-3` is not an error mapping and tells no caller anything untrue.** It is a provenance
  default on a `model_call` row. It does not belong with 2.1 and 2.2.

**No change made**, for two reasons that are each sufficient: there is no defect behind it, and
`analysis/text/stage.py` is not a file this session owns.

## 3 — the standard: characterization, and where the brief's premise did not hold

The brief's STEP 3 says: *"Every repair changes bytes a caller sees, so **every one is a
characterization change**"*, and directs me to record 31's `purpose` / `permitted_change` form
for anything I change.

**Measured: neither repair changes a single byte in `tests/characterization/w13_baseline/`.**
Record 31 was read first, as instructed, and its form is the right one — it simply had nothing
to apply to here:

- the 33 records were enumerated and none exercises the model proxy at all (no record reaches
  a `401` from it) and none exercises a missing bucket. The only storage failure in the corpus
  is record 31 itself, a refused **credential**, which is `StorageCredentialRefusedError` and
  is not a class this wave touched;
- `PYTHONPATH=src .venv/bin/python -m pytest tests/characterization -q` → **55 passed**, before
  and after both repairs, with no record edited;
- the `validation_failed` records that do exist (17, 18, 19, 23–27) are upload and request-body
  refusals — genuine caller-side validation, and none of them routes through
  `StorageBucketMissingError`.

So **no record was edited and no `permitted_change` was written**, because writing one would
have claimed a change that did not happen. Stating it here instead. The corollary is worth the
register's attention: **the two envelopes this wave repaired were not pinned by the byte-for-byte
corpus at all** — they were pinned only by the integration tests named above, which is why the
mutation proofs had to come from there.

### On `D-10` and the mutation method

`D-10` is accurate about the Makefile — `mutation_copy` (`Makefile:551-559`) does `cp -a src`
and symlinks `contracts docs fixtures db tools`; `tests` is absent. But **it did not actually
bind this wave**, and I would rather say so than imply the workaround was forced: both of my
mutations were in `src/`, and the target's own recipe (`Makefile:~933`) covers exactly that case
by running the worktree's tests with `-o pythonpath=<copy>/src`. I mutated **in place** anyway,
from a committed-clean tree, reverting with `git checkout -- <file>` and confirming
`git status --porcelain` empty afterwards each time. `D-10` blocks a *tests-only* mutation; that
is not what either of these was.

## 4 — anything false in this brief

Checked every premise against the tree, as instructed. **The brief is accurate on every line
number and every flag** — `proxy.py:222`, `storage/errors.py:112` and `:107`, the `retryable`
flags, the class hierarchy, and the whole of STEP 1's account of `R-3` and the 21st code. That
is a change from the pattern the brief warns about. Three things are nonetheless off:

1. **"Every one is a characterization change" is false**, as measured above. Zero of the 33
   records change. The repairs are real; the corpus simply never covered these two paths.
2. **STEP 2.3 and STEP 4 contradict each other.** `D-3` lives in
   `src/auditmanager/analysis/text/stage.py` and `D-4`'s residual in
   `src/auditmanager/storage/blob_repository.py`. STEP 4 grants this session `proxy.py`,
   `storage/errors.py`, their tests, the records and this review — **neither file is owned**.
   As it happens both rows measured out to "no change warranted", so nothing was blocked; had
   either been live, I would have had to stop at the ownership line and report.
3. **The expected gate figure is pre-change.** The brief says *1726 passed*. This wave adds two
   tests, so the arithmetic target is **1728**; see below for what was actually measured.

One stale item in the register rather than the brief: **`D-3`'s own text says "one call site
exists and passes it explicitly"; there are two, and the second does not.** Detail in 2.3.

## 5 — both defects were already known, and repaired by nobody

Neither of these is a new discovery by this session, and the record of who saw them is worth
keeping beside the repair:

- `docs/program/W13_CLOSURE.md:101` — *"`StorageBucketMissingError` still carries
  `validation_failed` for a server fault — **noticed independently by two streams, repaired by
  neither**"*;
- `docs/program/W13_CLOSURE.md:103` — *"**A second `D-7` in a second adapter**:
  `analysis/text/proxy.py` maps a **401 from the model proxy** onto `dependency_unavailable`,
  which the catalog pins **retryable** — it tells a caller to retry a rejected credential"*;
- `docs/program/reviews/W13-SEAL.md:492` saw the bucket case while resealing and left it
  explicitly: *"I noticed it while reading and left it alone"*;
- `docs/program/reviews/W13-API.md:510` met it a second time and left it too.

Those four prose accounts match what I measured in the tree line for line. Both are now closed,
each with a test that goes red when the mapping is put back. The prior reviews are historical
records and were **not** rewritten.

