/**
 * Why a browser is on the sign-in screen without a session: the closed list.
 *
 * The web tier's server side (`web/src/app/bff/**`) writes one of these three words into the
 * address of the sign-in screen when it knows why a session is gone — `/login?reason=ended` —
 * and the screen shows the matching sentence above the form, as the original portal's sign-in
 * page did («Сеанс истёк», «Сеанс завершён», «Сеанс недействителен»).
 *
 *   - `expired`  the session's own lifetime ran out: the browser holds a note that a session
 *                was opened here, and the session cookie is gone because its `Max-Age` passed;
 *   - `ended`    the API stopped accepting a credential this tier still held as live — an
 *                administrator ended the account's sessions, or the password or the rights
 *                changed, or the account was deactivated. The API answers all of these with
 *                the one `401 authentication_required`, so the server cannot say which, and
 *                the sentence does not either;
 *   - `invalid`  the browser presented a session cookie that names no session on this server.
 *
 * **A closed list, and the value is read as one.** The parameter is a query string the
 * browser controls, so a value outside this list is no reason at all: it is ignored, never
 * echoed, never rendered. {@link sessionEndReasonOf} is the one reader.
 */

/** The query parameter the redirect to the sign-in screen carries the reason in. */
export const SESSION_END_REASON_PARAM = 'reason';

/** Every reason the sign-in screen can give. */
export const SESSION_END_REASONS = ['expired', 'ended', 'invalid'] as const;

export type SessionEndReason = (typeof SESSION_END_REASONS)[number];

/** True for exactly the three values above. */
export function isSessionEndReason(value: unknown): value is SessionEndReason {
  return typeof value === 'string' && (SESSION_END_REASONS as readonly string[]).includes(value);
}

/**
 * The reason a query value names, or `null` for anything else.
 *
 * A repeated parameter arrives as an array; the first value is read, and is held to the list
 * like any other. An absent parameter, an empty one and a value outside the list are all
 * `null`: there is no «unknown reason» state to render, because the screen does not echo a
 * value it was not given the right to say.
 */
export function sessionEndReasonOf(
  value: string | readonly string[] | null | undefined,
): SessionEndReason | null {
  const first = Array.isArray(value) ? value[0] : value;
  return isSessionEndReason(first) ? first : null;
}
