# DEBT-REGISTER-APPLY-01 — the three debt audits applied to the register

Base `1703d5ba` (`integration/ar-close-1026`). Date 2026-10-26. Only `docs/program/DEBT_REGISTER.md` and this task's two documents changed.

## What changed in the register

| Class | Rows |
| --- | --- |
| struck, `closed in the tree ... found on 2026-10-26 by DEBT-AUDIT-<N>` (18) | `D-124` `D-126` `D-127` `D-141` (audit 1); `D-198` (audit 2); `D-79` `D-87` `D-91` `D-107` `D-110` `D-69` `D-71` `D-68` `D-60` `D-61` `D-1.6` `D-8` `D-9` (audit 3) |
| kept open as narrowed, "code in the tree; validation waits for the complete gate (`D-139`/`D-140`)" (6) | `D-125` `D-128` `D-131` `D-134` `D-135` `D-136` (audit 1 proposed closing them; the register holds them open for deferred QA, so they are not closed) |
| narrowed, the audit's statement (20) | `D-119` `D-121` `D-129` `D-133` `D-137` `D-138` `D-140` `D-144` (audit 1); `D-165` `D-183` `D-184` `D-186` `D-197` `D-199` `D-203` (audit 2); `D-75` `D-83` `D-108` `D-117` `D-59` (audit 3) |
| stale cite or count corrected only (3) | `D-178` (13 to 14 profiles), `D-187` (stage-registry hash and the `Makefile` cite), `D-191` (`nginx.conf:143` to `:257`) |

The table goes from 144 to 145 data rows (the shared `D-1.6, D-8` row becomes two struck rows): 73 struck and 72 open, from 55 and 89.

31 detail sections got one line at the top, `*Re-measured 2026-10-26 (DEBT-AUDIT-N): <class>; see the table row.*`: `D-119` `D-121` `D-124` `D-126` `D-127` `D-129` `D-133` `D-137` `D-138` `D-140` `D-141` `D-144` `D-165` `D-75` `D-79` `D-83` `D-87` `D-91` `D-107` `D-108` `D-110` `D-117` `D-69` `D-71` `D-68` `D-59` `D-60` `D-61` `D-1.6` `D-8` `D-9`. The six held-open rows have no line: their sections already read "narrowed ... not closed". `D-109`, `D-50`, `D-11` have none either, because their stale count and cites live only in the detail section and their table row is unchanged.

## Changed set against the audited set

A script kept out of git (scratchpad) parses the table before and after, lists every id whose row text changed and compares it with the ids the three audits classified `CLOSED-IN-TREE` or `NARROWED` plus the stale-cite rows.

```text
CHANGED table rows (47): D-1.6 D-8 D-9 D-59 D-60 D-61 D-68 D-69 D-71 D-75 D-79 D-83 D-87 D-91 D-107 D-108 D-110 D-117 D-119 D-121 D-124 D-125 D-126 D-127 D-128 D-129 D-131 D-133 D-134 D-135 D-136 D-137 D-138 D-140 D-141 D-144 D-165 D-178 D-183 D-184 D-186 D-187 D-191 D-197 D-198 D-199 D-203
EXPECTED: audited CLOSED-IN-TREE or NARROWED (45) minus proposal 'unchanged' ['D-104'] plus stale-cite rows ['D-178', 'D-187', 'D-191'] = 47
D-1.6 D-8 D-9 D-59 D-60 D-61 D-68 D-69 D-71 D-75 D-79 D-83 D-87 D-91 D-107 D-108 D-110 D-117 D-119 D-121 D-124 D-125 D-126 D-127 D-128 D-129 D-131 D-133 D-134 D-135 D-136 D-137 D-138 D-140 D-141 D-144 D-165 D-178 D-183 D-184 D-186 D-187 D-191 D-197 D-198 D-199 D-203
changed - expected: []
expected - changed: []
MATCH
rows total: 145 identical: 98
outside table (after removing the 31 note lines): BYTE-IDENTICAL
```

`D-104` is the one audited id that is not changed: the audit classifies it `NARROWED` and proposes its wording `unchanged` (the row is already worded as narrowed and holds). The script is red under a mutation: appending `!` to the `D-120` row prints `changed - expected: ['D-120']` and `MISMATCH`; appending `!` to a line of the closing prose prints `outside table ...: DIFFERENT`. Both were reverted (`cmp` against the saved final text).

## Verification

- `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`: exit 0, **105 passed**.
- `git diff --check`: exit 0, no output.
- The task file's `governance_findings`: `[]`.
- Every 8-hex commit written into a changed row (50 distinct) resolves to a commit in this repository (`git cat-file -t`). No commit or check was invented: the checks are those the audits quote, `D-125`/`D-128`/`D-131`/`D-134`/`D-135`/`D-136` take theirs from the audit's closed wording.

## Judgement calls the integrator may want to overrule

- Bold ids: NARROWED rows keep the id bold, per the brief. `D-117`, `D-125`, `D-128`, `D-129`, `D-131`, `D-134`, `D-135`, `D-136` were not bold before and are now.
- Needs cells were left as they were except in two rows where the new summary negates them: `D-119` (the rehearsal passed, so the cell now names the lifecycle decision and the stand promotion after `D-123`) and `D-121` (an endpoint serving `build_id` exists, so the cell now says a served commit name is the contract question). Both use the audit's own words.
- `D-187`: `DEBT-AUDIT-2` quotes the current `stage-registry.json` hash as `d7b9994b…`, true at its base. The contract seal `a6761bf4` landed after it and the file now hashes to `7e1aaaaf…` (`sha256sum`), so the row states the hash at `a6761bf4` and names the earlier changes (`a20f9211`, `e66b2483`, `b4291c12`) instead of the audit's value. The clause that the gate ignores a stale pin (`Makefile` 541-542) stands.
- `D-141` and `D-87` are struck on code and a test that need PostgreSQL; the wording says so (`D-141`: "read, not run, by the audit"; `D-87`: "needs the lane database").
- `D-71` is struck on code plus a ledger under `.local/` (invisible to git); `D-91` on an owner ruling plus the absence of the three strings in `web/src`.

## Left alone on purpose (rule 3: only a stale cite or count is corrected)

- `D-145`: "carried to the first minor version after the 1.0.0 seal" is overtaken (the contract is `1.5.0`, the field is still absent). A prose claim, not a cite or count.
- `D-171`: the 307 s and 415 s figures predate `0c5ab9ca`; the audit says a note "may be added".
- `D-109` (count 24 to 25), `D-50` and `D-11` (line cites): they sit in the detail sections, which are not rewritten.
- `D-96`: the audit confirms the row is still true.

## Not run

No database, stand, browser or Vitest run: the audits' own results stand for those. The DB-bound cases are `tests/integration/jobs/test_d141_final_transaction_keeps_the_lease.py`, `tests/integration/db/test_schema_invariant_inventory.py`, `tests/integration/db/test_norm_embeddings_migration.py` and the F-10 cases of `tests/integration/ingest/test_bundle_publication.py`.
