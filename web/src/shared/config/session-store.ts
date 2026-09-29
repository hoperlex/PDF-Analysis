/**
 * Where the session register persists, and why the answer is a configured path.
 *
 * `R-51`. Until wave 47 the register was a `Map` on `globalThis` and nothing else, so a
 * web-container restart signed every reviewer out — on **every deploy**, because
 * `infra/deploy/deploy.sh` recreates that container. The owner ruled a named docker volume,
 * mounted by the web container and by nothing else, over the two alternatives (a database
 * connection for the web tier, or a new contract operation).
 *
 * This module is here, and not beside the register, for one reason: `shared/config` is the
 * only place in `web/` that reads `process.env`, so that an environment lookup does not get
 * scattered through a slice and a localhost default does not get reintroduced one file at a
 * time. It is deliberately **not** re-exported from `shared/config/index.ts`, for
 * `server-env.ts`'s reason: the barrel is imported by client components, and a filesystem
 * path has no business in a browser bundle even though it is not a secret.
 *
 * **An unset value is a real configuration and not an error.** A developer running
 * `next dev`, and every test in this suite, has no volume and wants none; what they get is
 * the register this tier has always had, in memory, ending with the process. The deployed
 * stack sets the name, and `infra/deploy/compose.server.yml` is where it is set. The
 * difference is reported by the register the first time it matters rather than assumed
 * either way — see `app/bff/session/store.ts`.
 */

/** The name the deployed web container sets. Server-only: no `NEXT_PUBLIC_` prefix. */
export const SESSION_STORE_VARIABLE = 'AUDITMANAGER_SESSION_STORE';

/**
 * The file the register persists to, or `null` when this deployment keeps sessions in
 * memory only.
 *
 * A blank value reads as unset rather than as the path `''`: an empty environment variable
 * is how a compose file says "I did not set this", and treating it as a filename would
 * produce an error about a path nobody typed.
 */
export function getSessionStorePath(): string | null {
  const raw = process.env.AUDITMANAGER_SESSION_STORE;
  if (raw === undefined || raw.trim().length === 0) return null;
  return raw.trim();
}
