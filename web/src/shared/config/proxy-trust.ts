/**
 * Whether this web tier sits behind the deployment's proxy, and so may believe the client
 * address the proxy writes into `X-Real-IP`.
 *
 * `W49-PLAN.md` §3.5. The guest throttle on the two public forms (`POST /bff/v1/session` and
 * `POST /bff/v1/registration`) needs a per-client key, and a Next 15 route handler is handed
 * no peer address. The one place a client address reaches this process is the header both
 * proxy configurations set from `$remote_addr` (`infra/deploy/proxy/nginx.conf`,
 * `infra/deploy/proxy/tls-server.conf`): `proxy_set_header X-Real-IP $remote_addr;`. That
 * header is only evidence when the proxy is the only thing that can reach this container,
 * which is a property of the deployment and not of the request — so it is a flag the
 * deployment sets (`W49-EDGE-01` puts it on the `web` service in
 * `infra/deploy/compose.server.yml`, which publishes no port of its own).
 *
 * **`X-Forwarded-For` is never the key, flag or no flag.** Its first element is whatever the
 * client wrote; nginx appends to it rather than replacing it. `X-Real-IP` is *set* by the
 * proxy, so a client-supplied copy is overwritten on the way in.
 *
 * This module is here, and not beside the throttle, for `session-store.ts`'s reason:
 * `shared/config` is the only place in `web/` that reads `process.env`. It is deliberately
 * **not** re-exported from `shared/config/index.ts` (the barrel is imported by client
 * components), and the name is **not** in `SERVER_ONLY_VARIABLES`: that list is the set of
 * names that must never be inlined into a bundle because they carry or locate a secret, it
 * is pinned literally in three test files, and a flag saying "a proxy is in front" is
 * neither.
 */

/** The name the deployed web container sets. Server-only: no `NEXT_PUBLIC_` prefix. */
export const BEHIND_PROXY_VARIABLE = 'AUDITMANAGER_BEHIND_PROXY';

/**
 * True exactly when the deployment says the proxy is in front: the value `1`.
 *
 * Every other value — unset, blank, `0`, and also a typo such as `true` or `yes` — reads as
 * **not** behind the proxy. That is not a silent fallback in the direction that matters:
 * without the flag every guest shares **one** bucket, which is stricter than a bucket per
 * client, never looser. A mistyped flag can only make the throttle tighter; it can never
 * make this tier believe a header a client could have written.
 */
export function isBehindProxy(): boolean {
  const raw = process.env.AUDITMANAGER_BEHIND_PROXY;
  return raw !== undefined && raw.trim() === '1';
}
