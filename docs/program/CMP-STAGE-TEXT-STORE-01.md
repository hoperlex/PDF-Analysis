# CMP-STAGE-TEXT-STORE-01 — append-only Stage Text evidence writer

Task: [`CMP-STAGE-TEXT-STORE-01`](tasks/CMP-STAGE-TEXT-STORE-01.md). Base `318e0c7bb07c2a7c599b638225ef89004e85acc3` has the pure fragment, exact, difference and hint algorithms. The writer is worker-side code only; it is not yet wired into a served endpoint.

## Implemented

- `StageTextEvidenceStore.write` locks the same per-pair advisory key used by the frozen map-revision trigger, requires the requested revision to be current and the pair to be confirmed, checks every supplied profile against the pair, side, ready algorithm and latest document version, and requires a manifest entry for every map item profile.
- Exact exclusions and changed raw rows must refer to a confirmed paired row; removed/added rows must be on a side represented in that map. Cross-sheet hints require a linked left source and a different right target. The writer refuses a profile declared on both sides, an exact exclusion with different canonical text, and a `changed` row with equal canonical text.
- All four sealed `stage_text_*` tables are written inside one PostgreSQL transaction. Content keys are deterministic from the revision and fragment references. A repeat with the same payload reuses rows; a changed nonempty revision evidence set or a colliding fragment key refuses. The database's frozen scope triggers still enforce pair and side references.

## Evidence

- Isolated PostgreSQL at migration `0041`: **3 passed**. The tests verify first write/replay, one exclusion plus one changed row, changed replay refusal, stale revision refusal, wrong side and unlinked evidence refusal, and rollback after a malformed second fragment. Stage Text unit suite **17 passed**; package compile and `git diff --check` passed.
- Contract `1.12.0`, migration `0041`, root dependencies/locks, composition root, global styles, generated client, C2 runtime, C3 pair/link internals and remote refs were not changed.

## Remaining boundary

The future run handler must read the pinned page-profile archives, derive a complete manifest for *all* current pair pages, call the pure algorithms and this writer, and seal a run even when every evidence set is empty. This writer alone cannot prove that the caller supplied every source word, nor can an empty set be treated as a completed run. The served `ComparisonStageTextAdapter` remains a typed 503. No masks, UI search, background scheduling or full `CMP-STAGE-TEXT-01` parity is claimed.

## Integration instruction

Call this repository only from a durable worker step after rechecking the run's pinned revision and version list. On refusal, mark that step failed and keep previously committed evidence immutable. After storage, expose rows through a separately scoped read service that marks them stale when the map or versions change; never let a hint mutate a link or raw difference.
