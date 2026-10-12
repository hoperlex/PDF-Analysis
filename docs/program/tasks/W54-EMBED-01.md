# Task W54-EMBED-01 — A resumable, batch-bounded embedder over characters-v2 chunks with D-124 and D-127 closed

## Outcome
A resumable, batch-bounded embedder writes `bge-m3-dense-v1` vectors for `characters-v2` chunks, invisible until a completion row, with D-124 and D-127 closed.

## Depends on
- `W54-FREEZE-01`, `W54-SEAL-01`, `W54-BGE-IMAGE`, `W54-SNAPSHOT-01` (merged on `integration/w54`)

## Frozen inputs
- domain contract: after `W54-SEAL-01`
- API contract: after `W54-SEAL-01`
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the SNAPSHOT merge on `integration/w54`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- Exactly the `W54-EMBED-01` grant in `docs/program/dispatch/W54-PLAN.md` §4 Stage B item 4, plus `docs/program/W54-EMBED-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand, `.local/norms/corpus/**` (read-only)

## Non-goals
- the full ≈14 h corpus build (`W54-CORPUS-OPERATE-01`, night windows); bundle; search.

## Deliverables
- Per plan §3.4 and §4 Stage B item 4: D-124's red revert; D-127; windows equal the runner's on recorded offsets and, in the rebuilt image, on the real tokenizer; a build killed between batches resumes to the same digest; rows invisible until the completion row; memory bounded by the batch; MRR in the rebuilt image; `embed-texts` stable. SNAPSHOT's notes: embed `characters-v2` chunks; use `Chunk.paragraph_ordinal_first/last`; `content_key` may carry `+seg-`; `build_chunks_from_stored` exists.

## Required tests
- command: container-free tests now; DB-backed tests on PostgreSQL `57160`, S3 `60760/60761` and every check needing the built image or the real model are heavy steps for the integrator's window — list exact commands.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report and runs the listed heavy steps in the window.

## Failure/idempotency/security cases
- No model download, no docker, no corpus load in the lane. Never `pkill`/`killall`; never touch the stand, published refs or other worktrees.
