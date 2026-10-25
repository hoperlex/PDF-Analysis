# AR v3 beta activation — what is built, what is owed, in order

Written 2026-10-26 by the integration session of `AR-CLOSE-1026`. The code path for the owner's
six-Run Ф1.3 AR beta is complete on `integration/ar-close-1026`; **activation is a data and review
sequence that no code can perform**. This runbook is the order of that sequence. It claims no
approval, no expert decision and no legal-source check.

## What the code does today (verified)

| Step | Where | State |
| --- | --- | --- |
| six Run group start / read / review read | `startArV3BetaGroup`, `getArV3BetaGroup`, `getArV3BetaGroupReview` | served; refuses `dependency_unavailable / ar_v3_trusted_pack` while no pack is installed |
| v3 dispatch, journal, saved reply, CITE stage, review-only terminal | `runs/v3_*` | served behind the pack |
| decisions → six canonical scope maps, validation (distinct SHA, <= 22,000 chars, no upgrade of `context_only`) | `python -m auditmanager.analysis.profiles.ar_v3.norm_map.map_pack {build,validate}` | `AR-V3-BETA-MAP-TOOL-01`; exercised on synthetic data only |
| promote one reviewed set into custody (`plan` read-only, `promote` after the reviewer's digests match, idempotent replay) | `python -m auditmanager.norms.retrieval.promote_cli {new-id,plan,promote}` | `AR-V3-BETA-SET-TOOL-01`; 72 tests incl. real PostgreSQL/S3 |
| seal the six verified sets into a reviewed-pack manifest, verify it offline | `python -m auditmanager.runs.v3_pack_cli {seal,verify}` | `AR-V3-BETA-PACK-INSTALL-01` |
| install: both services read `AR_V3_BETA_PACK_MANIFEST` and refuse start on a bad file | composition roots; `infra/deploy/compose.server.yml`, `infra/deploy/ar-v3-pack/` | `AR-V3-BETA-PACK-DEPLOY-01` |

## The order of the sequence (every step has an owner that is not this session)

1. **Stand state** (owner window, `D-203`/`D-188` area): the repaired norms bundle imported on the stand and snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` designated current; 674 document PDF bindings and 28,920 object bindings rechecked
   (`AR-BETA-LOCAL-CUSTODY-01` proved this on an isolated local lane only).
2. **Decisions** (`D-204`): a qualified owner records include / revise / exclude for each C01–C22 branch with the project date, use and work boundary and the exact target range
   (`AR-NORM-MAP-APPROVAL-PREP-01.md`). The beta policy keeps C05, C06, C08, C09, C10, C15, C21, C22 `context_only`; the tool refuses any upgrade of them.
3. **Official source pages** (`D-204`): acquire and hash the missing D1–D5 amendment pages, the C15 ГОСТ correction page and the applicable D6 law text; record what changed.
4. **Query vectors** (`D-204`): BGE-M3 revision `5617a9f61b028005a4858fdac845db406aefb181`, CLS pooling, 1024 dimensions, with reproducible provenance. The weights are not on this host; no synthetic vector may stand in.
5. `map_pack build` then `validate` → six maps with six distinct `map_sha256` and the pack summary (`review_state: pending_expert` until a complete attestation is supplied).
6. For each of the six scopes: a reviewer computes the source and embedding digests independently; run `promote_cli plan`, compare, then `promote`. Six invocations; six `nrs_` sets.
7. `v3_pack_cli seal` with the reviewer attestation → manifest; `v3_pack_cli verify` → exit 0.
8. Copy the manifest to `infra/deploy/ar-v3-pack/`, set `AR_V3_BETA_PACK_MANIFEST=/run/ar-v3/<file>` in `alpha.env`, restart `api` and `worker`.
9. `AR-V3-BETA-ACCEPT-01`: recorded positive and negative cases, then a controlled live provider and cost check, the complete gate with the literal `GATE OK` on the exact tree, user review of source-PDF links; only then `RELEASES.md` and any `origin/main` instruction (a separate direct owner instruction).

## Honest limits

- The reviewer attestation in the manifest is a record; neither the loader nor `pack_sha256` authenticates it. File custody (read-only mount, host permissions) is the control (`D-212`).
- Numerical findings stay unavailable until an expert decision and an edition check exist; nothing here creates one.
- The 22,000-character check in `map_pack` is a lower bound; the final check happens at promotion with real windows.

Reports: `AR-V3-BETA-MAP-TOOL-01.md`, `AR-V3-BETA-SET-TOOL-01.md`, `AR-V3-BETA-PACK-INSTALL-01.md` (each carries its own operator commands and refusal codes).
