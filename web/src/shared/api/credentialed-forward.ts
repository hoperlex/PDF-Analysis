/**
 * The credentialed forward: the second — and last — place in `web/` that makes an HTTP
 * request, and the only one that ever attaches `Authorization`.
 *
 * It runs on the Next **server**, called by `src/app/bff/v1/[...path]/route.ts`. The
 * browser calls the Next server at `/bff/v1/...`; this forwards to the API with the
 * credential the caller names — a session's, or none for an operation the contract leaves
 * open — and returns the upstream answer unchanged. The token is
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
 * the browser supplies is *dropped* and then the caller's chosen one is set — never merged — so
 * a browser can neither substitute a credential of its own nor strip the real one; a `null`
 * credential sends no header at all. Outbound,
 * only the headers PC-01 reads survive, so no upstream header is republished by
 * accident.
 *
 * **One byte range passes up, and its answer passes down** (`W55A-CONTENT-01`, plan §A3.5).
 * The viewer's `<object>#page=N` lets the browser's own PDF reader ask for a window of a
 * large document; `range` goes up, and `content-range`, `content-length` and
 * `accept-ranges` come back with the API's `206`, so the reader can page through it rather
 * than download it whole.
 *
 * **A body that can be large is streamed, never held** (`W55B-STREAM-01`, plan §B3.2). An upload
 * is a portal bundle of up to 250 MiB, and `await request.arrayBuffer()` would put all of it in
 * this process's heap, twice. A `multipart/form-data` body, and any body its request declares
 * larger than `STREAM_FROM_BYTES`, is handed to `fetch` as the request's own stream with
 * `duplex: 'half'`: bytes reach the API as they arrive from the browser and nothing here reads
 * them. Every other body is a small JSON or form document and is read whole, as it always was.
 * No `undici` `Agent` is configured: that would be a second transport to keep correct, and the
 * deadline below can only *shorten* undici's own 300 s wait. **Streaming needs one more thing
 * than the stream** (`W55B-FIX`): `redirect: 'error'` and `window: null`, without which `fetch`
 * clones the request and tees the body, and the clone's branch keeps every byte (see
 * `forwardWithCredential`).
 *
 * **A request that sends a body carries a deadline of 290 s** (`UPSTREAM_DEADLINE_MS`), because
 * the chain of timeouts is meant to be strictly nested, outermost first: the proxy waits 300 s
 * for this server (`proxy_read_timeout` in `infra/deploy/proxy/nginx.conf`), this server gives up
 * on the API at 290 s, and the API answers an accepted 250 MiB upload within about 240 s
 * (measured, `docs/program/W55B-STREAM-01.md`). The deadline is not put on a read: a document
 * download may legitimately run for as long as the reader takes to fetch it. Whatever aborts the
 * browser's own request aborts the upstream one too, so an upload the user cancelled stops
 * holding one of the API's two upload slots.
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
  'range',
  'x-correlation-id',
  'x-archive-name',
] as const;

/**
 * Response headers returned to the browser, lowercased.
 *
 * `x-correlation-id` because `transport.ts` reads it off every response;
 * `content-disposition` because `exportRunCsv` and the evidence stream are downloads and
 * the filename is on that header; `content-range` and `accept-ranges` because a PDF reader
 * pages a document by them (`W55A-CONTENT-01`).
 *
 * `etag` and `cache-control` because a portal block's crop is an image the browser keeps in its
 * own HTTP cache (`W55B-FIX`, X-4: the API sends them only on that answer); `retry-after`
 * because the upload gate's busy refusal says when to send the same upload again
 * (`upload-failure.ts` reads it, `W55B-QA-01` O-1).
 *
 * `content-length` is forwarded too, so a reader knows the size before the body ends and a
 * stream the API stops short (the R-115 integrity rule) arrives short of what it declared
 * rather than looking complete. It is the one header with a condition: the fetch runtime
 * decodes a `content-encoding` it does not republish, and after decoding the upstream
 * length no longer describes the body, so it is dropped whenever one was applied.
 */
export const FORWARDED_RESPONSE_HEADERS = [
  'content-type',
  'content-disposition',
  'content-length',
  'content-range',
  'accept-ranges',
  'etag',
  'cache-control',
  'retry-after',
  'x-correlation-id',
] as const;

/** Statuses that must carry no body, per RFC 9110. */
const BODYLESS_STATUSES: ReadonlySet<number> = new Set([204, 205, 304]);

const METHODS_WITH_BODY: ReadonlySet<string> = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

/**
 * How long a request that streams a body may take before this server stops waiting for the
 * API: 290 s, ten seconds inside nginx's `proxy_read_timeout 300s` so the answer a caller
 * reads is this server's envelope and not the proxy's HTML 504.
 */
export const UPSTREAM_DEADLINE_MS = 290_000;

/**
 * A body larger than this, as its request declares it, is streamed rather than read whole; so
 * is every `multipart/form-data` body, whatever it declares. The sign-in, the profile and the
 * other JSON writes are far below it.
 */
export const STREAM_FROM_BYTES = 1024 * 1024;

/** `RequestInit` has no `duplex` in the DOM typings; Node's fetch requires it for a stream. */
type StreamingRequestInit = RequestInit & { duplex?: 'half' };

function mustStream(request: Request): boolean {
  const type = (request.headers.get('content-type') ?? '').trim().toLowerCase();
  if (type.startsWith('multipart/form-data') || type.startsWith('application/zip')) return true;
  return Number(request.headers.get('content-length') ?? 0) > STREAM_FROM_BYTES;
}

export interface ForwardTarget {
  /** Absolute origin and optional base path, no trailing slash. */
  readonly upstream: string;
  /**
   * The bearer credential to present — a session's, never the deployment's signing key — or
   * `null` for one of the contract's operations with an empty security requirement
   * (`issueToken`, `submitRegistration`, `readRegistrationStatus`), which is then sent with
   * **no** `Authorization` header at all (`W53-CLOSE` `C-17`). Presented, never logged,
   * never returned.
   */
  readonly token: string | null;
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
    contract_version: '1.14.0',
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

function selectRequestHeaders(source: Headers, token: string | null): Headers {
  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = source.get(name);
    if (value === null) continue;
    headers.set(name, value);
  }
  // Set last: the caller's chosen credential is the only one that goes, and with `null` none
  // does. `authorization` is not in the inbound allowlist, so a browser's own header is never
  // carried in either case.
  if (token !== null) headers.set('authorization', `Bearer ${token}`);
  return headers;
}

function selectResponseHeaders(source: Headers, bodyless: boolean): Headers {
  const encoded = (source.get('content-encoding') ?? 'identity').trim().toLowerCase() !== 'identity';
  const headers = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = source.get(name);
    if (value === null) continue;
    if (name === 'content-length' && (encoded || bodyless)) continue;
    headers.set(name, value);
  }
  return headers;
}

function resolveFetch(options: ForwardOptions | undefined): FetchLike {
  if (options?.fetch !== undefined) return options.fetch;
  return (input, init) => globalThis.fetch(input, init);
}

/**
 * Forward one request to the API with the caller's chosen credential, or with none.
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

  const init: StreamingRequestInit = { method: request.method, headers };
  if (METHODS_WITH_BODY.has(request.method) && request.body !== null) {
    if (mustStream(request)) {
      // Streamed: the request's own stream goes to `fetch` untouched.
      init.body = request.body;
      init.duplex = 'half';
      // `W55B-FIX`: and it must not be teed. The fetch standard clones the request -- and so
      // tees its body, keeping one branch for a redirect it might have to follow -- unless the
      // request has no window and refuses redirects; undici does exactly that, and the branch
      // nobody reads held the whole upload (`W55B-REHEARSAL-01`: +231 to +242 MiB of the
      // BFF's resident set for a 210 MiB bundle). The API never redirects an upload, so a
      // redirect is refused here rather than followed with a body that is already gone.
      init.redirect = 'error';
      init.window = null;
    } else {
      const body = await request.arrayBuffer();
      if (body.byteLength > 0) init.body = body;
    }
  }
  // The deadline belongs to a request that sends a body; a read has none (see the header note).
  const sendsBody = init.body !== undefined;
  if (sendsBody) {
    const uploadPath = /^\/bff\/v1\/projects\/[^/]+\/(?:documents(?:\/[^/]+\/versions)?|comparison-zip-uploads)$/.test(new URL(request.url).pathname);
    init.signal = AbortSignal.any([request.signal, AbortSignal.timeout(uploadPath ? 86_400_000 : UPSTREAM_DEADLINE_MS)]);
  }

  let upstream: Response;
  try {
    upstream = await resolveFetch(options)(`${target.upstream}${path}${search}`, init);
  } catch (cause) {
    const correlationId = request.headers.get('x-correlation-id') ?? mintForwardCorrelationId();
    if (sendsBody && cause instanceof Error && cause.name === 'TimeoutError') {
      // The deadline passed with the API still working. Unlike an unreachable API this does
      // NOT mean nothing was applied: the write may yet land. Sending the same request again
      // with the same `Idempotency-Key` is safe either way -- it replays or it applies once --
      // and the message says so rather than claiming otherwise.
      return envelopeResponse(
        503,
        synthesizedEnvelope(
          'dependency_unavailable',
          'API не ответил за отведённое время. Запрос мог быть выполнен: отправьте его ещё раз с тем же ключом идемпотентности.',
          true,
          correlationId,
        ),
      );
    }
    return envelopeResponse(
      503,
      synthesizedEnvelope(
        'dependency_unavailable',
        'Веб-сервер не смог связаться с API. Ничего не применено, запрос можно повторить.',
        true,
        correlationId,
      ),
    );
  }

  const bodyless = BODYLESS_STATUSES.has(upstream.status);
  const responseHeaders = selectResponseHeaders(upstream.headers, bodyless);
  const body = bodyless ? null : upstream.body;
  return new Response(body, { status: upstream.status, headers: responseHeaders });
}
