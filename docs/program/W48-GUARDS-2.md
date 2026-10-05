# W48-GUARDS-2 — completion report

## Result

**DONE, with the inherited full-contract quarantine reported below.** The G-1 through G-6
guards now reject executable semantic regressions rather than comments, fixed partial inventories
or unchecked strings:

- screen-wide consumers are discovered and may not install private router/query providers;
- dashboard mutation hooks are discovered in both `.ts` and `.tsx`, including namespace-qualified
  `useMutation`, and must execute the exact dashboard invalidation;
- prose count checks recognise the two missed sentence forms without depending on clone history;
- wave-governance evidence must contain valid declarations and substantive captured output;
- a partial journey with failed text analysis cannot pass provider-live acceptance, and the report
  calls the deployed SHA an operator attestation rather than served-revision proof;
- deploy-workflow triggers, top-level permissions and complete pinned host-key blobs are checked
  structurally.

The implementation is commit `a73a331` (`test: make W48 closure guards semantic`). This report is
the follow-up evidence commit.

## Changed files

- `web/tests/guards/screen-set.guard.test.ts`
- `web/tests/guards/dashboard-invalidation.guard.test.ts`
- `tests/contract/api_v1/test_surface_counts_in_prose.py`
- `tests/contract/api_v1/test_doc_prose_facts.py`
- `tests/contract/program/test_wave_governance.py`
- `tests/contract/test_alpha_acceptance_command.py`
- `tests/contract/test_deploy_auto_workflow.py`
- `tests/e2e/pc01/journey/verify-acceptance.mjs`
- `scripts/manual-alpha-check.sh`
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`
- `docs/program/W48-GUARDS-2.md`

## Required mutation evidence

Every mutation was applied in a unique external scratch copy. No mutation byte was applied to the
task worktree.

### G-1 — a sixth private screen provider is discovered

Scratch `/tmp/w48g2-g1.9Ktc6Q` added
`web/tests/guards/sixth-screen.guard.test.ts` with a real `AppRouterContext.Provider`. Running
`screen-set.guard.test.ts` exited 1 (`1 failed, 10 passed`) and named both defects: the new screen
did not consume the shared `renderScreen` harness and privately mounted
`AppRouterContext.Provider`.

### G-2 — call kind, extension and namespace syntax are load-bearing

- Scratch `/tmp/w48g2-g2a.QgZfqJ` replaced the create-project hook's `invalidateQueries` call
  with `getQueryData`. `dashboard-invalidation.guard.test.ts` exited 1 and reported that the
  create-project target lacked executable dashboard invalidation. Merely reading the same key did
  not satisfy the guard.
- Scratch `/tmp/w48g2-g2b.tnBdVe` added a `.tsx` hook using `RQ.useMutation`.
  `dashboard-invalidation.guard.test.ts` exited 1 (`1 failed, 10 passed`) and named the newly
  discovered `src/features/mutation-probe/model/use-mutation-probe.tsx` hook.

### G-3 — both missed prose forms are rejected

Scratch `/tmp/w48g2-g3.cLfz7J` inserted `twelve public operations. The API has twelve routes.`
into a tracked source file. The focused prose guard exited 1 and independently reported:

- `'twelve public operations' states 12 for operations, expected 20`;
- `'twelve routes' states 12 for unlisted surface noun, expected {17,20,61,22}`.

The committed self-test also replaces Git history access with a failing stub and remains green,
proving that shallow-clone depth cannot disable the historical-number check.

### G-4 — empty, unread and placeholder governance evidence is rejected

Each copy ran the whole-new-task governance test and exited 1:

- `/tmp/w48g2-g4a.Sdx6KY`: empty `Enumerator ownership` body —
  `ENUMERATOR_CHANGE_DECLARATION_REQUIRED`;
- `/tmp/w48g2-g4b.KgxFs3`: non-enumerator flag `perhaps` —
  `ENUMERATOR_CHANGE_DECLARATION_REQUIRED`;
- `/tmp/w48g2-g4c.ERcdV3`: `captured_output: x` —
  `PREMISE_OUTPUT_SUBSTANTIVE_REQUIRED`;
- `/tmp/w48g2-g4d.MNi7jf`: main authority
  `separate direct owner instruction x` — `MAIN_DIRECT_AUTHORITY_REFERENCE_REQUIRED`.

### G-5 — failed text analysis cannot become provider-live PASS

Scratch `/tmp/w48g2-g5.NGYSM4` supplied an otherwise valid journey with terminal `partial` and
`text_analysis.status: failed`. The verifier exited 1 and printed `acceptance verdict: FAIL` plus
`the newly created run has a failed text_analysis stage`; the verdict JSON recorded
`providerLive=FAIL` and overall `FAIL`.

The committed acceptance-command test now asserts the exact set of guard paths that fire when
prerequisites are absent, not only a non-zero exit. The runbook and generated report use
`attested_deployed_sha` and explicitly state that operator input is not served-revision proof.

### G-6 — workflow structure and complete host-key material are pinned

Each copy ran `tests/contract/test_deploy_auto_workflow.py` and exited 1 (`1 failed, 6 passed`):

- `/tmp/w48g2-g6a.Qrojyg`: added `pull_request_target:` — `DEPLOY_TRIGGER_SET`;
- `/tmp/w48g2-g6b.lScRU9`: changed top-level permission to `contents: write` —
  `TOP_LEVEL_PERMISSIONS`;
- `/tmp/w48g2-g6c.Md0qD9`: changed one full host-key blob while retaining its fingerprint
  comment — `PINNED_HOST_KEY_BLOB`.

## Checks and results

- `npm --prefix web test -- --run tests/guards` — **18 files passed, 185 tests passed**.
- `.venv/bin/python -m pytest tests/contract/api_v1/test_surface_counts_in_prose.py
  tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/program/test_wave_governance.py
  tests/contract/test_alpha_acceptance_command.py
  tests/contract/test_deploy_auto_workflow.py -q` — **108 passed in 5.95s** on the clean
  implementation commit.
- `.venv/bin/python -m pytest tests/contract
  --ignore=tests/contract/test_cp00_candidate.py
  --ignore=tests/contract/test_cp00_final_state.py
  --ignore=tests/contract/test_validate_bootstrap.py -q` — **439 passed, 49 subtests passed in
  10.34s**. These are the three quarantine exclusions prescribed by
  `OPERATING_CONSTRAINTS.md` §§7 and 11.
- `npm --prefix web run typecheck` — exit 0.
- `npm --prefix web run lint -- --quiet` — exit 0.
- `git diff --check` — exit 0.

The task's literal required `.venv/bin/python -m pytest tests/contract -q` is **inherited RED**,
not represented as a pass. In the linked task worktree it finished with **66 failed, 601 passed,
126 errors, 452 subtests passed in 82.24s**. The errors are the documented linked-worktree
limitation: legacy CP-00 tests call `shutil.copytree(REPOSITORY_ROOT / ".git", ...)`, while a valid
linked worktree has `.git` as a file. A second run from a standalone clone reached **695
passes and 510 passing subtests**, but the three documented quarantine modules remained red
(`196 failed` overall); an environment symlink also correctly tripped the checkout-clean
acceptance assertion. The task changes none of those three modules. Per the programme constraint,
they were neither weakened nor repaired outside this grant; the green 439-test run above proves
the non-quarantined contract boundary.

A broader canonical `tests` battery was started in the linked worktree, encountered the same
legacy `.git` copy errors, and then made no progress or output for more than five minutes in a
legacy segment. Only that task-owned pytest process was interrupted (exit 130); no service or
other lane process was touched. No green claim is made for that interrupted run.

## Contracts, migrations and runtime

No contract, schema, migration, dependency/lock file, production runtime, workflow, composition
root or global style changed. The frozen surface remains 17 paths / 20 operations / 61 schemas,
the error catalog remains 22 entries, and the accepted closure head remains
`0014_durable_analysis_effects`. The `test_doc_prose_facts.py` change only discovers that head
from the migration tree instead of pinning the former `0013` literal.

## Risks and known limitations

- No served revision identity endpoint exists. Alpha evidence can attest an operator-supplied
  deployed SHA, but cannot prove which revision a host served; the report says so explicitly.
- The literal full-contract command includes the three long-standing red quarantine modules
  described above. The scoped non-quarantined contract suite and all changed guard modules are
  green; changing quarantine policy is outside this task.
- This task used no public host, credentials or live services. It does not claim deployment or
  end-to-end alpha acceptance.

## Integrator handoff

Integrate the final report commit after the durable fix and before tails, then run the merged-tree
gate under the integration lane. No feature flag or data rollback applies: this is test/evidence
only, so rollback is a revert. This executor performed no merge, push, tag or deployment action.

## Forbidden-hotspot and allowed-path proof

`git diff --name-only 03c04a1d87fda862d085a6a49d0a46f2692f7ffd..HEAD` is limited to the
eleven paths under “Changed files”, each explicitly granted by `W48-GUARDS-2`. In particular,
`contracts/**`, `db/migrations/**`, production source, dependency/lock files, composition roots,
workflow files, global styles, programme state/registers and Git refs are untouched.
