/**
 * The one place in `web/` where an HTTP request is made.
 *
 * Everything above this module — every slice `B7` and `B8` will write — calls a generated
 * function from `client.gen.ts`, which calls `request` here. The ESLint boundary rules
 * and a guard test both forbid `fetch`, `XMLHttpRequest` and any HTTP library elsewhere,
 * so there is exactly one implementation of: how a URL is built, how the idempotency key
 * is attached, how the correlation id is carried, and how a failure is decoded.
 *
 * What this module deliberately does not do: retry, back off, cache, refresh, redirect,
 * or interpret a status code as a policy. Retryability comes from the envelope; caching
 * comes from the query client in `_app`; the one polling loop lives in `./polling`.
 */

import { getApiBaseUrl } from '../config';
import {
  ApiError,
  ClientUsageError,
  TransportError,
  UnrecognizedApiError,
  isErrorCode,
  isErrorEnvelope,
} from './errors';

const IDEMPOTENCY_HEADER = 'Idempotency-Key';
const CORRELATION_HEADER = 'X-Correlation-Id';
const JSON_MEDIA_TYPE = 'application/json';
const MULTIPART_MEDIA_TYPE = 'multipart/form-data';

/** What the generated `OPERATIONS` table supplies for one operation. */
export interface OperationDescriptor {
  readonly operationId: string;
  readonly method: string;
  readonly path: string;
  readonly pathParams: readonly string[];
  readonly queryParams: readonly string[];
  readonly headerParams: readonly string[];
  readonly requiresIdempotencyKey: boolean;
  readonly requestMediaType: string | null;
  readonly responseMediaType: string | null;
  readonly successStatuses: readonly number[];
  readonly errorStatuses: readonly number[];
  readonly tags: readonly string[];
}

/** The structural supertype every generated `...Input` satisfies. */
export interface OperationInput {
  readonly path?: Readonly<Record<string, string>>;
  readonly query?: Readonly<Record<string, string | number | boolean | undefined>>;
  readonly body?: unknown;
  readonly idempotencyKey?: string;
  readonly correlationId?: string;
  readonly headers?: Readonly<Record<string, string | undefined>>;
}

/** The subset of `fetch` this transport uses, so a test can supply its own. */
export type FetchLike = (input: string, init: RequestInit) => Promise<Response>;

export interface RequestOptions {
  /** Cancels the request. An abort surfaces as a non-retryable `TransportError`. */
  readonly signal?: AbortSignal;
  /** Overrides the configured base URL. For tests and for nothing else. */
  readonly baseUrl?: string;
  /** Overrides the fetch implementation. For tests and for nothing else. */
  readonly fetch?: FetchLike;
}

export interface ApiResponse<T> {
  /** The decoded success body. `Blob` for the streaming and export operations. */
  readonly data: T;
  /** The HTTP status actually returned, which for a stream may be 200 or 206. */
  readonly status: number;
  /** `X-Correlation-Id`, which the contract says is present on every response. */
  readonly correlationId: string | null;
}

function resolveFetch(options: RequestOptions | undefined): FetchLike {
  if (options?.fetch !== undefined) return options.fetch;
  const globalFetch = globalThis.fetch;
  if (typeof globalFetch !== 'function') {
    throw new ClientUsageError(
      'В этой среде выполнения нет реализации fetch. Передайте её через ' +
        'RequestOptions.fetch.',
    );
  }
  return (input, init) => globalFetch(input, init);
}

function buildPath(descriptor: OperationDescriptor, input: OperationInput): string {
  return descriptor.path.replace(/\{([^}]+)\}/g, (_match, name: string) => {
    const value = input.path?.[name];
    if (value === undefined || value === '') {
      throw new ClientUsageError(
        `${descriptor.operationId}: параметр пути «${name}» требуется шаблоном ` +
          `«${descriptor.path}» и не был передан.`,
      );
    }
    return encodeURIComponent(value);
  });
}

function buildQuery(descriptor: OperationDescriptor, input: OperationInput): string {
  const params = new URLSearchParams();
  // Iterate the descriptor, not the caller's object: an undeclared key is never sent.
  for (const name of descriptor.queryParams) {
    const value = input.query?.[name];
    if (value === undefined) continue;
    params.append(name, String(value));
  }
  const encoded = params.toString();
  return encoded.length > 0 ? `?${encoded}` : '';
}

function buildHeaders(descriptor: OperationDescriptor, input: OperationInput): Headers {
  const headers = new Headers();

  if (descriptor.responseMediaType !== null) {
    headers.set('Accept', descriptor.responseMediaType);
  }

  if (descriptor.requiresIdempotencyKey) {
    const key = input.idempotencyKey;
    if (key === undefined || key.length === 0) {
      throw new ClientUsageError(
        `${descriptor.operationId} — операция записи, ей требуется ${IDEMPOTENCY_HEADER}. ` +
          'Выпустите по одному ключу на намерение через newIdempotencyKey() и повторяйте ' +
          'с тем же значением: новый ключ — это новая команда, а не повтор.',
      );
    }
    headers.set(IDEMPOTENCY_HEADER, key);
  }

  if (input.correlationId !== undefined && input.correlationId.length > 0) {
    headers.set(CORRELATION_HEADER, input.correlationId);
  }

  for (const name of descriptor.headerParams) {
    const value = input.headers?.[name];
    if (value === undefined) continue;
    headers.set(name, value);
  }

  return headers;
}

function buildBody(descriptor: OperationDescriptor, input: OperationInput, headers: Headers): BodyInit | undefined {
  if (descriptor.requestMediaType === null) return undefined;

  if (descriptor.requestMediaType === JSON_MEDIA_TYPE) {
    headers.set('Content-Type', JSON_MEDIA_TYPE);
    return JSON.stringify(input.body ?? {});
  }

  if (descriptor.requestMediaType === MULTIPART_MEDIA_TYPE) {
    // Content-Type is left unset on purpose: only the runtime can supply the boundary.
    const form = new FormData();
    const body = input.body;
    if (typeof body !== 'object' || body === null) {
      throw new ClientUsageError(
        `${descriptor.operationId}: тело multipart должно быть объектом полей.`,
      );
    }
    for (const name of Object.keys(body as Record<string, unknown>).sort()) {
      const value = (body as Record<string, unknown>)[name];
      if (value === undefined || value === null) continue;
      if (value instanceof Blob) form.append(name, value);
      else form.append(name, String(value));
    }
    return form;
  }

  throw new ClientUsageError(
    `${descriptor.operationId}: тип содержимого запроса ` +
      `«${descriptor.requestMediaType}» не поддерживается. Транспорт знает ${JSON_MEDIA_TYPE} и ` +
      `${MULTIPART_MEDIA_TYPE}.`,
  );
}

async function decodeFailure(response: Response, correlationId: string | null): Promise<never> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch (cause) {
    throw new TransportError(
      `HTTP ${response.status}: тело ответа не является конвертом ошибки по контракту.`,
      { status: response.status, correlationId, cause },
    );
  }

  if (!isErrorEnvelope(payload)) {
    throw new TransportError(
      `HTTP ${response.status}: тело ответа — JSON, но не конверт ошибки по контракту.`,
      { status: response.status, correlationId },
    );
  }

  const rawCode = payload.error_code as unknown as string;
  if (!isErrorCode(rawCode)) {
    throw new UnrecognizedApiError(response.status, rawCode, payload.message, correlationId);
  }

  throw new ApiError(response.status, payload, correlationId);
}

/**
 * Execute one contract operation.
 *
 * Generated code is the only intended caller. A slice imports the generated function, not
 * this one.
 */
export async function request<TResult>(
  descriptor: OperationDescriptor,
  input: OperationInput,
  options?: RequestOptions,
): Promise<ApiResponse<TResult>> {
  const baseUrl = options?.baseUrl ?? getApiBaseUrl();
  const url = `${baseUrl}${buildPath(descriptor, input)}${buildQuery(descriptor, input)}`;

  const headers = buildHeaders(descriptor, input);
  const body = buildBody(descriptor, input, headers);

  const init: RequestInit = { method: descriptor.method, headers };
  if (body !== undefined) init.body = body;
  if (options?.signal !== undefined) init.signal = options.signal;

  let response: Response;
  try {
    response = await resolveFetch(options)(url, init);
  } catch (cause) {
    const aborted = options?.signal?.aborted === true;
    throw new TransportError(
      aborted
        ? `Запрос ${descriptor.operationId} был прерван до получения ответа.`
        : `Запрос ${descriptor.operationId} не дошёл до API.`,
      { cause, retryable: !aborted },
    );
  }

  const correlationId = response.headers.get(CORRELATION_HEADER);

  if (!response.ok) await decodeFailure(response, correlationId);

  if (descriptor.responseMediaType === null) {
    return { data: undefined as TResult, status: response.status, correlationId };
  }

  if (descriptor.responseMediaType === JSON_MEDIA_TYPE) {
    try {
      return { data: (await response.json()) as TResult, status: response.status, correlationId };
    } catch (cause) {
      throw new TransportError(
        `Запрос ${descriptor.operationId} вернул HTTP ${response.status} с нечитаемым JSON в теле.`,
        { status: response.status, correlationId, cause },
      );
    }
  }

  // Everything else on this surface is bytes: application/pdf and text/csv.
  return { data: (await response.blob()) as TResult, status: response.status, correlationId };
}
