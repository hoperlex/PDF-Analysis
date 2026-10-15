# GATE-OPT-INT-01 — local integration result

The remote `origin/dev` was rechecked at
`8069220909e40c39e2329d5f5cb9585a5a5714ec`. Local branch
`integration/gate-opt-01` fast-forwarded from that SHA to source commit
`8db6201139ef431f4e1479a20517f5e4b5100d72` without conflicts.
Nothing was pushed or deployed; no tag was created.

## Checks on the integrated source tree

| Check | Result |
| --- | --- |
| `git ls-remote --heads origin dev main` | dev `80692209`, main `23fd729d` |
| `git merge --ff-only task/gate-opt-01` | exit 0; exact source tip `8db62011` |
| `make -n gate-fast gate-affected gate` | exit 0 |
| Focused `test_gate_tiers.py`, `test_light_acceptance_command.py`, `test_gate_host.py` | 46 passed in 6.87 s; five pytest temporary-cleanup warnings |
| `tests/unit` and the two API prose/surface guards | 78 passed in 12.47 s; five pytest temporary-cleanup warnings |
| `git diff --check origin/dev..8db62011` | exit 0 |

The programme governance suite exposed missing template sections in both new
source task files and this integration task. The three task files now declare
enumerator ownership, captured premises, historical evidence and publication
authority. After that correction, their individual `governance_findings()`
sets are empty. The whole governance suite still has one failing inventory
test because six tracked `W56A-*` task files on the unchanged `origin/dev`
base lack the same declarations; the other 15 governance tests pass. Those
six paths are outside this task's allowed paths. This is a pre-existing gate
limitation, not a green governance suite claim.

The focused Python checks used `/root/projects/PDF-Analysis/.venv/bin/python`
from the equipped parent checkout, with the isolated integration worktree as
the working directory. That worktree has no `.venv`, `web/node_modules`,
corpus link or `.env`, so an actual `gate-fast`, frontend suite, complete gate
or service-backed run is not claimed. `R-135` defers the complete gate to the
final beta candidate. The markers `GATE FAST OK` and `GATE AFFECTED OK` are
not the literal full-gate `GATE OK`.

## Scope and follow-up

The source diff has six paths: `Makefile`, `test_gate_tiers.py`, the two task
files and their two reports. This integration corrects only those two task
files and adds its task and report.
No contract, migration, root dependency/lock, composition root, global style,
runtime code or deployment file changed. The API contract still hashes to
`fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`.

The later beta-gate task should run the complete gate on a provisioned clean
candidate and capture `GATE TIMING` plus pytest `--durations=20`. The suite
audit lists separate experiments for repeated frontend compiler/census work
and backend archive/shell subprocess work. Its historical times are not a
current full-gate baseline.

Rollback is a local reset or deletion of this integration branch; the source
branch remains intact. There is no ref publication authority in this task.
