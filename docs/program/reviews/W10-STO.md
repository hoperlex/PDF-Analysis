# `W10-STO` — mutation sweep of `storage/` and `documents/`

Integrator's own stream in wave 10. Base `e08da85`. **In progress**; this file is committed
as the sweep runs rather than at the end, because the first attempt at this wave lost four
dispatched sessions to a restart and the only thing that survived was what had been
committed.

Tree chosen because `storage/` and `documents/` have **zero commits since the PC-01
acceptance** — measured, not recalled. They are the only trees in the repository the
integrator has never touched.

## Method

Every constant and refusing branch mutated on a copy at `/root/w10sto-mut`, with
`contracts/`, `docs/` and `fixtures/` symlinked in and `auditmanager.storage.models.__file__`
printed and confirmed under the copy before any result was trusted. Each mutation run against
`tests/integration/storage` and, where the rule could plausibly be reached through upload,
`tests/integration/ingest` as well.

Baseline: `tests/integration/storage` 44 passed; with `ingest`, 109 passed.

## Sweep table

| # | Mutation | Result |
|---|---|---|
| M-A | `_CROCKFORD_ALPHABET` widened to full A–Z (admits I, L, O, U) | **22 failed, 10 errors** — well guarded |
| M-B | `TEMPORARY_PREFIX` `"temporary/"` → `"blobs/"` | **green — GAP** |
| M-C | `_ROLE_PATTERN` → `^.*$` (any string is a role) | **green — GAP** |
| M-D | drop the required-variable check in `settings.py` | **2 failed** — guarded |
| M-E′ | drop the unknown-detail-key refusal in `StorageError.__init__` | **1 failed** — guarded, but by a single test |
| M-F | `CANONICAL_PREFIX` `"blobs/"` → `"temporary/"` | **2 failed** — guarded |

### A false green I nearly recorded

M-E was first written as `frozenset() or frozenset({...})`, which evaluates to the **right**
operand — the real set. The mutation was a no-op and the green meant nothing. Caught by
reading the expression rather than the result. Re-run as M-E′ against the actual refusal in
`StorageError.__init__`, which does redden.

Recorded because it is the same class as wave 9's failure: a mutation that does not mutate
and a test that cannot discriminate produce identical evidence.

## Findings

**M-B — the staging prefix can collide with the canonical one and nothing notices.**
Publication is two-phase: bytes are staged under `temporary/` and promoted to `blobs/` only
after the digest and size are verified. Collapsing the prefixes means a corrupt upload's
staged object occupies the canonical location. Note the asymmetry with M-F: moving the
*canonical* prefix reddens two tests, so the tests pin where a published object lands and say
nothing about where an unverified one is held.

**M-C — any string is accepted as a blob role.** `_ROLE_PATTERN` requires
`^[a-z][a-z0-9_]{2,63}$`; nothing exercises a value outside it.

## Guards, and the mutations that prove them

`tests/integration/storage/test_two_namespaces_and_a_role_vocabulary.py`, 16 tests.

| Mutation | After the guards |
|---|---|
| M-B `TEMPORARY_PREFIX` → `"blobs/"` | **RED ×3** |
| M-C `_ROLE_PATTERN` → `^.*$` | **RED ×9** |
| M-G `TEMPORARY_PREFIX` → `"blobs/tmp/"` | **RED ×2** |

M-G was not in the original sweep and is the case worth having. Both classifiers use
`startswith`, so one prefix being a **sub**-prefix of the other breaks disjointness without
either constant being equal to the other. `test_neither_prefix_is_a_prefix_of_the_other`
exists for exactly that, and the two directional tests catch it independently.

Expected values are **literals**, not imports. The prefixes are an on-disk layout: changing
either renames every object already published, so it should be a deliberate migration and a
red test rather than a constant edit nothing notices.

`_object_layout` is private and not exported from the package, so the disjointness invariant
has no public surface — **which is part of why nothing was guarding it**. The test reaches
into the private module deliberately and says so; refusing to look would leave the invariant
unguarded for the same reason it already was.

The role vocabulary gets ten negative cases and two boundary cases. Without the boundaries —
three characters and sixty-four both accepted — the rule could be implemented far more
narrowly and every negative case would still pass.

## Not repaired

Nothing in `storage/` or `documents/` was found wrong. Both findings are missing guards over
correct behaviour, so this stream reports **no product defect**.

One observation short of a defect: **M-E′ is guarded by a single test.** Dropping the
unknown-detail-key refusal in `StorageError.__init__` reddens exactly one case, and that
refusal is what keeps bucket names and object keys out of caller-visible errors — the
comment in `errors.py` says they are "deliberately absent from the vocabulary". One test is
thin for a leak surface. Left as an observation rather than padded into a finding; the
`shared/errors` half of the same surface belongs to `W10-API`, which is sweeping it.
