/** Public API of the `dashboard` widget. */

export { Dashboard } from './ui/dashboard';

// The pure aggregation logic, exported so it can be unit-tested without reaching past
// this slice's public API — `web/tests/unit/widgets/dashboard.test.ts` imports it from
// here, the same discipline `entities/project` uses for `projectDocumentCount`.
export type { DocumentTotalsSummary, ProjectDocumentTotal } from './model/document-totals';
export { summarizeDocumentTotals } from './model/document-totals';

export type { VerdictTally } from './model/verdict-tally';
export { tallyVerdicts } from './model/verdict-tally';

export type { RunActivitySummary } from './model/run-activity';
export { summarizeRunActivity } from './model/run-activity';
