/**
 * `EXEC2-WEB-GROUPS-01` — the wording of the refusals (ADR-0026 decision 18). EXEC-2 adds no error
 * code: every refusal arrives as `validation_failed`, `conflict` or `dependency_unavailable` with a
 * typed safe detail, and each value the group, rule, routing-mode and start commands choose has a
 * Russian sentence of its own. Written under `R-149d` and not run in EXEC-2; none of it needs
 * PostgreSQL.
 *
 * Two surfaces say them: the commands of «Группы» and «Правила» (`groupFailure`) and the start of a
 * run (`classifyRunFailure`, rendered by `StartRunFailureView`). No sentence may carry a Latin word of
 * the stand’s English message or the identifier of the detail, and no refusal of a chosen group offers a
 * way round it.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { classifyRunFailure } from '@/entities/audit-run';
import { groupFailure, groupRefusalSentence } from '@/entities/executor-group';
import { StartRunFailureView } from '@/features/start-run';

import { PROJECT_UID, VERSION_UID, render } from '../review/fixtures';

function apiError(
  status: number,
  code: ErrorCode,
  details: Record<string, string | number | boolean | null>,
  retryable = false,
): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.37.0', error_code: code, message: 'A caller-safe English sentence.',
    correlation_id: 'cid-grp', retryable, details,
  };
  return new ApiError(status, envelope, 'cid-grp');
}

const invalid = (field: string, constraint: string) => apiError(422, 'validation_failed', { field, constraint });
const conflict = (reason: string) => apiError(409, 'conflict', { conflict_reason: reason });

describe('the commands of «Группы» and «Правила»', () => {
  const CASES: readonly [string, ApiError, string][] = [
    ['member_pin_mismatch', invalid('pin_id', 'member_pin_mismatch'), 'Модель: у одного из подключений закреплена другая модель'],
    ['member_model_mismatch', invalid('gateway_model', 'member_model_mismatch'), 'Имя модели на шлюзе: у одного из подключений другое имя модели'],
    ['member_billing_mismatch', invalid('billing', 'member_billing_mismatch'), 'Тарификация: у одного из подключений другая тарификация'],
    ['member_repeated', invalid('members', 'member_repeated'), 'Состав: одно подключение указано в составе дважды'],
    ['member_kind_not_served', invalid('members', 'member_kind_not_served'), 'Состав: подключение такого вида пока не обслуживается'],
    ['member_revision_not_of_connection', invalid('members', 'member_revision_not_of_connection'), 'версия настроек не принадлежит подключению'],
    ['unknown_executor_connection', invalid('members', 'unknown_executor_connection'), 'в составе есть подключение, которого на стенде нет'],
    ['members range', invalid('members', 'range'), 'Состав: в группе должно быть от 1 до 16 подключений'],
    ['model_not_pinned', invalid('pin_id', 'model_not_pinned'), 'эта модель не закреплена в замке провайдера'],
    ['group_archived', conflict('group_archived'), 'Группа в архиве'],
    ['group_name_in_use', conflict('group_name_in_use'), 'Группа с таким названием уже есть'],
    ['group_routed', conflict('group_routed'), 'Группу нельзя убрать в архив, пока правило направляет на неё работу'],
    ['routing_mode_rules', conflict('routing_mode_rules'), 'Включены правила: основное и резервное подключения не меняются'],
    ['routing_mode_unchanged', conflict('routing_mode_unchanged'), 'Режим уже такой'],
    ['preview_stale', conflict('preview_stale'), 'Предложение устарело'],
    ['connection_archived', conflict('connection_archived'), 'Подключение из состава в архиве'],
    ['preview_digest_required', invalid('preview_digest', 'preview_digest_required'), 'Предложение перехода: подтверждение должно нести сверку'],
    ['mapping_required', invalid('mapping', 'mapping_required'), 'не указано, какие виды работы переводятся'],
    ['mapping_entry_not_ready', invalid('mapping', 'mapping_entry_not_ready'), 'в соответствии есть вид работы, который перенести нельзя'],
    ['conflicts_with_executor_connection_id', invalid('executor_group_id', 'conflicts_with_executor_connection_id'), 'группу нельзя выбрать вместе с подключением'],
    ['conflicts_with_preset_id', invalid('executor_group_id', 'conflicts_with_preset_id'), 'группу нельзя выбрать вместе с пресетом'],
    ['environment_source', invalid('executor_group_id', 'environment_source'), 'источником «окружение»'],
    ['no_rule_for_work_kind', apiError(503, 'dependency_unavailable', { dependency: 'no_rule_for_work_kind' }, true), 'правила нет'],
  ];

  it('gives every named refusal its own Russian sentence', () => {
    for (const [name, error, expected] of CASES) {
      const sentence = groupRefusalSentence(error);
      expect(sentence, name).not.toBeNull();
      expect(sentence, name).toContain(expected);
      expect(groupFailure(error, true).detail, name).toContain(expected);
    }
    expect(new Set(CASES.map(([, error]) => groupRefusalSentence(error))).size).toBe(CASES.length);
  });

  it('prints no Latin word: neither the stand’s English message nor the identifier of the detail', () => {
    for (const [name, error] of CASES) {
      const failure = groupFailure(error, true);
      expect(failure.detail, name).not.toMatch(/[A-Za-z]/);
      expect(failure.detail, name).not.toContain('caller-safe');
    }
  });

  it('keeps the correlation id and calls a definite refusal a refusal, never an unknown outcome', () => {
    for (const [name, error] of CASES) {
      const failure = groupFailure(error, true);
      expect(failure.correlationId, name).toBe('cid-grp');
      expect(failure.kind, name).not.toBe('unknown_outcome');
    }
    // A 503 is an unknown outcome in general; a dependency the server names before it writes is not.
    expect(groupFailure(apiError(503, 'dependency_unavailable', { dependency: 'no_rule_for_work_kind' }, true), true).kind)
      .toBe('refusal');
  });

  it('keeps the shared sentence when the outcome is unknown, and does not explain what it cannot know', () => {
    const failure = groupFailure(apiError(500, 'internal_error', {}, true), true);
    expect(failure.kind).toBe('unknown_outcome');
    expect(failure.detail).toContain('Исход команды неизвестен');
    // A conflict that arrives as a server error is still an unknown outcome: nothing may be said about it.
    const odd = groupFailure(apiError(502, 'conflict', { conflict_reason: 'group_routed' }, true), true);
    expect(odd.kind).toBe('unknown_outcome');
    expect(odd.detail).not.toContain('Группу нельзя убрать в архив');
  });

  it('falls back to the code’s own catalogue sentence for a detail it does not know, never to the English message', () => {
    for (const error of [conflict('something_new'), invalid('members', 'something_new'), invalid('members', '')]) {
      expect(groupRefusalSentence(error)).toBeNull();
      const failure = groupFailure(error, true);
      expect(failure.detail).not.toContain('English');
      expect(failure.detail).not.toContain('something_new');
    }
  });

  it('does not take an unrelated refusal that shares a word for one of its own', () => {
    expect(groupRefusalSentence(apiError(409, 'conflict', { constraint: 'group_archived' }))).toBeNull();
    expect(groupRefusalSentence(apiError(422, 'validation_failed', { conflict_reason: 'group_archived' }))).toBeNull();
    expect(groupRefusalSentence(apiError(404, 'not_found', { conflict_reason: 'group_archived' }))).toBeNull();
  });
});

describe('the start of a run on a group', () => {
  const CASES: readonly [string, ApiError, string, string][] = [
    ['with a connection', invalid('executor_group_id', 'conflicts_with_executor_connection_id'),
      'group_with_executor', 'Группа и подключение выбраны вместе.'],
    ['with a preset', invalid('executor_group_id', 'conflicts_with_preset_id'),
      'group_with_preset', 'Группа и пресет выбраны вместе.'],
    ['unknown', invalid('executor_group_id', 'unknown_executor_group'),
      'group_unknown', 'Выбранной группы нет.'],
    ['environment source', invalid('executor_group_id', 'environment_source'),
      'group_environment_source', 'Прогон с источником «окружение» не может идти на группу.'],
    ['archived', conflict('group_archived'),
      'group_archived', 'Выбранная группа убрана в архив.'],
    ['no rule', apiError(503, 'dependency_unavailable', { dependency: 'no_rule_for_work_kind' }, true),
      'no_rule_for_work_kind', 'Для анализа текста нет правила.'],
  ];

  it('says each refusal as itself, in Russian, before the provider’s sentence', () => {
    for (const [name, error, kind, title] of CASES) {
      const failure = classifyRunFailure(error);
      expect(failure.kind, name).toBe(kind);
      expect(failure.title, name).toBe(title);
      expect(failure.kind, name).not.toBe('provider_unavailable');
      expect(failure.correlationId, name).toBe('cid-grp');
      expect(`${failure.title} ${failure.detail}`, name).not.toMatch(/[A-Za-z]/);
    }
  });

  it('presents every one as refused again until something changes: no retry under the same key', () => {
    for (const [name, error] of CASES) {
      expect(classifyRunFailure(error).presentation, name).toBe('unsupported');
      const markup = render(createElement(StartRunFailureView, {
        failure: classifyRunFailure(error), projectUid: PROJECT_UID, versionUid: VERSION_UID, onRetry: () => {},
      }));
      expect(markup, name).not.toContain('<button');
      expect(markup, name).not.toContain('Повторить');
      expect(markup, name).toContain('Прогон не запущен.');
    }
  });

  it('never invites the person to go round a refused group', () => {
    for (const [name, error] of CASES) {
      const markup = render(createElement(StartRunFailureView, {
        failure: classifyRunFailure(error), projectUid: PROJECT_UID, versionUid: VERSION_UID, onRetry: () => {},
      }));
      expect(markup, name).not.toContain('<select');
      expect(markup, name).not.toContain('href=');
      expect(markup, name).not.toMatch(/recorded|по умолчанию/i);
    }
    // The three that name a chosen group say outright that nothing takes its place.
    for (const [name, error] of CASES.filter(([, , kind]) => ['group_unknown', 'group_archived', 'group_environment_source'].includes(kind))) {
      expect(classifyRunFailure(error).detail, name)
        .toContain('Вместо выбранной группы прогон не запускается ни на другой группе, ни на подключении, ни по назначениям.');
    }
  });

  it('leaves the refusals of a connection and of a preset to their own sentences', () => {
    expect(classifyRunFailure(invalid('executor_connection_id', 'unknown_connection')).kind).toBe('executor_invalid');
    expect(classifyRunFailure(invalid('preset_id', 'unknown_preset')).kind).toBe('preset_unknown');
    expect(classifyRunFailure(apiError(503, 'dependency_unavailable', { dependency: 'executor_connection' }, true)).kind)
      .toBe('executor_unavailable');
    expect(classifyRunFailure(apiError(503, 'dependency_unavailable', { dependency: 'model_provider' }, true)).kind)
      .toBe('provider_unavailable');
  });
});
