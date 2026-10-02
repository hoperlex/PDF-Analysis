# W48-FIX-B — upheld Stage-B guard repairs

## Result

**DONE for the bounded repair; W48 remains blocked by `A-01` and `A-02`.** Implementation commit
`268d6ab` closes the three false greens upheld by both judges:

- `X-01`: `dependency_unavailable` can no longer coexist with an overall acceptance `PASS`;
- `X-02`: a `/projects` redirect is accepted only on the declared normalised origin;
- `Y-01`: every task file absent from the exact governance-activation tree is automatically
  enumerated and validated.

No public host, credential, provider, bucket, deployment, ref or tag was touched. The evidence
schema remains `w48-alpha-acceptance/v1`; API/domain/error contracts, migration head and
dependency locks are unchanged.

## Repairs

### X-01 — root acceptance is a projection of required phases

`verify-acceptance.mjs` now constructs all seven phase outcomes first. Its root verdict is:

1. `FAIL` if any required phase is `FAIL`;
2. otherwise `BLOCKED` if any phase is `BLOCKED`;
3. otherwise `PASS`.

The provider phase is always `BLOCKED` when the newly created run reports
`dependency_unavailable`, independent of `journeyExit`. A provider-caused journey stop also
classifies the deliberately unrun refusal process as BLOCKED only for the script's explicit
sentinel (`refusalsExit=99` plus missing envelope). Malformed present evidence, an actual refusal
finding and unrelated non-zero exits remain FAIL.

The exact judge shape is committed as a regression: `partial`, `provider_mode=live`, typed
dependency outage, complete 3/3 writes and 16/16 routes, and `journeyExit=0`. The verifier now
exits `2`, records `providerLive=BLOCKED`, records root `BLOCKED` and does not print PASS. The
positive control also asserts that a root PASS contains only PASS phase outcomes.

### X-02 — redirect origin is parsed, not suffix-matched

`manual-alpha-check.sh` resolves `Location` against `--origin` with Python's standard-library URL
parser. It rejects user-info and parse ambiguity, normalises scheme/hostname and default ports,
requires the same `(scheme, host, effective port)`, and then requires exact path `/projects` with
no query or fragment.

Controls prove relative `/projects`, absolute same-origin `/projects`, host-case normalisation and
explicit default HTTPS port pass. A foreign host, changed scheme, non-default port, user-info,
lookalike host, longer path and query all fail preflight. No package or lock change was needed;
`python3` is required only for networked modes, not `--files-only`.

### Y-01 — post-activation task set has a total enumerator

`test_wave_governance.py` fixes activation at the exact subject which delivered the governance
rules: `14caf886e78883ed771d81fbf463c98af727c938`. `git ls-tree` yields the captured 85 historical
task paths. The live side enumerates every `docs/program/tasks/*.md` file from the filesystem and
calls `governance_findings()` for every path absent from that exact baseline.

This keeps historical task bytes untouched without an editable exemption list. A new untracked or
tracked task is visible immediately. The committed synthetic test proves one exact legacy path is
excluded, a compliant new task passes, and a broken new task yields all four missing-section IDs.

The judge's stronger repository mutation was also repeated: adding an actual untracked
`docs/program/tasks/W49-FIX-B-BROKEN.md` and running the live-set test exited `1` and named:

```text
docs/program/tasks/W49-FIX-B-BROKEN.md
ENUMERATOR_SECTION_REQUIRED
PREMISE_SECTION_REQUIRED
HISTORY_SECTION_REQUIRED
PUBLICATION_SECTION_REQUIRED
```

The mutation was removed before commit.

## Checks

On clean implementation commit `268d6ab`:

```sh
bash -n scripts/manual-alpha-check.sh
/root/projects/PDF-Analysis/.venv/bin/python -m pytest \
  tests/contract/test_alpha_acceptance_command.py \
  tests/e2e/test_pc01_journey_conformance.py \
  tests/contract/program/test_wave_governance.py -q
git diff --check
```

Result:

```text
106 passed in 7.91s
```

Additional evidence:

- the exact invalid task-directory mutation failed `1` and named its path plus four rule IDs;
- the focused suite excluding the clean-checkout automated case passed `27` tests while the
  implementation worktree was dirty;
- PC-01 conformance alone passed `78` tests;
- `git diff --name-only cf69c76..268d6ab` lists exactly the four implementation/test paths below.

## Changed files

- `scripts/manual-alpha-check.sh`
- `tests/e2e/pc01/journey/verify-acceptance.mjs`
- `tests/contract/test_alpha_acceptance_command.py`
- `tests/contract/program/test_wave_governance.py`
- `docs/program/W48-FIX-B.md` — this completion report

## Contracts and known limitations

No API, domain, error, evidence-schema, migration, dependency/lock, composition-root or global
style contract changed. The frozen surface remains 17 paths / 20 operations / 61 schemas, error
catalog 22 and migration head `0013_norm_embeddings`.

Known limitations and blockers:

1. `A-01` remains release-blocking: provider effect still precedes durable call/attempt authority.
2. `A-02` remains release-blocking: analysis Blob publication still precedes committed metadata
   without an outbox/orphan reconciler.
3. `A-03` remains the measured minimum sixteen-site architecture debt pending an owner ruling.
4. No credentialed public alpha journey or kill-after-side-effect test ran in this task.
5. The activation enumerator intentionally depends on the repository Git tree, as the programme
   gate and the pre-existing immutable-history check already do.

## Integration and rollback

Integrate the complete `agent/w48-fix-b` branch after both judge reports. Re-run the 106-test scope
on the merged SHA. Do not claim W48 closure, create `alpha-w48`, publish `origin/dev`, or run a
deployment while `A-01` and `A-02` remain unresolved. `origin/main` additionally requires the
owner's separate direct instruction for the exact final candidate.

Rollback is a revert of the W48-FIX-B implementation and report commits; no data or host rollback
is required.

## Forbidden-hotspot proof

Relative to dispatch `cf69c76`, the task changes only its five allowed paths. Contracts,
migrations, root dependencies/locks, runtime/business/storage code, composition roots, frontend
source, workflows, global styles, task briefs, judge/audit reports, state/register documents,
deployment state, refs and tags are byte-untouched.
