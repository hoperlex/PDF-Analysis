import { USER_UID_PATTERN } from '@/shared/api';

const USER_UID_RE = new RegExp(USER_UID_PATTERN);

/**
 * Whether a route parameter is shaped like an account identity (`usr_<ULID>`), the way
 * `looksLikeProjectUid` is for a project (`C-24`).
 *
 * The UI never parses the value for meaning. This only separates "the address is malformed"
 * — a 404, without spending a request — from "the server says not found".
 */
export function looksLikeUserUid(value: string): boolean {
  return USER_UID_RE.test(value);
}
