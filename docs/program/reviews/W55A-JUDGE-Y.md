# W55A-JUDGE-Y — W55a consistency review (static)

**Reviewer:** a fresh-context subagent of the integrator, 2026-10-13.
**Subject:** `9c635ee`; W55a range `2122cee..9c635ee`.
**Verdict:** no blocker, one major finding (plan text), four minor findings.

## Holds

- **Lineage and qualification.** The setter's keys equal what the importer and embedder write: the `EMBEDDING_PROFILE` constant, `chunking_profile` foreign-keyed to `0013`, the completion row written last, and the binding slot equal to `export.py:564`. A partial binding set fails. `listNormSnapshots.qualified` runs the same SQL.
- **Pinning (`R-82`, `R-113`).** The pin is read in the caller's transaction after the ledger claims the key, and replays pin nothing new. A NULL-pin digest is byte-identical to the basis. A re-audit pins the current snapshot. Runs created before W55 are not rewritten.
- **ALR-05 and AGENTS §4.** Both hold.
- **`0020`.** `norm_designation_tokens` is honestly `IMMUTABLE`. Both partial-index predicates appear as literals in every search statement.

## Findings

| # | Severity | Finding | Where | Disposition |
| --- | --- | --- | --- | --- |
| Y-1 | Major | §A7 (P4) and P3 step 2 prescribe only the full copy. Under `R-110` the stand holds test data only, and any full `attest` writes the `real_data` marker, which permanently ends the waiver path. On the waiver path the plan's `restore-db` failure branch cannot run, because a waiver has no dump. Amendment 1's "P4 needs no copy or window" ignores the 12 h waiver expiry. | `W55-PLAN.md:278, 329-352`; `copy-serve.sh:770-792`; `W54-FREEZE-01.md` | `W55A-FREEZE-01` amendment 1 (fork on `real_data_marker`), plus both branches in `W55A-REHEARSAL-01` |
| Y-2 | Minor | §A7 step 4 says "re-run until it exits 0", but `import` is detached and exits 0 at once. | `W55-PLAN.md`; `receive-bundle.sh:456-479` | Same amendment: wait until `status` shows `exited 0`; `requeue` on poisoned |
| Y-3 | Minor | The history guard accepts a reused older event, and an event can be inserted without changing the current row, which makes a never-current snapshot searchable by explicit scope (direct SQL only). | `0020:10-13, 179-214`; `current_snapshot.py:133` | `W55A-FIX` (together with JUDGE-X M4) |
| Y-4 | Minor | The parser splits designation tokens on any Unicode whitespace; the SQL function splits on ASCII `[ ._-]`. A no-break space, a tab or an en dash gives an empty page. | `norms/search/query.py:102,145`; `0020:100-110` | `W55A-FIX` |
| Y-5 | Minor, plausible | Nothing before designation enforces `characters-v2`. A v1 bundle imports and reports clean, then designation is refused after the import. | `norms/bundle/cli.py:134`; `service.py:542` | Amendment precondition, plus an export or manifest refusal in `W55A-FIX` |

## Needs the database or the rehearsal

- `EXPLAIN` of the ranked query; whether the clause `LIKE` uses its index under psycopg generic plans.
- The stand's `datctype` («Бетон» against «бетон»), and the real `clause_number` format.
- The import-time cost of `text_tsv` and the GIN index.
- The whole of §A7, both branches.
