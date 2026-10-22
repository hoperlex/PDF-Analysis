# RECOVERY-DRILL-0029-01 — the B6 restore drill repeated at migration head 0029

task_id: RECOVERY-DRILL-0029-01
lane: `agent/recovery-drill-0029-01`, base `c8a11c60` (`origin/dev`, the freeze commit of the task file)
date: 2026-10-22 (UTC, about 09:48 to 09:58)

## 1. Result

The synthetic backup-and-restore drill of `RECOVERY-REBASE-01.md` §6 was run on a fresh lane stack migrated to
`0029_routing_refusal_codes`, with the realistic recorded-provider dataset, by the commands of §9 of that document. It passed at the first
attempt, with no change to any tool, test, migration or contract:

* **exit 0 on every step**, 11 drill steps in about 3.8 s of tool time;
* **23 of 23 objects and 23 of 23 Blobs**, 271,413 bytes each way, each read back through the public storage port with digest and size checked;
* **55 of 55 tables and 4 of 4 views equal** (227 rows, row count and content digest of every relation, source against restored target);
* **72 of 72 triggers equal** (and the other six shape categories: 606 columns, 657 constraints, 153 indexes, 145 functions, 7 sequences,
  2 extensions); 29 guarded tables, **40 of 40** UPDATE/DELETE attempts on the 20 populated guarded tables refused with the guard's own
  SQLSTATE;
* `alembic current` on the source and `alembic_version` on the restored target are both `0029_routing_refusal_codes`; the four `CHECK`s that
  `0029` widened carry both new codes on both sides;
* `tests/integration/recovery` in full on the lane stack: **308 passed**, exit 0;
* no defect found in `scripts/recovery/**` or `tests/integration/recovery/**` at head `0029`.

So B6 (`BETA-MATRIX-02.md` §B6) can read "drill run at the current head `0029`" with the same limits as the `0028` run (section 7).

## 2. Lane and provisioning

Lane resources (the only allocation): `FOUNDATION_INSTANCE=auditmanager-lane-i`, PostgreSQL `127.0.0.1:57700`, database `auditmanager_lane_i`,
MinIO `61500/61501`, bucket `auditmanager-lane-i`. Both sides of `.env` (service side and application side) were rewritten to these values;
the file is git-ignored and is not quoted here. Images were the pinned ones, identical to the `0028` run:
`auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9` (`sha256:4c34fc74…`) and `auditmanager-minio:RELEASE.2025-10-15T17-29-55Z-9e49d5e`
(`sha256:0d80ac74…`); server `17.11`, client tools `/usr/lib/postgresql/17/bin` (`pg_dump` 17.11). Host state before the stack: 5.3 GiB
MemAvailable, 3.3 GiB free on `/`, load 2.5; at the sampled points during the drill MemAvailable was at least 2.0 GiB and free space on `/` at least 2.9 GiB (checked before each heavy step).

| Step | Command | Exit | Time |
|---|---|---|---|
| shared interpreter first | `make up` (the worktree's `.venv` held only the `bootstrap` symlink) | 2 | 0.03 s |
| | refusal text: `the foundation runtime environment .venv/bin/python is missing. Run: make bootstrap` | | |
| bootstrap | `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | 0 | 15.4 s |
| stack up | `make up` | 0 | 8.06 s |
| health | `make check-services` | 0 | 0.54 s |
| migrate | `make migrate` (ends with `Running upgrade 0028_classification_corrections -> 0029_routing_refusal_codes`) | 0 | 1.23 s |
| database check | `make check-db` | 0 | 0.73 s |
| head | `PYTHONPATH=src .venv/bin/python -m alembic --config db/migrations/alembic.ini current` and `… heads` | 0 | 0.53 s |
| | both print `0029_routing_refusal_codes (head)` | | |
| stack down | `make down` (at the end) | 0 | 21.1 s |

Decision taken: the shared governance interpreter does not satisfy `make up` (the recipe requires an executable `.venv/bin/python`), so the
brief's fallback `make bootstrap` was used; the drill and the suite then ran on the worktree's own `.venv`.

## 3. The dataset

`PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.synthetic_drill_seed --env .env` on the freshly migrated lane database: **exit 0, 8.10 s**
(6.8 s at `0028`). Provider-selecting names are removed, the recorded provider is the checked-in recording, both endpoints loopback; no paid call.

```
{"accounts": 3, "decisions": 3, "findings": 3, "optimisation_decisions": 2, "optimisation_proposals": 4, "price_lists": 2, "run_id": "run_01M5HGA1BRDSAC0KTV1EWZ1DCR", "run_state": "published", "versions": 4, "work_assignments": 2}
```

Same dataset as at `0028` (§5 of `RECOVERY-REBASE-01.md`): 3 accounts, 4 projects, 3 documents and 4 versions, a classification and its append-only
correction, one finished recorded run with 3 findings and 3 expert decisions, 2 work assignments, 2 price-list revisions, one optimisation pass
with 4 proposals and 2 decisions. Measured on the lane: **227 rows in 55 tables** and **23 objects, 271,413 bytes** in the source bucket, all
`available` Blobs (`select count(*), sum(size_bytes) from blob` gives `23|271413` on both the source and the restored target).

## 4. The drill (`RECOVERY-REBASE-01.md` §9, one driver with per-step logging)

The driver is the §9 script with each step wrapped to record its exit status and elapsed time; every command line is the §9 one. Drill root
`.local/drill/drill-i0029` under the worktree (git-ignored, mode 700, 1.5 MB), label `i0029`, stamp `20261022T095107Z`, tree `c8a11c60`.
Target = a fresh database `auditmanager_w58_target_i0029` and an empty bucket `auditmanager-w58-synthetic-target-i0029` **on the same two
containers**, as in the `0028` run (section 7).

| Step | Command | Exit | Time |
|---|---|---|---|
| 01 source fingerprint | the marked `stand-fingerprint-v1` block of `infra/deploy/copy-serve.sh` piped into `psql` on the source | 0 | 0.03 s |
| 02 dump | `pg_dump --format=custom --no-owner --no-privileges` → **400,634 bytes** | 0 | 0.10 s |
| 03 list | `pg_restore --list` | 0 | 0.01 s |
| 04 / 05 fingerprint again, `cmp` | equal; **41** fingerprinted tables | 0 / 0 | 0.04 s / 0.00 s |
| 06 copy | `python -m scripts.recovery.synthetic_drill_fixture … --source-env` (list, conditional read, rehash, seal) → `"objects": 23, "source": "bucket"` | 0 | 0.78 s |
| 07 offline preflight | `python -m scripts.recovery.offline_restore_preflight` → `offline-restore preflight: verified local inputs` | 0 | 0.04 s |
| 08 / 09 target | `CREATE DATABASE auditmanager_w58_target_i0029`; create the empty target bucket | 0 / 0 | 0.07 s / 0.31 s |
| 10 isolated restore | `python -m scripts.recovery.synthetic_drill_runner --copy-dir … --objects-root … --target-env … --pg17-bin /usr/lib/postgresql/17/bin` (atomic `pg_restore --single-transaction --exit-on-error`, fingerprint, schema audit, Blob audit, bind, 23 puts, 23 full streams) | 0 | 1.33 s |
| 11 independent compare | `python -m scripts.recovery.synthetic_drill_compare … --probe-target-guards` | 0 | 1.05 s |

Runner result (`result.json`, identical figures to `0028` except the digests, which carry run-specific ids and timestamps):

```
{"dump_sha256": "f3f3dfd257d51eec639a026d02b4f087927355522d7a4368b81d9474db33b0f3",
 "record_sha256": "03d59ca07656472056ffd2b419d078423843ceaace0dd752f87ec942e9a597c8",
 "schema": {"guarded_tables": 29, "tables": 55, "triggers": 72, "views": 4,
            "sequences": {"audit_event_sequence_no_seq": [24, 24], "expert_decision_event_sequence_no_seq": [3, 3],
                          "norm_chunk_norm_chunk_pk_seq": [null, null], "norm_document_norm_document_pk_seq": [null, null],
                          "norm_embedding_norm_embedding_pk_seq": [null, null], "norm_paragraph_norm_paragraph_pk_seq": [null, null],
                          "release_pk_seq": [null, null]}},
 "source_counts": {"analysis_artifact_publication": 10, "input_manifest_entry": 13, "norm_custody_admission": 0,
                   "norm_custody_binding": 0, "norm_retrieval_set": 0, "price_list_revision": 2},
 "synthetic_isolated_drill": true,
 "target_blob_bytes": 271413, "target_blob_facts_sha256": "8da1800ef3a83d434f19ea2646c18079285dfda876ed390706e7e09a71ba3289",
 "target_blobs": 23, "target_object_bytes": 271413, "target_objects": 23}
```

Independent compare (`synthetic_drill_compare --probe-target-guards`), verbatim summary: `"differences": []`, `"objects": 23`, `"object_bytes": 271413`,
`"tables": 55`, `"views": 4`, `"table_rows": 227`, `"shape_categories": 8`, guard probe `"tables": 29`, `"refused": 40`, `"accepted_or_other": []`;
empty and therefore not probeable: `finding_observation_norm_citation`, `norm_current_snapshot_event`, `norm_custody_binding`, `norm_document`,
`norm_paragraph`, `norm_retrieval_set`, `norms_snapshot`, `release`, `release_revision`. The one `informational` entry is the known benign
one (`/constraints_exact_text`, below).

### 4.1 Every relation, source against restored target

The compare module prints aggregates only, so the per-relation table was produced by calling the module's own `database_profile` read-only on both
sides (helper A in the appendix; 0.9 s, exit 0). Digest = sha256 of all rows as text, first 12 characters. **0 unequal** among 55 tables and 4 views; rows
total 227 on both sides.

| relation | rows source | rows target | digest | equal |
|---|---|---|---|---|
| account_release_mark | 0 | 0 | e3b0c44298fc | yes |
| alembic_version | 1 | 1 | 3dac005f1bbe | yes |
| analysis_artifact_publication | 10 | 10 | 3bcff55edfae | yes |
| app_user | 4 | 4 | 2fc49d9f52dd | yes |
| app_user_role | 5 | 5 | e145f38e59c6 | yes |
| attempt | 1 | 1 | 06f2006ca8b3 | yes |
| audit_event | 24 | 24 | 9fc3509a3b43 | yes |
| audit_run | 1 | 1 | 69fa76a497b1 | yes |
| blob | 23 | 23 | 059dcde91b81 | yes |
| command_record | 10 | 10 | 8b577d765292 | yes |
| contract_state_transition | 51 | 51 | e3ce7184b7bb | yes |
| document | 3 | 3 | 236ec8647d51 | yes |
| document_version | 4 | 4 | 00d5f427d832 | yes |
| document_version_classification | 3 | 3 | 8fca3b606c94 | yes |
| document_version_classification_correction | 1 | 1 | 64dcb624872c | yes |
| execution_control | 1 | 1 | 5897f9630fe5 | yes |
| expert_decision_event | 3 | 3 | 1d999e442c00 | yes |
| finding | 3 | 3 | d98ad7ad2f21 | yes |
| finding_evidence | 5 | 5 | 53a8b2f82d92 | yes |
| finding_observation | 3 | 3 | 06cc438499f4 | yes |
| finding_observation_norm_citation | 0 | 0 | e3b0c44298fc | yes |
| input_manifest_entry | 13 | 13 | 518c02f22070 | yes |
| job | 1 | 1 | 3232bc13f9b1 | yes |
| lease | 1 | 1 | b508c6cf8e30 | yes |
| model_call | 1 | 1 | 409b0e0c7843 | yes |
| norm_chunk | 0 | 0 | e3b0c44298fc | yes |
| norm_chunk_build | 0 | 0 | e3b0c44298fc | yes |
| norm_current_snapshot | 0 | 0 | e3b0c44298fc | yes |
| norm_current_snapshot_event | 0 | 0 | e3b0c44298fc | yes |
| norm_custody_admission | 0 | 0 | e3b0c44298fc | yes |
| norm_custody_binding | 0 | 0 | e3b0c44298fc | yes |
| norm_document | 0 | 0 | e3b0c44298fc | yes |
| norm_embedding | 0 | 0 | e3b0c44298fc | yes |
| norm_embedding_build | 0 | 0 | e3b0c44298fc | yes |
| norm_embedding_profile | 1 | 1 | b743c5bccd99 | yes |
| norm_paragraph | 0 | 0 | e3b0c44298fc | yes |
| norm_repair_call | 0 | 0 | e3b0c44298fc | yes |
| norm_retrieval_set | 0 | 0 | e3b0c44298fc | yes |
| norms_snapshot | 0 | 0 | e3b0c44298fc | yes |
| optimisation_pass | 1 | 1 | 83b79392fec2 | yes |
| optimisation_proposal | 4 | 4 | 59e0cc408ef1 | yes |
| optimisation_proposal_decision | 2 | 2 | a9d9c4d34f8b | yes |
| price_list_position | 24 | 24 | bbb9f2895a15 | yes |
| price_list_revision | 2 | 2 | 7e4886b90bf5 | yes |
| project | 4 | 4 | b337b832b9b9 | yes |
| provider_call_effect | 1 | 1 | 42a408a8d611 | yes |
| registration_request | 0 | 0 | e3b0c44298fc | yes |
| release | 0 | 0 | e3b0c44298fc | yes |
| release_revision | 0 | 0 | e3b0c44298fc | yes |
| stage_result | 4 | 4 | fedf749b33a2 | yes |
| vendor_list_entry | 3 | 3 | fa3223e7c61c | yes |
| vendor_list_revision | 2 | 2 | fa7ca02aa967 | yes |
| work_assignment | 2 | 2 | 90696999dbba | yes |
| work_assignment_event | 5 | 5 | 58e85572e6d5 | yes |
| worker | 0 | 0 | e3b0c44298fc | yes |
| finding_current_verdict (view) | 3 | 3 | b56b59b91d4e | yes |
| version_classification_current (view) | 3 | 3 | 1f00bf8af466 | yes |
| version_classification_revision (view) | 4 | 4 | 0c7ab77f36ec | yes |
| work_assignment_current (view) | 2 | 2 | 84c68b432a98 | yes |

Schema shape, source against target (same helper): columns 606 / 606, constraints 657 / 657, indexes 153 / 153, **triggers 72 / 72**, functions 145 / 145,
views 4 / 4, sequences 7 / 7, extensions 2 / 2, all equal.

### 4.2 A second look through plain `psql`, not through the compare module

Run on both databases after the drill (read-only; `psql` 17.11): `alembic_version` = `0029_routing_refusal_codes` on both; public tables 55 / 55, views 4 / 4,
non-internal triggers 72 / 72, indexes 153 / 153, `blob` rows and bytes `23|271413` on both; an md5 over the sorted `relation.trigger:enabled` strings is
`0d78f53a9a24629c273ee2f72857dbcb` on both; 657 constraints on both with the same md5 over `relation.name:type:validated`
(`7a1d1e1a5b2f53ca419e8b137a96f807`). The four constraints migration `0029` rewrote (`ck_command_record_error_code`, `ck_audit_run_terminal_reason`,
`ck_model_call_error_code`, `ck_provider_effect_error_code`) are validated on both sides and each definition contains both added codes
(`version_classification_required`, `section_profile_unavailable`), so the restored target has the `0029` vocabulary, not the `0028` one.

### 4.3 The benign constraint-text difference, re-measured

As at `0028`, `pg_dump` re-emits `CHECK`s as text and the restore's parser flattens nested `AND`s; the compare normalises parentheses and whitespace
for constraints only and reports the exact-text mismatch as informational. Measured here with `psql` (an md5 of `pg_get_constraintdef` per constraint,
source against target): **15** constraints print differently, none of them one of the four `0029` rewrote; with parentheses and whitespace stripped all 657
are equal. The `0028` report states 28; the two figures were not reconciled (the compare gates on the normalised form, not on this count), and this report
claims only the 15 it measured.

## 5. The deliberate negative (the drill can fail)

The loud guard is `audit_restored_schema` (`scripts/recovery/schema_coverage.py`), which the runner calls on the restored database.

**On the drill's own data**, helper B (appendix; exit 0, 1.2 s): `CREATE DATABASE … TEMPLATE` from the restored target gave a copy; the audit on the
unmutated copy passed (`tables=55, views=4, triggers=72, guarded_tables=29`, sequences 24/24 and 3/3); after `CREATE TABLE zz_unregistered` it refused:
`tables differ: missing=[], unknown=['zz_unregistered']`; after dropping that table and `vendor_list_entry` it refused:
`tables differ: missing=['vendor_list_entry'], unknown=[]`. The copy database was dropped afterwards.

**The existing tests that do the same on a fresh migrated clone**, `pytest tests/integration/recovery/test_schema_coverage.py -v -k "unlisted_norm_table or (schema_audit_refuses and (unregistered or dropped or another or wrong))"`:
**11 passed**, exit 0, 4.7 s:

```
test_an_unlisted_norm_table_would_fall_out_of_the_fingerprint_unseen PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[dropped append-only trigger] PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[dropped check constraint] PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[dropped immutable trigger] PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[dropped index] PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[dropped table] PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[dropped view] PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[relation in another schema] PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[unregistered table] PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[unregistered view] PASSED
test_the_schema_audit_refuses_a_schema_that_is_not_the_declaration[wrong head] PASSED
```

`wrong head` is the case that makes the audit refuse a restored database whose `alembic_version` is not the declared head; in the full run the two loud guards
`test_the_declared_head_is_the_alembic_head` and `test_the_declared_schema_equals_the_migrated_schema` also passed.

## 6. The recovery suite

`.venv/bin/python -m pytest tests/integration/recovery -q -rs` on the lane stack, one pytest process, tree `c8a11c60`: **308 passed in 133.19 s
(wall 135.4 s), exit 0**, no skip, no warning summary line. The brief's reference was 239 at `0028` (`RECOVERY-REBASE-01.md` §10). The difference is
explained, not hidden: `0e09de8a` (`STAND-PURGE-TOOL-01`, after that reference) added `test_product_purge.py` and `test_product_purge_script.py`, and
`pytest --collect-only -q` on those two files gives **69** tests; 239 + 69 = 308, which is also the figure in the message of `345ac443` (the commit that
moved the pin to `0029`). Nothing red, so no cause to report.

## 7. Not claimed

* **No real stand backup.** The source is a freshly seeded lane database, `real_data_marker` is false and the record names a synthetic source. Nothing was
  read from the stand, its database, its S3 bucket or its volumes.
* **The stand's Blob store was not inventoried** (`D-123`); a local drill does not touch it.
* **The retention policy** (`U-04`, `OPEN-RETENTION`, `not_decided`) is not exercised or decided here.
* **One server, two databases.** Source and target share the lane's PostgreSQL and MinIO containers; the runner's guards (distinct instance and bucket names,
  empty bucket, empty database, loopback, PG 17 tools) held, but this is database- and bucket-level isolation, not a second compose stack.
* **The norms corpus is not in the dataset.** All `norm*` tables are empty (one `norm_embedding_profile` row from the migration), so the Blob-bearing norm
  tables were audited live on zero rows; nine guarded tables were empty and not probeable (listed in section 4).
* **Roles and privileges are not restored** (`--no-owner --no-privileges` is the pinned restore); the lane uses one role.
* **Quiescence** of the source bucket is guaranteed by the operator (nothing else wrote to this private lane); the tooling detects a changed object but cannot
  prove quiescence.
* **Scale.** 227 rows and 23 objects are not W54-scale (28,920 objects on that stand) and not an attested copy of anything.
* **Whether 23 synthetic objects are a B6 drill** or a larger source is wanted remains the owner's judgement (`BETA-MATRIX-02.md` §B6).
* The 15 versus 28 exact-text constraint figure (section 4.3) is unreconciled.

## 8. Findings, decisions, instruction for the integrator

* **Defect:** none in the tooling at `0029`. No test or script was changed; `scripts/recovery/**` and `tests/integration/recovery/**` are untouched.
* **Observation (not a defect):** the compare module prints aggregates only, so a per-relation table needs a small caller of `database_profile` (helper A).
  If the operators want that table from the tool itself, it is a candidate follow-up, not needed for B6.
* **Observation:** the brief's "239 passed" is stale; the reference for the recovery directory at the current base is 308.
* **Decisions taken:** (1) `make bootstrap` rather than the shared interpreter for `make up`, because the recipe refuses without `.venv/bin/python`; (2) the §9
  driver wrapped per step so each exit status and time is recorded, commands unchanged; (3) target on the same containers as the `0028` run, the brief
  allocating one port pair; (4) the second plain-`psql` look and the live negative were added because they cost seconds and need no tooling change.
* **Suggested B6 wording for `BETA-MATRIX-02.md` (the integrator's file, not changed here):** "the synthetic drill was run at head `0029` on 2026-10-22
  (`RECOVERY-DRILL-0029-01.md`): 23 objects = 23 Blobs, 271,413 bytes, 55 tables, 4 views, 72 triggers equal; recovery directory 308 passed; limits as in §7
  there; the owner still judges whether synthetic data is a B6 drill", and row 14 of the matrix's action list is closed for the executor part.
* **Cleanup:** `make down` ran for `auditmanager-lane-i` (exit 0, 21.1 s). The containers and the network are gone, ports `57700`, `61500`, `61501` are
  released, no process of the lane remains. The two volumes `auditmanager-lane-i-postgres-data` and `auditmanager-lane-i-s3-data` remain (`make down` does not
  remove volumes and nothing else was to be removed); the drill root `.local/drill/drill-i0029` and the worktree `.venv` are git-ignored. Removing the
  volumes is the integrator's call.
* **Checks on this document:** `git diff --check c8a11c60..HEAD` exit 0; `pytest tests/contract/api_v1/test_surface_counts_in_prose.py tests/contract/api_v1/test_doc_prose_facts.py -q`
  (the container-free documentation prose guards, run with this file present): 77 passed, exit 0, 23.2 s. No other contract test was run (`R-135`).
* **Hotspots:** the only file this lane adds is this document; nothing under `src/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, `web/**`,
  dependency or lock files, `tests/support/**`, any `conftest.py`, `CURRENT_STATE.md` or `DEBT_REGISTER.md` was touched; no ref, tag or the stand; nothing was
  merged or pushed.

## 9. Reproduce

Section 9 of `RECOVERY-REBASE-01.md` with lane resources from the task file; `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, then
`make up check-services migrate check-db`, the seed, the drill script, the compare, `PYTHONPATH=src:. .venv/bin/python -m pytest tests/integration/recovery -q`, `make down`.
Needs MemAvailable of at least 1.5 GiB and a few MiB of disk for the drill (the bootstrap is about 220 MB).

## Appendix: the two helper scripts (read-only callers of the repository's own modules)

Helper A prints the per-relation table of section 4.1:

```python
import sys
from pathlib import Path
from sqlalchemy import create_engine
from scripts.recovery import synthetic_drill_compare as c

root = Path(sys.argv[1])
src, tgt = c._env(root / "source.env"), c._env(root / "target.env")
p = []
for v in (src, tgt):
    e = create_engine(v["DATABASE_URL"])
    try:
        p.append(c.database_profile(e))
    finally:
        e.dispose()
a, b = p
for kind in ("tables", "views"):
    for name in sorted(a[kind]):
        s, t = a[kind][name], b[kind].get(name)
        print(name, kind, s[0], t[0] if t else "-", s[1][:12], "yes" if s == t else "NO")
for label in a["shape"]:
    print("shape", label, a["shape"][label][0], b["shape"][label][0], a["shape"][label] == b["shape"][label])
```

Helper B is the live negative of section 5: it connects as the target's role to the maintenance database, runs
`CREATE DATABASE auditmanager_lane_i_negcopy TEMPLATE auditmanager_w58_target_i0029`, calls
`audit_restored_schema(Session(engine))` on the copy unmutated, again after `CREATE TABLE zz_unregistered (id integer PRIMARY KEY)`, and again after
`DROP TABLE zz_unregistered` and `DROP TABLE vendor_list_entry CASCADE`, expects `RestoredSchemaRefused` on the second and third calls (exit 1 if either is
accepted), and drops the copy in a `finally` block.
