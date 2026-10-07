/**
 * Session subjects for the frame's tests and the instruments that render the frame
 * (`W50-SHELL-FRAME`): every state the bar distinguishes.
 *
 * The logins are Cyrillic e-mail addresses on purpose, for the reason
 * `rendered-language.guard.test.ts` gives for its own fixtures: they are the server's data,
 * not this programme's prose, and a Latin one would be read as English by the language
 * guard. The one Latin address, {@link LONGEST_LOGIN}, is the width case's, under the
 * reserved `example.test`, and no language instrument renders it.
 */

import type { AppFrameSession } from '@/_app';
import { initialsOf } from '@/entities/account';

function subject(
  displayLabel: string,
  login: string,
  roles: readonly string[],
  state: Partial<Pick<AppFrameSession, 'isDefaultCredential' | 'profileComplete'>> = {},
): AppFrameSession {
  return {
    login,
    displayLabel,
    initials: initialsOf(displayLabel),
    roles,
    isDefaultCredential: state.isDefaultCredential ?? false,
    profileComplete: state.profileComplete ?? true,
  };
}

/** An account holding `expert` only. */
export const EXPERT = subject('Экспертова А. С.', 'эксперт@пример.испытание', ['expert']);

/** An account holding both roles. */
export const ADMIN_AND_EXPERT = subject('Проверкина А. С.', 'администратор@пример.испытание', ['admin', 'expert']);

/** An account holding `admin` only (`R-60`: it reads everything and changes no product data). */
export const ADMIN_ONLY = subject('Управляева Б. В.', 'управление@пример.испытание', ['admin']);

/** An account with an empty role set. */
export const NO_ROLES = subject('Безролева Г. Д.', 'безроли@пример.испытание', []);

/** An account whose role set holds a value this build does not know. */
export const UNKNOWN_ROLE = subject('Незнакомова Е. Ж.', 'незнакомая@пример.испытание', ['expert', 'auditor']);

/** `R-50`: the seeded account, still on its default credential, before its profile is complete. */
export const DEFAULT_CREDENTIAL = subject('админ', 'админ', ['admin', 'expert'], {
  isDefaultCredential: true,
  profileComplete: false,
});

/** `R-59`: a changed password, an incomplete profile (the legacy login before the e-mail). */
export const INCOMPLETE_PROFILE = subject('админ', 'админ', ['admin', 'expert'], { profileComplete: false });

/** The longest name form: a sixty-letter last name, `Фамилия И. О.` — 66 characters. */
export const LONGEST_LABEL = `${'Ж'.repeat(60)} И. О.`;

/** A 254-character address, the longest an e-mail may be, under the reserved `example.test`. */
export const LONGEST_LOGIN = `${'a'.repeat(64)}@${'b'.repeat(63)}.${'c'.repeat(63)}.${'d'.repeat(48)}.example.test`;

/** The width case: the longest name and the longest address at once. */
export const LONGEST = subject(LONGEST_LABEL, LONGEST_LOGIN, ['admin', 'expert']);
