/**
 * The Russian heading for a finding's category, as the knowledge base shows it.
 *
 * **Moved here from `widgets/knowledge-base`, `W50-LAZY-01`.** `_pages/knowledge-base`
 * builds its category filter from this table, and while the table lived in the widget the
 * page held a static import of the widget for a label map — which kept the whole widget in
 * the page's first-load chunk after the widget itself was made lazy (`W50-PLAN.md` §3.4).
 * The vocabulary is the decision journal's (`DecisionRecord.category`), and the journal's
 * entity is this one, so the table lives beside `VERDICT_LABELS` rather than in either of
 * its two consumers.
 *
 * The contract value stays in `data-category` on the row, so the machine value has a home
 * and the reviewer reads Russian — the owner's 2026-09-22 ruling, and the same split
 * `RunStateBadge` and `DecisionHistory` already make. Keyed by the generated union, so a
 * category the contract adds does not compile until it has a label.
 */

import type { FindingCategory } from '@/shared/api';

export const CATEGORY_LABELS: Readonly<Record<FindingCategory, string>> = {
  internal_contradiction: 'Внутреннее противоречие',
  explicit_placeholder: 'Явный пропуск',
};
