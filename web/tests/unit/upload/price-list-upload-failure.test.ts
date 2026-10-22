/**
 * `WEB-FOLLOWUPS-02` / `D-195`: the price-list upload says a refusal from the web server in
 * Russian, as the document upload does.
 *
 * A price list bigger than the host's body limit is refused with an HTML `413` that never
 * reached the API. The price-list entity's reading made that «Запрос не дошёл до сервера …
 * повторите попытку»: Russian, but it sends the user to resend a file that is refused again,
 * and it hides that the limit is the administrator's to change. The feature now reads a
 * web-server answer through the shared `classifyUploadFailure` -- with the price list's own
 * 10 MiB in the sentence, not the document envelope's 250 MiB -- and leaves every other
 * failure to the entity, which knows the file constraints of `uploadPriceList`.
 */

import { createElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

const hold = vi.hoisted(() => ({
  state: {
    error: null as unknown,
    isPending: false,
    data: undefined as unknown,
    mutate: () => {},
    reset: () => {},
  },
}));

vi.mock('@/features/upload-price-list/model/use-upload-price-list', () => ({
  useUploadPriceList: () => hold.state,
}));

import type { ErrorCode, ErrorEnvelope, FetchLike } from '@/shared/api';
import { ApiError, TransportError, uploadPriceList } from '@/shared/api';
import { PC01_UPLOAD_ENVELOPE, classifyUploadFailure } from '@/entities/document-version';
import {
  PRICE_LIST_LIMIT_LABEL,
  PRICE_LIST_MAX_BYTES,
  UploadPriceListForm,
  priceListUploadFailure,
} from '@/features/upload-price-list';

import { render } from '../review/fixtures';

const NOT_AN_ENVELOPE = 'тело ответа не является конвертом ошибки по контракту.';
const TRANSPORT_SENTENCE = 'Запрос не дошёл до сервера или его ответ не удалось прочитать';
const RETRY_SAFE = 'повтор под тем же ключом безопасен';

const edge = (status: number) =>
  new TransportError(`HTTP ${status}: ${NOT_AN_ENVELOPE}`, {
    status,
    correlationId: 'corr-price-list-edge',
  });

function refusal(code: ErrorCode, details: Record<string, string | number | boolean | null>): ApiError {
  const body: ErrorEnvelope = {
    contract_version: '1.0.0',
    error_code: code,
    message: 'A caller-safe sentence.',
    correlation_id: 'corr-price-list-1',
    retryable: false,
    details,
  };
  return new ApiError(422, body);
}

describe('a 413 from the web server in front of the API', () => {
  it('is said as a refusal before the API, with the price list’s own limit', () => {
    const failure = priceListUploadFailure(edge(413));
    expect(failure.detail).toContain('Сервер отклонил файл как слишком большой ещё до API');
    expect(failure.detail).toContain('ограничение веб-сервера');
    expect(failure.detail).toContain('Ничего не сохранено');
    expect(failure.detail).toContain('Лимит продукта — 10 MiB');
    expect(failure.detail).toContain('обратитесь к администратору стенда');
    expect(failure.detail).not.toContain(PC01_UPLOAD_ENVELOPE.maxBytesLabel);
  });

  it('keeps the operator’s note, the transport sentence and the retry promise out of it', () => {
    const failure = priceListUploadFailure(edge(413));
    expect(failure.detail).not.toContain(NOT_AN_ENVELOPE);
    expect(failure.detail).not.toContain('HTTP');
    expect(failure.detail).not.toContain(TRANSPORT_SENTENCE);
    expect(failure.detail).not.toContain(RETRY_SAFE);
    expect(failure.detail).not.toContain('повторите попытку');
  });

  it('offers no retry, and carries the correlation id and the transport kind the form renders', () => {
    const failure = priceListUploadFailure(edge(413));
    expect(failure.retryable).toBe(false);
    expect(failure.kind).toBe('transport');
    expect(failure.errorCode).toBeNull();
    expect(failure.correlationId).toBe('corr-price-list-edge');
  });

  it('is Russian: no Latin word but the unit and the abbreviation', () => {
    const words = (priceListUploadFailure(edge(413)).detail.match(/[A-Za-z]+/g) ?? []).filter(
      (word) => word !== 'MiB' && word !== 'API',
    );
    expect(words).toEqual([]);
  });
});

describe('a 502, 503 or 504 from the web server', () => {
  it.each([502, 503, 504])('says %i as an unanswered upload whose resend is safe under the same key', (status) => {
    const failure = priceListUploadFailure(edge(status));
    expect(failure.detail).toContain('Веб-сервер');
    expect(failure.detail).toContain(`код ${status}`);
    expect(failure.detail).toContain('Было ли что-нибудь опубликовано, неизвестно');
    expect(failure.detail).toContain(RETRY_SAFE);
    expect(failure.detail).not.toContain(NOT_AN_ENVELOPE);
    expect(failure.detail).not.toContain(TRANSPORT_SENTENCE);
  });

  it('words each of the three differently', () => {
    const details = [502, 503, 504].map((status) => priceListUploadFailure(edge(status)).detail);
    expect(new Set(details).size).toBe(3);
  });
});

describe('every other failure is still the price-list entity’s reading', () => {
  it('keeps the transport sentence for a transport failure with no web-server status', () => {
    for (const other of [
      new TransportError('Запрос uploadPriceList не дошёл до API.', { retryable: true }),
      new TransportError(`HTTP 500: ${NOT_AN_ENVELOPE}`, { status: 500 }),
      new TransportError(`HTTP 404: ${NOT_AN_ENVELOPE}`, { status: 404 }),
    ]) {
      const failure = priceListUploadFailure(other);
      expect(failure.kind).toBe('transport');
      expect(failure.detail).toContain(TRANSPORT_SENTENCE);
    }
  });

  it('keeps the sentence for a file constraint, with what to do about it', () => {
    const failure = priceListUploadFailure(refusal('validation_failed', { constraint: 'price_list_header' }));
    expect(failure.detail).toBe(
      'В первых 20 непустых строках нет заголовка со столбцами наименования, единицы измерения и цены.',
    );
    expect(failure.errorCode).toBe('validation_failed');
  });

  it('keeps the entity’s own sentence for a reused key', () => {
    const failure = priceListUploadFailure(refusal('idempotency_key_reuse', {}));
    expect(failure.detail).toBe(
      'Этот запрос уже был отправлен с другим файлом. Выберите файл заново и повторите загрузку.',
    );
  });

  it('keeps the unexpected-failure sentence for something that is not a request failure', () => {
    expect(priceListUploadFailure(new Error('boom')).kind).toBe('unexpected');
  });
});

describe('the shared classifier takes the upload’s own limit', () => {
  it('names the document envelope’s limit by default, so the document upload is unchanged', () => {
    const failure = classifyUploadFailure(edge(413));
    expect(failure.kind).toBe('edge_too_large');
    expect(failure.detail).toContain(`Лимит продукта — ${PC01_UPLOAD_ENVELOPE.maxBytesLabel}`);
    expect(failure.detail).not.toContain('10 MiB');
  });

  it('names the limit it is given', () => {
    const failure = classifyUploadFailure(edge(413), { limitLabel: '10 MiB' });
    expect(failure.detail).toContain('Лимит продукта — 10 MiB');
    expect(failure.detail).not.toContain(PC01_UPLOAD_ENVELOPE.maxBytesLabel);
  });

  it('says the price list’s limit as the form states it', () => {
    expect(PRICE_LIST_LIMIT_LABEL).toBe(`${PRICE_LIST_MAX_BYTES / (1024 * 1024)} MiB`);
  });
});

describe('an HTML 413 page through uploadPriceList', () => {
  it('reaches the user as the sentence above, not as the operator’s note', async () => {
    const fetch: FetchLike = () =>
      Promise.resolve(
        new Response('<html><body><h1>413 Request Entity Too Large</h1></body></html>', {
          status: 413,
          headers: { 'Content-Type': 'text/html' },
        }),
      );
    const thrown = await uploadPriceList(
      {
        path: { project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' },
        body: { file: new Blob(['x'], { type: 'text/csv' }) as unknown as File },
        idempotencyKey: 'key-price-list-413',
      },
      { baseUrl: 'https://api.test/v1', fetch },
    ).catch((error: unknown) => error);
    expect(thrown).toBeInstanceOf(TransportError);
    const failure = priceListUploadFailure(thrown);
    expect(failure.detail).toContain('ещё до API');
    expect(failure.detail).toContain('10 MiB');
    expect(failure.detail).not.toContain('конвертом');
  });
});

describe('the form shows the sentence', () => {
  it('renders the web-server refusal under «Прайс-лист не загружен.» and offers no retry', () => {
    hold.state.error = edge(413);
    const markup = render(createElement(UploadPriceListForm, { projectUid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' }));
    expect(markup).toContain('Прайс-лист не загружен.');
    expect(markup).toContain('Сервер отклонил файл как слишком большой ещё до API');
    expect(markup).toContain('Лимит продукта — 10 MiB');
    expect(markup).not.toContain(TRANSPORT_SENTENCE);
    expect(markup).not.toContain('Повторить');
  });

  it('still renders the entity’s sentence for a file constraint', () => {
    hold.state.error = refusal('validation_failed', { constraint: 'price_list_format' });
    const markup = render(createElement(UploadPriceListForm, { projectUid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' }));
    expect(markup).toContain('Книги Excel 97–2003 не читаются');
  });
});
