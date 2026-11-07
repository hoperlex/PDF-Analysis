/**
 * The session note: the one thing the browser keeps so the sign-in screen can say *why* it is
 * being shown (`/login?reason=expired|ended|invalid`, `@/shared/lib/session-end-reason`).
 *
 * ## Why a second cookie, and why it holds a word and never an identity
 *
 * The session cookie cannot carry the reason. When a session is over the answer to the
 * browser is "clear that cookie", and a cleared cookie says nothing about why; when a session
 * *lapses*, the browser drops the cookie itself (its `Max-Age` is the session's lifetime) and
 * the next request looks exactly like a first visit. So the two facts the server genuinely
 * has — "I closed this session because the API stopped accepting its credential" and "a
 * session was opened in this browser a while ago" — would be lost with the cookie. The note
 * keeps them:
 *
 *   - `open`     written at sign-in, with a lifetime of the session plus a week. It says "a
 *                session was opened in this browser". It is what turns a vanished session
 *                cookie into «Сеанс истёк»: the cookie is gone, the note is not, and the only
 *                thing this tier does to a session cookie without writing another note is let
 *                its `Max-Age` pass;
 *   - `ended`    written when the API refused a credential this tier held as live
 *                (`endedOn` in the BFF route), which is what an administrator's «Завершить
 *                сеансы», a changed password or changed rights look like from here;
 *   - `invalid`  written when a request named a session this tier does not hold.
 *
 * `ended` and `invalid` live ten minutes: long enough to land on the sign-in screen from the
 * page that was open, short enough that the sentence is not there next week. A sign-in
 * replaces the note with `open`; an explicit sign-out removes it, because a reviewer who
 * signed out is not owed an explanation.
 *
 * The value is one of three words, `HttpOnly`, `SameSite=Strict` like the session cookie it
 * accompanies. It names no session, so a stolen or forged one grants nothing, and a forged
 * `ended` shows its forger a sentence about their own browser. A value outside the three is
 * no note at all: {@link readSessionNote} answers `null`, it never echoes.
 *
 * ## What is *not* told apart
 *
 * `ended` is one word for what the API answers with one `401`: the account's sessions were
 * ended, its password or roles changed, it was archived, or the credential's own signature
 * stopped verifying. The server cannot say which, so the screen says «Сеанс завершён» and
 * nothing more. This module never invents the narrower cause.
 */

import type { SessionEndReason } from '@/shared/lib/session-end-reason';

import { SESSION_COOKIE } from './store';

export const SESSION_NOTE_COOKIE = 'am_session_note';

export const SESSION_NOTES = ['open', 'ended', 'invalid'] as const;
export type SessionNote = (typeof SESSION_NOTES)[number];

/** How long `ended` and `invalid` stay: the time to reach the sign-in screen, not longer. */
export const END_NOTE_LIFETIME_SECONDS = 10 * 60;

/** How long `open` outlives its session cookie, so a lapse can be named a week on. */
export const OPEN_NOTE_GRACE_SECONDS = 7 * 24 * 60 * 60;

function isSessionNote(value: unknown): value is SessionNote {
  return typeof value === 'string' && (SESSION_NOTES as readonly string[]).includes(value);
}

function attributesOf(maxAge: number, secure: boolean): string[] {
  const attributes = ['Path=/', 'HttpOnly', 'SameSite=Strict', `Max-Age=${String(Math.floor(maxAge))}`];
  if (secure) attributes.push('Secure');
  return attributes;
}

/** `Set-Cookie`: a session was opened here, and its cookie lives for `lifetimeSeconds`. */
export function openNoteCookie(lifetimeSeconds: number, secure: boolean): string {
  return [
    `${SESSION_NOTE_COOKIE}=open`,
    ...attributesOf(lifetimeSeconds + OPEN_NOTE_GRACE_SECONDS, secure),
  ].join('; ');
}

/** `Set-Cookie`: the session was ended (`ended`) or named nothing here (`invalid`). */
export function endNoteCookie(note: 'ended' | 'invalid', secure: boolean): string {
  return [`${SESSION_NOTE_COOKIE}=${note}`, ...attributesOf(END_NOTE_LIFETIME_SECONDS, secure)].join('; ');
}

/** `Set-Cookie`: no note — after an explicit sign-out. */
export function clearedNoteCookie(secure: boolean): string {
  return [`${SESSION_NOTE_COOKIE}=`, ...attributesOf(0, secure)].join('; ');
}

/** One cookie's raw value out of a `Cookie` header, or `null` when it is absent. */
export function readCookie(cookieHeader: string | null, name: string): string | null {
  if (cookieHeader === null) return null;
  for (const pair of cookieHeader.split(';')) {
    const index = pair.indexOf('=');
    if (index < 0) continue;
    if (pair.slice(0, index).trim() !== name) continue;
    return pair.slice(index + 1).trim();
  }
  return null;
}

/** The note a value names, or `null` for an absent value and for any word outside the three. */
export function readSessionNote(value: string | null | undefined): SessionNote | null {
  return isSessionNote(value) ? value : null;
}

/**
 * Why a guest has no session, from what the browser sent — or `null` when nothing says.
 *
 * Called only for a browser that holds **no** live session (the register answered `null`).
 * In the order the evidence is firmest:
 *
 *   1. a note the server wrote when it ended or refused the session (`ended`, `invalid`);
 *   2. a session cookie that is present but names no session here — `invalid`;
 *   3. no session cookie, but the `open` note — a session was opened in this browser and its
 *      cookie has lapsed — `expired`;
 *   4. otherwise nothing: a first visit, or a browser that signed out, is not told a story.
 *
 * `sessionCookie` is the raw value as received, well-formed or not.
 */
export function guestSessionReason(
  sessionCookie: string | null | undefined,
  note: SessionNote | null,
): SessionEndReason | null {
  if (note === 'ended' || note === 'invalid') return note;
  if (typeof sessionCookie === 'string' && sessionCookie.length > 0) return 'invalid';
  if (note === 'open') return 'expired';
  return null;
}

/** The narrowest slice of the cookie jar `next/headers` hands a server component. */
export interface CookieJarReader {
  get(name: string): { readonly value: string } | undefined;
}

/** {@link guestSessionReason} over a server component's cookie jar. */
export function guestSessionReasonFromJar(jar: CookieJarReader): SessionEndReason | null {
  return guestSessionReason(
    jar.get(SESSION_COOKIE)?.value ?? null,
    readSessionNote(jar.get(SESSION_NOTE_COOKIE)?.value),
  );
}

/** {@link guestSessionReason} over a request's `Cookie` header. */
export function guestSessionReasonFromHeader(cookieHeader: string | null): SessionEndReason | null {
  return guestSessionReason(
    readCookie(cookieHeader, SESSION_COOKIE),
    readSessionNote(readCookie(cookieHeader, SESSION_NOTE_COOKIE)),
  );
}
