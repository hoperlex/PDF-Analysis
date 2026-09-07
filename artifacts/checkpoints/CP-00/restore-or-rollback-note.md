# CP-00 — restore and rollback

Recorded by `W0-INT-01` at the bounded closeout of 2026-09-04.

## What this checkpoint is

An architecture and behaviour freeze. It contains **no product code, no schema migration
and no deployed service**. Restoring it means putting a reader back in front of the same
documents, contracts, fixtures and validation tooling; it does not mean restoring a
running system, because none exists before CP-01.

That is why this note is short, and the shortness is the point rather than an omission.

The tree this restores to is `candidate_commit`
`92e13fa496a723ed6e4c3adbf138c4f4e1d7c368` for the four reviewed families, published as
the annotated tag `v0.0.0-architecture`. `migration_head` is `none`: `db/migrations/`
carries only `README.md`, so no restore step touches a database and there is no data to
lose.

## Restore

```bash
git clone <origin> auditmanager && cd auditmanager
git checkout v0.0.0-architecture
python3 -m venv .venv/bootstrap
.venv/bootstrap/bin/pip install --require-hashes -r requirements/validation.lock
.venv/bootstrap/bin/python scripts/validate_bootstrap.py          # expect PASS, exit 0
.venv/bootstrap/bin/python -m unittest discover -s tests/contract # expect OK, 103 tests
```

The tag is annotated and immutable. Everything the checkpoint certifies is reachable from
it: `artifacts/checkpoints/CP-00/contract-manifest.yaml` carries the family hashes, and
recomputing them from its own recipe reproduces `artifact_manifest_sha256`
`39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` over 100 files.

**Database:** none. `migration_head` is `none`; `db/migrations/` holds only `README.md`.
No restore step touches a database, and there is no data to lose.

**Object storage, message broker, external service:** none configured at CP-00.

## Rollback

There is nothing to roll back **from**: ratifying CP-00 changes no runtime, no schema and
no data. The rollback question that does arise is what to do if the checkpoint itself is
later found unsound.

- **Do not move or delete the tag.** `v0.0.0-architecture` is the name of a specific tree
  and later work references it. Moving it silently invalidates every reference.
- **Do not force-push `main`.** The closeout is a fast-forward; if `main` is ever not an
  ancestor of the branch being published, stop and escalate rather than forcing.
- To supersede this checkpoint, cut `v0.0.1-architecture` from a new accepted candidate
  and record the supersession in `docs/program/CHECKPOINT_REGISTRY.md` and in the CP-00
  manifest's history. The registry is the place a reader looks; a superseded checkpoint
  that says nothing about its successor is the defect this program spent nine acceptance
  rounds on.

## What a restorer should read first

1. `artifacts/checkpoints/CP-00/checkpoint-report.md` — what was accepted and on what
   evidence.
2. `artifacts/checkpoints/CP-00/known-risks.md` — what is open at ratification, including
   the one security item (`E-06`) that is owned by W1 and unrepairable inside the freeze.
3. `docs/program/CURRENT_STATE.md` — where the programme stands.
