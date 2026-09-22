/**
 * The register of open sessions, and the only place in `web/` that holds a user's
 * credential.
 *
 * ## Why the credential stays here and not in the browser
 *
 * `W15-AUTH` established the property this module must not break: the deployment's bearer
 * credential is read in the Node process, is never a `NEXT_PUBLIC_*` value, and is
 * therefore absent from the browser bundle by construction. `tests/guards/
 * server-credential.guard.test.ts` is the static half of that proof and the build-plus-grep
 * in `docs/program/reviews/W15-AUTH.md` is the dynamic half.
 *
 * A sign-in screen puts a *second* credential in play — the one the API mints in exchange
 * for a login and a password — and the cheap way to hold it is the wrong one. A token in
 * `localStorage`, or in a readable cookie, or in a React state that ends up serialised
 * into the RSC payload, is a token in the browser: any script on the origin can read it,
 * and it survives in a place no logout can reliably reach.
 *
 * So the token never leaves this process. What the browser receives is an **opaque
 * identifier** — 32 random bytes, hex — in an `HttpOnly` cookie, which names a row here.
 * The identifier authorises nothing at the API: it is a key to a map that only the Node
 * process can read. That is what makes `closeSession` a real logout rather than a cosmetic
 * one: the row is deleted, and the cookie the browser keeps is a key to nothing.
 *
 * ## Where the map lives
 *
 * On `globalThis`, under a `Symbol.for` key, rather than in a module-scope `const`.
 *
 * Next compiles route handlers and server components into separate module graphs, so two
 * copies of this module can exist in one process and a module-scope `Map` would let the
 * route handler open a session the page cannot see. The symbol registry is process-wide
 * and is the same object from both graphs. This is deliberate and is the only reason the
 * indirection is here.
 *
 * ## What this module is not
 *
 * It is **memory**, and the limitation is stated rather than hidden: a restart of the web
 * process ends every session, and two web replicas do not share one. For the alpha — one
 * container, one reviewer — that costs a re-entry after a deploy. Anything more durable is
 * a store this tier does not have, and inventing one (a signed token in the cookie, a file
 * beside the process) would move the credential back out of this process, which is the one
 * thing this module exists to prevent.
 */

/** The cookie that carries the opaque identifier. Never the credential itself. */
export const SESSION_COOKIE = 'am_session';

/** The identifier's shape: 32 random bytes as lowercase hex. */
export const SESSION_ID_PATTERN = /^[0-9a-f]{64}$/;

/**
 * Bounds on a lifetime this tier will accept from the API's `expires_in`.
 *
 * Neither is a default. A value outside them is refused, because a session whose lifetime
 * this tier had to guess is a session nobody can reason about — and `AGENTS.md` §4 forbids
 * the silent fallback that guessing would be.
 */
export const MIN_LIFETIME_SECONDS = 30;
export const MAX_LIFETIME_SECONDS = 12 * 60 * 60;

/** What a screen may learn about the open session. Deliberately no credential. */
export interface SessionSubject {
  readonly login: string;
  readonly openedAt: number;
  readonly expiresAt: number;
}

/** The row. `credential` leaves this module only through `credentialOf`. */
interface HeldSession extends SessionSubject {
  readonly credential: string;
}

const REGISTRY_KEY = Symbol.for('auditmanager.web.session-register');

function register(): Map<string, HeldSession> {
  const host = globalThis as unknown as Record<symbol, Map<string, HeldSession> | undefined>;
  const existing = host[REGISTRY_KEY];
  if (existing !== undefined) return existing;
  const created = new Map<string, HeldSession>();
  host[REGISTRY_KEY] = created;
  return created;
}

/** Raised when the API's `expires_in` is not a lifetime this tier will hold. */
export class SessionLifetimeError extends Error {
  constructor(seconds: unknown) {
    super(
      `The exchange answered with a lifetime of ${String(seconds)} seconds, which is outside ` +
        `the ${MIN_LIFETIME_SECONDS}..${MAX_LIFETIME_SECONDS} second band this tier holds.`,
    );
    this.name = 'SessionLifetimeError';
  }
}

/** 32 bytes of CSPRNG output as hex. Unguessable, and carrying no information. */
export function mintSessionId(): string {
  const bytes = new Uint8Array(32);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

/** Drop every row that has expired. Called on each read, so nothing lingers. */
function sweep(now: number): void {
  const rows = register();
  for (const [id, row] of rows) {
    if (row.expiresAt <= now) rows.delete(id);
  }
}

/**
 * Record an exchanged credential and return the identifier the cookie will carry.
 *
 * @throws {SessionLifetimeError} when the lifetime is not a finite number of seconds
 * inside the accepted band.
 */
export function openSession(
  login: string,
  credential: string,
  lifetimeSeconds: number,
  now: number = Date.now(),
): string {
  if (
    !Number.isFinite(lifetimeSeconds) ||
    lifetimeSeconds < MIN_LIFETIME_SECONDS ||
    lifetimeSeconds > MAX_LIFETIME_SECONDS
  ) {
    throw new SessionLifetimeError(lifetimeSeconds);
  }
  if (credential.trim().length === 0) {
    throw new SessionLifetimeError('an empty credential');
  }
  sweep(now);
  const id = mintSessionId();
  register().set(id, {
    login,
    credential,
    openedAt: now,
    expiresAt: now + Math.floor(lifetimeSeconds) * 1000,
  });
  return id;
}

/**
 * What the screen may show about the session: who, since when, until when.
 *
 * Returns `null` for an unknown, malformed or expired identifier — the three cases a
 * screen treats identically, because all three mean "there is no session here".
 */
export function subjectOf(id: string | null, now: number = Date.now()): SessionSubject | null {
  if (id === null || !SESSION_ID_PATTERN.test(id)) return null;
  sweep(now);
  const row = register().get(id);
  if (row === undefined) return null;
  return { login: row.login, openedAt: row.openedAt, expiresAt: row.expiresAt };
}

/**
 * The credential to present upstream for this session, or `null` when there is none.
 *
 * The **only** exit the credential has. The forwarder calls it; nothing rendered ever does.
 */
export function credentialOf(id: string | null, now: number = Date.now()): string | null {
  if (id === null || !SESSION_ID_PATTERN.test(id)) return null;
  sweep(now);
  return register().get(id)?.credential ?? null;
}

/** Forget the session. True when there was one to forget. */
export function closeSession(id: string | null): boolean {
  if (id === null || !SESSION_ID_PATTERN.test(id)) return false;
  return register().delete(id);
}

/** How many sessions are open. For a diagnostic and for a test, never for a decision. */
export function openSessionCount(now: number = Date.now()): number {
  sweep(now);
  return register().size;
}

/** Empty the register. For tests, and for nothing else. */
export function forgetEverySession(): void {
  register().clear();
}

/**
 * The identifier the request's `Cookie` header carries, or `null`.
 *
 * Parsed rather than trusted: a value that is not the minted shape is treated as absent,
 * so nothing outside `SESSION_ID_PATTERN` ever reaches the register as a key.
 */
export function readSessionId(cookieHeader: string | null): string | null {
  if (cookieHeader === null) return null;
  for (const pair of cookieHeader.split(';')) {
    const index = pair.indexOf('=');
    if (index < 0) continue;
    if (pair.slice(0, index).trim() !== SESSION_COOKIE) continue;
    const value = pair.slice(index + 1).trim();
    return SESSION_ID_PATTERN.test(value) ? value : null;
  }
  return null;
}

/**
 * The `Set-Cookie` value that puts the identifier in the browser.
 *
 * `HttpOnly` so no script on the origin can read it; `SameSite=Strict` so no other site
 * can cause a credentialed request with it; `Path=/` because both the screens and the
 * forwarder are under the one origin; `Max-Age` so the browser forgets it no later than
 * the register does. `Secure` is decided by the caller from the proxy's own header rather
 * than assumed: the alpha's nginx terminates TLS and speaks plain HTTP to this process, so
 * setting it unconditionally would make sign-in impossible on a plain-HTTP stand, and
 * setting it never would let the cookie travel in clear on a TLS one.
 */
export function sessionCookie(id: string, lifetimeSeconds: number, secure: boolean): string {
  const attributes = [
    `${SESSION_COOKIE}=${id}`,
    'Path=/',
    'HttpOnly',
    'SameSite=Strict',
    `Max-Age=${Math.floor(lifetimeSeconds)}`,
  ];
  if (secure) attributes.push('Secure');
  return attributes.join('; ');
}

/** The `Set-Cookie` value that removes it. Same attributes, no lifetime. */
export function clearedSessionCookie(secure: boolean): string {
  const attributes = [`${SESSION_COOKIE}=`, 'Path=/', 'HttpOnly', 'SameSite=Strict', 'Max-Age=0'];
  if (secure) attributes.push('Secure');
  return attributes.join('; ');
}

/** True when the browser reached this process over TLS, as the proxy reports it. */
export function requestIsSecure(request: Request): boolean {
  const forwarded = request.headers.get('x-forwarded-proto');
  if (forwarded !== null) return forwarded.split(',')[0]?.trim() === 'https';
  try {
    return new URL(request.url).protocol === 'https:';
  } catch {
    return false;
  }
}
