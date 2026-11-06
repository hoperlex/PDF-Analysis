/**
 * The engineer filter of «График работ» (`D-319`): one engineer's rows of the month and of the reserve, as the original's
 * filter narrows them. It works on what the reads returned — an administrator's read carries every engineer they may see,
 * an expert's their own row — so nothing here asks the server for less.
 */

import { USER_UID_PATTERN } from '@/shared/api';

const USER_UID_RE = new RegExp(USER_UID_PATTERN);

/** An `?engineer=` value, or `null` when it is not an account identifier. */
export function parseEngineer(value: string | null | undefined): string | null {
  return value !== null && value !== undefined && USER_UID_RE.test(value) ? value : null;
}

export interface EngineerFilter {
  /** The engineer the rows are narrowed to; `null` shows everyone. */
  readonly uid: string | null;
  /** The address named an engineer the read does not carry, so everyone is shown and the screen says so. */
  readonly unknown: boolean;
}

export const NO_ENGINEER_FILTER: EngineerFilter = { uid: null, unknown: false };

/** What a requested engineer means against the engineers a read carried. */
export function resolveEngineerFilter(
  engineers: readonly { readonly user_uid: string }[],
  requested: string | null,
): EngineerFilter {
  if (requested === null) return NO_ENGINEER_FILTER;
  return engineers.some((engineer) => engineer.user_uid === requested)
    ? { uid: requested, unknown: false }
    : { uid: null, unknown: true };
}

/** The rows the filter leaves. */
export function narrowEngineers<T extends { readonly user_uid: string }>(
  engineers: readonly T[],
  filter: EngineerFilter,
): readonly T[] {
  return filter.uid === null ? engineers : engineers.filter((engineer) => engineer.user_uid === filter.uid);
}
