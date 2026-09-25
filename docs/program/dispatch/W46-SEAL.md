# W46-SEAL — one reseal: the section field, and one aggregate read for all four panels

**task_id:** `W46-SEAL` · **wave:** 46, sub-stage A · **lane:** `gate-w46a`
**worktree:** `/root/w46seal` · **branch:** `agent/w46-seal`

**You own the reseal.** One stream carries it because wave 34 proved a reseal splits badly and
`R-11` reverted a whole wave over one discovered at the end. Read `OWNER_RULINGS_2026-09-17.md`
§3.13 (`R-40`) and §3.15 (`R-44`) before anything.

## Frozen inputs, measured at `alpha-w45`

| | |
|---|---|
| surface | **16 paths / 19 operations / 53 schemas** |
| error catalog | `contracts/domain/v1/error-codes.json` — **22 codes, frozen.** A new one is a second reseal and the owner's |
| migration head | `0010_run_terminal_detail` — yours is `0011` |
| **a reseal is FIVE documents** | `openapi.json`, the generated client, `web/openapi/openapi.json`, `web/FRONTEND_LOCK.json`, **and the pin at `tests/contract/api_v1/test_doc_prose_facts.py:290`** — `D-102` was opened because the fifth was missed |
| **and three more pins move on their own triggers** | `D-105`: the catalog count twice, the migration head once. **Your migration moves the head pin.** |

## S1 — `R-40`: the section field and its aggregation, in one wave

The owner took **both** halves against the recommendation to take the field now and counters
later. `D-56` measured the shape: legacy carries **14** sections
(`AR, AI, KM, KJ, OV, EOM, VK, PT, PB, SS, ITP, GP, TX, POS`), ours has none.

**The field is a migration and a contract property.** Where it lives — on the document, on the
version, on the project — is **yours to decide and to argue**, and the argument belongs in your
report, not only in a commit.

## S2 — `R-44`: one aggregate read, not three page-walks

**The integrator's decision under `R-29`, and it is against the cheaper path.** Three of the four
panels are reachable today by walking existing listings — `Project.document_count`,
`listDecisions` with `category`/`verdict`, `listRuns` with `RunStatus`'s cost fields. **Only the
per-section breakdown needs the new field.**

**Build one aggregate read that serves all four.** The argument is `R-24`'s own: it was ruled
**for** a listing operation and **against** a client-side walk, so founding the dashboard on
walks over the operation that exists to prevent walks is an odd inheritance — and three walks
built now are three a later aggregate read deletes.

**What the operation must not become.** A generic query endpoint with filters is a second
authority over the data. Name what it answers and refuse the rest.

**Absent is not empty**, and this programme has a guard family about it. A project with no runs,
a section with no documents and a verdict nobody has recorded are three different answers.

## S3 — the pin, because `D-102` exists

Your reseal moves the surface. **Move the pin in the same commit** and say in your report that
you did. A reseal that leaves it behind is an incomplete reseal and the gate will say so.

## allowed_paths

```
contracts/api/v1/openapi.json · web/openapi/** · web/FRONTEND_LOCK.json
web/src/shared/api/generated/** · src/auditmanager/** · db/migrations/**
tests/** (NOT tests/e2e/**) · docs/program/W46-SEAL.md
```

## forbidden_hotspots

`web/src/**` except `shared/api/generated/**` — **`W46-DASH` owns it**, live in `/root/w46dash` ·
`web/tests/**` · `contracts/domain/v1/error-codes.json` · `infra/**` · `tests/e2e/**` ·
`docs/program/DEBT_REGISTER.md` · `docs/program/dispatch/**` · `Makefile` · `package.json` ·
any container not named `gate-w46a*` · **the owner's stand is read-only.**

## Deliverables

1. The migration, the operation and the reseal — **the reseal is one commit, all five documents.**
2. `docs/program/W46-SEAL.md`, opened **before** the first measurement.
3. Every new guard **shown failing**, with the mutation and the failing assertion quoted.
4. Your two arguments: where the section field lives, and what the aggregate read refuses.
5. Anything outside the grant: reported, not repaired.

## Verification

Lane `gate-w46a` — PostgreSQL `127.0.0.1:56370`, S3 `59970`/`59971`. Provision with
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, `.venv/bin/python -c "import boto3"`,
`npm --prefix web ci`. `make migrate` must apply **and roll back**.

`make gate > /root/w46a-gate.log 2>&1`, verdict from the **`GATE OK` line in the log**.
`alpha-w45`: battery **2493**, foundation **35**, frontend **1110 in 78 files**.

**Run the canonical battery command literally.** Last wave a judge reported a battery run having
added `--ignore=tests/e2e`, which is in neither `OPERATING_CONSTRAINTS.md`'s command nor the
Makefile's `run_battery()`, and the integrator reported "contract suites green" from three named
paths that excluded the file most likely to break. **A chosen scope presented as the canonical
one is this programme's most repeated error.**

## Discipline

Commit each step. Do not tag, push or merge.
