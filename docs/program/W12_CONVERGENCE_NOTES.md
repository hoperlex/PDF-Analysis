# Wave 12 — convergence notes, written as the streams land

Integrator's running record, committed as each stream reports. **One of three stage-A streams
has landed; `W12-WEB` and `W12-DEC` are still running and nothing is merged** — convergence is
one act and the gate runs alone.

## The eleventh stale premise, and it was the foundation of the brief

`W12-RCN` was dispatched with a **design call**: repair `verify_version` or correct its
promise, because `reconciliation.py` makes *"never lists, never reads bytes"* a deliberate
property and converting the method to a full-body read changes what a cheap sweep costs.

**Every load-bearing part of that sentence was wrong.** Verified by me against the tree:

| My brief said | The tree says |
|---|---|
| the module makes "never lists, never reads bytes" a deliberate property | it is the docstring of **`_object_exists`**, a private helper at line 273 |
| that property constrains `verify_version` | `verify_version` **does not call `_object_exists`** — it calls `self._store.inspect` directly, and always has |
| `verify_version` is a cheap sweep over many versions | it takes **one** `version_uid` and walks one manifest. `report()` is the sweep |
| the cost objection is real and binding | **`verify_version` has no caller in `src/` or `tools/`** — three doc mentions, zero invocations. There is no loop paying the cost |

I attributed a private helper's docstring to the method being changed, and called a
single-version check a sweep. That did not merely mislead: **it manufactured a design dilemma
that did not exist.** The session could have been sent straight at the repair with the cost
question already answered.

It is the worse half of a pattern this programme keeps finding — a claim written at one scope
and read at another. Wave 11 repaired two comments that said a safety check was absent when it
was present; this is the same shape, made by me, in a brief.

**The session did not inherit it.** It checked, corrected it, and then argued its choice on
independent grounds — the invariant `ingest/service.py:204` states, *"one fault, one answer,
whichever path reaches it"*, which wave 11 spent a session making true. Correcting the promise
instead of the code would have made that false by hand, for the exact fault the method exists
to find. That argument stands whether or not my cost premise was sound, which is why the
repair survives the brief being wrong.

## `W12-RCN` — landed, not merged

Always hash, in `verify_version` only; `report()` untouched and still never reads a byte.
Three questions per manifest entry, cheapest first, with the body check running **only when
the record and the manifest already agree** — so the two comparisons can never contradict.

D-4 repaired: an object recording no digest is now `validation_failed` before the declaration
comparison, instead of an integrity verdict carrying `actual_sha256=""`.

Three mutations, each read back **through the AST** rather than by text, on a copy baselined
green at 82 first and proved byte-identical after. M3 — reordering the comparisons — reddens
an existing wave-10 test as well, so the chosen order is the one the suite already assumed.

Cost measured on live MinIO rather than estimated: AR baseline 2.08 → 4.11 ms, a 25 MiB object
2.23 → 50.10 ms. **Proportional to bytes rather than rows**, which is the honest way to state
it.

Gate after the repair: **1495 passed / 5 skipped / 163 subtests**, `GATE OK`.

## Carried forward for the next brief

**`make gate` fails if the checkout changes during the run.**
`tests/integration/foundation/conftest.py:558` compares `git status --porcelain` before and
after and refuses any difference — it is not a dirty-tree check, it is a *changed-during-the-
run* check, so a session that creates a file while the gate runs trips it. **Commit, then
gate.** No brief has said this and one session has now lost a gate run to it.

## Reported back, unrepaired, and they belong together

1. The residual case — **record wrong, bytes right** — still answers `storage_integrity_error`
   with the record as `actual_sha256`, because `read_source_bytes` answers that row the same
   way and splitting them would recreate what wave 11 removed.
2. `s3.read(verify=True)` reports `expected_sha256` as the object's **own** recorded digest —
   on a rewritten-metadata row that names a value nothing ever promised.

These are two halves of one thing and need a wave owning both the adapter and the service.

## On the frozen catalog

`storage_integrity_error` declares `blob_id, expected_sha256, actual_sha256, role` and **no
discriminator**. So "two causes, two codes" — which my brief asked for — cannot be fully
satisfied inside the frozen catalog without moving one cause to `validation_failed` and
breaking the invariant `service.py:204` states. The session kept the invariant and made the
comparisons separate, ordered and separately guarded instead. **If the owner ever unblocks the
21st error code, this is the clearest use for it the programme has found.**
