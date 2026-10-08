/**
 * The account as this application shows it: its name, its avatar's letters and its roles in
 * Russian (`W50-PLAN.md` §3.6).
 *
 * Built in Stage A by `W50-REGISTRY-01` so the home page and the frame can both consume one
 * reading of `getMe`, rather than each writing its own.
 *
 * ## An unknown role is a typed fault, never a fallback label
 *
 * `Role` is a closed set in the contract (`expert`, `admin`). A value outside it reaching a
 * screen means a server this build does not understand, and the two easy answers are both
 * wrong: dropping it would quietly hide an administrator's tools, and labelling it with a
 * generic word would show a role nobody can say the meaning of. So {@link roleLabel} throws
 * {@link UnknownRoleError} and the caller's error boundary shows a failure — the same rule
 * the BFF applies when it refuses a whole `getMe` answer carrying such a role
 * (`web/src/app/bff/session/subject.ts`).
 */

import type { Account, Role } from '@/shared/api';
import { ROLE_VALUES } from '@/shared/api';

/** The Russian name of each role. Keyed by the contract's set, so a new role fails to compile here. */
export const ROLE_LABELS: Readonly<Record<Role, string>> = {
  expert: 'Эксперт',
  admin: 'Администратор',
};

/** A role value outside the contract's closed set. */
export class UnknownRoleError extends Error {
  readonly value: unknown;

  constructor(value: unknown) {
    super('Учётная запись: значение роли вне набора, который знает договор.');
    this.name = 'UnknownRoleError';
    this.value = value;
  }
}

/** An account answer that breaks a promise the contract makes about it. */
export class MalformedAccountError extends Error {
  constructor(field: string) {
    super(`Учётная запись: поле ${field} не соответствует обещанию договора.`);
    this.name = 'MalformedAccountError';
  }
}

/** True for exactly the contract's role values. */
export function isKnownRole(value: unknown): value is Role {
  return typeof value === 'string' && (ROLE_VALUES as readonly string[]).includes(value);
}

/** The Russian label of one role. Throws {@link UnknownRoleError} for a value outside the set. */
export function roleLabel(role: unknown): string {
  if (!isKnownRole(role)) throw new UnknownRoleError(role);
  return ROLE_LABELS[role];
}

/** The labels of a role set, in the contract's order, each once. Throws on any unknown value. */
export function roleLabels(roles: readonly unknown[]): readonly string[] {
  for (const role of roles) if (!isKnownRole(role)) throw new UnknownRoleError(role);
  return ROLE_VALUES.filter((role) => roles.includes(role)).map((role) => ROLE_LABELS[role]);
}

/**
 * The name to show for an account: the server's `display_label`, which the contract promises
 * is never empty (`Фамилия И. О.`, else a display name, else the login).
 *
 * Not recomputed here from the names: the server resolves it, and a second resolution in the
 * browser is a second answer that can disagree with the first. An empty label breaks the
 * contract's promise and is a {@link MalformedAccountError}, not a blank greeting.
 */
export function displayLabelOf(account: Pick<Account, 'display_label'>): string {
  const label = account.display_label.trim();
  if (label.length === 0) throw new MalformedAccountError('display_label');
  return label;
}

/**
 * The avatar's letters (`R-57`): the first letter of each of the first two words of the
 * label, in capitals. `«Петрова А.»` gives `ПА`; a label with no letter gives its first
 * character, so the circle is never blank.
 *
 * The same rule the BFF records in the session (`initialsOf` in
 * `web/src/app/bff/session/subject.ts`), written again here because this layer may not
 * import the application's; `web/tests/unit/entities/account.test.ts` holds the two to the
 * same answers.
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
