/**
 * Configuration that exists **only** on the Next server, and the reason it is a separate
 * module from `env.ts`.
 *
 * `env.ts` holds the two `NEXT_PUBLIC_*` values and says why they may be there: Next
 * inlines every `NEXT_PUBLIC_*` reference into the browser bundle at build time, so
 * anything read through that prefix is public by construction. The deployment credential
 * cannot be public, so it cannot be a `NEXT_PUBLIC_*` name, so it cannot be read by
 * `env.ts` — and a module that reads it must never be reachable from a client component.
 *
 * Two mechanisms keep that true, and neither is a comment:
 *
 * 1. **The names have no `NEXT_PUBLIC_` prefix.** Next replaces `process.env.X` in client
 *    code only for `X` beginning `NEXT_PUBLIC_`; every other `process.env.X` in a module
 *    that reaches the client compiles to a lookup on an empty object, so the value is
 *    absent from the bundle rather than present and wrong.
 * 2. **Nothing imports this module except `src/app/bff/**`,** the route handlers that run
 *    in the Node process. It is deliberately *not* re-exported from `shared/config/index.ts`:
 *    the barrel is imported by client code, and a barrel that re-exported this would put
 *    the module in the client graph even where the binding is never called.
 *
 * `web/tests/guards/server-credential.guard.test.ts` asserts both, and asserts that the
 * literal names below carry no `NEXT_PUBLIC_` prefix.
 */

import { MissingConfigurationError } from './env';

/**
 * The absolute origin (and optional base path) of the API, as the Next **server** reaches
 * it. In the alpha stack that is `http://api:8000` over the compose network — a name that
 * does not resolve in a browser and never needs to.
 */
export const API_UPSTREAM_VARIABLE = 'AUDITMANAGER_API_UPSTREAM';

/**
 * The bearer credential `T-6` requires. The same name the API container reads, because it
 * is the same secret: the deployment hands one value to two processes.
 */
export const API_TOKEN_VARIABLE = 'AUDITMANAGER_API_TOKEN';

/** Pinned as data so a guard can assert neither name is a `NEXT_PUBLIC_*` one. */
export const SERVER_ONLY_VARIABLES = [API_UPSTREAM_VARIABLE, API_TOKEN_VARIABLE] as const;

/**
 * Reject a relative or non-HTTP upstream.
 *
 * A relative value is the interesting failure: `fetch('/projects')` inside the Next
 * server resolves against the server's own origin, so the route handler would forward to
 * itself and recurse until something ran out. Refusing at read time turns that into one
 * explicit message instead of a hang.
 */
function requireAbsoluteHttpUrl(raw: string, variable: string): string {
  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new MissingConfigurationError(
      variable,
      'It must be an absolute http(s) URL such as `http://api:8000`, not a path. A ' +
        'relative value would make the server forward to itself.',
    );
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new MissingConfigurationError(
      variable,
      `It must be an http or https URL; '${parsed.protocol}' is not a transport this ` +
        'forwarder speaks.',
    );
  }
  return raw.trim().replace(/\/+$/, '');
}

/**
 * The API base the server forwards to, with any trailing slash removed.
 *
 * @throws {MissingConfigurationError} when unset, blank, or not an absolute http(s) URL.
 */
export function getApiUpstreamUrl(): string {
  const raw = process.env.AUDITMANAGER_API_UPSTREAM;
  if (raw === undefined || raw.trim().length === 0) {
    throw new MissingConfigurationError(
      API_UPSTREAM_VARIABLE,
      'The web server forwards every API call and needs the absolute origin it forwards ' +
        'to, e.g. `http://api:8000`. There is no default: a guessed one would point at ' +
        'nothing and report it as an outage.',
    );
  }
  return requireAbsoluteHttpUrl(raw.trim(), API_UPSTREAM_VARIABLE);
}

/**
 * The bearer credential.
 *
 * @throws {MissingConfigurationError} when unset or blank. Fail-closed, matching the API:
 * `W13_CLOSURE.md` section 7 makes the seam refuse rather than default, and a web tier
 * that forwarded uncredentialed requests instead would turn one clear refusal into twelve
 * confusing ones.
 */
export function getApiToken(): string {
  const raw = process.env.AUDITMANAGER_API_TOKEN;
  if (raw === undefined || raw.trim().length === 0) {
    throw new MissingConfigurationError(
      API_TOKEN_VARIABLE,
      'The deployment holds one bearer credential and hands it to both the API container ' +
        'and this one. See infra/deploy/env/alpha.env.example.',
    );
  }
  return raw.trim();
}

/** True when both server-side values are present. For a diagnostic, never for a fallback. */
export function hasServerCredential(): boolean {
  const token = process.env.AUDITMANAGER_API_TOKEN;
  const upstream = process.env.AUDITMANAGER_API_UPSTREAM;
  return (
    token !== undefined &&
    token.trim().length > 0 &&
    upstream !== undefined &&
    upstream.trim().length > 0
  );
}
