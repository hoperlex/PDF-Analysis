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
 * ## Where the map lives inside the process
 *
 * On `globalThis`, under a `Symbol.for` key, rather than in a module-scope `const`.
 *
 * Next compiles route handlers and server components into separate module graphs, so two
 * copies of this module can exist in one process and a module-scope `Map` would let the
 * route handler open a session the page cannot see. The symbol registry is process-wide
 * and is the same object from both graphs. This is deliberate and is the only reason the
 * indirection is here.
 *
 * ## What the map outlives, since `R-51`
 *
 * On a **named docker volume that only the web container mounts**, as a file, and the owner
 * ruled it over the two alternatives: giving the web tier its own database connection, and
 * growing the contract with an operation to store sessions through. Until wave 47 this
 * module was memory and nothing else, so a web-container restart signed every reviewer out
 * — on every deploy, because `infra/deploy/deploy.sh` recreates that container, not on some
 * rare crash.
 *
 * **What it costs, stated here rather than discovered later** (`R-51`'s own words): until
 * each credential expires, the API credentials sit on that volume, on the server's disk.
 * They still never reach the browser, and a revoked credential still stops working the
 * moment it is revoked, because the API checks `token_epoch` on every request wherever the
 * token was kept. The runbook, `infra/deploy/README.md`, says the same thing where an
 * operator will meet it.
 *
 * The cookie-borne alternative this module's earlier text rejected is still rejected, and
 * for the same reason: *"a signed token in the cookie ... would move the credential back
 * out of this process, which is the one thing this module exists to prevent."* A file on a
 * volume the browser cannot reach does not move it out; it keeps it in one more place the
 * same process, and only that process, can read.
 *
 * **A deployment that names no file keeps the old behaviour**, deliberately: `next dev` and
 * this suite have no volume and want none. That is a configured absence rather than a
 * silent fallback — {@link sessionDurability} reports which of the two is in force, and the
 * register says so in the log the first time it writes.
 */

import { existsSync, mkdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';

import { SESSION_STORE_VARIABLE, getSessionStorePath } from '@/shared/config/session-store';

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
  /**
   * `R-50`. Whether the account this session belongs to is still on the password the
   * deployment seeded it with.
   *
   * **Read from the API's answer and never decided here.** The exchange returns
   * `is_default_credential` on `IssueTokenResponse`; this tier records what it was told.
   * A tier that worked it out for itself — from the login, from the shape of the password
   * — would be inventing a security state, and the same state is enforced a second time by
   * the API, which refuses every operation but the exchange and the change while it holds.
   * So this field decides where a reviewer is *sent*, and never what they are *allowed*.
   */
  readonly isDefaultCredential: boolean;
}

/** The row. `credential` leaves this module only through `credentialOf`. */
interface HeldSession extends SessionSubject {
  readonly credential: string;
}

const REGISTRY_KEY = Symbol.for('auditmanager.web.session-register');

/**
 * What lives under the symbol: the rows, and whether this process has read the file yet.
 *
 * The flag is beside the rows rather than in a module-scope variable for the reason the
 * rows are: Next compiles route handlers and server components into separate module graphs,
 * so a module-scope `hydrated` would let one graph believe the file had been read while the
 * other had never opened it.
 */
interface Registry {
  readonly rows: Map<string, HeldSession>;
  hydrated: boolean;
}

/** The shape written to the volume. Versioned, so a later format is distinguishable. */
interface PersistedRegister {
  readonly version: 1;
  readonly sessions: readonly (HeldSession & { readonly id: string })[];
}

function registry(): Registry {
  const host = globalThis as unknown as Record<symbol, Registry | undefined>;
  const existing = host[REGISTRY_KEY];
  if (existing !== undefined) return existing;
  const created: Registry = { rows: new Map<string, HeldSession>(), hydrated: false };
  host[REGISTRY_KEY] = created;
  return created;
}

/**
 * Say, once per process, which of the two registers this deployment is running.
 *
 * `AGENTS.md` §4 forbids a silent fallback, and "sessions end when this container is
 * recreated" is exactly the kind of fact that is discovered in an incident rather than read
 * in a log. So it is said out loud, at the first use, whichever answer it is.
 */
let announced = false;

function announce(path: string | null): void {
  if (announced) return;
  announced = true;
  if (path === null) {
    console.warn(
      `[session-register] ${SESSION_STORE_VARIABLE} is not set: sessions are held in this ` +
        'process and end when it does. Every reviewer signs in again on the next deploy. ' +
        'The deployed stack sets it to a file on a volume only the web container mounts.',
    );
  } else {
    console.info(
      `[session-register] sessions persist to ${path}. Until each credential expires, the ` +
        'API credentials are on that volume; they still never reach the browser, and a ' +
        'revoked credential still stops working on its next request.',
    );
  }
}

/**
 * Read the file into this process, once.
 *
 * A file that is absent is an empty register and not an error: the first deploy has no file
 * and neither does a volume that has just been created. A file that cannot be read or
 * parsed is **reported and then treated as empty** — the alternative is a web tier that
 * refuses to serve anything because of one corrupt line, which turns a lost session into a
 * lost deployment. Every expired row is dropped on the way in, so a restart does not
 * resurrect a session that died while the process was down.
 */
function hydrate(now: number): void {
  const held = registry();
  if (held.hydrated) return;
  held.hydrated = true;
  const path = getSessionStorePath();
  announce(path);
  if (path === null || !existsSync(path)) return;
  try {
    const parsed = JSON.parse(readFileSync(path, 'utf8')) as PersistedRegister;
    if (parsed.version !== 1 || !Array.isArray(parsed.sessions)) {
      throw new Error(`unexpected register format: version ${String(parsed.version)}`);
    }
    for (const row of parsed.sessions) {
      if (!SESSION_ID_PATTERN.test(row.id)) continue;
      if (typeof row.credential !== 'string' || row.credential.length === 0) continue;
      if (typeof row.expiresAt !== 'number' || row.expiresAt <= now) continue;
      held.rows.set(row.id, {
        login: row.login,
        credential: row.credential,
        openedAt: row.openedAt,
        expiresAt: row.expiresAt,
        isDefaultCredential: row.isDefaultCredential === true,
      });
    }
  } catch (error) {
    console.error(
      `[session-register] ${path} could not be read (${String(error)}). Starting with no ` +
        'open sessions: every reviewer signs in again. The file is rewritten by the next ' +
        'sign-in.',
    );
  }
}

/**
 * Write the whole register out, atomically, after every change that alters it.
 *
 * The whole file and not an append: the register is a handful of rows for one reviewer, and
 * a log that had to be compacted would be a second mechanism to get wrong. Written to a
 * temporary name beside it and renamed, so a process that dies mid-write leaves the
 * previous file rather than half of this one; mode `0o600`, because what is in it is a
 * credential.
 *
 * A write that fails is **reported and not swallowed, and does not refuse the request**: the
 * session is live in this process either way, and turning a full disk into "you cannot sign
 * in" would take a deployment down for a reason the reviewer cannot act on. What the
 * operator gets is the error, named, on every attempt rather than once.
 */
function persist(): void {
  const path = getSessionStorePath();
  if (path === null) return;
  const held = registry();
  const snapshot: PersistedRegister = {
    version: 1,
    sessions: [...held.rows].map(([id, row]) => ({ id, ...row })),
  };
  const temporary = `${path}.writing-${String(process.pid)}`;
  try {
    mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
    writeFileSync(temporary, JSON.stringify(snapshot), { encoding: 'utf8', mode: 0o600 });
    renameSync(temporary, path);
  } catch (error) {
    console.error(
      `[session-register] could not write ${path} (${String(error)}). The sessions open ` +
        'now will not survive this container being recreated.',
    );
    try {
      if (existsSync(temporary)) unlinkSync(temporary);
    } catch {
      // Nothing more to do about a temporary file we could not remove, and the error above
      // is the one worth reading.
    }
  }
}

/** Which of the two registers is in force, for a diagnostic and for a test. */
export function sessionDurability(): { readonly durable: boolean; readonly path: string | null } {
  const path = getSessionStorePath();
  return { durable: path !== null, path };
}

function register(): Map<string, HeldSession> {
  return registry().rows;
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

/**
 * Drop every row that has expired. Called on each read, so nothing lingers.
 *
 * It is also where the file is read into a fresh process: every reader goes through here,
 * so a process that has just started finds the sessions the previous one left before it
 * answers "there is no session here". A row that expired while nothing was running is
 * dropped by the same pass that would have dropped it had the process stayed up.
 */
function sweep(now: number): void {
  hydrate(now);
  const rows = register();
  let removed = false;
  for (const [id, row] of rows) {
    if (row.expiresAt <= now) {
      rows.delete(id);
      removed = true;
    }
  }
  if (removed) persist();
}

/**
 * Record an exchanged credential and return the identifier the cookie will carry.
 *
 * `isDefaultCredential` is the API's own answer, passed in rather than computed: see
 * {@link SessionSubject.isDefaultCredential}. It is a required argument and not an
 * optional one with a default, because the value a caller would get by omitting it is the
 * permissive one — the reviewer walks into the application and meets a wall of refusals.
 *
 * @throws {SessionLifetimeError} when the lifetime is not a finite number of seconds
 * inside the accepted band.
 */
export function openSession(
  login: string,
  credential: string,
  lifetimeSeconds: number,
  isDefaultCredential: boolean,
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
    isDefaultCredential,
  });
  persist();
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
  return {
    login: row.login,
    openedAt: row.openedAt,
    expiresAt: row.expiresAt,
    isDefaultCredential: row.isDefaultCredential,
  };
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
  // Hydrated first, so that signing out of a session this process inherited from the
  // previous one really removes it rather than answering "there was nothing to remove".
  hydrate(Date.now());
  const forgotten = register().delete(id);
  if (forgotten) persist();
  return forgotten;
}

/** How many sessions are open. For a diagnostic and for a test, never for a decision. */
export function openSessionCount(now: number = Date.now()): number {
  sweep(now);
  return register().size;
}

/**
 * Empty the register, here **and** on the volume. For tests, and for nothing else.
 *
 * It clears the file as well as the map, because a test that emptied only the map would
 * find the rows again on the next read — which is the durability working, and would look
 * like a leak between cases.
 */
export function forgetEverySession(): void {
  const held = registry();
  held.rows.clear();
  held.hydrated = true;
  persist();
}

/**
 * Forget what this process holds **without touching the volume**: what a restart loses.
 *
 * The one function in this module that exists only for a test, and it is not
 * `forgetEverySession` with a flag: the two mean opposite things. `forgetEverySession` ends
 * the sessions; this ends the *process's knowledge* of them, which is precisely the event
 * `R-51` is about. The next read hydrates from the file again.
 */
export function dropTheInMemoryRegister(): void {
  const host = globalThis as unknown as Record<symbol, Registry | undefined>;
  delete host[REGISTRY_KEY];
  announced = false;
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
