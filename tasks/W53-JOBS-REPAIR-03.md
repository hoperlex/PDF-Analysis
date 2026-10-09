# Task W53-JOBS-REPAIR-03 — atomic pause gate and complete effect history

## Outcome

After a dispatcher hint, a committed global pause prevents new Attempt authority. Lease reclaim and terminal effect settlement journal every actual provider effect state change in the same transaction. Concurrent periodic and forced reclaim of two expired Runs do not deadlock or lose recovery.

## Depends on

- W53-EXEC-01
- W53-EXEC-REPAIR-02
- W53-QA-01 (independent red counterexamples recorded)
- W53-JUDGE-X (pause race independently reproduced)
- W53-JUDGE-Y (private PostgreSQL `40P01` reproduced)
- W53-ALR05-REPAIR-01 (shared repository hotspot now integrated)

## Frozen inputs

- Domain revision 9 / 29 identities; state-machine SHA-256 `cd6a8b1bb6a5a413a3c03a1360d7af8d0b0eb36f70182f9b9e261b16c1805466`.
- API `1.0.0-draft.1`, 36/43/91; OpenAPI SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`.
- W53 SEAL analysis/comparison/event set; migration head `0017_execution_queue`.
- Base before this grant: `3170ae30379d6c84e124d241e5a4bde82c7dd689`. Integrator assigns exact post-grant SHA.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- `tests/integration/qa_w53/test_queue_and_effect_journal.py` has red `test_pause_between_hint_and_claim_refuses_new_authority`, `test_lease_reclaim_journals_the_effect_outcome`, and `test_terminal_effect_settlement_journals_abandonment`. QA's independent red log `/tmp/w53-qa-01/independent-regressions.log` SHA-256 `cd6d26b9b000616604b2796f9e959a74159a7d91c85ddc6a29b723f33d54d5e3`.
- `docs/program/W53-JUDGE-X.md` independently reproduces pause/claim race. `docs/program/W53-JUDGE-Y.md` records a two-connection regular/forced reclaim lock inversion across Runs A/B, PostgreSQL `40P01`; probe log `/tmp/w53-judge-y/probe.log` SHA-256 `a9ec0aa9f1f5068b6549b30b7951709bc461a0be9c4ff257028698251613a074`.
- Current `jobs/repository.py` reads pause in `next_queued_run` only, not in `start_execution`; `reclaim_expired` updates prepared effects to `outcome_unknown` without `append_execution_event`; `settle_terminal_provider_effects` returns changed rows without event append; forced reclaim promotes one Attempt in a 100-candidate sweep, reversing Run lock order.
- On 2026-10-09, private ports `56950/60550/60551` were unbound; worktree and Docker filesystem had 10,895,888,384 bytes free. Re-measure before service use.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/jobs/repository.py` (exclusive shared hotspot grant for the three listed defects)
- `tests/integration/runs/test_w53_execution.py` (focused pause/reclaim coverage only)
- `tests/integration/runs/test_durable_effect_boundaries.py` (effect settlement/reclaim coverage only)
- `tests/integration/runs/test_w53_jobs_repair.py` (new two-connection deadlock regression, if needed)
- `docs/program/W53-JOBS-REPAIR-03.md`

## Forbidden hotspots

`contracts/**`, migrations, any API/router/UI/other source path, independent `tests/integration/qa_w53/**`, root dependency/lock, composition root, global styles, queue query/cursor, proxy, release/backup/deployment paths, working stand, refs/tags.

## Non-goals

Changing the global pause event's public-journal scope; changing provider retry policy, frozen state graph, stop decisions `W53-EXEC-STOP-01/02`, or architecture seams already repaired by ALR-05.

## Deliverables

- Serialize `start_execution` and `set_paused` on the singleton control row so a committed pause is seen before authority is created. Handle the initial missing row safely; preserve Run→Job→Attempt→Lease lock order and rollback behavior. A pause that commits after a claim may affect later claims, not retroactively revoke an acquired lease.
- Emit exactly one safe `provider.outcome_unknown` event per prepared effect actually changed by reclaim and one safe `provider.abandoned` event per effect actually changed by settlement, with correct Run/Attempt IDs; no secret, prompt, raw response, idempotency key or path in payload. Event and state mutation share the transaction. Preserve idempotency on repeat sweep.
- Eliminate cross-Run lock inversion in overlapping periodic/forced reclaim. A 2-second timeout alone is not a fix. Preserve recovery of all eligible candidates and safe forced fencing, or document an explicit bounded follow-up mechanism already present. Prove with a real two-connection PostgreSQL regression.
- Six-item AGENTS.md §5 handback, changed-path audit, exact branch/HEAD and evidence logs.

## Required checks

Run the three unchanged independent QA tests listed above on a private migrated `0017` database; they must pass. Run focused `test_w53_execution.py`, `test_durable_effect_boundaries.py`, and a two-connection forced/periodic overlap regression against PostgreSQL (including absence of `40P01` and final state). Repeat ALR-05 2/2. Check `git diff --check`, frozen hashes and exact allowed paths. Preflight disk under AGENTS.md §8 before heavy tests; do not build a new image or touch the working stand. Private lane `gate-w53jobs`: PG `56950`, old S3 API `60550`, console `60551`; isolated database/bucket/volumes/credentials, clean up only own resources. Keep logs under `/tmp/w53-jobs-repair-03/` with SHA-256.

## Integration contract

Only the repository's durable behavior changes; API shape and frozen contracts do not. Integrator repeats QA cases and concurrency regression after cherry-pick. If a new path/contract is necessary, return exact evidence for an amended grant before editing.

## Failure/idempotency/security cases

Paused and unpaused control row from an empty table, concurrent claim versus pause, repeated reclaim/settlement, multiple effects per Attempt, two expired Runs with opposing watchdog/periodic sweep starts, terminal Run already fenced, and no sensitive journal payload.

## Rollback / feature flag

No flag; revert this narrow repair if independent checks fail. No migration or runtime schema change.

## Handoff

Changed files; checks/results; contracts; risks; integrator instructions; forbidden-hotspot proof — all six AGENTS.md §5 items.
