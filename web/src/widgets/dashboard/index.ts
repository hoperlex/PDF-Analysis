/** Public API of the `dashboard` widget. */

export { Dashboard } from './ui/dashboard';

// The pure aggregation logic, exported so it can be unit-tested without reaching past
// this slice's public API — `web/tests/unit/widgets/dashboard.test.ts` imports it from
// here, the same discipline `entities/project` uses for `projectDocumentCount`.
export type { SectionBreakdownSummary } from './model/section-breakdown';
export { summarizeSectionBreakdown } from './model/section-breakdown';

export { summarizeVerdictBreakdown } from './model/verdict-breakdown';

export type { DashboardFailure, DashboardFailureKind } from './model/dashboard-failure';
export { classifyDashboardFailure } from './model/dashboard-failure';

export { useDashboardSummary } from './api/use-dashboard-summary';
