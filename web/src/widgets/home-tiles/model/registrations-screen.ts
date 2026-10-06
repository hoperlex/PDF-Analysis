/**
 * Where the administrator's registration tile links to — or that it links nowhere yet.
 *
 * `W50-PLAN.md` §3.6: the tile links to `/admin/registrations` **only once that row exists in
 * the screen registry**, and the row arrives with the administration screens in `W51`. So the
 * answer is read from the registry rather than written here: in `W50` there is no row and the
 * tile shows its count without a link, and a link can never point at an address the
 * application does not serve.
 */

import type { ScreenEntry } from '@/shared/config';
import { SCREEN_REGISTRY, screenAt } from '@/shared/config';

/** The address the administration screens are planned at (`W50-PLAN.md` §3.6). */
export const REGISTRATIONS_SCREEN = '/admin/registrations';

/** The tile's link, or `null` while the registry has no row for it. */
export function registrationsScreenLink(
  registry: readonly ScreenEntry[] = SCREEN_REGISTRY,
): string | null {
  return screenAt(REGISTRATIONS_SCREEN, registry) === undefined ? null : REGISTRATIONS_SCREEN;
}
