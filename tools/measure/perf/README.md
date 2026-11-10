# The read-model performance harness

Seeds a throwaway PostgreSQL with a realistic volume and times the product's heavy read statements cold and warm, with their `EXPLAIN (ANALYZE, BUFFERS)`.
It was written by two lanes on 2026-11-10 (PERF: `D-463`, `D-494`; PERF-2: `D-572`, `D-574`, `D-620`) in git-ignored evidence directories and moved here by
lane WALK-TOOLS (`D-577`, `D-621`), so that the figures below can be taken again on a release candidate. It imports only the product's public modules and the
migrated schema, changes nothing in the repository, and runs on a disposable database only.

| file | what it is |
|---|---|
| `perf_stand.sh` | PostgreSQL 17.11 on tmpfs (the project's own image, the server's own defaults), migrated to head, one driver run against it, the container stopped by its own name |
| `perf_seed.py` | the volume: `prepare` (accounts and the id helper), `seed_d463` (documents, runs, findings, price lists, passes, proposals, decisions), `seed_memory` (decision-memory cases up to N) |
| `perf_lib.py` | the cold/warm bench, the buffer eviction, `EXPLAIN` of the exact statement the code sent, the result file |
| `perf_main.py` | the measurement: `listDocuments`' optimisation counts (`D-463`) and the decision memory's read model (`D-494`), with the index trials |
| `perf_final.py` | the statement before `D-463` (kept verbatim) against the shipped one on the same database, rows compared; the finding-verdict candidate `R1` |
| `perf_exp.py` | candidate rewrites of the optimisation counts (`D-463`'s second stage); stops if the shipped `_OPTIMISATION_RULE` loses `latest_pass` / `pass_undecided` |
| `perf_base_compare.py` | the working tree's statements against a base commit's (`git show <commit>:<path>` loaded under another name), every row compared before anything is timed; `D-574`, `D-572`, JIT on and off |
| `perf_explore_counters.py` | candidate rewrites of the counters' statement `_AUDIT_GROUPS` and of the pass's `decision_counts` (`D-572`, `D-574`); breaks on purpose when the statement's text changes |
| `perf_explore_plans.py` | seven ways of reading `finding_current_verdict`, plan shapes only |

## The command

```
while [ $(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo) -lt 2500 ]; do sleep 30; done      # wait OUTSIDE the lock
set -o pipefail; flock <the host's run lock> timeout 1200 tools/measure/perf/perf_stand.sh --label NAME 2>&1 | tee NAME.log
```

`--driver perf_final.py` (or any `perf_*.py`) picks the driver, `--smoke` builds the small volume (seconds), `--dry-run` says what would run and touches nothing.
Results: `$PERF_RESULTS/run-NAME/` (default `<repo>/.local/perf`, git-ignored): `result.json`, `explain/*.txt`, `main.log`, `main.err`, `alembic.log`. The script
refuses to start under 2500 MB of available memory, needs `docker` and the image `auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9`, and uses the container
`am-lane-perf-pg` on port 55731 (`LANE_PG_NAME`, `LANE_PG_PORT`). The data directory is a 2500 MB tmpfs (`PERF_TMPFS_MB`): the full run of 2026-11-10 (the 700 documents and the memory grown to 100,000 cases) ended with 1.7 GB of it used (`df` in `.local/evidence/lane-perf-d463/full.log`); the script prints it at the end of every run.

The base commit of `perf_base_compare.py` is `PERF_BASE` (default `73206c679`, the tree `D-574` was measured against; it must be in the local clone):

```
PERF_BASE=<commit> flock <lock> timeout 1200 tools/measure/perf/perf_stand.sh --driver perf_base_compare.py --label vs-<commit>
```

The integration groups of a lane (`tests/integration/dashboard`, `tests/integration/optimisation/proposals`) need PostgreSQL **and** MinIO: use
`tools/measure/with_throwaway_stand.sh pytest ...` (beside this directory), which the lane's `checks.sh` and `test-stand.sh` duplicated and which are therefore not moved.

## The volume

The defaults of `perf_seed.py` (`PERF_P1_DOCS` 400, `PERF_P2_DOCS` 300, `PERF_PASS_SIZES` 300,500,800, `PERF_OLD_PASS_SIZE` 400, `PERF_P2_PASS_SIZE` 100), every trigger on:

| | |
|---|---|
| documents | 700 in two projects: the page project (400 AR documents, each with a published run of 10 to 109 findings and a latest optimisation pass of 300, 500 or 800 proposals, about 60 % of the proposals decided once, some withdrawn and decided again; 40 % also have an older pass, a fifth a non-current V1 with a pass of its own) and a background project of 300 lighter ones |
| totals (the database's own counts) | 769 passes, 324,300 proposals, 282,307 decisions, 32,100 findings |
| decision memory (`PERF_MEMORY_STEPS` 5000,20000,100000) | 5,000 / 20,000 / 100,000 cases with 7,500 / 30,000 / 150,000 decisions, their text, content and evidence; 1,000 / 4,000 / 20,000 status events; at the end 9 % of the cases withdrawn and 3 % forgotten (their content deleted by the guard's own rule) |
| `--smoke` | 12 + 8 documents, passes of 20 to 40 proposals, memory to 150 and 400 cases, 2 warm runs |

Seeding the 700 documents took 48 to 54 s; the whole `perf_main.py` run (seed, `D-463`, the memory to 100,000 cases and every figure) 264 s (2026-11-10).

## What it measured (2026-11-10, PostgreSQL 17.11, `shared_buffers` 128 MB, `work_mem` 4 MB, JIT on, data on tmpfs)

Cold = shared buffers evicted and a fresh connection (the tmpfs data directory stays in the kernel's page cache, so cold here is a lower bound of a disk-cold read);
warm = the median of 5 runs. The figures are the registers' (`docs/program/DEBT_REGISTER.md`), repeated here with the command that produced them.

| row | command (driver, tree) | figure |
|---|---|---|
| `D-463` | `perf_stand.sh` (`perf_main.py`) on `672609ab1`, then on `43f5dfbd6` | `DocumentAuditReadModel.audits`, a page of 200 documents: warm 1291 ms before (the optimisation counts 832 ms of it: 106,100 `LATERAL` probes) -> 455 ms after (cold 1659 -> 484); a page of 50: 290 -> 211 ms; the audits of all 400 documents 2222 -> 773 ms; `listDocuments` `limit=200` 1393 -> 525 ms |
| `D-494` | `perf_stand.sh` (`perf_main.py`) on `672609ab1` | `MemoryReader.list_cases`, page of 50, no filter, warm (cold): 22 (25) / 81 (90) / 402 (406) ms at 5,000 / 20,000 / 100,000 cases; `counts()` 5 / 18 / 79 ms; `case_summary` 1 ms and `get_case` 3 to 6 ms at every size |
| `D-572` | `perf_stand.sh --driver perf_base_compare.py` on `c445e18db` against `73206c679` | the counters (`_AUDIT_GROUPS`, whole deployment): 708 and 713 ms warm in two runs (cold 787 and 811); one project of 400 documents 263 and 248 ms; `jit = off`: 303 ms |
| `D-574` | the same | `listOptimisationPasses`, project of 640 passes of ~530 proposals, 200 passes: 726 -> 298 ms warm (cold 871 -> 306); 50 passes 138 -> 117 ms; 20 passes 60 -> 64 ms; rows equal on every pass |
| `D-620` | the same, JIT on and off | `audits` over all 700 documents 1389 -> 802 ms with `jit = off`; a page of 50: 171 -> 188 (no JIT in that plan) |

The `perf_main.py` full run took 264 s (2026-11-10, tree `672609ab1`, `.local/evidence/lane-perf-d463/run-full/result.json`), the `perf_base_compare.py` run 128 s
(tree `c445e18db`, `.local/evidence/lane-perf-2/run-final1/result.json`), both git-ignored. **These files are not in the repository**; the registers' rows hold the figures.

## What stops it rotting

The harness reads a long list of tables and a dozen private names of the product, and nothing used to import it, so it broke on the day somebody wanted the figures.
Two tests, each shown able to fail:

* `tests/unit/measure/test_perf_harness.py` (no database, no docker, a few seconds): every driver imports; every product name the harness reaches for exists
  (`from auditmanager.x import n` at any depth, and `A.n` where `A = importlib.import_module("auditmanager.x")`, checked by `ast`; the check is shown red on a file that
  names what is not there); `--dry-run` prints the documented 700-document volume and `perf_stand.sh --smoke`'s small one; the stand script refuses what it does not
  know before it starts a container; this README names every file of the directory.
* `tests/integration/measure/test_perf_seed_smoke.py` (a migrated PostgreSQL): the smoke volume builds with every trigger on, and the product's own read models
  (`DocumentAuditReadModel.audits`, `MemoryReader`) answer over it. A migration that renames a column or adds a refusing constraint breaks the seed here, not at the next measurement.

```
.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/measure
flock <lock> timeout 1200 tools/measure/with_throwaway_stand.sh .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/measure
```

## Limits, stated

* The drivers `perf_exp.py`, `perf_explore_counters.py` and `perf_base_compare.py` are tied to the TEXT of the statements they rewrite or compare. When `audit_state.py` or the
  pass repository is rewritten, they stop on an `assert` (on purpose: a candidate built from a block that moved measures something else). The unit test sees a moved
  NAME, not a changed text; run `--smoke` on each after touching those statements.
* Cold is a lower bound (tmpfs, kernel page cache), the server is a Docker container on a shared host, and the figures move by 10 to 15 % between runs: two runs of the
  counters gave 708 and 713 ms. A figure for a decision should be taken twice, on a quiet host (`flock`, one run at a time).
* `perf_seed.py` leaves two scaffolding tables (`perf_ver`, `perf_run_plan`) in the database; the measured statements do not read them, and the database is thrown away.
* Nothing here measures the HTTP layer, the BFF or the browser; `perf_main.py` calls the adapter and the router's own helpers of `listDocuments` and encodes the body, without a socket.
