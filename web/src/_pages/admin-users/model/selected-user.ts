import type { AddressParams } from '@/shared/lib';
import { looksLikeUserUid } from '@/entities/user';

/** The address parameter that holds the account open beside the list. */
export const SELECTED_USER_PARAM = 'user';

/**
 * The account open in the panel, read from the address (`R-150c`): a value that is not shaped like an account identity is no
 * selection, so a hand-typed address opens nothing and asks the server nothing.
 */
export function readSelectedUser(params: AddressParams): string | null {
  const value = new URLSearchParams(params.toString()).get(SELECTED_USER_PARAM);
  return value !== null && looksLikeUserUid(value) ? value : null;
}

/** The address with the selection set or, for `null`, removed; every other parameter is carried through. */
export function writeSelectedUser(params: AddressParams, next: string | null): URLSearchParams {
  const out = new URLSearchParams(params.toString());
  if (next === null) out.delete(SELECTED_USER_PARAM);
  else out.set(SELECTED_USER_PARAM, next);
  return out;
}
