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
 *
 * ## What a row holds, since `W49-BFF-01`
 *
 * The credential, the two instants, and the **subject** `getMe` described when the session
 * was opened — `login`, `displayLabel`, `initials`, `roles`, `isDefaultCredential`,
 * `profileComplete` (`./subject.ts`, `W49-PLAN.md` §3.5). The subject is rewritten after a
 * successful profile change or password change ({@link refreshSubject}), so a completed
 * profile is visible without signing in again.
 *
 * The file format is therefore **version 2**. A version-1 file — written before rows carried
 * a subject — is **replaced at the first read, not read**: its rows have no roles and no
 * profile state, and inventing either for a session that is already open would be deciding a
 * reviewer's rights in this tier. Replacing it signs every reviewer out once, which is the
 * rollback cost the task file states.
 */

import {
  accessSync,
  constants as fsConstants,
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs';
import { dirname } from 'node:path';

import { SESSION_STORE_VARIABLE, getSessionStorePath } from '@/shared/config/session-store';

import type { SessionAccount } from './subject';
import { initialsOf, isRoleSet } from './subject';

export type { SessionAccount } from './subject';

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

/**
 * What a screen may learn about the open session: the account `getMe` described (see
 * {@link SessionAccount} for each field) and the two instants. Deliberately no credential.
 */
export interface SessionSubject extends SessionAccount {
  readonly openedAt: number;
  readonly expiresAt: number;
}

/** The row. `credential` leaves this module only through `credentialOf`. */
interface HeldSession extends SessionSubject {
  readonly credential: string;
}

/** The version this module writes, and the only one it reads rows from. */
export const REGISTER_FORMAT_VERSION = 2;

/** The version written before rows carried a subject. Replaced at the first read, never read. */
const REPLACED_REGISTER_FORMAT_VERSION = 1;

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
  /**
   * `Y7`. Whether the last attempt to write the file failed, and with what.
   *
   * It lives beside the rows for the reason `hydrated` does — two module graphs, one
   * process — and it exists because a *permission* probe cannot see a full disk. A
   * directory the process may write to and a directory it can actually write a file into
   * are different questions, and `ENOSPC` only answers the second. So
   * {@link sessionDurability} asks both: the probe before anything has been written, and
   * this after.
   */
  lastWriteError: string | null;
}

/** The shape written to the volume. Versioned, so a later format is distinguishable. */
interface PersistedRegister {
  readonly version: typeof REGISTER_FORMAT_VERSION;
  readonly sessions: readonly (HeldSession & { readonly id: string })[];
}

/** One row as it comes off the disk: nothing is trusted until {@link heldSessionFrom} checks it. */
type StoredRow = { readonly [field in keyof HeldSession | 'id']?: unknown };

/**
 * A version-2 row the register will hold, or `null` when any field is not the type it must
 * be. A row that fails is skipped, exactly as an expired one is: one bad row costs one
 * reviewer a sign-in, never the whole register.
 */
function heldSessionFrom(row: StoredRow, now: number): HeldSession | null {
  if (typeof row.credential !== 'string' || row.credential.length === 0) return null;
  if (typeof row.expiresAt !== 'number' || row.expiresAt <= now) return null;
  if (typeof row.openedAt !== 'number') return null;
  if (typeof row.login !== 'string' || row.login.length === 0) return null;
  if (typeof row.displayLabel !== 'string' || row.displayLabel.length === 0) return null;
  if (typeof row.initials !== 'string') return null;
  if (!isRoleSet(row.roles)) return null;
  if (typeof row.isDefaultCredential !== 'boolean') return null;
  if (typeof row.profileComplete !== 'boolean') return null;
  return {
    credential: row.credential,
    openedAt: row.openedAt,
    expiresAt: row.expiresAt,
    login: row.login,
    displayLabel: row.displayLabel,
    initials: row.initials,
    roles: Object.freeze([...row.roles]),
    isDefaultCredential: row.isDefaultCredential,
    profileComplete: row.profileComplete,
  };
}

function registry(): Registry {
  const host = globalThis as unknown as Record<symbol, Registry | undefined>;
  const existing = host[REGISTRY_KEY];
  if (existing !== undefined) return existing;
  const created: Registry = {
    rows: new Map<string, HeldSession>(),
    hydrated: false,
    lastWriteError: null,
  };
  host[REGISTRY_KEY] = created;
  return created;
}

/**
 * Say, once per process, which of the two registers this deployment is running.
 *
 * `AGENTS.md` §4 forbids a silent fallback, and "sessions end when this container is
 * recreated" is exactly the kind of fact that is discovered in an incident rather than read
 * in a log. So it is said out loud, at the first use, whichever answer it is.
 *
 * **The two branches are on different channels on purpose, and `D-118` is why that is
 * written down here.** `eslint.config.mjs:94` sets `no-console` to allow `warn` and `error`
 * only, so the *configured* branch — the healthy one — is the one that trips the rule, and
 * the linter is not in `make gate` (`D-118`'s structural half, which is not this repair's).
 * Three answers were available and two of them cost something real:
 *
 * - **escalate it to `warn`.** Then both branches are warnings, and the level stops carrying
 *   any information: an operator reading `docker compose logs web` could no longer tell a
 *   healthy stand from one that has silently lost its volume without reading the sentence.
 *   The unset branch below is a genuine warning — every reviewer is signed out on the next
 *   deploy and somebody has to act — and burying it beside a notice that fires on every
 *   correct deployment is how a warning becomes furniture;
 * - **delete it.** `R-51` asked for this to be said out loud: it is the cost the owner
 *   accepted, in the one place an operator meets it. `infra/deploy/README.md` describes both
 *   lines as things a reader will see. Deleting it to satisfy a rule about debug logging
 *   would be the tool editing the product;
 * - **keep it, on the channel that says what it is, and exempt this one line by name** —
 *   taken. It is information about a healthy configuration, which is what `info` means, and
 *   the exemption is narrow, permanent and reasoned rather than a blanket rule change. The
 *   rule exists to stop debug logging being left behind; this is not that, and it is once
 *   per process rather than once per request.
 *
 * The structural half of `D-118` — wiring `lint` into `make gate` — is deliberately not done
 * here and stays open.
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
    // `D-118`. Deliberate, and argued in this function's own docstring: `info` is what this
    // is, and the alternatives cost either the unset branch's warning or the statement
    // `R-51` asked for. Not a blanket exemption -- one line, by name.
    // eslint-disable-next-line no-console
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
 *
 * **A version-1 file is replaced, not read** (`W49-PLAN.md` §3.5). Its rows carry no roles
 * and no profile state, so reading them would mean inventing both for a session that is
 * already open. The file is overwritten with an empty version-2 register on the spot — so
 * the credentials it held leave the volume now rather than at the next sign-in — and the
 * replacement is said out loud: every reviewer signs in again, once.
 */
function hydrate(now: number): void {
  const held = registry();
  if (held.hydrated) return;
  held.hydrated = true;
  const path = getSessionStorePath();
  announce(path);
  if (path === null || !existsSync(path)) return;
  try {
    const parsed = JSON.parse(readFileSync(path, 'utf8')) as {
      readonly version?: unknown;
      readonly sessions?: unknown;
    };
    if (parsed.version === REPLACED_REGISTER_FORMAT_VERSION) {
      console.warn(
        `[session-register] ${path} is a version-${String(REPLACED_REGISTER_FORMAT_VERSION)} ` +
          `register, written before sessions carried a subject. It is replaced with an empty ` +
          `version-${String(REGISTER_FORMAT_VERSION)} register and none of its sessions is ` +
          'read: every reviewer signs in again, once.',
      );
      persist();
      return;
    }
    if (parsed.version !== REGISTER_FORMAT_VERSION || !Array.isArray(parsed.sessions)) {
      throw new Error(`unexpected register format: version ${String(parsed.version)}`);
    }
    for (const row of parsed.sessions as readonly StoredRow[]) {
      if (typeof row.id !== 'string' || !SESSION_ID_PATTERN.test(row.id)) continue;
      const session = heldSessionFrom(row, now);
      if (session !== null) held.rows.set(row.id, session);
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
    version: REGISTER_FORMAT_VERSION,
    sessions: [...held.rows].map(([id, row]) => ({ id, ...row })),
  };
  const temporary = `${path}.writing-${String(process.pid)}`;
  try {
    mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
    writeFileSync(temporary, JSON.stringify(snapshot), { encoding: 'utf8', mode: 0o600 });
    renameSync(temporary, path);
    held.lastWriteError = null;
  } catch (error) {
    held.lastWriteError = String(error);
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

/**
 * Which of the two registers is **in force**, for a diagnostic and for a test.
 *
 * `Y7`, repaired 2026-09-29. This used to answer `durable: path !== null` — that is, it
 * reported **how this deployment is configured**, while its own sentence promised *which
 * register is in force*, and on an unwritable volume those are different answers. Driven by
 * `W47-JUDGE-Y` §2e: on a directory the process cannot write and on a full filesystem, the
 * register actually in force is the memory one, every open session dies with the container,
 * and this answered `durable: true`. It is the one function an operator or a later readiness
 * check would reach for, and it could not distinguish the state this whole wave is about.
 *
 * **Configured is necessary and not sufficient**, so it is now three questions:
 *
 * 1. is a path configured at all? An unset value is a real configuration — `next dev` and
 *    this suite — and it is the memory register, announced at the first sign-in;
 * 2. has a write already failed? `persist()` records it. This is the only question that can
 *    see a **full disk**: the permissions are fine, the directory exists, and `ENOSPC`
 *    arrives at the moment of writing and at no earlier one;
 * 3. if nothing has been written yet, can this process write there? Asked of the filesystem
 *    (`mkdir` the directory as `persist()` would, then `W_OK | X_OK` on it, and `W_OK` on
 *    the file when it already exists) rather than assumed from the variable being set. This
 *    is what catches a **restored volume owned by `root`** on the first request of a fresh
 *    container, before a session has been opened to fail.
 *
 * It **writes nothing** and creates no session file: a diagnostic that had to write to
 * answer would be a diagnostic nobody could call twice. Creating the directory is what
 * `persist()` does anyway on its first write and is the only way to ask about a path whose
 * parent the image creates.
 *
 * `path` still reports what is **configured**, unchanged, because "durable: false, path:
 * /var/lib/…" is exactly the pair an operator needs: the volume that was meant to hold the
 * register, and the fact that it is not holding it.
 */
export function sessionDurability(): { readonly durable: boolean; readonly path: string | null } {
  const path = getSessionStorePath();
  if (path === null) return { durable: false, path: null };
  if (registry().lastWriteError !== null) return { durable: false, path };
  return { durable: canPersistTo(path), path };
}

/**
 * Can this process actually put the register at `path`? Asked of the filesystem.
 *
 * Deliberately the same two steps `persist()` takes, minus the write: the directory is
 * created if it is missing, because that is what the first write would do and a not-yet-
 * created directory is not an unwritable one. Anything that throws is an answer of `false`
 * — the question is whether the register can live there, and every reason it cannot is the
 * same answer to the caller. The **reason** is not swallowed: a real failure to write says
 * so on `console.error` from `persist()`, per attempt.
 */
function canPersistTo(path: string): boolean {
  try {
    const directory = dirname(path);
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    accessSync(directory, fsConstants.W_OK | fsConstants.X_OK);
    if (existsSync(path)) accessSync(path, fsConstants.W_OK);
    return true;
  } catch {
    return false;
  }
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
 * Record an exchanged credential and the account `getMe` described, and return the identifier
 * the cookie will carry.
 *
 * The account is the API's own answer, passed in rather than computed: see
 * {@link SessionAccount}. It is a required argument and not an optional one with defaults,
 * because the values a caller would get by omitting it are decisions about a reviewer's
 * rights that this tier does not take.
 *
 * @throws {SessionLifetimeError} when the lifetime is not a finite number of seconds
 * inside the accepted band.
 */
export function openSession(
  account: SessionAccount,
  credential: string,
  lifetimeSeconds: number,
  now?: number,
): string;
/**
 * The form this function had before sessions carried a subject: a login and the `R-50` flag.
 *
 * **Kept for exactly one caller, which this task may not edit:**
 * `web/tests/guards/default-credential-screens.guard.test.ts` drives the change-password lock
 * with `openSession(login, credential, lifetime, isDefaultCredential)`. The route handler never
 * uses this form — every session it opens carries the account `getMe` described.
 *
 * The fields this form cannot know are filled with the **restrictive** values, never the
 * permissive ones: no roles, an incomplete profile, and the login as the label. A screen
 * reading such a session shows the least it can and sends the reviewer to the profile, which
 * is the direction a default must point. Nothing is authorised by it either way: the API
 * reads the account's row on every request.
 */
export function openSession(
  login: string,
  credential: string,
  lifetimeSeconds: number,
  isDefaultCredential: boolean,
  now?: number,
): string;
export function openSession(
  accountOrLogin: SessionAccount | string,
  credential: string,
  lifetimeSeconds: number,
  defaultOrNow?: boolean | number,
  legacyNow?: number,
): string {
  let account: SessionAccount;
  let now: number;
  if (typeof accountOrLogin === 'string') {
    account = {
      login: accountOrLogin,
      displayLabel: accountOrLogin,
      initials: initialsOf(accountOrLogin),
      roles: Object.freeze([]),
      isDefaultCredential: defaultOrNow === true,
      profileComplete: false,
    };
    now = legacyNow ?? Date.now();
  } else {
    account = accountOrLogin;
    now = typeof defaultOrNow === 'number' ? defaultOrNow : Date.now();
  }
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
    ...accountFields(account),
    credential,
    openedAt: now,
    expiresAt: now + Math.floor(lifetimeSeconds) * 1000,
  });
  persist();
  return id;
}

/**
 * Exactly the six subject fields, copied: never a spread of whatever object the caller
 * passed, so a property that is not part of the subject — a credential included — cannot
 * ride into the row, the file or a screen's props by accident.
 */
function accountFields(account: SessionAccount): SessionAccount {
  return {
    login: account.login,
    displayLabel: account.displayLabel,
    initials: account.initials,
    roles: Object.freeze([...account.roles]),
    isDefaultCredential: account.isDefaultCredential,
    profileComplete: account.profileComplete,
  };
}

/**
 * Rewrite the subject of an open session with what `getMe` says now. True when there was a
 * live session to rewrite.
 *
 * `W49-PLAN.md` §3.5's refresh: called after a successful profile change, so a completed
 * profile — its new login, its name, `profileComplete` — is current without a new sign-in.
 * The credential and both instants are kept: the API did not issue a new credential, so the
 * session is the same session, and its lifetime is the one the exchange granted.
 */
export function refreshSubject(
  id: string | null,
  account: SessionAccount,
  now: number = Date.now(),
): boolean {
  if (id === null || !SESSION_ID_PATTERN.test(id)) return false;
  sweep(now);
  const rows = register();
  const row = rows.get(id);
  if (row === undefined) return false;
  rows.set(id, {
    ...accountFields(account),
    credential: row.credential,
    openedAt: row.openedAt,
    expiresAt: row.expiresAt,
  });
  persist();
  return true;
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
    ...accountFields(row),
    openedAt: row.openedAt,
    expiresAt: row.expiresAt,
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
