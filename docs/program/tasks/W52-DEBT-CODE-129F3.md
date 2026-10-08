# Task W52-DEBT-CODE-129F3 — keep derived name labels within the frozen API bound

task_id: W52-DEBT-CODE-129F3

## Outcome

Every name accepted by the access boundary produces a `name_label` no longer than the
frozen `RegistrationRequest.display_label` maximum of 66 characters, including an
initial whose Unicode upper-case mapping expands into two code points.

## Depends on

- `W52-INT-128F10-01` — published at
  `2f82396d60ca32630584471292d36317c9d226bf`.

## Frozen inputs

- Exact base `2f82396d60ca32630584471292d36317c9d226bf`; domain revision 9 / 29
  identities, API 27 paths / 34 operations / 77 schemas, error catalog 23, migration
  head `0015_accounts_roles_registration`.
- D-129 Y F-3 in `reviews/W49-JUDGE-Y.md`; the existing API bound stays 66. No W52
  freeze or contract reseal is claimed.
- Owner direction 2026-10-08: proceed without approval; only basic tests and lint;
  QA, stand and full gate remain D-139/D-140.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `name_label` upper-cases the entire first code point, which may expand.

### P-01 — exact base and code/test locations

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; rg -n '^def name_label|^MAX_NAME_LABEL_LENGTH|class TestTheLabel|test_the_longest_label' src/auditmanager/access/models.py tests/integration/access/test_account_names.py`
- captured_output:
  ```text
  2f82396d60ca32630584471292d36317c9d226bf
  src/auditmanager/access/models.py:148:MAX_NAME_LABEL_LENGTH: Final[int] = MAX_PERSON_NAME_LENGTH + 6
  src/auditmanager/access/models.py:356:def name_label(last_name: str, first_name: str, middle_name: str | None) -> str:
  tests/integration/access/test_account_names.py:148:class TestTheLabel:
  tests/integration/access/test_account_names.py:153:    def test_the_longest_label_is_66_and_inside_author_label(self) -> None:
  ```
- interpretation: the existing longest-label test uses simple Cyrillic initials and
  misses the judge's three accepted expanding Latin initials.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/access/models.py`
- `tests/integration/access/test_account_names.py`
- `docs/program/W52-DEBT-CODE-129F3.md`

## Forbidden hotspots

Every other path, especially contracts, migration head, dependency/lock files,
routers, composition root, global styles and unrelated D-129 findings.

## Non-goals

No change to accepted name characters, API `maxLength`, database column, W52 freeze,
QA, stand, full gate, release, tag or `origin/main` publication.

## Deliverables

- A one-code-point initial for every accepted first/middle name: an uppercase letter
  where its mapping provides one, including `ß`, `ŉ` and `ǰ`; an uncased glyph keeps
  its existing form.
- Focused tests holding the 66-character bound and sensible initials for all three.

## Required tests

- `pytest -q tests/integration/access/test_account_names.py -k TestTheLabel` with the
  pinned venv; Python compilation, frontend lint and `git diff --check`.

## Integration contract

Hand back a clean branch from the exact dispatch SHA with only allowed paths. The
integrator may publish this narrow code correction to `origin/dev` after exact
remote-ref and fast-forward verification. No contract reseal is needed.

## Failure/idempotency/security cases

`ŉ` must not become the modifier apostrophe as an initial. The output must remain a
capital letter for ordinary and expanding mappings. Identical inputs give identical
labels; no input value or role decision changes.

## Rollback / feature flag

Revert the code commit. No runtime feature flag.

## Handoff

- changed files, commands/results, contracts, risks, integration notes, forbidden-hotspot proof.
