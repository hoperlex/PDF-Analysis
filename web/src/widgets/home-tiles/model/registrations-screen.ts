/**
 * Where the administrator's registration tile links to.
 *
 * `W50-PLAN.md` §3.6: the tile links to `/admin/registrations` **only while that row exists in
 * the screen registry**. The answer is read from the registry rather than written here, so a
 * link can never point at an address the application does not serve; without the row the
 * tile shows its count and no link.
 */

import type { ScreenAddress, ScreenEntry } from '@/shared/config';
import { SCREEN_REGISTRY, screenAt } from '@/shared/config';

/** The registration requests screen (`W50-PLAN.md` §3.6), a registry row. */
export const REGISTRATIONS_SCREEN = '/admin/registrations' satisfies ScreenAddress;

/** The tile's link, or `null` while the registry has no row for it. */
export function registrationsScreenLink(
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): string | null {
  return screenAt(REGISTRATIONS_SCREEN, registry) === undefined ? null : REGISTRATIONS_SCREEN;
}
