# W52-FACTS-01 — executor handoff

Task: `docs/program/tasks/W52-FACTS-01.md`. Exact dispatch base:
`186637faeed19eef3dfa2f039d766ee6b5315e92`. This is code preparation under the
owner's QA/gate deferral, not W52 freeze or release evidence.

## Result

`tests/support/expected_facts.json` is the hand-maintained independent opinion about the
currently frozen W51 contract: explicit method/path/operationId triples and schema names,
path count, separate API and stored error counts, migration head and contract version. Its
Python reader validates the version, shape and uniqueness without consulting a contract
artifact. The existing Python and web tests now compare artifacts against those facts.

All 27 `CONTRACT_PIN_REGISTRY.md` entries now identify the corresponding consumers. The
inventory in `test_doc_prose_facts.py` rejects a new numeric assertion on a recognized
surface, error or head subject regardless of the number. It scans Python syntax and
masked TypeScript, excludes fixture data and leaves the unrelated `len(report)` assertion
out by its subject. The current facts match the frozen artifacts; focused mutations of
each current family (`surface`, `error_catalog`, `migration_head`, `contract_version`) are
detected. The history-boundary consumer retains its own needle mutation test.

## Changed files

- `tests/support/expected_facts.json`, `tests/support/expected_facts.py`
- `tests/contract/api_v1/test_doc_prose_facts.py`, `test_openapi_conformance.py`
- `tests/contract/domain_p02/test_contract_vocabulary.py`, `test_openapi_document.py`
- `tests/integration/api/test_served_document_and_health_plane.py`,
  `test_operation_surface.py`, `test_router_and_body_rules.py`,
  `test_envelope_screen_rules.py`
- `tests/integration/composition/test_api_token_channel.py`,
  `test_composition_root.py`; `tests/e2e/pc01/test_acceptance.py`
- `web/tests/contract/seam-operations.contract.test.ts`,
  `web/tests/unit/api/failure-surface.test.ts`,
  `web/tests/guards/frontend-lock.guard.test.ts`
- `docs/program/CONTRACT_PIN_REGISTRY.md`, `docs/program/W52-FACTS-01.md`

## Checks and limits

- Focused Python contract and pin-sweep tests: **211 passed**.
- Three focused web files: **86 passed**; `npm --prefix web run lint`: passed.
- Python syntax compilation and `git diff --check`: passed.
- Broad integration/API tests were stopped after a setup error: the suite requires a real
  private S3 bucket and `S3_ENDPOINT_URL` is absent. No stand was started. The owner
  deferred that evidence under D-139.
- Web typecheck was inspected after fixing this lane's tuple inference. It still reports
  the same two `exactOptionalPropertyTypes` errors on the dispatch base and this branch,
  in `src/_pages/account/ui/account-page.tsx` and
  `src/_pages/register/ui/register-page.tsx`. These are outside this task's grant and
  remain for a later correction stage and the D-140 gate run.
- No live QA or full `make gate` was run; D-139/D-140 remain open.

## Integration

No application contract, migration, runtime code, dependency, lockfile or global style
changed. Merge this clean branch into the integration line and publish only to `origin/dev`.
At W52 freeze, confirm the proposed facts-file policy, re-sweep the registry and task grants,
then run the later SEAL lane. A separate validation wave must settle the pending integration,
QA, typecheck and full-gate evidence before any W52 release claim.

All changed files are within the task's `allowed_paths`; forbidden hotspots are untouched.
Rollback is a revert of the implementation commit. There is no runtime feature flag.
