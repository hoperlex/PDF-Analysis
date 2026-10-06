/**
 * Public API of the `account` page slice — the screen at `/account`.
 *
 * A placeholder in W50 (`W50-PLAN.md` §3.2, decision three): the guard sends a session whose
 * profile is incomplete here, so the screen says what is missing. `W51` builds the profile
 * screen in its place.
 */

export type { AccountPageProps } from './ui/account-page';
export { AccountPage } from './ui/account-page';
