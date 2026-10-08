# W52-RELNOTES-01 — authored release notes hand-back

**Base:** `origin/dev` read-back
`3fcdb3ee5a08b12d9145f29da02de358bdbd57f7`.
**Lane:** `agent/w52-relnotes-01`. This is a development candidate; neither
entry is claimed to be deployed as a `0.3.0` product release.

## 1. Result and changed files

Both authored files now have revision 2. `0.3.0` has four dated product items;
`0.2.0` is the one-entry `0.1–0.2` archive. A dictionary and gate-time Python
form checks cover version/date ordering, title and item bounds, kind order,
length, punctuation, code traces and dictionary words. A Vitest check binds
only the current entry's display paths to the live registry. The English
release process and technical ledger scaffold are ready for a later measured
release row.

Changed paths:

```text
release-notes/0.3.0.json
release-notes/0.2.0.json
release-notes/dictionary.json
tests/contract/release_notes/test_release_notes_form.py
web/tests/unit/release-notes/current-screen.test.ts
docs/program/RELEASE_PROCESS.md
docs/program/RELEASES.md
docs/program/W52-RELNOTES-01.md
```

## 2. Checks

- `.venv/bin/python -m pytest -q tests/contract/release_notes
  tests/integration/releases/test_release_loader.py::test_shape_schema_matches_the_served_item_and_kind
  tests/integration/releases/test_release_loader.py::test_unknown_or_invalid_entry_refuses_before_database`:
  **26 passed**. This validates both authored files against the sealed shape
  and runs 19 named bad-form fixtures, plus a quoted-term allowance and
  unknown-field refusal.
- `npm exec -- vitest run tests/unit/release-notes` from `web/`:
  **3 passed**, including bad current paths and a historical path that is no
  longer in the registry.
- `npm run lint -- --quiet` and `npm run typecheck` from `web/`: passed.
- `git diff --check`: passed. The final commit/path audit is in the integration
  hand-back.
- Database-backed loader tests, full `make gate`, built-stand/browser QA and
  live/manual acceptance were not run here. They remain D-137–D-140.

## 3. Claim evidence

| Entry and item | Author-facing claim | Exact implementation/test evidence |
| --- | --- | --- |
| `0.3.0` 1 | The account menu opens dated release history | `93bd4da` (`web/src/_app/account-menu.tsx`, `web/src/widgets/version-history/ui/version-history.tsx`); `web/tests/unit/release/history.test.ts` |
| `0.3.0` 2 | An administrator approves with a role or rejects with a reason | W51 merge `4442921` and `docs/program/W51-ADMIN-REQUESTS.md`; `web/tests/unit/widgets/registration-queue.test.ts` |
| `0.3.0` 3 | An administrator sees users and edits account roles | W51 merge `c88e794` and `docs/program/W51-ADMIN-USERS.md`; `web/tests/unit/widgets/user-management.test.ts` |
| `0.3.0` 4 | Projects and dashboard share the Work navigation group | W50 frame commit `ca8674c`, `web/src/_app/navigation.ts`, registry rows; `web/tests/unit/shell/navigation.test.ts` |
| `0.2.0` 1 | Early prototype flow covered document work, finding review and expert decisions | W48 deployed candidate `23e0579`; `docs/manual-tests/PC-01_prototype.md` §§3–4 names the upload, findings and decisions; `tests/e2e` PC-01 journey |

The item categories and display locations are separately checked by the form
and registry suites. The archive sentence describes earlier capability, not a
new W52 implementation.

## 4. Contracts and risks

No API, domain, migration, schema, generated client or `contract_version`
changed. The JSON data follows the sealed schema. The loader must append
revision 2 above any stored revision 1; a same-revision content change would
refuse, so reverting a published correction requires a higher revision.

`tests/integration/releases/test_release_loader.py` currently asserts literal
revision-1 rows and constructs revision 2 as its *next* edit from `_notes()`.
Those assumptions become stale when `_notes()` reads these new revision-2
files. The path is outside this lane's grant. The integrator needs a narrow
test-only correction task before claiming a full gate. No loader behavior
change is indicated by this finding.

## 5. Integration instruction

Verify the clean lane diff, merge it into the Stage-C2 integration tree before
`W52-ACCEPT-01`, then correct the stale database-test revision literals under
an integration-owned grant. Re-run the targeted form, registry and loader
checks that the environment permits, and publish only the accepted candidate
to `origin/dev`. `origin/main`, a tag and a ledger release row require the
later exact-candidate release process and separate owner instruction.

## 6. Hotspot proof

The changed-path list in §1 is exactly the task's allowed set. In particular,
`release-notes/schema.json`, `contracts/**`, migrations, root dependencies and
locks, the loader, UI implementation, screen registry, composition root,
global styles, `origin/main`, tags and deployment are untouched.
