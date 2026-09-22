/**
 * Per-stage rows for a run.
 *
 * Uses `StageStatusBadge`, whose value set is `succeeded`, `partial`, `failed`,
 * `skipped` — the `StageResult` vocabulary. This is the one place `succeeded` is a legal
 * word in this slice, and it is legal here precisely because a stage is not a run.
 *
 * A stage the run has not reported yet renders as "not started" rather than as a missing
 * row: an absent row reads as "there is nothing to say about this stage", which is a
 * different claim from "this stage has not run".
 *
 * **Why there is a Took column.** `formatInstant` prints to the second. PC-01's stages
 * finish in tens of milliseconds, so Started and Finished are the same string on a real
 * run and the pair carries no information at all. The elapsed column is what makes the
 * two columns a measurement rather than a decoration.
 *
 * **Why it is a table and not a pipeline of connected buttons.** The owner asked; the
 * answer stands and `D-62` records it. A PC-01 run is over in 0.4–9.1 seconds, so nobody
 * watches a progress pipeline — the table is what is read afterwards, and it is the shape
 * that supports "which stage took longest" and "which stage never ran". What `D-62`
 * conceded is everything below.
 *
 * **What this file gained in wave 35, and why each is not cosmetic:**
 *
 *   1. **The twelve inline styles are gone, and they were not what `D-62` thought.**
 *      `globals.css` styles `table`, `thead th`, `tbody td`, `tbody tr:hover`, `code` and
 *      `em` by ELEMENT selector, so this table always reached the token layer and always
 *      reached `W33-THEME`'s second palette. What the twelve attributes were is a
 *      token-free DUPLICATE of those rules, winning on inline specificity — a literal
 *      `padding: '0.35rem 0.75rem 0.35rem 0'` standing where the stylesheet's own spacing
 *      tokens were. Eleven overrode a tokenised rule with a literal; only `overflowX:
 *      auto` had nothing behind it. Deleting them is the repair, and the collocated module
 *      carries only the cells this wave added rather than a third copy of `thead th`.
 *
 *   2. **Russian stage names.** It rendered `<code>{row.stageId}</code>` — the first column
 *      of the one table on the run screen was `source_preparation`,
 *      `page_geometry_extraction`, `document_context_build`, `text_analysis`, shown to a
 *      Russian auditor with no sentence beside any of them. `STAGE_LABELS` names them; the
 *      contract value keeps its home in `data-stage-id`, which is what the browser journey
 *      and `PA-01` criterion 4 read.
 *
 *   3. **The order, which the data held and the markup threw away.** `PC01_STAGE_IDS` is
 *      an ordered tuple and `stageRows` walks it, so row order *implied* a sequence and
 *      asserted nothing. Two columns now state it: an ordinal over the stages PC-01
 *      schedules, and each stage's declared dependency under its name.
 *
 *      **The ordinal is deliberately not over the nine.** `stage-registry.json` forks:
 *      `text_analysis` and `block_analysis` both wait on `document_context_build` and have
 *      no order between them, `finding_merge` joins them, and `finding_review` and
 *      `norm_verification` fork again. Numbering a graph is a lie, so a stage PC-01 does
 *      not schedule shows `—` here and states its dependency instead. That the four
 *      scheduled stages ARE a chain is proven against the registry by
 *      `web/tests/guards/stage-vocabulary.guard.test.ts`, not assumed — if a later wave
 *      schedules a forked stage, that guard reddens before this column can mislead anyone.
 */

import type { StageId, StageStatus } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

import { elapsedMs, formatElapsed } from '../model/run-presentation';
import { STAGE_LABELS, StageStatusBadge } from '@/shared/ui';

import styles from './stage-table.module.css';

import type { StageRow } from '../model/run-presentation';

export interface StageTableProps {
  readonly rows: readonly StageRow[];
}

function StatusCell({
  status,
  errorCode,
}: {
  readonly status: StageStatus | null;
  readonly errorCode: string | null;
}) {
  if (status === null) {
    return (
      <em className={styles.aside} data-stage-status="not-reported">
        не начинался
      </em>
    );
  }
  return <StageStatusBadge status={status} errorCode={errorCode} />;
}

/**
 * What the stage waits for, in the reader's language.
 *
 * The machine values stay in `data-depends-on`; the sentence carries their labels. A stage
 * with no dependency is the entry point and says so rather than rendering an empty cell,
 * which would read as "not stated".
 */
function DependencyNote({ dependsOn }: { readonly dependsOn: readonly StageId[] }) {
  return (
    <span className={styles.dependency} data-depends-on={dependsOn.join(' ') || 'none'}>
      {dependsOn.length === 0
        ? 'первый этап'
        : `после: ${dependsOn.map((stageId) => STAGE_LABELS[stageId]).join(', ')}`}
    </span>
  );
}

export function StageTable({ rows }: StageTableProps) {
  return (
    <div className={styles.scroller}>
      <table>
        <thead>
          <tr>
            <th scope="col">№</th>
            <th scope="col">Этап</th>
            <th scope="col">Статус</th>
            <th scope="col">Начало</th>
            <th scope="col">Окончание</th>
            <th scope="col">Длительность</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.stageId} data-stage-id={row.stageId}>
              <td className={styles.ordinal} data-stage-ordinal={row.ordinal ?? 'unscheduled'}>
                {row.ordinal ?? '—'}
              </td>
              <td>
                <span className={styles.name}>{STAGE_LABELS[row.stageId]}</span>
                {row.expected ? null : (
                  <span className={styles.aside}> (на этом этапе не планируется)</span>
                )}
                <DependencyNote dependsOn={row.dependsOn} />
              </td>
              <td>
                <StatusCell status={row.status} errorCode={row.errorCode} />
              </td>
              <td className={styles.instant}>{formatInstant(row.startedAt)}</td>
              <td className={styles.instant}>{formatInstant(row.finishedAt)}</td>
              <td
                className={styles.elapsed}
                data-stage-elapsed={elapsedMs(row.startedAt, row.finishedAt) ?? 'unknown'}
              >
                {formatElapsed(elapsedMs(row.startedAt, row.finishedAt))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
