/**
 * `AR-V3-BETA-PACK-STATUS-WEB-01`: what the reader is told when the six checks do not start.
 *
 * Every refusal `startArV3BetaGroup` raises (`src/auditmanager/runs/v3_group.py`) has a sentence
 * of its own, because each is cured by a different person. Two sentences that were the same would
 * send two different causes to the same place, so distinctness is asserted, not assumed. A code
 * outside the set is the generic reading with its correlation id — never silence, and never one
 * of the specific sentences.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError, TransportError, UnrecognizedApiError } from '@/shared/api';
import { routes } from '@/shared/lib';
import {
  MALFORMED_GROUP_ANSWER,
  StartArV3GroupView,
  classifyArV3GroupStartFailure,
} from '@/features/start-ar-v3-group';
import type { ArV3GroupStartFailure, ArV3GroupStartFailureKind } from '@/features/start-ar-v3-group';

const PROJECT_UID = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const VERSION_UID = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

function refusal(
  status: number,
  code: ErrorCode,
  options: { details?: Record<string, string | number | boolean | null>; retryable?: boolean } = {},
): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.5.0',
    error_code: code,
    message: 'A caller-safe sentence.',
    correlation_id: 'cid-group',
    retryable: options.retryable ?? false,
    ...(options.details === undefined ? {} : { details: options.details }),
  };
  return new ApiError(status, envelope, 'cid-group');
}

/** The refusals the start raises, each with the kind it must be told as. */
const SPECIFIC: ReadonlyArray<readonly [string, ApiError, ArV3GroupStartFailureKind]> = [
  [
    'the reviewed pack is not usable',
    refusal(503, 'dependency_unavailable', { details: { dependency: 'ar_v3_trusted_pack' }, retryable: true }),
    'pack_unavailable',
  ],
  [
    'another dependency is unavailable',
    refusal(503, 'dependency_unavailable', { details: { dependency: 'metadata_store' }, retryable: true }),
    'provider_unavailable',
  ],
  ['a norms source is not ready', refusal(422, 'required_norm_unavailable', { details: { reference_kind: 'norms_snapshot' } }), 'norm_unavailable'],
  ['the version has no confirmed classification', refusal(422, 'version_classification_required'), 'version_unclassified'],
  ['the confirmed section is not AR', refusal(422, 'section_profile_unavailable'), 'section_not_ar'],
  ['the version lacks its source document', refusal(422, 'analysis_input_invalid', { details: { reason: 'missing_required_input' } }), 'input_invalid'],
  [
    'the text exceeds the input budget',
    refusal(422, 'analysis_input_budget_exceeded', { details: { character_count: 300000, budget_characters: 152000 } }),
    'input_budget_exceeded',
  ],
  ['the key was used for another request', refusal(409, 'idempotency_key_reuse'), 'key_reused'],
  ['the same request is still running', refusal(409, 'idempotency_key_in_progress', { retryable: true }), 'in_progress'],
  ['the recorded result is gone', refusal(409, 'idempotency_key_stale'), 'stale_intent'],
  ['the version does not exist', refusal(404, 'not_found'), 'not_found'],
  ['the caller is not signed in', refusal(401, 'authentication_required'), 'not_authenticated'],
  ['the caller may not start it', refusal(403, 'permission_denied'), 'not_permitted'],
];

describe('every refusal the six-check start raises is told as itself', () => {
  it.each(SPECIFIC)('%s', (_name, error, kind) => {
    const failure = classifyArV3GroupStartFailure(error);
    expect(failure.kind).toBe(kind);
    expect(failure.correlationId).toBe('cid-group');
    expect(failure.title.length).toBeGreaterThan(10);
    expect(failure.detail.length).toBeGreaterThan(10);
  });

  it('gives each refusal a title and a detail no other refusal has', () => {
    const failures = SPECIFIC.map(([, error]) => classifyArV3GroupStartFailure(error));
    expect(new Set(failures.map((f) => f.kind)).size).toBe(SPECIFIC.length);
    expect(new Set(failures.map((f) => f.title)).size, 'two refusals share a title').toBe(SPECIFIC.length);
    expect(new Set(failures.map((f) => f.detail)).size, 'two refusals share a detail').toBe(SPECIFIC.length);
  });

  it('offers a retry for no refusal that the same request would meet again', () => {
    const unsupported = SPECIFIC.map(([, error]) => classifyArV3GroupStartFailure(error)).filter(
      (failure) => failure.presentation === 'unsupported',
    );
    expect(unsupported.map((f) => f.kind).sort()).toEqual([
      'input_budget_exceeded',
      'input_invalid',
      'norm_unavailable',
      'pack_unavailable',
      'section_not_ar',
      'version_unclassified',
    ]);
    // The pack refusal says retry is pointless even though the envelope marks a 503 retryable.
    const pack = classifyArV3GroupStartFailure(SPECIFIC[0]![1]);
    expect(pack.retryable).toBe(false);
  });

  it('keeps a retry for the transient dependency under the same key', () => {
    const failure = classifyArV3GroupStartFailure(SPECIFIC[1]![1]);
    expect(failure.presentation).toBe('error');
    expect(failure.retryable).toBe(true);
    expect(failure.detail).toContain('тот же ключ идемпотентности');
    expect(failure.detail).toContain('не запускаются вместо этого в другом режиме провайдера');
  });

  it('carries the budget figures beside the sentence, and none when they are odd', () => {
    const withFigures = classifyArV3GroupStartFailure(SPECIFIC[6]![1]);
    expect(withFigures.detail).toContain('Символов в тексте версии');
    const odd = classifyArV3GroupStartFailure(
      refusal(422, 'analysis_input_budget_exceeded', { details: { character_count: 1.5, budget_characters: 152000 } }),
    );
    expect(odd.detail).not.toContain('Символов в тексте версии');
  });

  it('never offers another provider mode, pack, section or the single-run start as a substitute', () => {
    for (const [, error] of SPECIFIC) {
      const failure = classifyArV3GroupStartFailure(error);
      const text = `${failure.title} ${failure.detail}`;
      expect(text, failure.kind).not.toMatch(/запустить прогон|вместо этого запущ|по умолчанию|recorded/i);
    }
  });
});

describe('a code outside the set is the generic reading, with its correlation id', () => {
  it('maps a catalog code the start does not raise to the generic sentence', () => {
    const known = new Set(SPECIFIC.map(([, error]) => classifyArV3GroupStartFailure(error).detail));
    for (const code of ['internal_error', 'validation_failed', 'conflict', 'analysis_failed'] as const) {
      const failure = classifyArV3GroupStartFailure(refusal(500, code));
      expect(failure.kind, code).toBe('generic');
      expect(failure.correlationId, code).toBe('cid-group');
      expect(failure.title, code).toBe('Запрос на шесть проверок не выполнен.');
      expect(known.has(failure.detail), code).toBe(false);
    }
  });

  it('maps a code this client does not know, a transport failure and a stray throw to it as well', () => {
    const unknownCode = classifyArV3GroupStartFailure(new UnrecognizedApiError(500, 'future_code', 'm', 'cid-future'));
    expect(unknownCode.kind).toBe('generic');
    expect(unknownCode.correlationId).toBe('cid-future');
    expect(unknownCode.detail).toContain('future_code');

    const transport = classifyArV3GroupStartFailure(new TransportError('no route', { retryable: true }));
    expect(transport.kind).toBe('generic');
    expect(transport.retryable).toBe(true);

    const stray = classifyArV3GroupStartFailure(new TypeError('Cannot read properties of undefined'));
    expect(stray.kind).toBe('generic');
    expect(stray.detail).not.toContain('Cannot read');
  });
});

function view(failure: ArV3GroupStartFailure | null, pending = false): string {
  return renderToStaticMarkup(
    createElement(StartArV3GroupView, {
      projectUid: PROJECT_UID,
      versionUid: VERSION_UID,
      pending,
      failure,
      onSend: () => undefined,
    }),
  );
}

describe('the control shows each refusal with only the actions that can help', () => {
  it('idle: one button, the fixed note, no selector and no failure', () => {
    const markup = view(null);
    expect(markup).toContain('>Запустить шесть проверок АР v3</button>');
    expect(markup).toContain('Шесть отдельных прогонов; результат — предварительные цитаты для проверки экспертом, без числовых выводов.');
    expect(markup).not.toContain('<select');
    expect(markup).not.toContain('type="radio"');
    expect(markup).not.toContain('<input');
    expect(markup).not.toContain('data-ar-v3-group-failure');
    expect(markup.match(/<button\b/g)).toHaveLength(1);
    expect(markup).not.toContain('disabled');
  });

  it('pending: the button is disabled and the request is named', () => {
    const markup = view(null, true);
    expect(markup).toContain('disabled');
    expect(markup).toContain('Загрузка: запрос на шесть проверок…');
  });

  it('a pack refusal is a warning with the correlation id, one button and no retry', () => {
    const markup = view(classifyArV3GroupStartFailure(SPECIFIC[0]![1]));
    expect(markup).toContain('am-state--warning');
    expect(markup).toContain('data-ar-v3-group-failure="pack_unavailable"');
    expect(markup).toContain('cid-group');
    expect(markup).toContain('Шесть проверок не запущены.');
    expect(markup.match(/<button\b/g)).toHaveLength(1);
    expect(markup).not.toContain('Повторить');
  });

  it('links the two classification refusals to the version panel and no other refusal', () => {
    const address = routes.versionClassification(PROJECT_UID, VERSION_UID);
    for (const [, error, kind] of SPECIFIC) {
      const markup = view(classifyArV3GroupStartFailure(error));
      const linked = kind === 'version_unclassified' || kind === 'section_not_ar';
      expect(markup.includes(`href="${address}"`), kind).toBe(linked);
    }
  });

  it('a transient failure keeps its retry under the same key', () => {
    const markup = view(classifyArV3GroupStartFailure(SPECIFIC[1]![1]));
    expect(markup).toContain('am-state--error');
    expect(markup).toContain('Повторить с тем же ключом');
  });

  it('a 202 without a usable group address is a fault with a same-key retry', () => {
    const markup = view(MALFORMED_GROUP_ANSWER);
    expect(markup).toContain('Ответ сервера не соответствует контракту.');
    expect(markup).toContain('data-ar-v3-group-failure="malformed_answer"');
    expect(markup).toContain('Повторить с тем же ключом');
  });
});
