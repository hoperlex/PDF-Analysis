# Task W52-INT-WEB-GRANT-01 — grant the account-menu action seam

task_id: W52-INT-WEB-GRANT-01

## Outcome

WEB can open its release-history side panel from the existing account menu
through a keyboard-accessible action item, with the directly affected
menu tests in scope.

## Depends on

- `W52-INT-C-API-01`, published on `origin/dev` at
  `fa3975a32473d69bec1eb9bdba27cef21a6c29e4`.

## Frozen inputs

- Development base `fa3975a32473d69bec1eb9bdba27cef21a6c29e4`;
  W52 API 30 paths / 37 operations / 83 schemas, 23 errors, domain
  revision 9 / 29 identities, migration head `0016_release_notes`,
  `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` §3.5 and Stage C; D-137–D-140 retain
  deferred release evidence.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: no API or screen-registry member changes

## Captured premise evidence

- premise: the account-menu primitive cannot presently express a client
  action, and four existing tests pin its three-item shape.

### P-01 — menu variant and affected assertions

- captured_at: 2026-10-08
- command: `rg -n "kind: 'link'|kind: 'submit'|\['link', 'link', 'submit'\]|ITEMS = 3|the account menu’s items" web/src/shared/ui/menu.tsx web/tests/unit/ui/menu.test.ts web/tests/unit/shell/frame.test.ts web/tests/unit/qa_w50/r66-navigation.test.ts web/tests/unit/qa_w50/primitives-keyboard.test.ts`
- captured_output:
  ```text
  web/tests/unit/qa_w50/primitives-keyboard.test.ts:41:const ITEMS = 3;
  web/tests/unit/qa_w50/primitives-keyboard.test.ts:183:        { kind: 'link', label: 'Профиль', href: '/account' },
  web/tests/unit/qa_w50/primitives-keyboard.test.ts:184:        { kind: 'link', label: 'Сменить пароль', href: '/account/password' },
  web/tests/unit/qa_w50/primitives-keyboard.test.ts:185:        { kind: 'submit', label: 'Выйти', action: '/bff/v1/session/end' },
  web/tests/unit/shell/frame.test.ts:118:    expect(accountMenuProps(EXPERT).items.map((item) => item.kind)).toEqual(['link', 'link', 'submit']);
  web/tests/unit/qa_w50/r66-navigation.test.ts:318:  it('the account menu’s items: Профиль, Сменить пароль, and Выйти as a POST', () => {
  web/src/shared/ui/menu.tsx:40:  | { readonly kind: 'link'; readonly label: string; readonly href: string }
  web/src/shared/ui/menu.tsx:42:  | { readonly kind: 'submit'; readonly label: string; readonly action: string };
  web/tests/unit/ui/menu.test.ts:23:  { kind: 'link', label: 'Профиль', href: '/account' },
  web/tests/unit/ui/menu.test.ts:24:  { kind: 'link', label: 'Сменить пароль', href: '/account/password' },
  web/tests/unit/ui/menu.test.ts:25:  { kind: 'submit', label: 'Выйти', action: '/bff/v1/session/end' },
  ```
- interpretation: a history action cannot be represented without changing
  the shared menu primitive or using a false navigation link. Only the
  action variant and directly affected assertions are granted.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-WEB-GRANT-01.md`,
  `docs/program/tasks/W52-RELEASES-WEB.md`,
  `docs/program/W52-INT-WEB-GRANT-01.md` — this narrow grant only
- `docs/program/dispatch/W52-PLAN.md` — Stage-C ownership row only
- clean `integration/w51` ref and `origin/dev` fast-forward

## Forbidden hotspots

Every product, contract, migration, test, dependency, lock, generated
client, composition-root and global-style path in this docs-only task;
`origin/main`, tags and deployment. The downstream WEB task alone owns
the newly granted menu and test edits.

## Non-goals

No WEB implementation, contract reseal, gate, QA, release verdict,
tag or deployment.

## Deliverables

- A current-tree grant naming the one shared primitive and four directly
  affected test files; reviewed ownership row and docs-only publication.

## Required checks

- Focused governance/prose tests, `git diff --check`, changed-path audit,
  fresh `origin/dev` read and fast-forward readback.
- Full `make gate` remains D-140.

## Integration contract

WEB begins on the new read-back `origin/dev` SHA. The action item is local
client behavior; it does not create a route or modify the menu's submit
semantics. WEB hands a clean candidate back before Stage-C integration.

## Failure / idempotency / security

If the menu action needs another shared path, stop and grant it explicitly.
The existing sign-out POST stays a form. No credential crosses to the
browser through this action.

## Rollback / feature flag

Revert the docs-only grant with a new reviewed dev commit if wrong.
No behavior flag or deployment.

## Handoff

Return changed files, checks, contracts, risks, integrator steps and
forbidden-hotspot proof. No checkpoint or tag.
