/**
 * The expert an address of «Назначения» names (`UIP-S14-03`, `?expert=<номер учётной записи>`): the form «Назначить работу»
 * opens with that expert chosen, as a link from «Календарь запаса» does for the engineer it has narrowed to. The value is
 * only a request. It is read when it is an account identifier and applied when that account is among the active experts the
 * screen has loaded; any other value is dropped and is never drawn.
 */

import { USER_UID_PATTERN } from '@/shared/api';

const USER_UID_RE = new RegExp(USER_UID_PATTERN);

/** The query parameter that carries the expert. */
export const EXPERT_PARAM = 'expert';

/** An `?expert=` value, or `null` when it is not an account identifier. */
export function parseExpertAddress(value: string | null | undefined): string | null {
  return value !== null && value !== undefined && USER_UID_RE.test(value) ? value : null;
}

/**
 * The requested expert when the experts loaded include them, otherwise `null`: while the list is not loaded it is empty,
 * so no choice is made yet and nothing is assigned to someone the screen has not seen.
 */
export function resolveExpertChoice(
  experts: readonly { readonly userUid: string }[],
  requested: string | null,
): string | null {
  return requested !== null && experts.some((expert) => expert.userUid === requested) ? requested : null;
}
