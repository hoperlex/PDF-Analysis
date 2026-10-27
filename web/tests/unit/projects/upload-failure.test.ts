/**
 * Every upload failure is an explicit, distinguishable state.
 *
 * The three the PC-01 acceptance criteria name separately — an unsupported input, a
 * checksum failure and an unavailable dependency — must not collapse into one another
 * and must not collapse into a spinner or a success. That is what this suite holds.
 */

import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope, FetchLike } from '@/shared/api';
import { ApiError, TransportError, UnrecognizedApiError, uploadDocument } from '@/shared/api';
import {
  PC01_UPLOAD_ENVELOPE,
  UPLOAD_CONSTRAINTS_STATED,
  classifyUploadFailure,
  uploadConstraintSentence,
} from '@/entities/document-version';

function envelope(
  code: ErrorCode,
  retryable: boolean,
  details?: Record<string, string | number | boolean | null>,
): ErrorEnvelope {
  return {
    contract_version: '1.8.0',
    error_code: code,
    message: 'A caller-safe sentence.',
    correlation_id: 'corr-upload-1',
    retryable,
    ...(details === undefined ? {} : { details }),
  };
}

function apiError(
  status: number,
  code: ErrorCode,
  retryable: boolean,
  details?: Record<string, string | number | boolean | null>,
): ApiError {
  return new ApiError(status, envelope(code, retryable, details), 'corr-upload-1');
}

describe('the three named criteria are three different states', () => {
  const unsupported = classifyUploadFailure(
    apiError(422, 'validation_failed', false, { constraint: 'page_count_at_most_30' }),
  );
  const checksum = classifyUploadFailure(
    apiError(422, 'storage_integrity_error', false, { role: 'source.pdf' }),
  );
  const unavailable = classifyUploadFailure(apiError(503, 'dependency_unavailable', true));

  it('classifies an unsupported input as unsupported, with no retry', () => {
    expect(unsupported.kind).toBe('unsupported_input');
    expect(unsupported.presentation).toBe('unsupported');
    expect(unsupported.retryable).toBe(false);
    expect(unsupported.errorCode).toBe('validation_failed');
  });

  /**
   * `W31-RUS`, under `R-18`. This asserted the **envelope message** and the classifier.
   * The message is the API's own English — `contracts/domain/v1/error-codes.json` carries
   * 22 summaries and not one Cyrillic character — so the screen now renders
   * `catalogMessage(code)` in its place and keeps `details`.
   *
   * The claim in the name survives the change and is what is asserted here: the state is
   * still **specific**, not generic. The discriminating fact was never in the English
   * prose — it is `details.constraint`, which is what `tests/e2e/pc01/journey/manifest.json`
   * checks under `expects_rendered_from_envelope` (`not_encrypted`,
   * `every_page_has_extractable_text`, `page_count`). So: the constraint is still rendered,
   * and two different codes still read differently. (`page_count_at_most_30` is a spelling
   * nobody registered: it is shown by name, with no sentence guessed for it.)
   */
  it('renders the specific reason, not a sentence every code would get', () => {
    expect(unsupported.detail).toContain('page_count_at_most_30');
    expect(unsupported.detail).not.toBe(checksum.detail);
    expect(unsupported.detail).not.toBe(unavailable.detail);
    // And it is Russian, which is the whole point of the substitution.
    expect(/[а-яА-ЯёЁ]/u.test(unsupported.detail)).toBe(true);
    expect(unsupported.detail).not.toContain('A caller-safe sentence.');
  });

  it('classifies a checksum failure as its own state, not as an unsupported input', () => {
    expect(checksum.kind).toBe('checksum_mismatch');
    expect(checksum.kind).not.toBe(unsupported.kind);
    expect(checksum.retryable).toBe(false);
    expect(checksum.errorCode).toBe('storage_integrity_error');
    expect(checksum.detail).toContain('Ничего не опубликовано');
  });

  it('classifies an unavailable dependency as its own state, and as retryable', () => {
    expect(unavailable.kind).toBe('dependency_unavailable');
    expect(unavailable.retryable).toBe(true);
    expect(unavailable.errorCode).toBe('dependency_unavailable');
  });

  it('gives the three of them three distinct kinds and three distinct titles', () => {
    const kinds = new Set([unsupported.kind, checksum.kind, unavailable.kind]);
    const titles = new Set([unsupported.title, checksum.title, unavailable.title]);
    expect(kinds.size).toBe(3);
    expect(titles.size).toBe(3);
  });

  it('never reads as a success and never as "still working"', () => {
    for (const failure of [unsupported, checksum, unavailable]) {
      expect(failure.title.length).toBeGreaterThan(0);
      expect(failure.title.toLowerCase()).not.toContain('success');
      expect(failure.title.toLowerCase()).not.toContain('uploading');
      expect(failure.detail.length).toBeGreaterThan(0);
    }
  });
});

describe('retryability comes from the envelope and never from the status', () => {
  it('does not treat a 503 as retryable when the envelope says it is not', () => {
    const failure = classifyUploadFailure(apiError(503, 'storage_integrity_error', false));
    expect(failure.retryable).toBe(false);
  });

  it('does treat a 422 as retryable when the envelope says it is', () => {
    const failure = classifyUploadFailure(apiError(422, 'dependency_unavailable', true));
    expect(failure.retryable).toBe(true);
  });
});

describe('the idempotency outcomes stay apart', () => {
  it('separates in-progress, which is retried under the same key, from reuse, which is terminal', () => {
    const inProgress = classifyUploadFailure(
      apiError(409, 'idempotency_key_in_progress', true, { command_type: 'upload_document' }),
    );
    const reuse = classifyUploadFailure(apiError(409, 'idempotency_key_reuse', false));
    const stale = classifyUploadFailure(apiError(409, 'idempotency_key_stale', false));

    expect(inProgress.kind).toBe('in_progress');
    expect(inProgress.retryable).toBe(true);
    expect(inProgress.detail).toContain('тем же ключом');

    expect(reuse.kind).toBe('duplicate_intent');
    expect(reuse.retryable).toBe(false);
    expect(reuse.detail).toContain('Ничего не создано');

    expect(stale.kind).toBe('stale_intent');
    expect(stale.retryable).toBe(false);
    expect(new Set([inProgress.kind, reuse.kind, stale.kind]).size).toBe(3);
  });
});

describe('nothing thrown escapes classification', () => {
  it('renders an unrecognized code as an explicit state that retries nothing', () => {
    const failure = classifyUploadFailure(
      new UnrecognizedApiError(422, 'a_code_from_the_future', 'ignored', 'corr-9'),
    );
    expect(failure.kind).toBe('unrecognized');
    expect(failure.retryable).toBe(false);
    expect(failure.correlationId).toBe('corr-9');
  });

  it('renders a transport failure as its own state', () => {
    const failure = classifyUploadFailure(
      new TransportError('uploadDocument could not reach the API.', { retryable: true }),
    );
    expect(failure.kind).toBe('transport');
    expect(failure.retryable).toBe(true);
  });

  it('renders an unclassifiable value explicitly, and never as retryable', () => {
    const failure = classifyUploadFailure(new Error('something nobody modelled'));
    expect(failure.kind).toBe('unknown');
    expect(failure.retryable).toBe(false);
    expect(failure.correlationId).toBeNull();
    expect(failure.title.length).toBeGreaterThan(0);
  });
});

describe('only the safe classifiers the catalog declares are rendered', () => {
  it('ignores a detail key that is not declared safe for the reported code', () => {
    const failure = classifyUploadFailure(
      apiError(422, 'validation_failed', false, {
        constraint: 'encrypted_pdf',
        // Not in the safe key list for validation_failed. It must not reach the screen
        // even if a server ever put it in the envelope.
        dependency: 'must-not-be-rendered',
      }),
    );
    expect(failure.detail).toContain('encrypted_pdf');
    expect(failure.detail).not.toContain('must-not-be-rendered');
  });
});

describe('a refused bundle states the rule it broke, in Russian, beside the constraint', () => {
  const refuse = (constraint: string) =>
    classifyUploadFailure(apiError(422, 'validation_failed', false, { constraint, field: 'file' }));

  it('adds the constraint sentence to the generic one and keeps the constraint name', () => {
    for (const constraint of UPLOAD_CONSTRAINTS_STATED) {
      const failure = refuse(constraint);
      const sentence = uploadConstraintSentence(constraint);
      expect(failure.kind, constraint).toBe('unsupported_input');
      expect(failure.presentation, constraint).toBe('unsupported');
      expect(failure.retryable, constraint).toBe(false);
      expect(failure.detail, constraint).toContain(sentence ?? 'no sentence');
      expect(failure.detail, constraint).toContain(`constraint: ${constraint}`);
      expect(failure.detail, constraint).toContain('field: file');
    }
  });

  it('tells a bare PDF it is not a bundle and what to upload instead', () => {
    const failure = refuse('portal_bundle_required');
    expect(failure.detail).toContain('Загружается комплект портала распознавания');
    expect(failure.detail).toContain('Отдельный PDF');
    expect(failure.detail).toContain('constraint: portal_bundle_required');
  });

  it('states the 500-page and 250 MiB bounds in the page and size refusals', () => {
    expect(refuse('1 <= page_count <= 500').detail).toContain('от 1 до 500');
    expect(refuse('byte_size <= 262144000').detail).toContain('не более 250 MiB');
  });

  it('puts the rule of the member set in terms of the files a reviewer holds', () => {
    const detail = refuse('bundle_member_set').detail;
    for (const suffix of ['_blocks.json', '_results.md', '_results.html', '_stamp_audit.json']) {
      expect(detail).toContain(suffix);
    }
  });

  it('adds no sentence for a constraint nobody registered, and still shows its name', () => {
    const failure = refuse('a_constraint_nobody_registered');
    expect(failure.detail).toContain('constraint: a_constraint_nobody_registered');
    expect(failure.detail).toBe(
      classifyUploadFailure(apiError(422, 'validation_failed', false, {})).detail.replace(
        /$/,
        ' (constraint: a_constraint_nobody_registered, field: file)',
      ),
    );
  });

  it('adds no sentence when the refusal names no constraint', () => {
    const bare = classifyUploadFailure(apiError(422, 'validation_failed', false, {}));
    expect(bare.detail).not.toContain('(');
  });
});


describe('the upload gate’s busy refusal says what it is and when to send again (W55B-FIX, O-1)', () => {
  function busy(retryAfter: number | null): ApiError {
    return new ApiError(
      503,
      envelope('dependency_unavailable', true, { dependency: 'upload_capacity' }),
      'corr-upload-1',
      retryAfter,
    );
  }

  it('is not shown as a dependency that is down, and names the wait the answer gave', () => {
    const failure = classifyUploadFailure(busy(5));
    expect(failure.kind).toBe('dependency_unavailable');
    expect(failure.retryable).toBe(true);
    expect(failure.title).toBe('Сервер сейчас принимает другие загрузки.');
    expect(failure.detail).toBe(
      'Одновременно принимаются не больше двух загрузок, и обе заняты. Повторите загрузку через 5 с. ' +
        'Ничего не создано; повтор использует тот же ключ идемпотентности.',
    );
    expect(failure.detail).not.toContain('Зависимость');
  });

  it('asks for a little patience when the answer named no wait', () => {
    expect(classifyUploadFailure(busy(null)).detail).toContain('Повторите загрузку немного позже.');
  });

  it('leaves every other unavailable dependency as it was', () => {
    const other = classifyUploadFailure(
      new ApiError(503, envelope('dependency_unavailable', true, { dependency: 'object_store' }), 'c', 5),
    );
    expect(other.title).toBe('Зависимость, нужная этой загрузке, недоступна.');
  });
});

describe('every constraint the panel can be shown has a sentence (W55B-FIX, Y-4)', () => {
  it.each(['non_empty', 'plain_base_name', 'blocks_count', 'pdf_page_content', 'pdf_document_content', 'pdf_reader_limits'])(
    '%s is a Russian sentence on the panel, not a bare token',
    (constraint) => {
      const sentence = uploadConstraintSentence(constraint);
      expect(sentence).not.toBeNull();
      expect(sentence).toMatch(/^[А-ЯЁ].*[а-яё]\.$/u);
      const failure = classifyUploadFailure(apiError(422, 'validation_failed', false, { constraint, field: 'content' }));
      expect(failure.detail).toContain(sentence ?? '');
    },
  );
});

/**
 * `WEB-FOLLOWUPS-01`: a refusal that never came from the API.
 *
 * A real user choosing an 8.6 MiB bundle on the deployed stand was told «HTTP 413: тело ответа
 * не является конвертом ошибки по контракту. Было ли что-нибудь опубликовано, неизвестно;
 * повтор под тем же ключом безопасен.» The 413 was the host's TLS terminator refusing the body
 * (nginx's default 1 MiB), an HTML page and not an `ErrorEnvelope`; the sentence was an
 * operator's note about the transport, and its second half was false: the file was refused
 * before anything could be stored, and sending it again is refused again.
 */
describe('a refusal from the web server in front of the API says so (WEB-FOLLOWUPS-01)', () => {
  const NOT_AN_ENVELOPE = 'тело ответа не является конвертом ошибки по контракту.';
  const RETRY_SAFE = 'повтор под тем же ключом безопасен';

  const edge = (status: number) =>
    classifyUploadFailure(new TransportError(`HTTP ${status}: ${NOT_AN_ENVELOPE}`, { status }));

  it('reads a 413 as a refusal before the API and states the product limit from the envelope constant', () => {
    const failure = edge(413);
    expect(failure.kind).toBe('edge_too_large');
    expect(failure.presentation).toBe('error');
    expect(failure.errorCode).toBeNull();
    expect(failure.retryable).toBe(false);
    expect(failure.detail).toContain('Сервер отклонил файл как слишком большой ещё до API');
    expect(failure.detail).toContain('ограничение веб-сервера');
    expect(failure.detail).toContain('Ничего не сохранено');
    expect(failure.detail).toContain(`Лимит продукта — ${PC01_UPLOAD_ENVELOPE.maxBytesLabel}`);
    expect(failure.detail).toContain('обратитесь к администратору стенда');
  });

  it('keeps the transport note and the retry-safety sentence out of a 413: nothing was stored, a resend is refused again', () => {
    const failure = edge(413);
    expect(failure.detail).not.toContain(NOT_AN_ENVELOPE);
    expect(failure.detail).not.toContain('HTTP');
    expect(failure.detail).not.toContain(RETRY_SAFE);
    expect(failure.detail).not.toContain('неизвестно');
  });

  it.each([502, 503, 504])('reads a %i from the web server as an unanswered upload, whose retry is safe', (status) => {
    const failure = edge(status);
    expect(failure.kind).toBe('edge_unavailable');
    expect(failure.retryable).toBe(false);
    expect(failure.detail).toContain('Веб-сервер');
    expect(failure.detail).toContain(`код ${status}`);
    expect(failure.detail).not.toContain(NOT_AN_ENVELOPE);
    expect(failure.detail).not.toContain('HTTP');
    // True here, and only here: the upload may have reached the API, and the key is the
    // API's proof that a second send is the same command.
    expect(failure.detail).toContain('Было ли что-нибудь опубликовано, неизвестно');
    expect(failure.detail).toContain(RETRY_SAFE);
  });

  it('words each of the three differently, because each means something different', () => {
    const details = [502, 503, 504].map((status) => edge(status).detail);
    expect(new Set(details).size).toBe(3);
  });

  it('leaves every other transport failure as it was', () => {
    for (const other of [
      new TransportError('Запрос uploadDocument не дошёл до API.', { retryable: true }),
      new TransportError(`HTTP 500: ${NOT_AN_ENVELOPE}`, { status: 500 }),
      new TransportError(`HTTP 404: ${NOT_AN_ENVELOPE}`, { status: 404 }),
    ]) {
      const failure = classifyUploadFailure(other);
      expect(failure.kind).toBe('transport');
      expect(failure.title).toBe('Загрузка не дошла до API.');
      expect(failure.detail).toContain(other.message);
      expect(failure.detail).toContain(RETRY_SAFE);
    }
  });

  it('does not touch an envelope: a 413 the API itself sent keeps its code', () => {
    const failure = classifyUploadFailure(apiError(413, 'validation_failed', false, { constraint: 'max_bytes' }));
    expect(failure.kind).toBe('unsupported_input');
    expect(failure.errorCode).toBe('validation_failed');
  });

  it('is what a user gets from the transport: an HTML 413 page through uploadDocument', async () => {
    const fetch: FetchLike = () =>
      Promise.resolve(
        new Response('<html><body><h1>413 Request Entity Too Large</h1></body></html>', {
          status: 413,
          headers: { 'Content-Type': 'text/html' },
        }),
      );
    const thrown = await uploadDocument(
      {
        path: { project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' },
        body: { file: new Blob(['x'], { type: 'application/zip' }) },
        idempotencyKey: 'key-edge-413',
      },
      { baseUrl: 'https://api.test/v1', fetch },
    ).catch((error: unknown) => error);
    expect(thrown).toBeInstanceOf(TransportError);
    const failure = classifyUploadFailure(thrown);
    expect(failure.kind).toBe('edge_too_large');
    expect(failure.detail).toContain('ещё до API');
    expect(failure.detail).not.toContain('конвертом');
  });
});
