# W48-GOV — completion report

## Result

`W48-GOV` is complete on local branch `agent/w48-gov`.

The governance lessons behind D-77, D-89, D-96 and D-117 are now maintained rules rather than
register prose alone:

- the task template requires an enumerator path, sole owner and totality query whenever a task
  changes a maintained set;
- an exact path, line or count premise requires a dated command and its captured, untruncated
  output;
- corrections to completed task/review evidence are new addenda, never rewrites;
- `origin/dev` is the development-candidate ref, while `origin/main` is an external deployment
  action requiring a separate direct owner instruction for the exact SHA.

`tests/contract/program/test_wave_governance.py` executes those rules and proves four superficially
plausible documents fail for their intended reason: missing enumerator owner, command without
dated captured output, rewritten-history mode and implicit `origin/main` publication.

## Historical correction and D-52 reconciliation

`docs/program/W46-HISTORICAL-ADDENDUM.md` corrects D-117 without changing one byte of any W46
source report. It distinguishes task-local evidence from the later integrated gate, corrects the
M5 quote, separates the behaviour commit `f50e656` from contract reseal `069f656`, and preserves
the prospective cookie/422 test limitation as still uncorrected.

The audit's A-05 / D-52 finding is confirmed as stale governance, not an open licence omission:

- commit `4a602baffee21567f7623de4dd0bcc672c788351` introduced both the copied icon geometry and
  `web/NOTICE`;
- `web/NOTICE` contains the Feather source/provenance map, Cole Bemis copyright and MIT text;
- `icon-convention.test.ts` and `icon-provenance.test.ts` pass **43/43** on this tree.

This task cannot edit `DEBT_REGISTER.md`; `W48-INT-CLOSE` must append the D-52 closure there and
link this report/A-05, rather than deleting the historical row.

## Changed files

- `docs/templates/TASK_TEMPLATE.md`
- `docs/program/WAVE_EXECUTION_GUIDE.md`
- `docs/program/dispatch/OPERATING_CONSTRAINTS.md`
- `docs/program/W46-HISTORICAL-ADDENDUM.md`
- `tests/contract/program/test_wave_governance.py`
- `docs/program/W48-GOV.md`

## Checks

| Check | Result |
| --- | --- |
| `.venv/bin/python -m pytest tests/contract/program/test_wave_governance.py -q` | PASS; 10 passed |
| same module plus `test_surface_counts_in_prose.py` and `test_doc_prose_facts.py` | PASS; 77 passed |
| invalid: enumerated set with no owner | fails `ENUMERATOR_OWNER_REQUIRED` |
| invalid: command without dated output | fails `PREMISE_OUTPUT_REQUIRED` and the missing-date rule |
| invalid: `correction_mode: rewrite` | fails `HISTORICAL_ADDENDUM_REQUIRED` |
| invalid: `development_target: origin/main` with no direct authority | fails `MAIN_DIRECT_AUTHORITY_REQUIRED` |
| frozen-base comparison for six original W46 reports | PASS; every byte identical to `fad3c287…` |
| `npm --prefix web test -- --run tests/unit/icon-convention.test.ts tests/unit/icon-provenance.test.ts` | PASS; 2 files / 43 tests |
| `git diff --check` | PASS |

## Contracts

No API/domain contract, generated client, error catalog, migration, dependency/lock, Makefile,
composition root, global style or runtime source changed. The governance field names are a task
document convention, not an application API.

## Risks and known limitations

- Existing task files are historical inputs and are not retroactively rewritten into the new
  template. The executable validator is applied to the template and its valid/invalid fixtures;
  new dispatches inherit the fields from that template.
- Host logs are mutable. The W46 addendum uses immutable commit messages as the durable evidence
  and labels 2026-10-02 log hashes as corroboration only.
- The D-117 cookie/422 proof-test limitation remains a test-design debt; this docs-only task does
  not repair contract tests.
- D-52 remains textually open in `DEBT_REGISTER.md` until integration close, even though its
  operational repair and 43 tests are now re-proved.

## Integrator instruction

1. Integrate this lane after `W48-LIVE`, as dispatched.
2. Preserve all six W46 source reports byte-for-byte; take the new addendum as the correction.
3. In `W48-INT-CLOSE`, append/reconcile D-52 as closed by `4a602ba`, with this report and
   `W48-AUDIT` A-05 as the later proof. Do not erase its original evidence.
4. Use the four new template sections for every newly dispatched task.
5. Publish the final clean candidate to `origin/dev` only. Do not update `origin/main` unless the
   owner separately and directly authorises deployment of that exact candidate.

## Forbidden-hotspot proof

The diff from Stage-B dispatch base `7ad7cfe` contains only the six allowed paths listed above.
The W46 source reports, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, contracts, runtime sources,
workflow/deploy files, refs, tags, host state and secrets are untouched. No remote write occurred.
