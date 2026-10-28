# Task ACCESS-COMPARE-JUDGE-FIXES-01 — the findings of the independent judge J4 on the access and comparison lanes

task_id: ACCESS-COMPARE-JUDGE-FIXES-01
status: fix lane C; branch `agent/access-compare-judge-fixes-01`, base `93bc5037` (tip of `integration/ar-close-1026`)

## Outcome

Seven findings of an independent read-only judge (J4) at `93bc5037` are fixed, each with a test written first and a mutation that turns it red, and an eighth is listed as latent:

1. a replayed `generateComparisonSummary` says `is_current` from the sealed evidence recomputed now (revision and seal), not always `true`;
2. the registration day cap counts `pending` and `approved` requests only, so an administrator who rejects spam frees places; the screen text for `queue_full` is true of a spent day;
3. the run CSV looks past blanks and invisible characters, knows the fullwidth triggers and treats a line feed like a tab or a carriage return;
4. the preset create, revise and archive keys belong to the administrator who spent them;
5. a pair whose own sheet is unchanged says why its differences are hidden when another approved sheet changed;
6. `release-notes/0.9.0.json` item 3 (revision 3) quotes the profile versions that exist; a contract test reads every `profile.json`;
7. the manual acceptance step for «Настройки анализа» expects the neutral label while the review switch is off.

## Depends on

- `SMALL-HARDENING-02`, `ANALYSIS-PRESETS-01`, `COMPARE-PERSISTED-SUMMARY-01`, `REVIEW-INDICATION-SWITCH-01`, `RELEASE-0-9-0-DEV-01` — completed; the judge's findings are about their results.

## Frozen inputs

- domain contract: unchanged (`contracts/**` is not touched; another integrator holds it)
- API contract: unchanged (`web/openapi/**` and the generated client are not touched; no operation or field added)
- analysis/comparison/event contract: unchanged; `SummaryOutcome` is an internal value of the comparison context, not a contract shape
- migration head: `0037_analysis_presets`, unchanged (no migration)
- base commit: `93bc5037`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: every file, line and number the brief names was re-read at the base commit and matches it; the output is below

### P-01 — the replay branch of generate returns the stored row before the evidence is recomputed, and the adapter writes is_current=True for every outcome
- captured_at: 2026-10-28
- command: `git show 93bc5037:src/auditmanager/comparison/summaries.py | grep -n 'CommandReplay)\|def _replayed\|SummaryOutcome(' ; git show 93bc5037:src/auditmanager/bootstrap/adapters.py | grep -n 'is_current=True'`
- captured_output:
  ```text
  280:        if isinstance(claimed, CommandReplay):
  281:            return SummaryOutcome(self._replayed(session, claimed.outcome), True)
  315:            return SummaryOutcome(existing, True)
  368:        return SummaryOutcome(stored, False)
  370:    def _replayed(self, session: Session, outcome: object) -> StoredSummary:
  3392:            summary=_summary_view(outcome.summary, is_current=True), replayed=outcome.replayed,
  ```
- interpretation: At the base the replay branch (line 280-281) returns `SummaryOutcome(self._replayed(...), True)` before `sealed_evidence` is called, and the adapter (line 3392) passes `is_current=True` unconditionally. The finding is as the judge wrote it.

### P-02 — the served read decides is_current from the sealed evidence, revision and seal
- captured_at: 2026-10-28
- command: `grep -n 'approved.evidence_state == EVIDENCE_SEALED' -B1 -A3 src/auditmanager/comparison/service.py`
- captured_output:
  ```text
  401-                    stored.input_sha256, stored.raw_evidence_seal_sha256, stored.cost_basis,
  402:                    approved.evidence_state == EVIDENCE_SEALED
  403-                    and stored.link_revision == approved.link_revision
  404-                    and stored.raw_evidence_seal_sha256 == approved.raw_evidence_seal_sha256,
  405-                    stored.actor_label, stored.created_at,
  ```
- interpretation: The read path (`VersionComparisonService.compare`) says a stored summary is current only when the set is sealed and the stored revision and seal equal the recomputed ones. The replay now applies the same rule to `sealed_evidence` (a seal exists exactly when the set is sealed).

### P-03 — the registration day cap counts every state, and the browser text for queue_full names only a full queue
- captured_at: 2026-10-28
- command: `git show 93bc5037:src/auditmanager/access/registrations.py | grep -n '_COUNT_ACCEPTED_IN_WINDOW = ' -A4 ; git show 93bc5037:web/src/features/register/model/exchange.ts | grep -n "case 'queue_full'" ; sed -n 296,301p db/migrations/versions/20261005_0015_accounts_roles_registration.py`
- captured_output:
  ```text
  220:_COUNT_ACCEPTED_IN_WINDOW = text(
  221-    "SELECT count(*) FROM registration_request "
  222-    "WHERE submitted_at > now() - (:window_hours * interval '1 hour')"
  223-)
  224-
  26:    case 'queue_full': return 'Очередь заявок заполнена. Попробуйте позже.';
                  CHECK (password_salt IS NULL OR password_salt ~ '^[0-9a-f]{{32}}$'),
              CONSTRAINT ck_registration_request_password_hash_format
                  CHECK (password_hash IS NULL OR password_hash ~ '^[0-9a-f]{{64}}$'),
              CONSTRAINT ck_registration_request_status
                  CHECK (status IN ('pending', 'approved', 'rejected')),
              CONSTRAINT ck_registration_request_decided_by_format
  ```
- interpretation: The count at the base has no `status` condition, so a rejected request keeps its place for 24 hours and an administrator has no lever. The statuses are the three of the CHECK (`pending`, `approved`, `rejected`). The screen text at line 26 says only «Очередь заявок заполнена».

### P-04 — the run CSV rule looks at the first character only, the proposals CSV looks past spaces and treats a line feed as a trigger
- captured_at: 2026-10-28
- command: `git show 93bc5037:src/auditmanager/exports/serializer.py | grep -n 'FORMULA_TRIGGERS: Final\|text\[0\] in FORMULA_TRIGGERS' ; git show 93bc5037:src/auditmanager/optimisation/proposals/export.py | grep -n 'FORMULA_TRIGGERS: Final\|stripped = \|stripped\[:1\]'`
- captured_output:
  ```text
  95:FORMULA_TRIGGERS: Final[frozenset[str]] = frozenset({"=", "+", "-", "@", "\t", "\r"})
  107:    if text and text[0] in FORMULA_TRIGGERS:
  93:FORMULA_TRIGGERS: Final[frozenset[str]] = frozenset({"=", "+", "-", "@", "\t", "\r", "\n"})
  109:    stripped = text.lstrip(" ")
  110:    if text and (text[0] in FORMULA_TRIGGERS or stripped[:1] in FORMULA_TRIGGERS):
  ```
- interpretation: As the judge wrote: `' =1+1'`, `'\n=1+1'`, a no-break space, a byte-order mark, a zero-width character or a fullwidth sign before the trigger all pass the run CSV unchanged.

### P-05 — architecture: a context may import from shared without restriction
- captured_at: 2026-10-28
- command: `grep -n '_EXEMPT_IMPORTERS\|_EXEMPT_TARGETS' tests/contract/architecture/test_alr05_boundaries.py | head -4 ; ls src/auditmanager/shared`
- captured_output:
  ```text
  16:_EXEMPT_IMPORTERS = frozenset({"bootstrap", "shared"})
  17:_EXEMPT_TARGETS = frozenset({"shared"})
  90:        if importer in _EXEMPT_IMPORTERS:
  118:                if target_context in _EXEMPT_TARGETS or target_context == importer:
  db
  errors
  identity
  README.md
  spreadsheet
  statemachine
  ```
- interpretation: `shared` is an exempt target of the context-boundary test, so a small subpackage there can be imported by `exports` without a deep import across bounded contexts. Its existing subpackages (`db`, `errors`, `identity`, `statemachine`) each have an `__init__.py`.

### P-06 — preset commands fingerprint the payload without the actor, the comparison commands with it
- captured_at: 2026-10-28
- command: `git show 93bc5037:src/auditmanager/executors/preset_commands.py | grep -n 'fingerprint=payload_fingerprint(payload)\|_begin(session' ; git show 93bc5037:src/auditmanager/comparison/pairing.py | grep -n '"actor_uid": actor_uid' ; git show 93bc5037:src/auditmanager/comparison/summaries.py | grep -n '"actor_uid": actor_uid'`
- captured_output:
  ```text
  74:        fingerprint=payload_fingerprint(payload),
  131:    claimed = _begin(session, ledger, _CREATE, idempotency_key,
  167:    claimed = _begin(session, ledger, _REVISE, idempotency_key, {
  207:    claimed = _begin(session, ledger, _ARCHIVE, idempotency_key, {"preset_id": preset_id})
  288:                "actor_uid": actor_uid,
  436:                "actor_uid": actor_uid,
  277:                "actor_uid": actor_uid,
  ```
- interpretation: The three preset commands pass a payload with no `actor_uid`; the approve and withdraw commands (pairing.py 288, 436) and the summary command (summaries.py) include it. `startRun` has the same gap and is reported only.

### P-07 — the web seam: a pair with no diff renders nothing, and the evidence state text is section-wide
- captured_at: 2026-10-28
- command: `git show 93bc5037:web/src/widgets/version-comparison/ui/version-comparison.tsx | grep -n 'if (item.diff === null) return null' ; grep -n 'text_changed' web/src/entities/version-comparison/model/pairing.ts`
- captured_output:
  ```text
  414:  if (item.diff === null) return null;
  35:  text_changed:
  47:  text_changed: 'Текст листа изменился после подтверждения.',
  84:  | 'approved_text_changed'
  93:  'approved_text_changed',
  110:  approved_text_changed:
  ```
- interpretation: `ApprovedPairDiff` returns null for a withheld diff, so a pair whose own sheet is unchanged shows only the section-wide text. The entity file (`pairing.ts`) is outside the allowed paths; the line is added in the widget.

### P-08 — the profile versions that exist, and what the note says
- captured_at: 2026-10-28
- command: `grep -H '"profile_version"' src/auditmanager/analysis/text/profiles/*/profile.json ; git show 93bc5037:release-notes/0.9.0.json | grep -n '1.1.0 или 1.2.0\|"revision"'`
- captured_output:
  ```text
  src/auditmanager/analysis/text/profiles/ai/profile.json:  "profile_version": "1.3.0",
  src/auditmanager/analysis/text/profiles/eom/profile.json:  "profile_version": "1.3.0",
  src/auditmanager/analysis/text/profiles/gp/profile.json:  "profile_version": "1.2.0",
  src/auditmanager/analysis/text/profiles/itp/profile.json:  "profile_version": "1.3.0",
  src/auditmanager/analysis/text/profiles/kj/profile.json:  "profile_version": "1.2.0",
  src/auditmanager/analysis/text/profiles/km/profile.json:  "profile_version": "1.2.0",
  src/auditmanager/analysis/text/profiles/ov/profile.json:  "profile_version": "1.2.0",
  src/auditmanager/analysis/text/profiles/pb/profile.json:  "profile_version": "1.1.0",
  src/auditmanager/analysis/text/profiles/pos/profile.json:  "profile_version": "1.2.0",
  src/auditmanager/analysis/text/profiles/ps/profile.json:  "profile_version": "1.2.0",
  src/auditmanager/analysis/text/profiles/pt/profile.json:  "profile_version": "1.2.0",
  src/auditmanager/analysis/text/profiles/ss/profile.json:  "profile_version": "1.3.0",
  src/auditmanager/analysis/text/profiles/tx/profile.json:  "profile_version": "1.3.0",
  src/auditmanager/analysis/text/profiles/vk/profile.json:  "profile_version": "1.2.0",
  3:  "revision": 2,
  23:      "text": "У профилей анализа 14 разделов, кроме АР, версия 1.1.0 или 1.2.0 и состояние «проверен» вместо «черновик, требует экспертной проверки». Для 12 разделов добавлены сверки внутри документа, например итога таблицы с суммой строк: о расхождении модель просят сообщить в категории «Внутреннее противоречие» с цитатами. Ни человек, ни реальные документы эти инструкции для модели не проверяли."
  ```
- interpretation: Five profiles (`ai`, `eom`, `itp`, `ss`, `tx`) are at `1.3.0`, `pb` at `1.1.0`, the other eight at `1.2.0`; the note at the base quotes «1.1.0 или 1.2.0» and is at revision 2.

### P-09 — the manual acceptance step expects the removed label
- captured_at: 2026-10-28
- command: `git show 93bc5037:docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md | grep -n 'рабочая версия, проверка человеком не проводилась' ; grep -n 'SHOW_REVIEW_INDICATION = ' web/src/shared/config/review-indication.ts`
- captured_output:
  ```text
  308:    «рабочая версия, проверка человеком не проводилась» (reviewed without a human review,
  23:export const SHOW_REVIEW_INDICATION = false as boolean;
  ```
- interpretation: Step 21 expects the label that the switch (default `false`) no longer draws.

### P-10 — finding 8, latent: where the three behaviours sit
- captured_at: 2026-10-28
- command: `grep -n 'один запрос к модели' web/src/entities/version-comparison/ui/comparison-summary.tsx ; grep -n "state = 'ready'\|reply = self._model.complete\|if not self._model.unmetered" src/auditmanager/comparison/summaries.py`
- captured_output:
  ```text
  100:            Будет сделан один запрос к модели по изменившимся строкам подтверждённых пар. Сводка не
  144:    "AND prompt_version = :prompt_version AND state = 'ready'"
  336:        reply = self._model.complete(prompt)
  337:        if not self._model.unmetered:
  ```
- interpretation: The offer text is unconditional; `ready_for` looks only for a `ready` row, so a `rejected` row is paid for again under a new key; `complete` is called before `unmetered` is checked. All three are inert while the only model is the recorded one (cost zero, no network).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/**`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/access/registrations.py`
- `src/auditmanager/exports/**`
- `src/auditmanager/optimisation/proposals/export.py`
- `src/auditmanager/shared/spreadsheet/**`
- `src/auditmanager/executors/preset_commands.py`
- `web/src/widgets/version-comparison/**`
- `web/src/features/register/model/exchange.ts`
- `web/tests/unit/comparison/sheet-pairing.test.ts`
- `web/tests/unit/session/registration-queue-text.test.ts`
- `release-notes/0.9.0.json`
- `tests/contract/release_notes/**`
- `tests/unit/comparison/**`
- `tests/unit/exports/**`
- `tests/integration/comparison/test_comparison_summary_db.py`
- `tests/integration/access/test_registration_day_cap.py`
- `tests/integration/api/qa_w49/test_qa_w49_queue_cap.py`
- `tests/integration/executors/test_preset_commands.py`
- `docs/program/RELEASES.md`
- `docs/program/RELEASE-0-9-0-DEV-01.md`
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md`
- `docs/program/ACCESS-COMPARE-JUDGE-FIXES-01.md`
- `docs/program/tasks/ACCESS-COMPARE-JUDGE-FIXES-01.md`

## Forbidden hotspots

- `contracts/**`, `web/openapi/**`, the generated client
- `db/migrations/**`, root dependency and lock files
- `infra/**`, `runs/**`, `analysis/**`, the section packages
- composition roots, global styles, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals

- the optimisation (proposals) CSV keeps its own rule: adopting the new one would change its bytes (a table of the differences is pinned by a test); this is reported as a follow-up
- `startRun` has the same actor-less key gap as the presets had: reported, not changed
- finding 8 (the offer text in recorded mode, a `rejected` reply paid again under a new key, a model with `unmetered` false called before it is refused) is latent while the only model is the recorded one: listed, not changed
- the sentence «Ни человек, ни реальные документы эти инструкции для модели не проверяли» in the release note (an owner decision about it, `A-10`, is pending)
- the contract prose that still describes the old day cap and the apostrophe rule (the contract slot's)

## Deliverables

- the fixes, tests and mutations listed in `docs/program/ACCESS-COMPARE-JUDGE-FIXES-01.md`
- the report `docs/program/ACCESS-COMPARE-JUDGE-FIXES-01.md`

## Required tests

- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/exports tests/unit/access tests/unit/comparison tests/unit/executors tests/unit/api tests/contract tests/integration/access tests/integration/comparison tests/integration/exports tests/integration/api` with the stack variables of the lane and a private database
- expected: every test passes (the counts and the three excluded contract files are in the report); web `npx vitest run`, `tsc --noEmit`, `eslint .` clean; `git diff --check` clean

## Integration contract

- `SummaryOutcome` has a third field, `is_current`; the `generateComparisonSummary` response carries it in `summary.is_current` (the field already existed in the contract)
- a rejected registration request no longer counts towards the 40 a day; `409 conflict / queue_full` is unchanged in shape
- `auditmanager.shared.spreadsheet.neutralise_formula` is the rule of the run CSV; a follow-up may adopt it in the proposals CSV
- an idempotency key of `createAnalysisPreset`, `reviseAnalysisPreset` and `archiveAnalysisPreset` is bound to the administrator who spent it; another administrator gets `idempotency_key_reuse`

## Failure/idempotency/security cases

- a retry with an old key after the pair was withdrawn, after another pair was approved, after withdraw and approve again, and after a sheet was redrawn: the old row, `replayed: true`, `is_current: false`
- a day of forty rejected requests is an open door; an approved request still counts
- a formula behind a no-break space, a byte-order mark, a zero-width character, a line feed or in fullwidth form is neutralised; the cell `a=b`, a cell of blanks and a cell with an apostrophe first keep their bytes
- a second administrator reusing a key with the same payload gets no result of the first

## Rollback / feature flag

Not applicable as a flag. Each finding is its own commit and a single-commit revert: the summary flag (`89a99f82`), the day cap and text (`d189e90d`), the CSV rule (`98967a8f`), the preset keys (`e73a15fb`), the web line (`7a81aed1`), the release note (`84cd7c4f`), the manual step (`56df8f5e`).

## Handoff

- changed files: see `docs/program/ACCESS-COMPARE-JUDGE-FIXES-01.md`
- commands/results: see the same report
- known limits: see the same report
- integration notes: see the same report
