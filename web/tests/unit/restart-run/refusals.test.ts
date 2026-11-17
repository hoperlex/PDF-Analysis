/**
 * `RUN-RESTART-01`: a refused restart reads as one plain sentence. The vocabulary is held to the contract's own text in both directions
 * (a reason the server can give that the screen cannot say reddens here), and each sentence names its chip by the short name.
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { ApiError } from '@/shared/api';
import {
  RESTART_CONFLICT_REASONS, RESTART_REFUSAL_REASONS, RestartSourceChanged, restartFailureText, restartReasonSentence, restartRefusal,
} from '@/features/restart-run';

const refusal = (status: number, code: string, details: Record<string, string>) => new ApiError(status, {
  contract_version: '1.59.0', error_code: code as never, message: 'x', correlation_id: 'c', retryable: false, details,
}, 'c');
const invalid = (details: Record<string, string>) => refusal(422, 'analysis_input_invalid', details);

describe('the typed refusals of restartRun', () => {
  it('say a published run is repeated, not restarted, and a run that has not ended is stopped first', () => {
    const transition = (current_state: string) => refusal(409, 'state_transition_not_allowed',
      { machine: 'audit_run', current_state, requested_state: 'restart' });
    expect(restartRefusal(transition('published'))).toBe('Опубликованный прогон не перезапускается: его можно повторить целиком.');
    expect(restartRefusal(transition('running'))).toBe('Прогон ещё не завершился. Сначала остановите его.');
    expect(restartRefusal(transition('failed'))).toBe('Прогон в этом состоянии перезапустить нельзя.');
    // Another command's transition refusal keeps its usual wording.
    expect(restartRefusal(refusal(409, 'state_transition_not_allowed', { requested_state: 'cancel', current_state: 'failed' }))).toBeNull();
  });

  it('say each conflict', () => {
    const conflict = (conflict_reason: string) => restartRefusal(refusal(409, 'conflict', { conflict_reason }));
    expect(conflict('restart_source_deleted')).toBe('Этот прогон уже удалён, перезапустить его нельзя.');
    expect(conflict('restart_source_leased')).toContain('ещё не остановился');
    expect(conflict('restart_in_progress')).toContain('Перезапуск этого прогона уже идёт');
    expect(conflict('run_cost_estimate_stale')).toBeNull();
  });

  it('name the chip of a reply that is missing, by its short name', () => {
    const text = restartRefusal(invalid({ reason: 'restart_reply_missing', restart_point: 'blocks', stage_id: 'block_analysis' }));
    expect(text).toContain('этапа «Блоки»');
    expect(text).toContain('Перезапустите с «Блоки».');
    // A refusal that names only the stage id is mapped to its chip.
    expect(restartRefusal(invalid({ reason: 'restart_reply_missing', stage_id: 'finding_review' }))).toContain('этапа «Критик»');
    expect(restartRefusal(invalid({ reason: 'restart_reply_missing' }))).toContain('Для этого этапа');
  });

  it('say a changed norms search as the advice to restart from the norms', () => {
    const text = restartRefusal(invalid({ reason: 'restart_request_changed', restart_point: 'norms', stage_id: 'norm_verification' }));
    expect(text).toContain('Поиск норм дал другой результат');
    expect(text).toContain('Перезапустите с «Норм».');
    expect(restartRefusal(invalid({ reason: 'restart_request_changed', restart_point: 'cross_check' }))).toContain('этапа «Сверка»');
  });

  it('say what to do for the reasons that no chip helps', () => {
    for (const reason of ['restart_source_not_stage_layout', 'restart_source_not_v2', 'restart_settings_differ']) {
      expect(restartRefusal(invalid({ reason })), reason).toContain('повторите прогон');
    }
    expect(restartRefusal(invalid({ reason: 'restart_text_not_reusable' }))).toContain('Перезапустите с «Текста».');
  });

  it('say the artifacts of the preparation, by the chip, and advise the preparation', () => {
    const text = restartRefusal(invalid({ reason: 'source_artifact_changed', stage_id: 'page_geometry_extraction' }));
    expect(text).toContain('этапа «Подготовка»');
    expect(text).toContain('не совпадает с записанным');
    expect(text).toContain('Перезапустите с «Подготовки».');
  });

  it('are nothing for any other failure, which keeps its usual wording', () => {
    expect(restartRefusal(new Error('x'))).toBeNull();
    expect(restartRefusal(refusal(409, 'conflict', { reason: 'restart_reply_missing' }))).toBeNull();
    expect(restartRefusal(invalid({ reason: 'something_else' }))).toBeNull();
    expect(restartRefusal(invalid({}))).toBeNull();
  });

  it('say a source that changed, and a failure that is not a refusal after «Перезапуск не выполнен:»', () => {
    expect(restartRefusal(new RestartSourceChanged('Состояние прогона изменилось.'))).toBe('Состояние прогона изменилось.');
    expect(restartFailureText(new TypeError('Failed to fetch'), true)).toMatch(/^Перезапуск не выполнен: Исход команды неизвестен/);
    expect(restartFailureText(invalid({ reason: 'restart_settings_differ' }), true)).not.toContain('Перезапуск не выполнен');
  });
});

describe('a restart that failed at the executor', () => {
  it('says the same sentence from the new run\'s terminal detail', () => {
    expect(restartReasonSentence({ reason: 'restart_request_changed', stage_id: 'norm_verification' })).toContain('Перезапустите с «Норм».');
    expect(restartReasonSentence({ stage_id: 'text_analysis' })).toBeNull();
    expect(restartReasonSentence({ reason: 7 })).toBeNull();
  });
});

describe('the vocabulary against the contract', () => {
  const contract = JSON.parse(readFileSync(resolve(__dirname, '../../../../contracts/api/v1/openapi.json'), 'utf-8'));
  const description: string = contract.paths['/runs/{run_id}/restart'].post.description;

  it('has a sentence for each restart reason the operation lists, and the operation lists each sentence', () => {
    const listed = [...description.matchAll(/`(restart_[a-z0-9_]+)`/g)].map((match) => match[1]!)
      .filter((word) => word !== 'restart_point');
    const conflicts = ['restart_source_deleted', 'restart_source_leased', 'restart_in_progress'];
    expect(listed.length).toBeGreaterThan(0);
    for (const word of conflicts) expect(listed).toContain(word);
    const reasons = RESTART_REFUSAL_REASONS.filter((reason) => reason.startsWith('restart_'));
    expect([...reasons, ...RESTART_CONFLICT_REASONS].sort()).toEqual([...new Set(listed)].sort());
  });

  it('has a sentence for each artifact reason of the start from a stage the restart can also give', () => {
    const start: string = contract.paths['/runs/{run_id}/start-from-stage'].post.description;
    const listed = [...start.matchAll(/`(source_[a-z_]+)`/g)].map((match) => match[1]!);
    expect(RESTART_REFUSAL_REASONS.filter((reason) => reason.startsWith('source_')).sort()).toEqual([...new Set(listed)].sort());
  });
});
