/**
 * The credentialed forward: the second — and last — place in `web/` that makes an HTTP
 * request, and the only one that ever attaches `Authorization`.
 *
 * It runs on the Next **server**, called by `src/app/bff/v1/[...path]/route.ts`. The
 * browser calls the Next server at `/bff/v1/...`; this forwards to the API with the
 * deployment's bearer credential and returns the upstream answer unchanged. The token is
 * a parameter, never a module-scope read, so this file holds no secret and is inert if it
 * is ever imported somewhere it should not be.
 *
 * It lives under `src/shared/api/` because that is the one prefix where raw `fetch` is
 * legal — both the ESLint config and `tests/guards/lib/source-scan.ts` name that prefix —
 * and a second exemption carved out for `src/app/**` would have widened the transport
 * boundary permanently to solve a problem that did not need it widened.
 *
 * ## What passes through and what does not
 *
 * **Status and body bytes are verbatim.** That is the whole point: `transport.ts` decodes
 * the `ErrorEnvelope` the API sent, so every failure this client already classifies keeps
 * classifying, and a 401 arrives at the browser as a 401 with the contract's own
 * `authentication_required` envelope rather than as something this file invented.
 *
 * **Headers are allowlists in both directions, not denylists.** Inbound, an `Authorization`
 * the browser supplies is *dropped* and then the deployment's is set — never merged — so a
 * caller can neither substitute a credential of its own nor strip the real one. Outbound,
 * only the three headers PC-01 reads survive, so no upstream header is republished by
 * accident.
 *
 * **The path is rebuilt from segments, never concatenated from a string.** An open
 * forwarder's characteristic defect is that `/bff/v1/../../admin` or an absolute URL in
 * the tail reaches something the caller was not offered. Each segment is checked and
 * re-encoded, so the only thing reachable through here is a path under the API base.
 */

import type { ErrorEnvelope } from './generated/types.gen';
import type { FetchLike } from './transport';

/** The base path the browser calls. Same-origin and relative: `T-2` keeps one origin. */
export const BFF_BASE_PATH = '/bff/v1';

/**
 * Request headers forwarded to the API, lowercased. Everything else is dropped, including
 * `cookie`, `authorization`, `host` and every `x-forwarded-*` the proxy added.
 */
export const FORWARDED_REQUEST_HEADERS = [
  'accept',
  'content-type',
  'idempotency-key',
  'x-correlation-id',
] as const;

/**
 * Response headers returned to the browser, lowercased.
 *
 * `x-correlation-id` because `transport.ts` reads it off every response;
 * `content-disposition` because `exportRunCsv` and the evidence stream are downloads and
 * the filename is on that header. `content-length` is deliberately absent: the body is
 * streamed through, so the runtime frames it.
 */
export const FORWARDED_RESPONSE_HEADERS = [
  'content-type',
  'content-disposition',
  'x-correlation-id',
] as const;

/** Statuses that must carry no body, per RFC 9110. */
const BODYLESS_STATUSES: ReadonlySet<number> = new Set([204, 205, 304]);

const METHODS_WITH_BODY: ReadonlySet<string> = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export interface ForwardTarget {
  /** Absolute origin and optional base path, no trailing slash. */
  readonly upstream: string;
  /** The deployment's bearer credential. Presented, never logged, never returned. */
  readonly token: string;
}

export interface ForwardOptions {
  /** Overrides the fetch implementation. For tests and for nothing else. */
  readonly fetch?: FetchLike;
}

/** Raised when the caller's path segments cannot form a legal upstream path. */
export class ForwardPathError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ForwardPathError';
  }
}

/**
 * A correlation id for an envelope this module has to synthesise. Matches the contract's
 * `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$` and is marked `web-` so an operator reading a log
 * can tell at a glance that the API never saw the request.
 */
export function mintForwardCorrelationId(): string {
  return `web-${globalThis.crypto.randomUUID().replace(/-/g, '')}`;
}

/**
 * Build the upstream path from catch-all segments.
 *
 * @throws {ForwardPathError} on an empty segment, a dot segment, or a separator inside
 * one — the three ways a tail escapes the base it was supposed to stay under.
 */
export function buildUpstreamPath(segments: readonly string[]): string {
  if (segments.length === 0) {
    throw new ForwardPathError('Для пересылки нужен хотя бы один сегмент пути.');
  }
  for (const segment of segments) {
    if (segment.length === 0) {
      throw new ForwardPathError('Пустой сегмент пути путём не является.');
    }
    if (segment === '.' || segment === '..') {
      throw new ForwardPathError(
        `Сегмент «${segment}» вывел бы за пределы базового пути API. Ничего выше него здесь не предлагается.`,
      );
    }
    if (segment.includes('/') || segment.includes('\\')) {
      throw new ForwardPathError(
        'Разделитель пути внутри одного сегмента — не тот путь, который строит этот пересылающий слой.',
      );
    }
  }
  return `/${segments.map((segment) => encodeURIComponent(segment)).join('/')}`;
}

/** An `ErrorEnvelope` this module produces when the API never answered. */
export function synthesizedEnvelope(
  errorCode: ErrorEnvelope['error_code'],
  message: string,
  retryable: boolean,
  correlationId: string,
): ErrorEnvelope {
  return {
    contract_version: '1.0.0-draft.1',
    correlation_id: correlationId,
    error_code: errorCode,
    message,
    retryable,
  };
}

/** A JSON `ErrorEnvelope` response carrying the correlation id on the header too. */
export function envelopeResponse(status: number, envelope: ErrorEnvelope): Response {
  return new Response(JSON.stringify(envelope), {
    status,
    headers: {
      'content-type': 'application/json',
      'x-correlation-id': envelope.correlation_id,
    },
  });
}

function selectRequestHeaders(source: Headers, token: string): Headers {
  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = source.get(name);
    if (value === null) continue;
    headers.set(name, value);
  }
  // Set last and unconditionally: the deployment's credential is the only one that goes.
  headers.set('authorization', `Bearer ${token}`);
  return headers;
}

function selectResponseHeaders(source: Headers): Headers {
  const headers = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = source.get(name);
    if (value === null) continue;
    headers.set(name, value);
  }
  return headers;
}

function resolveFetch(options: ForwardOptions | undefined): FetchLike {
  if (options?.fetch !== undefined) return options.fetch;
  return (input, init) => globalThis.fetch(input, init);
}

/**
 * Forward one request to the API with the deployment's credential.
 *
 * Never throws for a transport failure: the browser gets an `ErrorEnvelope` either way,
 * because a route handler that threw would hand Next's HTML error page to a client whose
 * only decoder is `isErrorEnvelope`.
 */
export async function forwardWithCredential(
  request: Request,
  segments: readonly string[],
  target: ForwardTarget,
  options?: ForwardOptions,
): Promise<Response> {
  let path: string;
  try {
    path = buildUpstreamPath(segments);
  } catch (cause) {
    return envelopeResponse(
      404,
      synthesizedEnvelope(
        'not_found',
        cause instanceof Error ? cause.message : 'Это не тот путь, который строит этот пересылающий слой.',
        false,
        request.headers.get('x-correlation-id') ?? mintForwardCorrelationId(),
      ),
    );
  }

  const search = new URL(request.url).search;
  const headers = selectRequestHeaders(request.headers, target.token);

  const init: RequestInit = { method: request.method, headers };
  if (METHODS_WITH_BODY.has(request.method)) {
    const body = await request.arrayBuffer();
    // Buffered rather than streamed: a Node stream body needs `duplex: 'half'`, and the
    // largest thing on this surface is a 25 MiB PDF the proxy already caps at 32m.
    if (body.byteLength > 0) init.body = body;
  }

  let upstream: Response;
  try {
    upstream = await resolveFetch(options)(`${target.upstream}${path}${search}`, init);
  } catch {
    return envelopeResponse(
      503,
      synthesizedEnvelope(
        'dependency_unavailable',
        'Веб-сервер не смог связаться с API. Ничего не применено, запрос можно повторить.',
        true,
        request.headers.get('x-correlation-id') ?? mintForwardCorrelationId(),
      ),
    );
  }

  const responseHeaders = selectResponseHeaders(upstream.headers);
  const body = BODYLESS_STATUSES.has(upstream.status) ? null : upstream.body;
  return new Response(body, { status: upstream.status, headers: responseHeaders });
}
