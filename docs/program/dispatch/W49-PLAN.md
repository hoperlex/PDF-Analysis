# Wave 49 — verified normative corpus promotion

**Status:** queued behind `alpha-w48`; not dispatchable.
**Release target:** `alpha-w49`, bound to both an exact code SHA and a retained data manifest.
**Product boundary:** internal data-plane only; no public corpus-backed route or screen.

## 1. Objective and demonstrable result

W49 turns the already accepted normative designs into a recoverable alpha data-plane. At the
end of the wave, and only if every gate is green:

- all 674 source PDFs and 28,246 crop inputs are accounted for by confirmed immutable custody
  bindings, with no implicit filesystem serving dependency;
- all 121 ruled pages have an immutable, provider-measured repair outcome and no page disappears
  through a fallback;
- one repaired canonical snapshot is loaded atomically into PostgreSQL with fresh measured
  counts and digests;
- one complete `bge-m3-dense-v1` embedding build for that exact repaired snapshot is visible in
  pgvector, while incomplete builds remain invisible;
- backup, restore, dispatcher retry and reconciliation are exercised against the same code and
  storage topology used by alpha;
- a checkpoint manifest binds code SHA, deployment SHA, storage version, object inventory,
  repair ledger, snapshot and embedding build.

W49 does **not** expose search. It creates the evidence W50 needs before W50 may define an exact
retrieval/citation contract or make an audit run pin and consume a normative snapshot.

## 2. Why this is not yet the search wave

Four facts prevent an honest end-to-end retrieval release today:

1. The corpus has been projected read-only but not promoted to the alpha database or private
   object store.
2. The 121 source defects precede paid embedding; their corrected output changes content keys,
   paragraph/chunk counts and the number of tokenizer windows.
3. The BGE bake-off used a warm isolated environment. It did not measure cold model load,
   single-query latency, full HNSW recall or index overhead on the target runtime.
4. `NORM-Q04` authorizes internal use with attribution, not an externally available
   corpus-backed feature.

Adding a route first would either search a missing/stale snapshot or create an external release
right the programme has explicitly not claimed.

## 3. Entry conditions

| Gate | Required evidence | If absent |
| --- | --- | --- |
| W48 released | `alpha-w48` names the exact `origin/dev` candidate that was separately authorised for `origin/main`; deployed verification and public manual pass are attached | do not freeze W49 |
| clean base | no pending task or unowned working-tree change; full `make gate` prints `GATE OK` | stop |
| D-70 live provider | alpha acceptance A04 records `provider_mode=live`; endpoint and credential are supplied only through the approved secret boundary | repair execution blocked |
| source inventory | read-only inventory proves 674 PDFs, 28,246 crops and stable input digests without committing source bytes | custody batch blocked |
| alpha backup capacity | PostgreSQL backup, MinIO inventory and free-space estimate cover source/crop admission plus retained pre/post state | external mutation blocked |
| internal-only boundary | routing, authentication and deployment configuration expose no normative corpus consumer | release blocked if violated |

Entry does not pretend the two owner choices in §4 are already answered. It permits only the
freeze and decision slots that make them answerable.

## 4. Stage 0 — freeze and owner decisions

### `W49-FREEZE-01` — exact successor base

**Depends on:** completed `W48-INT-CLOSE`.

Records the exact `alpha-w48` SHA, re-measures the frozen API/domain/error/migration set, captures
source inventory without content, and creates every executable W49 task file from
`TASK_TEMPLATE.md`. It owns only W49 programme documents and integration bookkeeping; it cannot
push `main`, mutate alpha or edit product code.

Freeze stops if W48 introduced a contract, migration or storage fact that this plan assumes
unchanged. Symbolic candidate paths below become exact file lists here.

### `W49-DECIDE-01` — two decisions that code cannot make

**Depends on:** `W49-FREEZE-01`.

The owner records both choices before implementation dispatch:

1. **D-119 storage lifecycle:** rehearse and accept the source-pinned final MinIO security
   release, or select and qualify another S3-compatible implementation. Custody writes cannot
   enlarge an unmaintained storage commitment first and ask the question later.
2. **Blob identity conflict:** the current product contract describes `blob_id` as derived from
   `(sha256, size)` and re-upload as content-idempotent, while `NORM-Q05` requires every PDF and
   crop admission — even equal bytes — to receive its own `blob_id`. The owner must choose a
   coherent contract: reseal Blob identity across all consumers, or revise the custody ruling
   and introduce a distinct admission identity while preserving content Blob semantics.

The same task freezes the retry ceiling/poison transition, confirms full retention/no TTL, and
reaffirms that corpus-backed external release remains forbidden. It records trade-offs; it does
not hide either decision in a migration implementation.

## 5. Stage A — measurement and contract seal

After `W49-DECIDE-01`, the two lanes below may run in parallel because one writes only a report
and the other owns the complete shared contract/migration slot.

### `W49-RUNTIME-EVAL` — target-like BGE and pgvector measurement

**Outcome:** a report selects a reproducible offline worker boundary for the fixed BGE profile.

**Allowed path:** `docs/program/reviews/W49-RUNTIME-EVAL.md` only. Temporary environments,
download caches and generated vectors remain outside the repository.

**Required measurements:** exact model artifact/revision/license and digest inventory; cold and
warm load; single-query p50/p95; batch throughput; peak RSS; full repaired-or-base rehearsal
window build time; PostgreSQL rows/index bytes; exact-scan versus HNSW recall at declared
parameters; restart behaviour; and a no-network inference run from the packaged artifact.

The existing 4.866-second 24-query batch is not accepted as interactive latency. The existing
1.252 passage windows/s and 3,177.9 MiB peak RSS are planning baselines, not a pass threshold.
Any dependency/image recommendation remains isolated and pinned; it does not edit a root lock.

### `W49-CUSTODY-SEAL` — one identity and migration owner

**Outcome:** the chosen identity model, custody state machine, persistence schema and caller-safe
faults are frozen before code branches.

**Sole ownership:** the exact domain contract files affected by `W49-DECIDE-01`, their generated
domain consumers, the next migration (expected `0014`, re-measured at freeze), custody schema
tests and decision/current-state records. Public API operations remain 17/20/61 unless a new
owner ruling explicitly replans the wave.

The migration must represent intent/outbox, independent target/anchor, expected checksum/size/
media type, attempt/poison state, confirmation and visible binding. It must preserve the
invariant that neither object existence alone nor a pending database row is publication.
Fresh-upgrade, existing-volume upgrade and retained-data downgrade refusal are required.

`W49-JUDGE-A` attacks this seal before storage or corpus implementation starts.

## 6. Stage B — two exclusive implementation lanes

Both lanes start from the accepted seal and runtime report. Their exact files are disjoint at
freeze; neither has alpha credentials or remote-ref authority.

### `W49-STORAGE` — maintained object store plus recoverable custody

**Sole ownership:** `src/auditmanager/storage/**`, the concrete custody dispatcher/reconciler
adapters, `infra/minio/**` or the owner-selected successor, its exact compose entries, focused
storage/migration integration tests and operator storage runbook. It owns no norms projection,
provider, public API, UI or root application dependency.

**Deliverables:**

- D-119's chosen source/image pin and an upgrade rehearsal from a restored alpha-volume copy;
- intent dispatcher with bounded retry, read-back SHA/size/media verification and idempotent
  confirmation in a second transaction;
- reconciler outcomes for missing staging, checksum mismatch, verified/unconfirmed object,
  confirmed/missing object, poison and orphan;
- private object-key layout that no caller or domain identity can observe;
- exact replay returning the same result and conflicting replay writing nothing.

### `W49-CORPUS` — one owner for batch, repair, load and embedding tools

**Sole ownership:** exact files under `src/auditmanager/norms/**`, `tools/norms/**`, a dedicated
offline embedding-worker image/lock area, focused norms tests and the corpus-promotion runbook.
It does not own storage internals, the sealed migration/contract, public API/UI, raw corpus bytes
or root dependency locks.

**Deliverables:**

- a resumable inventory-to-custody command that creates intents but never direct-writes S3;
- a repair command that reads only confirmed crop bindings, accounts for all 121 targets,
  writes the immutable ledger after every attempt and records cost after every provider call;
- fail-closed handling for degenerate, truncated, too-short and source-mismatched output;
- a DB-only repaired-snapshot promotion command whose replay returns the same IDs and whose
  conflict rolls back the whole transaction;
- a pinned, no-network-at-runtime BGE worker that writes through the existing transaction-local
  embedding repository and makes only complete builds visible;
- dry-run/inventory modes that emit digests and counts, never corpus text or credentials.

The USD 5 ceiling is a hard resumable stop. All 121 rows must have an explicit terminal outcome.
Promotion requires 121 acceptable applied repairs; any unresolved outcome blocks it unless the
owner records a new, narrower ruling. Keeping old bad text silently is not acceptance.

## 7. Counts and identities after repair

The base facts remain immutable historical evidence:

```text
674 documents
348,777 canonical paragraphs
55,702 character chunks
62,325 BGE windows
content key 2026-07-23..2026-08-20+17d.4b74348debf7
```

W49 must not assert those same projection counts for repaired text. The repair can change text
length, segmentation, chunk packing and tokenizer windows. Acceptance records a new content key,
opaque snapshot ID, document/paragraph/chunk/window counts, projection digest and build digest
computed from the repaired source. Document membership is expected to remain 674; any difference
is a stop and investigation, not an automatic correction.

IDs remain opaque and exact replay must reuse them. Path, filename, source reference, object key,
checksum and display ordinal remain attributes, never identity.

## 8. Stage C — disposable full rehearsal and judging

The integrator first combines the accepted seal, storage and corpus lanes on one candidate SHA.
All stateful tests use disposable PostgreSQL/S3 instances and a private copy of the inventory.
No alpha mutation occurs here.

Required rehearsal, in order:

1. upgrade a restored storage/database copy and prove all pre-existing objects still read;
2. interrupt custody before object write, after object write and before confirmation; resume and
   reconcile each state;
3. admit the complete PDF/crop inventory twice; the second pass creates no new admission;
4. run repair with a deterministic provider fixture, forced timeout and budget stop/resume;
5. load the repaired projection twice and inject a conflicting digest;
6. interrupt embedding before completion, resume/rebuild and prove incomplete rows are invisible;
7. restart services, reconcile, restore from backup and compare the whole manifest.

`W49-JUDGE-X` and `W49-JUDGE-Y` then inspect the same SHA from different entry points and
cross-examine each other. Only the integrator may open one bounded `W49-FIX` slot for upheld
release blockers, with newly explicit paths and repeated mutations.

## 9. Ownership matrix

| Shared hotspot | Sole W49 owner | Parallel writer |
| --- | --- | --- |
| W49 task files and frozen base | `W49-FREEZE-01` | none |
| owner decisions / decision backlog | `W49-DECIDE-01` | none |
| affected domain identity contract/generated domain consumer | `W49-CUSTODY-SEAL` | none |
| migration head / next custody migration | `W49-CUSTODY-SEAL` | none |
| storage adapters, dispatcher, reconciler, S3 image/composition | `W49-STORAGE` | none |
| norms batch/repair/load/embed tools and dedicated worker packaging | `W49-CORPUS` | none |
| public API/router/UI/global styles | frozen, no owner | none |
| root dependency/lock files | frozen, no owner | none |
| whole-tree repair after judges | `W49-FIX`, only explicit upheld paths | none |
| alpha DB/S3/provider, final `origin/dev`, tag | `W49-INT-CLOSE` | none |
| `origin/main` auto-deploy publication | separately assigned integration task after direct owner instruction | none |
| judge reports | each named judge, report-only | none |

If exact file enumeration reveals overlap between `W49-STORAGE` and `W49-CORPUS`, freeze moves
the seam to one owner or serializes a named handoff. It does not let both tasks write it.

## 10. Automated acceptance gate

At minimum, the final code candidate must show:

```text
make gate                                      -> literal GATE OK
fresh PostgreSQL upgrade                       -> exact sealed head
restored-copy PostgreSQL + object-store upgrade -> all retained reads green
custody fault/retry/reconcile suite             -> no partial visible binding
norm repair/load/embed integration suite         -> all mutations green
dedicated worker no-network inference            -> exact frozen profile
full disposable inventory rehearsal              -> expected input inventory, zero silent skips
git diff --check and clean git status             -> green
```

The gate remains credential-free. Live provider and alpha data operations are release steps
with separately signed evidence; a missing credential is `BLOCKED`, never `SKIP` or `PASS`.

## 11. Alpha promotion and checkpoint sequence

`W49-INT-CLOSE` owns final development publication and mutable alpha work after deployment is
separately authorised. It executes this serialized sequence:

1. Freeze the final clean candidate SHA; run the full code gate and disposable rehearsal.
2. Fast-forward `origin/dev`; prove equality to the gated SHA.
3. Back up alpha PostgreSQL and object storage, capture inventory/digests and prove a disposable
   restore before any upgrade.
4. Stop and report the exact development candidate. Only after a separate direct owner
   instruction may an assigned integration action re-read `origin/main` and fast-forward that
   exact candidate. Auto-deploy may install code/schema only: it must not import corpus, call the
   provider or build embeddings.
5. Verify the deployed SHA and schema/storage version; prove existing alpha objects and PC-01
   still work.
6. Run the custody batch to convergence: 674 PDF inputs and 28,246 crop inputs each have an
   explicit confirmed or failed status; release requires zero failed/unresolved bindings.
7. Price the 121-page provider plan before spend. Run/resume it under the USD 5 ceiling, recording
   each cost and ledger transition without logging body text or credentials.
8. Validate 121 acceptable ledger outcomes, derive the new content key, then atomically load the
   repaired snapshot. A mismatch publishes nothing.
9. Build embeddings in the isolated worker, verify the complete-build digest/count/index, and
   expose no incomplete build.
10. Restart/reconcile, run read-only integrity checks, PC-01 regression and a second backup/restore
    comparison. Confirm there is still no corpus-backed public route.
11. Commit the redacted checkpoint manifest, re-run documentary guards, and create/push annotated
    `alpha-w49` at the exact deployed code SHA only after all data evidence is accepted.

The tag alone never claims mutable data state. The retained checkpoint manifest is the binding
between that tag and the measured snapshot/build/object inventory.

## 12. Checkpoint manifest

The final manifest contains no source text, URLs with credentials, provider bodies or object
keys. It records:

- code candidate, `origin/dev`, `origin/main`, workflow and deployed SHAs;
- API/domain/error counts and exact migration head;
- object-store implementation/release and configuration digest;
- expected/confirmed/failed counts separately for PDFs and crops plus inventory digest;
- repair base snapshot, ledger version/digest, 121 outcome counts, measured calls and total cost;
- repaired content key, opaque snapshot ID, fresh document/paragraph/chunk counts and digest;
- embedding profile/revision, complete build ID/digest, fresh window count, index bytes and
  exact-scan/HNSW measurement;
- backup IDs/digests, restore/restart/reconciler outcomes and timestamps;
- explicit assertion that search/API/UI/run pinning remain absent.

## 13. Rollback and forward recovery

- Before custody data exists, failed code/storage rehearsal is reverted normally and no alpha
  state changes.
- After intent creation, retry/reconciliation resumes the same identity; it never allocates a
  replacement silently.
- A provider or budget stop leaves confirmed custody intact and a resumable immutable ledger;
  no snapshot is promoted.
- Snapshot loading and embedding visibility are each all-or-nothing transactions. An aborted
  build is private rebuildable state and cannot be selected by consumers.
- Full retention means confirmed Blobs, snapshots and repair ledgers are not deleted for rollback.
  After promotion, recovery is forward repair or restore to a separately named environment,
  never destructive downgrade against retained data.
- A failed post-main alpha operation leaves W49 untagged. Recovery uses a new gated commit or
  resumable operator command; branches are never force-pushed and evidence is never rewritten.

## 14. Stop conditions

Stop the affected stage when:

- D-119 or Blob identity has no signed owner decision;
- public API count changes, a new external route appears or licensing scope expands;
- any code path directly dual-writes PostgreSQL plus object storage;
- alpha runtime reads `.local/norms/corpus/**` or downloads a floating model;
- an input is missing, extra or silently deduplicated contrary to the sealed identity model;
- any of 121 repairs is unaccounted, unacceptable or would exceed USD 5;
- repaired digests/counts are assumed from the base rather than measured;
- model/runtime resource use exceeds the accepted target envelope;
- incomplete binding, snapshot or embedding build is visible;
- restore, reconciliation, exact-SHA deployment or PC-01 regression fails.

## 15. Following wave

W50 is the earliest candidate for normative retrieval. Its planning inputs will be the accepted
W49 checkpoint, measured target-runtime latency/recall and a fresh licensing ruling for the
intended audience. W50 must separately contract result ordering, exact canonical citations,
empty/degraded behaviour, authorization, snapshot selection and the moment an audit run pins a
snapshot. W49 supplies none of those semantics by implication.
