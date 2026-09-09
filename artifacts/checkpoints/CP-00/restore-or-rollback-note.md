# CP-00 — restore and rollback

Recorded by `W0-INT-01` at the bounded closeout of 2026-09-04; corrected by `W0-INT-02`.

> **The procedure below did not work as shipped, and this note is the one deliverable whose
> whole purpose is to be run by somebody who was not here.** It told a restorer to clone a
> remote and check out `v0.0.0-architecture`. That tag is local and unpublished: it exists on
> no remote, so the first two lines failed for every reader outside this machine. It also
> told them to expect 103 tests, a figure no tree of this repository produces, and to
> reproduce a digest that is the reviewed **input** value rather than the checkpoint's.
> `erratum.md`, E-5 and E-7.

## What this checkpoint is

An architecture and behaviour freeze. It contains **no product code, no schema migration
and no deployed service**. Restoring it means putting a reader back in front of the same
documents, contracts, fixtures and validation tooling; it does not mean restoring a
running system, because none exists before CP-01.

That is why this note is short, and the shortness is the point rather than an omission.

The tree this restores to is the commit `v0.0.0-architecture` points at,
`39a3a6430bd97c38cb20bafc793fc9d077d0df8e`. The four reviewed families it certifies come
from `candidate_commit` `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`, byte-identical in
`contracts/`, `fixtures/` and `scripts/` and reconciled in five declared files under
`docs/architecture/` — see `erratum.md`, E-2. `migration_head` is `none`: `db/migrations/`
carries only `README.md`, so no restore step touches a database and there is no data to
lose.

**Publication state, which the procedure depends on.** The tag is annotated, local and
**unpublished**. Measured by the orchestrator in the main checkout on 2026-09-07 and recorded
in `docs/program/EXECUTION_PLAN.md` §3.4: no remote carries a CP-00 tag, `origin/main` stands
at `43a84d93` and `origin/integration/W0.3` at `803d22b8`. That measurement is quoted, not
re-taken: this bundle's own clone has the local checkout as its `origin`, so `git ls-remote`
run from here describes the local checkout and proves nothing about publication.

## Restore

While the tag is unpublished, a restorer must be given a repository that has the objects —
a clone of the machine holding it, or a bundle produced with
`git bundle create cp00.bundle v0.0.0-architecture`. A clone of a public remote will not
resolve the tag, and the restore stops at line two.

```bash
# from a source that carries the objects; see "Publication state" above
git clone <source> auditmanager && cd auditmanager
git rev-list -n1 v0.0.0-architecture   # expect 39a3a6430bd97c38cb20bafc793fc9d077d0df8e
git checkout v0.0.0-architecture
python3 -m venv .venv/bootstrap
.venv/bootstrap/bin/pip install --require-hashes -r requirements/validation.lock
.venv/bootstrap/bin/python scripts/validate_bootstrap.py          # expect PASS, exit 0
.venv/bootstrap/bin/python -m unittest discover -s tests/contract # expect OK, 324 tests
```

324 is what that tree collects, measured on a clean clone at `39a3a643` and recorded in the
round-ten automated evidence, `automated-summary.txt`. The figure that stood here, 103, comes
from a contour split that was never performed: `erratum.md`, E-3.

The tag is annotated and immutable. Everything the checkpoint certifies is reachable from
it: `artifacts/checkpoints/CP-00/contract-manifest.yaml` carries the per-file hashes of all
100 members grouped by directory, and recomputing the recipe **at a named commit** gives:

| Commit | Digest over the four reviewed families |
|---|---|
| `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`, the reviewed input | `39721aac0ebe1aa5c13d0ae3e01ee93380671daddc5d9f3f3b774997d6f75e08` |
| `39a3a6430bd97c38cb20bafc793fc9d077d0df8e`, the tagged checkpoint | `f362647cc9b1d2201ac4663bf5d877346eeeccf046734219103c3ac822d2845d` |

The commit is part of the recipe. This paragraph used to name the first value as what the
tagged tree reproduces, which is false of that tree; `erratum.md`, E-1 and E-7. The tag's own
message states the same wrong value and cannot be corrected — a tag message false of its own
commit is corrected by a superseding checkpoint, which is `W0-INT-03`'s act.

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
  rounds on. **This is now in progress and not hypothetical:** the repository owner decided
  a formal superseding checkpoint on 2026-09-07, acceptance round eleven is owed, and the
  disposition is recorded in `manifest.json` under `supersession` and in
  `docs/program/tasks/W0-INT-03.md`.

## What a restorer should read first

1. `artifacts/checkpoints/CP-00/checkpoint-report.md` — what was accepted and on what
   evidence.
2. `artifacts/checkpoints/CP-00/known-risks.md` — what is open at ratification, including
   the one security item (`E-06`) that is owned by W1 and unrepairable inside the freeze.
3. `docs/program/CURRENT_STATE.md` — where the programme stands.
