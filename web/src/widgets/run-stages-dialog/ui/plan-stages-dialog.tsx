'use client';

/** @jsxRuntime automatic */

/**
 * «Этапы анализа раздела» before a run exists (`READINESS-WEB-01`, plan 2026-11-09 §8 and §9.4): the same window as the run's, in
 * **plan mode**. The eight stages are on the left; the chosen one is on the right with the models that would do its work.
 *
 * It is opened by «Модели по этапам ▸» under «Запустить». There is no run, so there is **no fact**: no state, no start or end, no
 * duration, no tokens, no error code, and no «Запустить с этого этапа»; the table is only «План», one row per cell: the model, the
 * effort and how it would be paid. A cell whose model no server has says «⚠ нет на серверах», and nothing else is marked.
 *
 * It is built from the plan the readiness answer states (`readinessPlan`), never from a run. An administrator is also drawn
 * «Изменить», a link to «Исполнители → Модели по этапам»; everyone else reads and has no control (`R-150w`, plan §7.4). The server and
 * its name are not shown: the readiness says how a cell is paid, not which server will take it, and none is invented.
 *
 * The window is the run's window's chrome (`./run-stages-dialog.module.css`, the same native modal, `../model/use-modal-dialog.ts`).
 */

import { useId, useState } from 'react';

import { RUN_CHIPS } from '@/entities/audit-run';
import type { RunChipDefinition } from '@/entities/audit-run';
import { ACCESS_LABELS } from '@/entities/executor-host';
import { EDIT_LABEL, NOT_ON_SERVERS, NOT_ON_SERVERS_HINT } from '@/entities/stage-layout';
import type { PlanRow } from '@/entities/stage-layout';

import { CHIP_ALGORITHMS } from '../model/chip-algorithms';
import { useModalDialog } from '../model/use-modal-dialog';

import styles from './run-stages-dialog.module.css';

export interface PlanStagesDialogProps {
  /** The plan a start would freeze, row by row (`readinessPlan`). */
  readonly rows: readonly PlanRow[];
  /** The set the layout is based on, «Только Claude»; `null` before it has one. */
  readonly kit: string | null;
  readonly onClose: () => void;
  /** An administrator: where «Изменить» leads. Absent for everyone else, who has no control here. */
  readonly editHref?: string | undefined;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

/** What the stage says of itself on the left, where the models are read at a glance. */
function listLine(chip: RunChipDefinition, row: PlanRow | undefined): string {
  if (!chip.callsModel) return 'без модели';
  if (row === undefined) return 'не входит в запуск';
  return [...new Set(row.cells.map((cell) => cell.model))].join(' · ');
}

function PlanTable({ row }: { readonly row: PlanRow }) {
  return (
    <table className={styles.plan} data-plan-only="" data-plan-stage={row.row}>
      <caption>План</caption>
      <thead>
        <tr>
          <th scope="col">Модель</th>
          <th scope="col">Усилие</th>
          <th scope="col">Доступ</th>
        </tr>
      </thead>
      <tbody>
        {row.cells.map((cell) => (
          <tr key={cell.cellKey} data-plan-cell={cell.cellKey} data-stage-role={cell.role}>
            <th scope="row">{cell.roleLabel === '' ? cell.model : `${cell.roleLabel}: ${cell.model}`}</th>
            <td data-plan-effort={cell.effort}>{cell.effortLabel}</td>
            <td data-plan-access={cell.access ?? 'none'}>
              {cell.access === null || !cell.available
                ? <span title={NOT_ON_SERVERS_HINT} data-plan-missing="">{NOT_ON_SERVERS}</span>
                : ACCESS_LABELS[cell.access]}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function PlanStagesDialog({ rows, kit, onClose, editHref, staticOpen = false }: PlanStagesDialogProps) {
  const dialog = useModalDialog(staticOpen, onClose);
  const titleId = useId();
  const chipTitleId = useId();
  const byStage = new Map(rows.map((row) => [row.row as string, row] as const));
  const [selected, setSelected] = useState<RunChipDefinition['id']>(
    (RUN_CHIPS.find((chip) => byStage.has(chip.id)) ?? RUN_CHIPS[0])?.id ?? 'preparation',
  );
  const chip = RUN_CHIPS.find((candidate) => candidate.id === selected) ?? RUN_CHIPS[0] ?? null;
  const algorithm = chip === null ? null : CHIP_ALGORITHMS[chip.id];
  const row = chip === null ? undefined : byStage.get(chip.id);

  return (
    <dialog
      ref={dialog}
      className={styles.dialog}
      open={staticOpen ? true : undefined}
      aria-labelledby={titleId}
      data-run-stages-dialog=""
      data-stages-plan=""
    >
      <header className={styles.bar}>
        <h2 id={titleId} className={styles.title}>Этапы анализа раздела</h2>
        <button type="button" className="am-button am-button--quiet am-button--small" data-run-stages-close="" onClick={onClose}>
          Закрыть
        </button>
      </header>
      <div className={styles.body}>
        <nav className={styles.list} aria-label="Этапы анализа">
          <ul>
            {RUN_CHIPS.map((candidate) => (
              <li key={candidate.id}>
                <button
                  type="button"
                  className={styles.item}
                  data-stage-item={candidate.id}
                  aria-current={chip !== null && candidate.id === chip.id ? 'true' : undefined}
                  onClick={() => setSelected(candidate.id)}
                >
                  <span className={styles.itemName}>{candidate.short}</span>
                  <span className={styles.itemState}>{listLine(candidate, byStage.get(candidate.id))}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {chip === null || algorithm === null ? null : (
          <section className={styles.detail} aria-labelledby={chipTitleId} data-run-stage-detail={chip.id}>
            <h3 id={chipTitleId} className={styles.chipTitle}>{chip.full}</h3>
            <p className={styles.summary}>{algorithm.summary}</p>
            {kit === null ? null : <p className={styles.note} data-plan-kit="">{`Набор: ${kit}`}</p>}

            {!chip.callsModel ? (
              <p className={styles.note} data-plan-none="no-model">Этап не вызывает модель.</p>
            ) : row === undefined ? (
              <p className={styles.note} data-plan-none="not-in-run">Этот этап не входит в запуск.</p>
            ) : (
              <PlanTable row={row} />
            )}

            <details className={styles.how} data-stage-algorithm={chip.id}>
              <summary>Как устроен этап</summary>
              <ol className={styles.steps}>
                {algorithm.steps.map((step, index) => (
                  <li key={step} data-step-result={index === algorithm.steps.length - 1 ? '' : undefined}>
                    {step}
                    {index === algorithm.steps.length - 1 ? null : <span className={styles.arrow} aria-hidden="true">↓</span>}
                  </li>
                ))}
              </ol>
            </details>

            {editHref === undefined ? null : (
              <div className={styles.start}>
                <a className="am-button" href={editHref} data-plan-edit="">{EDIT_LABEL}</a>
              </div>
            )}
          </section>
        )}
      </div>
    </dialog>
  );
}
