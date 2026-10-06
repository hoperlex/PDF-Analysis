/**
 * Who a session belongs to, as `getMe` says it, and the one place this tier reads that answer.
 *
 * `W49-PLAN.md` §3.5. After the exchange the BFF calls `getMe` with the credential it has just
 * been minted and keeps what comes back beside the credential in the register:
 * `{login, displayLabel, initials, roles, isDefaultCredential, profileComplete}`. The screens
 * of `W50` read it through `subjectOf` — never through `credentialOf`, which stays the
 * forwarder's alone — to decide what to show and where to send a browser. **None of it
 * decides what anybody is allowed to do.** The API reads the account's row on every
 * credentialed request (`auditmanager.api.security`), and refuses on its own evidence; a
 * subject that had gone stale here would show a menu its holder cannot use, and nothing
 * more.
 *
 * ## Why the answer is checked rather than cast
 *
 * A body this tier does not understand is not a subject. Every field is checked for the type
 * the contract declares (`Account` in `contracts/api/v1/openapi.json`), and a role outside
 * the contract's closed `Role` set refuses the whole answer rather than being dropped or kept:
 * a dropped role would quietly hide an administrator's tools, a kept one would hand a screen
 * a value it has no label for. Either is a decision this tier has no business taking, so the
 * caller treats the answer exactly as it treats one that did not arrive.
 */

import type { Role } from '@/shared/api/generated/types.gen';
import { ROLE_VALUES } from '@/shared/api/generated/types.gen';

/** What the register records about the account behind a session. Deliberately no credential. */
export interface SessionAccount {
  /** The sign-in identifier: the e-mail, or a legacy login until the profile is completed. */
  readonly login: string;
  /** The server's name for the account (`Фамилия И. О.`, else a display name, else the login). */
  readonly displayLabel: string;
  /** Up to two capital letters for the generated avatar (`R-57`), derived from `displayLabel`. */
  readonly initials: string;
  /** The account's role set, exactly as `getMe` listed it. Empty is a valid set. */
  readonly roles: readonly Role[];
  /**
   * `R-50`. Whether the account must change its password before anything else opens.
   *
   * **Read from the API's answer and never decided here.** A tier that worked it out for
   * itself — from the login, from the shape of the password — would be inventing a security
   * state, and the same state is enforced a second time by the API, which refuses every
   * operation but the exchange, `getMe` and the change while it holds. So this field decides
   * where a reviewer is *sent*, and never what they are *allowed*.
   */
  readonly isDefaultCredential: boolean;
  /** `R-59`. False until the account has given its names and e-mail. */
  readonly profileComplete: boolean;
}

/** True for exactly the contract's role values. */
export function isRole(value: unknown): value is Role {
  return typeof value === 'string' && (ROLE_VALUES as readonly string[]).includes(value);
}

/**
 * A role list the register will hold: an array of distinct contract roles.
 *
 * A duplicate is refused rather than collapsed, for the reason an unknown value is: the
 * contract says `roles` is a set, so a list that repeats a member is an answer from a server
 * this tier does not understand.
 */
export function isRoleSet(value: unknown): value is readonly Role[] {
  return (
    Array.isArray(value) && value.every(isRole) && new Set(value as unknown[]).size === value.length
  );
}

/**
 * The avatar's letters (`R-57`): the first letter of each of the first two words of the
 * label, in capitals.
 *
 * `«Петрова А.»` gives `ПА`, `«Смирнов Б. И.»` gives `СБ`, a legacy `admin` gives `A` and an
 * e-mail address the server fell back to gives its first letter. A label with no letter in it
 * at all gives its first character, so the circle is never blank; the contract promises the
 * label itself is never empty.
 *
 * Derived from the label and not from the e-mail on purpose: the avatar shows *who*, and the
 * label is the name this application shows everywhere else. The circle's colour is `W50`'s
 * and is hashed from the e-mail, so a corrected name does not recolour an account.
 */
export function initialsOf(displayLabel: string): string {
  const letters: string[] = [];
  for (const word of displayLabel.trim().split(/\s+/)) {
    const letter = word.match(/\p{L}/u)?.[0];
    if (letter !== undefined) letters.push(letter);
    if (letters.length === 2) break;
  }
  const chosen = letters.length > 0 ? letters.join('') : ([...displayLabel.trim()][0] ?? '');
  return chosen.toLocaleUpperCase('ru-RU');
}

/** The fields of `Account` this tier reads. Everything is `unknown` until it is checked. */
interface AccountBody {
  readonly login?: unknown;
  readonly display_label?: unknown;
  readonly roles?: unknown;
  readonly is_default_credential?: unknown;
  readonly profile_complete?: unknown;
}

/**
 * The subject a `getMe` answer describes, or `null` when the answer is not one.
 *
 * `null` for a body that is not an object, a missing or empty `login` or `display_label`, a
 * role list that is not a set of contract roles, or a non-boolean `is_default_credential` or
 * `profile_complete`. Never a partial subject with a default in the gap: the default for
 * `is_default_credential` would have to be `false`, which is the value that lets a reviewer
 * on the seeded password past the screen `R-50` sends them to.
 */
export function accountFromMe(body: unknown): SessionAccount | null {
  if (typeof body !== 'object' || body === null || Array.isArray(body)) return null;
  const account = body as AccountBody;
  if (typeof account.login !== 'string' || account.login.length === 0) return null;
  if (typeof account.display_label !== 'string' || account.display_label.trim().length === 0) {
    return null;
  }
  if (!isRoleSet(account.roles)) return null;
  if (typeof account.is_default_credential !== 'boolean') return null;
  if (typeof account.profile_complete !== 'boolean') return null;
  return {
    login: account.login,
    displayLabel: account.display_label,
    initials: initialsOf(account.display_label),
    roles: Object.freeze([...account.roles]),
    isDefaultCredential: account.is_default_credential,
    profileComplete: account.profile_complete,
  };
}
