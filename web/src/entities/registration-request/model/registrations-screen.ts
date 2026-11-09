import type { ScreenAddress } from '@/shared/config';

/**
 * The registration requests screen's address, a registry row. The side menu names the item the pending count belongs to
 * by it (`UI-A-91`); `satisfies ScreenAddress` makes the compiler refuse it the day the row is renamed.
 */
export const REGISTRATIONS_REQUESTS_SCREEN = '/admin/registrations' satisfies ScreenAddress;
