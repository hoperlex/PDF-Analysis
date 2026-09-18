# W18-OPS — a restore is proved by writing, not by reading

**Session** `W18-OPS` · **HEAD on arrival** `3df17a7` ("docs(register): D-19 closes, and the
baseline had been protecting half of it"), worktree `/root/w18ops` on `agent/w18-ops` off
`origin/dev`. Logs under `/root/w18ops-logs/`.

**Rows:** `D-17` — fixed and proved by writing. `D-18` — measured only; the catalog is the
owner's and nothing in `contracts/` was touched.

**Live stack used:** my own, `auditmanager-w18c`, brought up from this worktree and torn
down with `docker compose down -v` at the end. `auditmanager-w14a` (31480) and
`auditmanager-w15b` (31490) were not touched. Only the `api` image was built; `web` and
`proxy` were never started, because the whole proof is an API-level write and the web build
is 1.2 GB on a host with 8 GB free.

---

## 1. The key set, read from the adapter — and the brief's figure is wrong

```
grep -rn 'Metadata=\|ContentType\|MetadataDirective\|put_object\|copy_object\|upload_fileobj' \
    src/auditmanager/storage/
```

One publication site: `S3BlobStore.publish` (`src/auditmanager/storage/s3.py:249`), a single
`copy_object` with `MetadataDirective="REPLACE"`. It writes **four user-metadata keys**
(`_metadata_for`, `s3.py:472`) and **one system header**:

| written on publication | read back by | lost by the old restore |
|---|---|---|
| `blob-id` | *nothing in `src/`* | **yes** |
| `blob-role` | `_record_from_head` -> `PublishedBlob.role` | **yes** |
| `content-sha256` | `read()` validation, `_record_from_head` | no |
| `content-size` | `_record_from_head` size cross-check | **yes** |
| `Content-Type` (header, `= verified.media_type`) | `_record_from_head` -> `media_type` | no |

**The brief says "two of the four ... `blob-role` is lost". Both halves are wrong, and the
report it came from counted the header as a user-metadata key.** Of the four user-metadata
keys, the old restore reattached **one**, not two. Three were lost, not one: `blob-id` and
`content-size` as well as `blob-role`. `Content-Type` survived, but it is the header, not
one of the four.

Measured on the live object rather than argued — `mc --json stat` on a freshly published
blob, before any wipe:

```json
{ "Content-Type": "application/pdf",
  "X-Amz-Meta-Blob-Id": "blob_7KDZE8SQTZ9K23JYB742HG7K8J",
  "X-Amz-Meta-Blob-Role": "source_document",
  "X-Amz-Meta-Content-Sha256": "6d53674f...bd31f",
  "X-Amz-Meta-Content-Size": "58978" }
```

and the same object after a restore by the **pre-fix** script:

```json
{ "Content-Type": "application/pdf",
  "X-Amz-Meta-Content-Sha256": "6d53674f...bd31f" }
```

**Why the three losses are not equally bad, said plainly rather than levelled:**

* **`blob-role` is `D-17`.** `BlobRole` is a `NewType` over `str`, so
  `BlobRole(metadata.get(_META_ROLE, ""))` does not raise — it yields `""`.
  `publish` then compares `record.role != verified.role` and refuses. That is the 409.
* **`content-size` fails quietly, which is different from failing less.**
  `_record_from_head` raises `SizeMismatchError` only `if recorded_size is not None`. A
  restore without it does not break; it silently stops checking. Nothing reddens, and an
  integrity guard is gone.
* **`blob-id` is read by nothing in `src/`.** Carried anyway. A sidecar that records four
  of five keys is one whose rule the next reader has to re-derive.

The direction of the brief's error matters: a fix built on "one key is missing" would have
carried `blob-role`, closed `D-17`, passed the write-back test, and left `content-size`
lost. That is `DEBT_REGISTER.md`'s own rule 2 — measure across every site — applied to keys.

## 2. What changed

**`infra/deploy/object_attrs.py`** — the sidecar is six tab-separated fields:
`key`, `blob-id`, `blob-role`, `content-sha256`, `content-size`, `content-type`. A missing
attribute is written as an **empty field**, never a default. `Content-Type` used to default
to `application/octet-stream`, which is precisely the value a dropped header takes — the
default made the loss unreadable. The guard now refuses the empty field instead.

**`infra/deploy/reset.sh`**, restore — `mc cp --attr` reattaches all five:
`blob-id;blob-role;content-sha256;content-size;Content-Type`.

**`infra/deploy/reset.sh`**, `dump-verified` — now two refusals with two messages, because
an operator shown one must not read the other:

* *"the object metadata sidecar is **short**"* — the row count disagrees with the bucket.
* *"the object metadata sidecar is **incomplete** — a row is missing an attribute"* — new.
  Every row must be six non-empty fields. The message prints the offending row through
  `cat -A`, so the empty field is visible rather than inferred.

**Guard marker count: 11, unchanged.** `dump-verified` was widened, not added to, so
`test_every_guard_in_the_script_has_a_case_here` still pins 11 and every marker still has a
case.

### 2a. A second defect, found on the way: the old empty-digest check never fired

The brief says `dump-verified` "already refuses ... a sidecar with an empty digest". **It
does not, on any host a deployment would run on.** The check read:

```sh
grep -q '^[^\t]*\t\t' "$DUMP_DIR/objects.attrs"
```

GNU grep does not read `\t` as a tab. Outside a bracket expression it is the letter `t`;
inside `[^\t]` it is "not a backslash and not a `t`". So the pattern looked for the literal
letters `tt` and matched no sidecar this script has ever produced. Measured at `3df17a7`
with **GNU grep 3.11** (`/bin/grep`) against a row whose digest field is empty:

```
GNU grep: NO MATCH      <- no refusal
literal tab: MATCHED    <- the refusal that was intended
```

It looks correct on this host only because `grep` first on `PATH` here is **ugrep 7.8.4**,
which *does* read `\t`. A guard written in a regex dialect the target does not speak is not
a guard, and this one had never been shown able to fail — there was no case for it. The tab
is now a literal (`TAB="$(printf '\t')"`), and there is a case.

## 3. Which test reddened, and how

`tests/integration/composition/test_reset_script_refusals.py`: **23 -> 31 cases**, guard
markers **11 -> 11**.

Reaching the sidecar check needs a `docker` that plays the dump through — the existing stub
answers `pg_dump` with nothing, so every run stops at *"the dump is empty"* first. The new
`STAGING_STUB` writes the artefacts the guard reads, from content the test chooses, and
still **opens no connection and runs no container**: the property the suite is built on is
kept, and `DROP SCHEMA` never leaves the log.

Run against the pre-fix script (`git show 56f37ab:infra/deploy/reset.sh`), five redden:

```
FAILED ...::test_an_incomplete_sidecar_stops_the_wipe[role]
FAILED ...::test_an_incomplete_sidecar_stops_the_wipe[three-column]
FAILED ...::test_an_incomplete_sidecar_stops_the_wipe[truncated]
FAILED ...::test_an_incomplete_sidecar_stops_the_wipe[empty-digest]
FAILED ...::test_a_short_sidecar_is_still_refused_by_its_own_message
FAILED ...::test_the_restore_reattaches_every_attribute_the_adapter_publishes
```

(`empty-digest` is section 2a: the case the guard was written for and never caught.)

Two of the eight deliberately do **not** redden, and should not:
`test_a_complete_sidecar_lets_the_wipe_proceed` is the control — without it a guard that
refused everything would look correct — and `test_that_refusal_is_shown_able_to_fail`
deletes `dump-verified` from a copy and requires the `DROP` to happen, which is true either
way. That deletion is the "shown able to fail" half, in the suite's own shape.

`test_the_restore_reattaches_every_attribute_the_adapter_publishes` pins three files to each
other: `_META_*` in `s3.py`, `USER_META_KEYS` in `object_attrs.py`, and the `--attr` string
in `reset.sh`. A fifth key added to `_metadata_for` reddens there rather than in a wipe.

## 4. The write-back proof

Instance `auditmanager-w18c`, database `auditmanager_w18c`, bucket `auditmanager-w18c`.
Bytes: `fixtures/synthetic/ar/ar_baseline.pdf`, 58978 bytes,
sha256 `6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f`.

### 4a. Post-fix — the row

```
create project -> 201
FIRST UPLOAD  -> 201    ver_01M2SKJPSGZ7MSW378W5WT0MTK

$ reset.sh --database auditmanager_w18c --bucket auditmanager-w18c --yes-destroy-everything
object_attrs: recorded 1 objects
reset.sh: dump verified -- database.dump readable, 1/1 objects mirrored
reset.sh: dropping and recreating schema public in auditmanager_w18c
...                                                          WIPE EXIT=0

sidecar (cat -A, ^I is a tab):
blobs/7K/DZ/7KDZE8SQTZ9K23JYB742HG7K8J^Iblob_7KDZE8SQTZ9K23JYB742HG7K8J^Isource_document^I6d53674f...bd31f^I58978^Iapplication/pdf$

$ reset.sh ... --restore .../auditmanager-w18c-20260918T063505Z
  reset.sh: restored 1 objects                               RESTORE EXIT=0

READ BACK -> 200 sha256: 6d53674f...bd31f bytes: 58978
byte-identical: True                       <- NECESSARY, AND NOT SUFFICIENT

RE-UPLOAD AFTER RESTORE -> 201             <- THE ROW
{"version_uid": "ver_01M2SKMWZ0BEKP3EPTTR3QEP97", ..., "byte_size": 58978,
 "sha256": "6d53674f...bd31f", "page_count": 8, ...}
```

**Both, said in the same breath, because the whole row is the difference between them.**
Reading the object back is necessary: a restore that loses `content-sha256` 422s on the
read, and wave 14 was right to check it. It is not sufficient: `blob-role` is consulted by
no read at all, only by `publish`'s idempotency check, so the object reads back perfect and
the instance is still broken for every later upload of those bytes. **A restore is proved
by writing to the restored instance, not by reading from it.**

### 4b. Pre-fix — `D-17` reproduced here, first-hand

The same stack, same bytes, with `reset.sh` and `object_attrs.py` checked out at `56f37ab`:

```
pre-fix sidecar: blobs/7K/DZ/7KDZE8SQTZ9K23JYB742HG7K8J^I6d53674f...bd31f^Iapplication/pdf$
restored object: only Content-Type and X-Amz-Meta-Content-Sha256

READ BACK -> 200 ... byte-identical: True
RE-UPLOAD AFTER RESTORE -> 409
{"error_code": "conflict", "message": "A concurrent write lost the optimistic-concurrency
 check or a uniqueness invariant would be violated. Used only when no more specific
 conflict code applies.", "retryable": false, "details": {"aggregate_type": "Blob"}}
```

`W15-RUN`'s finding is confirmed on the wire. Its *count* is not — see section 1.

### 4c. The new guard, refusing a live instance it could not restore

The bucket left behind by 4b holds an object with no `blob-role`. Running the **fixed**
script against it:

```
reset.sh: dumping into .../auditmanager-w18c-20260918T063641Z
object_attrs: recorded 1 objects
reset.sh: REFUSED: the object metadata sidecar is incomplete -- a row is missing an attribute.
    expected per row    : key, blob-id, blob-role, content-sha256, content-size, content-type
    first bad row       : 1:blobs/7K/DZ/7KDZE8SQTZ9K23JYB742HG7K8J^I^I^I6d53674f...bd31f^I^Iapplication/pdf$
  Nothing has been purged. A restore missing blob-role gives back an object that
  reads correctly and answers 409 to the next upload of its own bytes (D-17).
                                                             WIPE EXIT=3
```

Exit 3, **nothing purged**. That is `R-4`'s commitment holding: the script will not destroy
an instance whose objects it cannot put back.

## 5. `D-18` — what an operator can and cannot tell from that 409

Measured, not described. **Nothing in `contracts/` was changed; which keys `conflict` may
carry is the owner's call.**

`contracts/domain/v1/error-codes.json`, code `conflict`: `http 409`, `retryable false`,
`safe_detail_keys: ["aggregate_type", "expected_revision"]`.
`BlobAttributeConflictError` (`storage/errors.py:284`) raises with
`allowed_details = {aggregate_type, blob_id, role, media_type}`. The envelope screen
(`shared/errors/envelope.py:129`) keeps only what the **reported code** declares, so
`blob_id`, `role` and `media_type` are dropped. `expected_revision` is never set here.

**The `message` is dropped too, and that is worth naming separately.**
`envelope.py:126` — `text = ... if message is not None else code.summary` — uses the
*catalog's* summary. `BlobAttributeConflictError.summary` ("These bytes are already
published with different declared attributes. Available blobs are immutable.") **never
reaches the wire**. The live 409 in 4b carries the generic catalog sentence instead.

**What an operator can tell:** something conflicted; it is a `Blob`; it is not retryable;
a correlation id to search logs with.

**What an operator cannot tell:** *which* blob; what role or media type is recorded against
it versus what was sent; and — the sharp one — **which of two different failures happened.**
Exactly two errors in `src/` carry code `conflict` with `aggregate_type: "Blob"`:

| error | what it means | what the operator should do |
|---|---|---|
| `BlobAttributeConflictError` | recorded role/media type disagree — `D-17`'s restore damage | stop; the instance was restored wrong |
| `TemporaryBlobLostError` | a staged upload vanished between staging and verification | retry the upload |

Their envelopes are **byte-identical apart from `correlation_id`**: same status, same
`error_code`, same `message` (both take the catalog summary), same
`details: {"aggregate_type": "Blob"}`, same `retryable: false`. Two failures with opposite
operator responses, one indistinguishable answer. Note also that `retryable: false` is
correct for one of them and arguably wrong for the other.

**The measured question for the owner** is therefore narrower than "add detail keys": *may
a `conflict` envelope carry a discriminator distinguishing these two, and if so is that a
detail key on `conflict` or a second code?* `R-3`'s `dependency_credential_refused` — added
in round 6 precisely because `permission_denied` meant two unrelated things "and both
declared exactly `aggregate_type` and `required_capability` with no discriminator" — is the
same shape, already ruled once. `D-18` is left open and unchanged here.

## 6. The gate

Instance `gate-w18b`, `POSTGRES_PORT=55810`, `S3_API_PORT=59410`, `S3_CONSOLE_PORT=59411`,
`POSTGRES_DB=audit_w18b`, bucket `auditmanager-gate-w18b`. One measurement, nothing else
running on this lane, no subagents dispatched during it, tree committed and clean before it
started.

```
$ make gate FOUNDATION_PYTHON=/usr/bin/python3.12 > /root/w18ops-logs/gate.log 2>&1
$ echo $?
0
```

**Exit code read from `$?` after the redirect, not through a pipe.**

| | base `3df17a7` | here |
|---|---|---|
| battery | 1746 / 5 skipped / 168 subtests | **1754** / 5 skipped / 168 subtests |
| foundation | 35 | **35** |
| frontend | 592 (44 files) | **592 (44 files)** |

`GATE OK: battery, foundation, frontend and whitespace all pass`.

The battery moves by **+8, and by exactly the eight cases added** to
`test_reset_script_refusals.py` (23 -> 31). Nothing else moved: no `src/`, `web/` or
`contracts/` file was touched.

## 7. What was false in this brief

1. **`DEBT_REGISTER.md` is at `docs/program/DEBT_REGISTER.md`**, not the repository root.
2. **"`reset.sh --restore` and `object_attrs.py` reattach two of the four metadata keys"** —
   they reattach **one** of the four (`content-sha256`) plus the `Content-Type` header,
   which is not one of the four. Section 1.
3. **"`blob-role` is lost"** — true but incomplete. `blob-id` and `content-size` are lost
   too. Section 1.
4. **"That guard already refuses ... a sidecar with an empty digest"** — it does not, under
   GNU grep, which is the grep a deploy host has. Section 2a.
5. **`df -h /` showed ~9.5 GB free on arrival, not ~11 GB**, and 7.9 GB after the `api`
   build. The `web` image was therefore never built and the proxy never started.

Everything else held: the eleven markers, the deletion-based suite, the `docker` stub, the
`database-matches` / `bucket-matches` refusals, `PA-01` criterion 10 being false in the
direction that looks true, and `D-18`'s envelope.

## 8. Elapsed

**Measured, not estimated.** `date +%s` on arrival `1789712704` (2026-09-18T11:25:04+05:00);
at the end of the gate `1789713813` (11:43:33). **18 min 29 s** to a green gate, of which
the gate itself was 3 min 24 s of battery plus 28 s of foundation plus 4 s of frontend.

Cost that is worth recording because the next session will meet it: the `api` image build
was 400 MB on a host with 8.5 GB free, and building `web` as well would have been another
1.2 GB. Skipping `web` and `proxy` cost nothing — the proof is an API-level write — and the
stack was torn down with `docker compose down -v`, leaving the two alpha stacks untouched.

## 9. Not done here, and why

`DEBT_REGISTER.md` **D-17 is left open**. This session owns `infra/deploy/**`,
`tests/integration/composition/test_reset_script_refusals.py` and this review; the register
is not on that list, and two writers on it is how a row gets closed twice. The row's close
belongs to the integrator, with this file as its evidence, and it should record that the
key count in the row is one key too generous. **D-18 is left open and unmeasured in the
register**; section 5 is the measured question it needs.
