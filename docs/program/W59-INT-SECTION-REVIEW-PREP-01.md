# W59-INT-SECTION-REVIEW-PREP-01 — explicit section review choices

Base: published `origin/dev` at
`d416e185d3b42da55ba2e8bfdd02d7126da7f41e`.

The new pure `prepare_section_review` builds a packet for one well-formed
`VersionUid`. It lists all 15 candidate sections in stable code order and
attaches existing filename/text match evidence where available. A neutral
input still offers every choice; an AR filename does not hide PS or PB, and
an AR/KJ tie stays on two separate options. The packet has no selected or
confirmed field and cannot be passed to the existing routing guard as a
persisted confirmation.

## Checks

- Focused review, suggestion and confirmation suite: **41 passed**.
- Python compilation: passed for the new module and test.
- Direct task governance: `[]`.
- Frozen API/domain/error/stage/resource SHA-256 values match the task's
  exact base; migration head remains `0022_findings_v2`.
- Staged `git diff --check` and exact four-path proof: pass at commit.
- No Docker, DB/S3, provider, network or complete gate was used while the
  W55b host lane ran; R-135 defers the complete beta gate.

## Contracts, limits and handoff

No contract, migration, catalogue, existing module, API, UI, run, profile or
database behavior changed. This is an unserved display projection, not an
expert confirmation or permission grant. The future W59 owner must complete
the SECTION-SEAL after W58-code close, load authoritative version membership,
authenticate the expert, persist the explicit stage and section decision,
then route only from that persisted confirmation and a sealed executable
profile map. The local candidate catalogue does not establish profile
readiness or a production section route.

Malformed version identities, nonstring evidence, duplicate/incomplete
catalogue entries and mismatched suggestion metadata refuse explicitly.
Repeated input gives the same immutable packet and no side effect. The
catalogue is still a candidate resource; its legacy pattern weights have not
been calibrated against real project packages. There is no runtime rollback:
remove this additive module and test before integration if the later seal
chooses another review projection.

Changed paths are this report, its formal task,
`src/auditmanager/sections/review.py` and
`tests/integration/sections/test_review.py`. Frozen `contracts/**`, migration
head, existing section files, root dependencies/locks, composition root,
global styles, `CURRENT_STATE.md`, tags and `origin/main` were not touched.
