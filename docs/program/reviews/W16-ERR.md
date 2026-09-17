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

