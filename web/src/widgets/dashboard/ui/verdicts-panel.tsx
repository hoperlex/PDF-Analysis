/**
 * Panel 2 — findings by verdict.
 *
 * `W46-WIRE`, `F-3b`. Presentational: `Dashboard` reads `getDashboardSummary` once and
 * hands this panel its `findings_by_verdict` rows.
 *
 * **The panel's meaning changed, and the caption says so.** The walk this panel used to
 * read (`useDecisionJournal`) is the ledger of *recorded* events: a finding nobody has
 * ever judged carries no event and never appeared there, at any page size, so its old
 * caption said `pending` meant "commented on or reverted, still undecided" and explicitly
 * excluded a finding nobody had opened. The aggregate counts differently — a finding with
 * no decision at all is what `Verdict`'s own `pending` member means, and the server counts
 * it as `pending` (`docs/program/reviews/W46-JUDGE-A.md` §5, and the integrator's ruling
 * quoted in `docs/program/dispatch/W46-WIRE.md`'s brief: *a computed zero is a fact*). So
 * `pending` here is wider than it used to be, and the caption is rewritten rather than
 * carried over unchanged.
 *
 * **All four rows, always**, including `needs_manual_review` — which today has no PC-01
 * producer, so it always reads zero, and a computed zero is shown rather than dropped: the
 * non-negotiable both the brief and `R-23`'s addendum state.
 *
 * **The per-category table is gone.** `DashboardSummary.findings_by_verdict` carries only
 * a verdict and a count — no category — because the aggregate does not compute one. The
 * old panel's category breakdown came from walking `listDecisions` and reading
 * `DecisionRecord.category` off each event; that source is not part of this one read, and
 * "reads `getDashboardSummary` and nothing else" rules out reaching back for it. This is a
 * visible change to the screen, not an oversight: category counts stay available on
 * `widgets/finding-list` and `/knowledge-base`, which already carry `data-category`.
 *
 * **An omitted or unrecognised verdict row is a fault, never a zero.**
 * `summarizeVerdictBreakdown` only returns a breakdown over the whole closed vocabulary —
 * all four `Verdict` members, each once. Anything short of that renders no numbers at all:
 * the shape `dashboard-failure.ts` already has, not a zero nobody computed
 * (`docs/program/reviews/W46-JUDGE-Y.md` §5, `Y5-a`).
 */

import { ErrorState } from '@/shared/ui';
import { VERDICT_LABELS } from '@/entities/expert-decision';
import type { VerdictCount } from '@/shared/api';
import { VERDICT_VALUES } from '@/shared/api';

import { incompleteBreakdownFailure } from '../model/dashboard-failure';
import { summarizeVerdictBreakdown } from '../model/verdict-breakdown';

export interface VerdictsPanelProps {
  readonly rows: readonly VerdictCount[];
}

export function VerdictsPanel({ rows }: VerdictsPanelProps) {
  const result = summarizeVerdictBreakdown(rows);

  if (!result.ok) {
    const failure = incompleteBreakdownFailure('Разбивка по вердиктам пришла неполной.');
    return (
      <div data-panel="findings-by-verdict" data-panel-fault={failure.kind}>
        <ErrorState title={failure.title} detail={failure.detail} />
      </div>
    );
  }

  const { byVerdict } = result;
  const total = VERDICT_VALUES.reduce((sum, verdict) => sum + byVerdict[verdict], 0);

  return (
    <div data-panel="findings-by-verdict">
      <p>
        Находок: <strong>{total}</strong>.
      </p>
      <p className="am-state__correlation">
        Каждая находка системы считана по своему текущему вердикту, включая ту, которую ещё
        никто не открывал, — «не решено» здесь не то же самое, что «по ней есть
        отложенное решение».
      </p>
      <table>
        <caption>По вердикту</caption>
        <tbody>
          {VERDICT_VALUES.map((verdict) => (
            <tr key={verdict} data-verdict={verdict}>
              <th scope="row">{VERDICT_LABELS[verdict]}</th>
              <td>{byVerdict[verdict]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
