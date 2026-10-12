# Task W55A-CONTENT-01 — Document and norm-document content is streamed from S3 in chunks with one Range honoured and the full read's last chunk held back until the digest matches

## Outcome
Document and norm-document content is streamed from S3 in chunks with one Range honoured and the full read's last chunk held back until the digest matches.

## Depends on
- `W55A-FREEZE-01`, `W55A-SEAL-01` (merged)

## Frozen inputs
- domain contract: after `W55A-SEAL-01`
- API contract: after `W55A-SEAL-01` (45 / 52 / 116)
- analysis/comparison/event contract: unchanged
- migration head: `0020_norms_search`
- base commit: the SEAL merge

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
- Exactly the `W55A-CONTENT-01` grant in `docs/program/dispatch/W55-PLAN.md` §A4 Stage B item 1, except `web/tests/unit/api/configuration-and-cache-keys.test.ts` (WEB-NORMS owns it in parallel), plus `docs/program/W55A-CONTENT-01.md`

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand

## Non-goals
- other W55a lanes' paths (plan §A5).

## Deliverables
- Per plan §A3.5 and §A4 item 1, on SEAL's `stream_content`, `ByteRange` and `StreamingWireResponse`: a ranged read never loads the object; `206`/`422`; the held-back last chunk and the short body on a tampered object; records 14, 15, 31 byte-identical; the BFF passes `Range` up and `Content-Range`/`Content-Length`/`Accept-Ranges` down.

## Required tests
- command: container-free now; DB/S3-backed cases on PostgreSQL `57220`, S3 `60820/60821` are window steps — list commands.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; no containers; never touch the stand, published refs or other worktrees.
