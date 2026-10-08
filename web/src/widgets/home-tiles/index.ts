/**
 * Public API of the `home-tiles` widget: the three tiles of the home page
 * (`W50-PLAN.md` §3.6, `W50-HOME-01`).
 *
 * The pure parts are exported too, so `web/tests/unit/screens/home.test.ts` can hold them
 * without reaching past this slice's public API.
 */

export { RecentProjectsTile } from './ui/recent-projects-tile';
export { SummaryTile } from './ui/summary-tile';
export type { PendingRegistrationsTileProps } from './ui/pending-registrations-tile';
export { PendingRegistrationsTile } from './ui/pending-registrations-tile';

export { RECENT_PROJECT_LIMIT, recentProjects } from './model/recent-projects';

export type { SummaryFigures } from './model/summary-figures';
export { summaryFigures } from './model/summary-figures';

export type { HomeReadFailure, HomeReadFailureKind } from './model/read-failure';
export { classifyRegistrationsFailure, classifySummaryFailure } from './model/read-failure';

export { REGISTRATIONS_SCREEN, registrationsScreenLink } from './model/registrations-screen';

export * as HOME_TILE_COPY from './ui/copy';
