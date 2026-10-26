/**
 * Configuration that exists **only** on the Next server, and the reason it is a separate
 * module from `env.ts`.
 *
 * `env.ts` holds the two `NEXT_PUBLIC_*` values and says why they may be there: Next
 * inlines every `NEXT_PUBLIC_*` reference into the browser bundle at build time, so
 * anything read through that prefix is public by construction. A deployment secret
 * cannot be public, so it cannot be a `NEXT_PUBLIC_*` name, so it cannot be read by
 * `env.ts` — and a module that reads one must never be reachable from a client component.
 *
 * **The signing key is no longer handed to this process** (`HARDEN-01`,
 * `EXPOSURE-REVIEW-02` `F-03`). `AUDITMANAGER_API_TOKEN` is the key the API signs every
 * user credential with; whoever holds it mints a credential for any known account. Until
 * `HARDEN-01` the compose file gave it to the web container as well, under the belief that
 * the web tier forwards it. No module forwards it: the BFF presents a session's own
 * credential (`credentialed-forward.ts`: "a session's, never the deployment's signing
 * key") and sends none at all for a request without a session. So the web container, which
 * an internet visitor reaches first, no longer holds it. `getApiToken` and
 * `hasServerCredential` below have no caller and, in a deployed container, nothing to
 * read — `getApiToken` throws there, on purpose. They and the name stay for one reason:
 * the guard keeps the NAME out of the browser bundle on a developer machine whose
 * `web/.env` still sets it, and fails the day a module starts to call them
 * (`tests/integration/composition/test_web_service_holds_no_signing_key.py` does the same
 * from the deployment side). Removing them is a follow-up that also retires their two unit
 * tests; it is not needed for the key to be out of the container.
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
 * The deployment's signing key, by the name the API reads it under. Since `HARDEN-01` the
 * deployment hands it to the API container only (see the note at the top); the name is kept
 * so the guard can keep it out of the browser bundle and out of every module but this one.
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
 * The deployment's signing key — **not available in a deployed container, and no module may
 * call this** (`HARDEN-01`, `F-03`; see the note at the top). It is the key that signs every
 * user credential, the compose file no longer hands it to the web service, and the BFF
 * authenticates with a session's own credential. Fail-closed all the same: where the
 * variable is set (a developer's `next dev`) it is returned trimmed, where it is not it
 * throws rather than defaulting.
 *
 * @throws {MissingConfigurationError} when unset or blank.
 */
export function getApiToken(): string {
  const raw = process.env.AUDITMANAGER_API_TOKEN;
  if (raw === undefined || raw.trim().length === 0) {
    throw new MissingConfigurationError(
      API_TOKEN_VARIABLE,
      'The deployment does not give the signing key to the web tier (HARDEN-01): the API ' +
        'container holds it and the BFF presents a session credential instead. Nothing ' +
        'under web/src may call this function.',
    );
  }
  return raw.trim();
}

/**
 * True when both server-side values are present. For a diagnostic, never for a fallback.
 * Like {@link getApiToken}, it has no caller; the token half is true only where a developer
 * set it.
 */
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
