/**
 * `/bff/v1/*` — the route handler that holds `T-6`'s credential.
 *
 * The browser calls this, on the same origin it was served from; this calls the API with
 * `Authorization: Bearer <token>`. The token is read here, in the Node process, and is
 * never a `NEXT_PUBLIC_*` value, so it is not in the browser bundle and cannot be.
 *
 * **Why the path is `/bff/v1` and not `/api/v1`.** `infra/deploy/proxy/nginx.conf` sends
 * `/api/v1/` straight to the API container; only `location /` reaches Next. So a handler
 * mounted at `/api/v1` would never be called, and moving that `location` would be an
 * nginx change this session does not own. `/bff/v1` falls under `location /` and reaches
 * the Next server through the proxy wave 14 already deployed, unchanged.
 *
 * **Why every operation and not a route per operation.** `T-6` says the same twelve
 * operations must keep working when the alpha's static token is replaced by a real
 * issuer. A catch-all forwards the contract rather than restating it: the twelve paths,
 * their methods, their idempotency keys and their error envelopes are decided by
 * `contracts/api/v1/openapi.json` and the generated client, and nothing here knows how
 * many operations there are. Swapping the credential later is an edit to
 * `getApiToken()`'s two lines, not to twelve handlers.
 *
 * This file is deliberately thin. The forwarding rules — the two header allowlists, the
 * path-segment check, the verbatim status and body — are in
 * `@/shared/api/credentialed-forward`, where they are unit-testable without a server.
 */

import { getApiToken, getApiUpstreamUrl } from '@/shared/config/server-env';
import {
  envelopeResponse,
  forwardWithCredential,
  mintForwardCorrelationId,
  synthesizedEnvelope,
} from '@/shared/api/credentialed-forward';

/**
 * Node, not edge. The forward uses the platform HTTP client and the configuration read is
 * an environment lookup, and both want the Node runtime.
 */
export const runtime = 'nodejs';

/** Nothing here is cacheable: every response depends on a credential and a request body. */
export const dynamic = 'force-dynamic';

interface RouteContext {
  /** Next 15 hands route params as a promise. */
  readonly params: Promise<{ readonly path?: string[] }>;
}

/**
 * A deployment with no credential answers exactly what the API answers when it is handed
 * none: `401 authentication_required`.
 *
 * This is the fail-closed half, and it is the honest code rather than a convenient one.
 * The request genuinely was not authenticated — no credential was presented, because this
 * process has none to present — and the operator sees the 401 state the UI now has, which
 * says the deployment is unconfigured. Answering `500` would blame the API; answering
 * `200` is not available; inventing a thirteenth code would put something outside the
 * closed catalog on the wire.
 */
function unconfigured(request: Request): Response {
  return envelopeResponse(
    401,
    synthesizedEnvelope(
      'authentication_required',
      'This deployment presented no credential to the API, because none is configured for ' +
        'its web tier. No request was sent.',
      false,
      request.headers.get('x-correlation-id') ?? mintForwardCorrelationId(),
    ),
  );
}

async function handle(request: Request, context: RouteContext): Promise<Response> {
  const { path } = await context.params;

  let upstream: string;
  let token: string;
  try {
    upstream = getApiUpstreamUrl();
    token = getApiToken();
  } catch {
    // The message is deliberately not forwarded: `MissingConfigurationError` names an
    // environment variable, and a variable name on a public response is a hint about the
    // deployment that nothing outside needs.
    return unconfigured(request);
  }

  return forwardWithCredential(request, path ?? [], { upstream, token });
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const HEAD = handle;
