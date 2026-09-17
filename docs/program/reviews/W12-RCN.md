# `W12-RCN` — reconciliation proves less than it promises

Session `W12-RCN`, wave 12 stage A. Worktree `/root/w12rcn`, branch `agent/w12-rcn`,
logs `/root/w12rcn-logs/`, instance `gate-w12a` (55650 / 59250 / 59251, `audit_w12a`,
`auditmanager-gate-w12a`). No live provider used.

**HEAD on arrival: `3ebe34dbdeda5873e51c8067d227a4c41e28a025`** — `merge: two tests-only
streams for wave 12 stage A`, the tip of `origin/dev`. The brief says "base `38a973a` or
later"; `3ebe34d` is four commits later on the same line.

I make **no claim about PC-01 or any criterion.** `W12-CERT` follows.

**Elapsed: 11:29:20 to 11:48 +05:00, about 19 minutes wall-clock**, of which the
two full gate runs are roughly 8 and the four mutation-copy suite runs about 1.

---

## 1. The defect, confirmed against the tree

`Reconciler.verify_version` resolved `published = self._store.inspect(entry.blob_id)` — a
`head_object`, which returns what the object *records* — and compared `published.sha256`
and `published.size` against the manifest entry. Both sides are declarations. An object
replaced out of band with its recorded metadata copied verbatim and its length unchanged
satisfies both, and the version was reported sound while `read_source_bytes` refused the
same row. `W11-RD` measured that on real MinIO; I did not re-measure it, I reproduced it
as a red test (§4, M1).

## 2. The shape I chose, and why

**Always hash, in `verify_version` only. `report()` is untouched.**

`verify_version` now asks three questions per manifest entry, cheapest first:

1. **Is anything there?** `BlobNotFoundError` → `storage_integrity_error` with
   `expected_sha256` and no `actual_sha256`. Unchanged.
2. **Can the store vouch for it, and does its record agree with the manifest?** No
   recorded digest → `validation_failed` (§5). A record that disagrees →
   `storage_integrity_error` with the record as `actual_sha256`. Unchanged apart from the
   empty-digest case being lifted out in front of it.
3. **Are the bytes the document the manifest names?** `read(..., verify=False)`, hash,
   compare against `entry.sha256`. **New.**

### Why not "correct the promise"

It would leave the tree with two paths over one row giving two answers, with
reconciliation the permissive one. `src/auditmanager/ingest/service.py:204` states the
opposite as an invariant, in the tree, today: *"the same `storage_integrity_error`, with
the same details, that `Reconciler.verify_version` raises over the same row — one fault,
one answer, whichever path reaches it."* Wave 11 spent a session making that true for the
read path. Renaming the method would make it false again by hand, and would do it for the
exact fault the method exists to find. A reconciler that reports a replaced version as
sound is worse than no reconciler, because an operator acts on the verdict.

### Why not an opt-in `deep=False`

Because the default would be the wrong answer, and defaults nobody passes are how this
programme has been bitten before. `test_reconciliation_rules_with_no_guard.py` exists in
part because `report()`'s `stale_command_age="1 hour"` default was raised to
`"9999 hours"` and nothing failed — *"a default nobody reads is a decision nobody made"*.
A `deep=False` would reproduce that shape precisely: every call site in the tree would
keep getting the declaration-only verdict, the flag would be exercised by nothing, and
the method's name would still over-promise for every caller who did not know to opt in.
An opt-in is the right shape for a check that is *optional*. This one is the method's
entire purpose.

### Why the cost objection does not apply here, stated precisely

The brief and `W12-PLAN.md` §2 both say `reconciliation.py` makes **"never lists, never
reads bytes"** a deliberate property of the module. **Checked against the tree: it does
not.** Two separate things are being run together.

- The *module* docstring's section is headed "Why the scan can work without listing the
  bucket" and its claim is `It never enumerates the store.` That is about **listing**, it
  is about `report()`, and it is still true — I did not touch `report()`, `_object_exists`
  or `_AVAILABLE_WITHOUT_MANIFEST`.
- The sentence `"Never lists, never reads bytes."` is the docstring of
  **`_object_exists`**, the private helper `report()` asks its questions through.
  **`verify_version` does not call `_object_exists`.** It never did; it calls
  `self._store.inspect` directly. So the no-bytes property was never stated about
  `verify_version` at all, and the module has had a cheap half and an expensive half since
  it was written.

Two further facts about the supposed sweep:

- `verify_version` takes **one** `version_uid` and walks **that version's** manifest,
  which is one `source_document` entry for every version P01 and P02 produce. It is not a
  sweep over many versions; `report()` is.
- `grep` over `src/` and `tools/` finds **no caller of `verify_version` and no
  construction of `Reconciler` outside the module itself.** It is an operator entrypoint
  reached only from tests. There is no loop in this repository whose cost this changes.

So the objection is real in general and does not bind this method. The cheap sweep stays
cheap; the verdict gets to mean something. I still measured the price and pinned it
(§3, §4 G3).

### The two causes, and the 21st error code

**I do not need it.** But the brief's instruction not to flatten two causes into one code
cannot be fully satisfied inside the frozen catalog, and that is worth saying plainly.

`contracts/domain/v1/error-codes.json` declares exactly `blob_id`, `expected_sha256`,
`actual_sha256`, `role` for `storage_integrity_error` — **no discriminator**, and
`actual_size`/`expected_size` are deliberately *not* declared for it (`failures.py` names
that as the reason it narrows details at all). So an envelope cannot carry "which
comparison refused". The only way to give the two causes two codes is to move one of them
to `validation_failed`, and the one it would move is "the store's record disagrees with
the manifest" — which `read_source_bytes` answers with `storage_integrity_error` over the
same row. That trade is: satisfy the brief's sentence, break the invariant `service.py`
states. I kept the invariant.

What I did instead, which is the discrimination convention this suite already uses (an
absent object reports no `actual_sha256`; a disagreement reports both digests):

- the two comparisons are **separate, ordered, and separately guarded** — each has a test
  that reddens when it alone is removed (§4);
- **`actual_sha256` names the strongest fact the refusal established** — the store's
  record when nothing was read, the digest of the bytes when they were — and the two can
  never contradict each other, because the body check runs *only* when the record and the
  manifest already agree;
- the docstring says which question produced which refusal.

If the owner ever unblocks the 21st code, **this is the clearest use for it I found**: a
code meaning "the store's own record of this object is not usable evidence", distinct
from "the bytes are not the document". It would let the residual case in §6 be answered
honestly on both paths at once. I did not need it to land this repair.

## 3. What an operator observes differently

| | Before | After |
|---|---|---|
| `verify_version`, healthy, AR baseline (59 014 B) | one `head_object` | `head` + full body + SHA-256 |
| — measured, median of 20 | **2.08 ms** | **4.11 ms** (×2.0) |
| `verify_version`, healthy, 25 MiB object, median of 5 | **2.23 ms** | **50.10 ms** (×22.5) |
| `report()` (the sweep) | `head` only, never a body | **unchanged** |
| a version replaced under intact metadata | returns, **reported sound** | `storage_integrity_error` |
| a version whose object records no digest | `storage_integrity_error`, `actual_sha256=""` | `validation_failed`, `field="sha256"` |

Method: `/root/w12rcn-logs/cost_probe.py`, against this lane's live MinIO over loopback,
through the real adapter, at commit `1b2549b`; log `/root/w12rcn-logs/cost.log`. It times
`inspect` against `inspect + read(verify=False) + sha256_of` — the marginal cost of the
repair per manifest entry — and purges by exact identity afterwards. **The cost of
`verify_version` is now proportional to bytes rather than to rows.** At P01/P02 sizes
that is two milliseconds; on an object three orders of magnitude larger it is fifty.

Three more things an operator sees:

- **New refusals appear that did not before.** Running `verify_version` over a bucket that
  was restored from a bad backup can now fail where the same command passed last wave.
  That is the repair, not a regression, and it is the point.
- **`actual_sha256` has two meanings now**, told apart by which comparison fired. Before,
  it was always the store's record. A dashboard that read it as "what the store claims"
  will sometimes now be reading "what the bytes actually are" — which is the more useful
  of the two, and is what `read_source_bytes` has always put there.
- **The unstamped-object envelope loses `blob_id` and `role`.** `validation_failed`
  declares `field`, `constraint`, `aggregate_type` and nothing else, so the operator is
  told *which kind* of fault and not *which object*. I added `aggregate_type="Blob"` so it
  at least names the aggregate, and the `DomainError` still carries the rest for a log.
  This is the same trade wave 11 accepted for `read(verify=True)`, and taking it keeps the
  two paths answering alike.

**No stored row observes anything differently.** `verify_version` writes nothing, and
nothing in `src/` calls it, so no `command_record`, `blob` or version row changes. No
schema change, no migration, no contract change.

## 4. The guards, each shown red without the repair

`make mutation-copy MUT=/root/w12rcn-mut` (symlinked form; nothing here mutates a
contract, a fixture or a migration). **The unmutated copy was baselined first: 82 passed**
(`/root/w12rcn-logs/mut-baseline.log`), with `auditmanager.__file__` printed and confirmed
to resolve to `/root/w12rcn-mut/src/auditmanager/__init__.py`. After the three mutations
the copy was restored, proved byte-identical to the worktree, and re-baselined green at 82
— so each red below is attributable to its mutation and not to drift.

Each mutation was **read back for meaning, not text**: `/root/w12rcn-logs/mutate.py` parses
the mutated file, finds `Reconciler.verify_version` in the AST, and prints the set of calls
it makes and every `if` test it contains. Transcripts in `/root/w12rcn-logs/mutate-M*.txt`.

| | Mutation | Read back as | Result |
|---|---|---|---|
| **M1** | delete the read-hash-compare block — *the pre-wave-12 defect exactly* | calls lose `read` and `sha256_of`; the `actual_sha256 != entry.sha256` test is gone | **2 failed, 80 passed** |
| **M2** | `if not published.sha256:` → `if False:` — *the D-4 defect* | first `if` test is the literal `False` | **1 failed, 81 passed** |
| **M3** | move the declaration comparison to *after* the read | `published.sha256 != entry.sha256 …` now follows `actual_sha256 != entry.sha256` | **2 failed, 80 passed** |

What each red says:

- **M1** → `test_a_version_whose_bytes_were_replaced_under_intact_metadata_is_refused`:
  `Failed: DID NOT RAISE DomainError`. That single line is the defect: the replaced
  version is reported sound. Also
  `test_the_body_is_read_once_per_entry_and_not_at_all_when_the_record_already_fails`:
  `assert [] == ['blob_0RXA056HW1E75HSMQ2Y63Y5CX2']` — no body was transferred.
- **M2** → `test_a_version_whose_object_records_no_digest_is_not_an_integrity_verdict`:
  `assert <ErrorCode.STORAGE_INTEGRITY_ERROR> is <ErrorCode.VALIDATION_FAILED>`. The
  envelope is back to being an integrity verdict, and it is the one that carried
  `actual_sha256=""`.
- **M3** → the cost guard: `assert ['blob_6QJFN1BCW9ZY1Y2TT4JT9RMP52'] == []` — a body was
  fetched for a row the record had already failed. **It also reddens an existing wave-10
  test**, `test_a_version_whose_stored_size_disagrees_with_its_manifest_is_refused`
  (`assert '7383109f…' == '0afd4e7b…'`): with the body read first, that test's pinned
  `actual_sha256 == honest_sha256` becomes the hash of the truncated bytes. So the
  ordering I chose is the one the existing suite already assumed, and M3 is the mutation
  that proves the two existing wave-10 assertions still pin their own halves of the
  declaration comparison under the repair.

All three guards are in one new file, `tests/integration/ingest/
test_reconciliation_reads_the_bytes.py`. Every expected value is a literal or is computed
from bytes the test built; nothing is imported from `reconciliation.py` and compared to
itself. No test in this session scans source text, so the `auditmanager.__file__` rule did
not arise — the `__file__` printed above is a check on the *copy*, not an assertion.

**Nothing was added to a frozen corpus.** All three tests build their bytes in-process by
appending a unique comment after `%%EOF`, the way `_unique_pdf` already does, and register
every blob for teardown by exact identity.

## 5. D-4 — disposition: repaired

Against an object recording no digest, `inspect` returns `PublishedBlob(sha256="")`
(`s3.py:_record_from_head`, `sha256=recorded_sha or ""` — confirmed), the declaration
comparison fired because `"" != entry.sha256`, and `actual_sha256=""` went into the
envelope. Two things wrong with it: an empty string where an operator reads a digest, and
a claim about bytes nothing had looked at.

`verify_version` now refuses such an object *before* the comparison, as
`validation_failed` with `field="sha256"`, `constraint="recorded on every published
object"`, `aggregate_type="Blob"`. That is the same code and the same reasoning wave 11
gave `read(verify=True)` for the same row: the store has compared nothing to anything, so
"this store cannot vouch for this object" and not "these bytes are corrupt". In the guard
the bytes are in fact the right bytes, asserted through the independent client — telling
an operator the document is corrupt would send them to restore a backup they do not need.

`field="sha256"` and not `"content-sha256"`: `Reconciler` holds a `BlobStore`, reads
`PublishedBlob.sha256`, and has no business naming an S3 user-metadata key. The read
path's `field="content-sha256"` is raised *inside* the adapter, where that name is the
adapter's own. Same code, same category, different layer's spelling of the same field.

The test asserts the defect directly: `"actual_sha256" not in envelope.details` and
`"" not in set(envelope.details.values())`.

## 6. Not repaired, and why

- **The residual case: the store's record is wrong and the bytes are right.** After the
  repair the method *could* read the body, discover the document is intact, and report
  something more precise than "integrity failure". It does not: the declaration comparison
  still refuses it as `storage_integrity_error` with the record as `actual_sha256`, as it
  did before. Reason: `read_source_bytes` answers that same row with
  `storage_integrity_error` too (via the adapter's `ChecksumMismatchError`), so making
  reconciliation say `validation_failed` would split one fault into two answers again.
  Changing both paths together is a repair for a wave that owns both files; this one owns
  neither the adapter nor the service.
- **`src/auditmanager/ingest/service.py:210`** — *"`verify_version` compares both because
  it compares two declarations, where the size is recorded independently of the digest."*
  Still true of the declaration comparison and now an incomplete description of the
  method. Outside my owned paths. **Reported, unrepaired.**
- **`s3.read(verify=True)` reports `expected_sha256` = the object's own recorded digest.**
  On a row whose metadata was rewritten, that names a value nothing ever promised, and an
  operator reading it would think the manifest asked for the rewritten digest. Outside my
  owned paths. **Reported, unrepaired.** It is the read-path half of the residual case
  above and they should be looked at together.
- **D-3** (`_record`'s defaulted `cost_basis`) — not mine, and `W12-PLAN.md` §5 keeps it
  open deliberately.

## 7. Premises in the brief, checked against the tree

| Premise | Verdict |
|---|---|
| `verify_version` at `reconciliation.py:203` calls `inspect` and compares `published.sha256` to `entry.sha256` | **True**, verbatim, at `3ebe34d` |
| `inspect` is a `head_object` returning recorded metadata | **True** (`s3.py:299`, `_head` → `head_object`) |
| The docstring's first sentence over-promises and its second is accurate | **True** |
| `reconciliation.py` makes **"never lists, never reads bytes"** a deliberate property of the module | **False as stated, and it is the load-bearing premise of the design call.** The module's stated property is `It never enumerates the store` — about *listing*. `"Never lists, never reads bytes."` is `_object_exists`'s docstring, and **`verify_version` does not call `_object_exists`**. The no-bytes property was never claimed for the method being changed |
| `verify_version` is "a cheap sweep over many versions" (dispatch STEP 3) | **False.** It takes one `version_uid` and walks that version's manifest — one entry in P01/P02. `report()` is the sweep. And `grep` finds **no caller of `verify_version` and no `Reconciler(...)` anywhere in `src/` or `tools/`**: it is reached only from tests, so no in-tree loop pays this cost |
| `inspect` yields `sha256=""` against an unstamped object (D-4) | **True** — `sha256=recorded_sha or ""` |
| Gate is 1492 passed / 5 skipped / 163 subtests | **True**, exact, measured on arrival |
| Frontend 289 | **True**, measured: 289 passed across 24 files |
| A linked worktree has no `web/node_modules`; `npm --prefix web ci` once | **True**; 184 packages |
| `make mutation-copy MUT=…` works and links five directories | **True**; the unmutated copy baselined 82 on my suite |
| Base `3ebe34d` or later; `origin/dev` carries the brief | **True** |
| The 21st code is avoidable | **True** — see §2. It is avoidable; the brief's "two causes, two codes" instruction is what is not, inside the frozen catalog |

**One thing the brief does not say and the next session should know:** `make gate` fails
if the checkout changes *during the run* — `tests/integration/foundation/conftest.py:558`
compares `git status --porcelain` before and after and refuses any difference. My first
gate run failed on `?? tests/integration/ingest/test_reconciliation_reads_the_bytes.py`
because I created the file while the gate was running. It is not a dirty-tree check; it is
a "the suite must not change the checkout" check, and a session editing its own tree
mid-run trips it. **Do not edit while the gate runs.** Commit, then gate.

## 8. The gate

| | Result |
|---|---|
| on arrival, `3ebe34d` | **1492 passed / 5 skipped / 163 subtests**, frontend **289** — exactly the brief's figure |
| at `d1bcace`, after the repair | **`GATE OK`** — 1495 passed / 5 skipped / 163 subtests in 205.87 s, frontend 289 passed (24 files) |

`1495 = 1492 + 3`: the three new guards, and no existing test changed its verdict. I
changed no existing test — the two wave-10 assertions on the declaration comparison pass
verbatim under the repair, which is itself part of the argument for the ordering (§4, M3).
Logs: `/root/w12rcn-logs/gate-baseline.log`, `/root/w12rcn-logs/gate-final.log`.

## 9. Constraints

Files changed, all owned:

```
src/auditmanager/ingest/reconciliation.py
tests/integration/ingest/test_reconciliation_reads_the_bytes.py   (new)
docs/program/reviews/W12-RCN.md
```

No root dependency (`requirements/` untouched, `P02_LOCK.json` untouched). No byte added
to `fixtures/synthetic/ar/**` or `fixtures/validation/PC-02/**`. No tag, no push, no merge
to `main`. Instance/ports/bucket exactly as assigned; no other lane's containers touched.
No live provider used. I did not coordinate with the two tests-only streams and touched
none of their paths.
