# W54-FREEZE-01 — the W54 development freeze

**Integrator:** `pdf-analysis-62`, 2026-10-12. **Base:** `integration/w54` from `origin/dev`
`4fe7615` (W53 released as `v0.4.0`; `origin/main` `2653dbf`), plus `W54-RULE-01` (`fb6e79b`).
**Plan:** `dispatch/W54-PLAN.md` as adopted (owner approval `R-100`).
**Rulings:** `R-88` … `R-108` (`OWNER_RULINGS_2026-09-17.md` §3.30).

## Checks (`R-102`)

Every lane uses light acceptance: the touched contexts' tests, plus migrations on its private
lane. Exactly one full `make gate` runs, on the wave's final candidate before `origin/main`. The
plan's per-lane "full gate" levels in §4 are replaced. The pin sweep stays in `W54-SEAL-01`:
`tools/plan/pin_sweep.py`, with every printed path granted to SEAL.

## Heavy steps (§3.9) and windows

A heavy step is any of:

- an image build;
- a private stack run;
- a corpus load;
- a dump or restore;
- the repair run;
- an embedding build;
- a bundle export;
- a rehearsal;
- the full gate.

Heavy steps run one at a time, and only inside an owner-designated window. On 2026-10-12 the
owner said the window opens after 18:00 GMT+3 and will be stated precisely. Until then lanes do
code and container-free checks only, and hand back with each heavy step they still need. The
integrator runs those steps, or resumes the lane, inside the window. A heavy step also needs
`free` to show at least 6 GiB available and `df` to show its increment plus 3 GiB free, both
measured just before it starts.

Host at freeze: 22 GB free on `/` after `R-101`/`R-108`. Available RAM was 2 GiB under
co-tenant load (load average 24).

## Decisions taken at the freeze (plan §4 `W54-FREEZE-01`)

- **D-150:** recorded-mode provider effects are reclaimable as `not_processed`. A recorded call
  spends nothing. `W54-WORKER-01` implements this and updates the QA assertion.
- **Migrations:** `0018_norm_custody` and `0019_execution_workers`, both owned by
  `W54-SEAL-01`. W55 and later own `0020` … `0024` (CD-2).
- **Deferred in Stage A:**
  - `W54-OCR-PROBE` and `W54-VISION-PROBE` need the owner's fresh portal ZIP export under
    `.local/portal-exports/`. The vision probe also needs the live proxy credential on this host,
    outside git. Neither input exists yet, so both probes are dispatched when the inputs arrive.
    They are report-only and gate nothing else in W54 (§3.8).
  - `W54-BGE-IMAGE` writes its image definition and tests now. Its build and MRR reproduction
    (about 6.5 GB increment, about 3.2 GiB RAM) is a heavy step for the first window.

## Stage A lanes and ports

| Task | Branch / worktree | Private ports (window only) |
| --- | --- | --- |
| `W54-SEAL-01` | `agent/w54-seal-01`, `.local/worktrees/w54-seal` | PostgreSQL `57110`, S3 `60710/60711` |
| `W54-TRANSPORT-01` | `agent/w54-transport-01`, `.local/worktrees/w54-transport` | none (`docker` stubbed) |
| `W54-BGE-IMAGE` | `agent/w54-bge-image`, `.local/worktrees/w54-bge` | none (image build in a window) |
| integrator | `integration/w54`, `.local/worktrees/w54-int` | PostgreSQL `57100`, S3 `60700/60701` |

The merge order is SEAL, then BGE-IMAGE, then TRANSPORT, rebased on SEAL's merge (plan §5).
Stage B starts from the Stage A merges, one lane at a time.

## Amendment 1 — `R-109`, `R-110` (owner, 2026-10-12)

Wherever the adopted W54–W57 plans and `FAST-PATH-NORMS-SECTIONS.md` require the one-off copy
or the `R-92` window before a migrating publication or the corpus import, read the requirement
as conditional: "if the stand holds real client data". The integrator applies this reading; the
plan texts are not rewritten.

Under that reading:

- P2 and P3 publish without a copy while the stand holds test data only.
- P4 keeps `capacity`, `report` reconciliation and `resume`, but needs no copy or window.
- `W54-STAND-COPY-01` and the rehearsal still build and prove the copy tooling.
- The P2 bootstrap of `copy-serve.sh` is deferred to the first real upload.
- `D-156` registers the beta-transition purge of the test data.

## Amendment 2 — the importer under `R-110` (integrator decision, 2026-10-12)

The owner's answer covers the copy only. The importer's behaviour is technical and is decided
here.

- **(a) Quiesce stays.** `import` stops the stand's writers for its own duration and leaves
  them stopped until `resume`, exactly as with a copy. The one-transaction row import is not
  relied on for consistency against live writers.
- **Test-data waiver instead of the attested copy record.** `attest --test-data` writes a copy
  record of kind `test_data_waiver`. It holds the operator's statement, the fingerprint at that
  moment and a timestamp, and carries no dump or inventory. The importer accepts either a full
  attested `import` copy record or an unexpired `test_data_waiver` whose fingerprint still
  matches.
- **Real-data marker.** A full copy taken under `R-110` before the first real client upload
  writes a `real_data` marker. From then on any waiver is refused, so `R-88` and `R-93` apply in
  full.
- **Owners.** `W54-STAND-COPY-01` owns the waiver verb, the marker and the `deploy.sh`
  interaction. `W54-BUNDLE-01` owns the importer's acceptance rule. The rehearsal proves the
  waiver path, the full path and the refusal after the marker.
