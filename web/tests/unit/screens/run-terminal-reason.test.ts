/**
 * The sentence a failed run renders, measured on the rendered markup.
 *
 * `W28-LIVE` read this screen in a cold browser and wrote down what it said. The outcome
 * block printed `Terminal reason: dependency_unavailable` and no sentence, while every
 * neighbouring line — the cost paragraph, the review panel — was prose. These tests hold
 * the repair at the place a person meets it: the HTML, not the selector.
 *
 * **Each catalog code is asserted by its own case.** `it.each` over the whole catalog
 * means replacing the sentence table with one constant reddens twenty-two named tests,
 * not one, and replacing a single sentence reddens exactly the case that names its code.
 * `W12-WEB`'s U-01 is the precedent: `terminal_reason` reached a user in one line of this
 * application and that line could be made to print `redacted` with 498 tests green.
 *
 * The assertions are on the visible text between the tags, not only on the data
 * attribute, for the same reason U-01 gives: an attribute survives a mutation that empties
 * the text.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ErrorCode, RunStatus } from '@/shared/api';
import { ERROR_CODE_VALUES, queryKeys } from '@/shared/api';
import { ABSENT_SENTENCE, UNDESCRIBED_PREFIX, terminalReasonNote } from '@/entities/audit-run';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from './harness';

function screen(overrides: Partial<RunStatus> = {}): string {
  const status = runStatus(overrides);
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  return renderWith(
    client,
    createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }),
  );
}

function failedWith(reason: ErrorCode | null): string {
  return screen({ state: 'failed', terminal_reason: reason, published_finding_count: 0 });
}

/**
 * What each code must be seen to say, stated here as a literal and never read back out of
 * the module under test.
 *
 * The first draft of this file asserted `markup).toContain(terminalReasonNote(code).sentence)`,
 * which is a re-capture and not an assertion: replacing all twenty-two sentences with one
 * constant left every case green, because the expectation moved with the implementation.
 * `MEMORY: characterization can freeze a defect` is the same shape. Each phrase below is
 * chosen to be specific to its own code, so one constant reddens twenty-two named cases.
 */
const MUST_SAY: Readonly<Record<ErrorCode, string>> = {
  validation_failed: 'Нарушены объявленная схема, перечисление, формат или инвариант',
  not_found: 'не существует либо не видно вызывающей стороне',
  authentication_required: 'не был предъявлен действительный аутентифицированный',
  permission_denied: 'не разрешено действие, которое требовалось прогону',
  conflict: 'проиграла проверку оптимистичной блокировки',
  state_transition_not_allowed: 'зафиксированная машина состояний из его состояния',
  idempotency_key_reuse: 'повторно использован с другим телом запроса',
  idempotency_key_in_progress: 'тем же ключом и тем же телом ещё выполнялась',
  idempotency_key_stale: 'больше не удалось установить',
  unsupported_contract_version: 'неизвестна этому развёртыванию',
  storage_integrity_error: 'не совпали с сохранёнными или переданными байтами',
  dependency_unavailable: 'Зависимость, нужная прогону, была недоступна.',
  dependency_credential_refused: 'отвергла учётные данные этого развёртывания',
  staged_upload_lost: 'больше не содержало байты, подготовленные загрузкой',
  required_norm_unavailable: 'не удалось разрешить в неизменяемую',
  analysis_input_invalid: 'объявленный вход этапа оказались неприемлемыми',
  analysis_failed: 'завершился в терминальном состоянии отказа',
  partial_result_not_publishable: 'запросили то, что требует прогона без неё',
  cost_budget_exceeded: 'бюджет стоимости или токенов для этого прогона исчерпан',
  stale_attempt: 'больше не является для неё публикующей инстанцией',
  execution_token_invalid: 'отсутствовал, был искажён или не был',
  internal_error: 'неклассифицированная серверная неисправность',
};

describe('every catalog reason reaches the screen as a sentence', () => {
  it.each(ERROR_CODE_VALUES)('renders a sentence for %s, beside the code', (code) => {
    const markup = failedWith(code);

    // The code is kept: an operator quoting it into an issue still can.
    expect(markup).toContain(`data-terminal-reason="${code}"`);
    expect(markup).toContain(`>${code}</code>`);

    // And the sentence is beside it, as text, in the failed outcome block.
    expect(markup).toContain('data-terminal-reason-note="described"');
    expect(markup, `the screen did not say what ${code} means`).toContain(MUST_SAY[code]);
  });

  it('gives each code a phrase no other code renders', () => {
    // Otherwise a mutation that pointed two codes at one sentence could still pass the
    // per-code cases above.
    for (const [code, phrase] of Object.entries(MUST_SAY)) {
      const others = ERROR_CODE_VALUES.filter(
        (other) => other !== code && failedWith(other).includes(phrase),
      );
      expect(others, `${code}'s phrase also appears for ${others.join(', ')}`).toEqual([]);
    }
  });

  it('renders one sentence and not a list of all of them', () => {
    const markup = failedWith('analysis_failed');
    const others = ERROR_CODE_VALUES.filter((code) => code !== 'analysis_failed')
      .map((code) => terminalReasonNote(code))
      .filter((note) => note.kind === 'described')
      .filter((note) => markup.includes(note.sentence));
    expect(others, 'the screen printed a sentence for a code the run did not record').toEqual([]);
  });
});

describe('the reason a person actually meets', () => {
  /**
   * `W28-LIVE`, `recorded` mode, a document with no recording: `failed`,
   * `dependency_unavailable`, three runs of three. The provider was healthy. What the
   * screen may say is bounded by what the reading carries, and the reading carries the
   * code alone — `RunStatus` has no `details`.
   */
  it('names the class the catalog groups, and says it does not know which member', () => {
    const markup = failedWith('dependency_unavailable');
    expect(markup).toContain('Зависимость, нужная прогону, была недоступна.');
    expect(markup).toContain('не фиксирует, о какой из них шла речь');
  });

  it('does not tell the reader the provider is down', () => {
    const markup = failedWith('dependency_unavailable');
    expect(markup).not.toContain('Провайдер, нужный этому прогону, недоступен.');
    expect(markup.toLowerCase()).not.toContain('the provider is down');
  });

  it('keeps the cost paragraph and the review panel it already got right', () => {
    // A repair that broke a neighbouring true sentence would be a net loss. Both of these
    // are `W28-LIVE`'s verbatim readings.
    const markup = failedWith('dependency_unavailable');
    expect(markup).toContain('Прогон не обращался к провайдеру, поэтому сообщать о стоимости нечего.');
    expect(markup).toContain('Разбирать нечего.');
  });
});

describe('a reason nobody anticipated still says something true on screen', () => {
  /**
   * The generated client casts the response body rather than validating it, so a
   * deployment one reseal ahead of this client can put a string here that `ErrorCode` says
   * cannot exist. `W15-AUTH` found five classifiers collapsing into `server_error` for
   * want of a branch; this is the branch.
   */
  const ROGUE = 'recording_not_found_for_this_document' as ErrorCode;

  it('prints the code it received and says it has no description for it', () => {
    const markup = failedWith(ROGUE);
    expect(markup).toContain(`data-terminal-reason="${ROGUE}"`);
    expect(markup).toContain('data-terminal-reason-note="undescribed"');
    expect(markup).toContain(UNDESCRIBED_PREFIX);
    expect(markup).toContain('описания для него у этого клиента нет');
  });

  it('does not borrow the sentence of a code it does know', () => {
    const markup = failedWith(ROGUE);
    for (const code of ERROR_CODE_VALUES) {
      const note = terminalReasonNote(code);
      if (note.kind !== 'described') continue;
      expect(markup, `the undescribed reason rendered the ${code} sentence`).not.toContain(
        note.sentence,
      );
    }
  });
});

describe('a failed reading that carries no reason at all', () => {
  it('keeps "не сообщено" and adds what the contract obliges', () => {
    const markup = failedWith(null);
    expect(markup).toContain('не сообщено');
    expect(markup).toContain('data-terminal-reason-note="absent"');
    expect(markup).toContain(ABSENT_SENTENCE);
  });
});

describe('the sentence belongs to the failed outcome and to no other', () => {
  it.each(['published', 'partial', 'cancelled'] as const)('renders no note on a %s run', (state) => {
    const markup = screen({
      state,
      ...(state === 'partial' ? { degradation_set: ['text_analysis' as const] } : {}),
    });
    expect(markup).not.toContain('data-terminal-reason-note');
  });
});
