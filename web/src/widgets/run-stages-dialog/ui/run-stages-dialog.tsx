'use client';

/** @jsxRuntime automatic */

/**
 * «Этапы анализа раздела» (`RUN-SCREEN-01a`, plan §9.4): the run's chips on the left, the chosen one on the right.
 *
 * The right side is one table, «План + Факт», with what the reading carries today: the plan (the run's model and the server it is
 * on) and the fact (state, start, end, duration, error code). The model is **the run's**, labelled so: the contract carries one
 * model per run, and a model per stage arrives with `getRunStages`. Under the table, what the run reported for the chip's code
 * stages (`StageTable`) and the extended review's planned procedures («План полного анализа», moved here from the review panel),
 * the memo «Как устроен этап» (collapsed), and «Запустить с этого этапа» for the stages a new run may be started from.
 *
 * A native modal `<dialog>`, as the pair viewer and the review's full-screen view are: the browser keeps focus inside, Esc closes it
 * (the `close` event calls `onClose`), the page behind is inert, and focus returns to the chip that opened it. Where `showModal` is
 * missing, or the harness asks for `staticOpen` (the static render, the contrast census), it is drawn open as it is.
 *
 * The server and its access are the dispatcher's information (`R-150w`): the reader who may not see them (`showServer` false) is
 * shown the model and the stages, and no executor line.
 */

import { useId } from 'react';

import type { RunStatus, StageId } from '@/shared/api';
import { STAGE_ID_VALUES } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import {
  CHIP_STATE_LABELS,
  StageTable,
  formatElapsed,
  runExecutorLine,
  runExecutorValue,
  runPresetLine,
  runPresetValue,
  shortModelName,
} from '@/entities/audit-run';
import type { ProcedureReading, ProcedureStatus, RunChip, RunChipDefinition } from '@/entities/audit-run';
import { procedureReasonSentence } from '@/widgets/extended-review';
import { StartRunFromStageControl } from '@/features/start-run-from-stage';

import { CHIP_ALGORITHMS } from '../model/chip-algorithms';
import { useModalDialog } from '../model/use-modal-dialog';

import styles from './run-stages-dialog.module.css';

export interface RunStagesDialogProps {
  readonly status: RunStatus;
  readonly chips: readonly RunChip[];
  /** The chip shown on the right. */
  readonly selected: RunChipDefinition['id'];
  readonly onSelect: (id: RunChipDefinition['id']) => void;
  readonly onClose: () => void;
  /** The stage ids this run took by reference from the run it was started from. */
  readonly reusedStageIds?: ReadonlySet<string> | undefined;
  /** Whether the reader may see the executor and its server (`maySeeServer`). */
  readonly showServer: boolean;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

const PROCEDURE_STATUS_LABELS: Readonly<Record<ProcedureStatus, string>> = {
  queued: 'Запланировано',
  running: 'Выполняется',
  repairing: 'Исправляется ответ',
  completed: 'Завершено',
  partial: 'Частично',
  failed: 'Ошибка',
  unavailable: 'Недоступно',
  skipped: 'Пропущено',
};

const isStageId = (value: string): value is StageId => (STAGE_ID_VALUES as readonly string[]).includes(value);

/** Plan rows: the run's model and its server. */
function PlanRows({ chip, status, showServer }: { readonly chip: RunChip; readonly status: RunStatus; readonly showServer: boolean }) {
  const executor = runExecutorLine(status);
  const model = executor?.model ?? null;
  const short = shortModelName(model);
  return (
    <tbody>
      <tr>
        <th scope="colgroup" colSpan={2} className={styles.group}>План</th>
      </tr>
      <tr data-plan-row="model">
        <th scope="row">Модель (прогона)</th>
        <td>
          {!chip.definition.callsModel
            ? 'этап не вызывает модель'
            : short === null || model === null
              ? '—'
              : <><strong>{short}</strong> <code title="Идентификатор модели прогона">{model}</code></>}
        </td>
      </tr>
      {chip.definition.callsModel && showServer ? (
        <tr data-plan-row="server">
          <th scope="row">Сервер</th>
          <td>
            {executor === null
              ? '—'
              : executor.phase === 'planned'
                ? 'будет выбран при отправке в работу'
                : executor.name}
          </td>
        </tr>
      ) : null}
    </tbody>
  );
}

function FactRows({ chip }: { readonly chip: RunChip }) {
  const timed = chip.stages.length > 0;
  return (
    <tbody>
      <tr>
        <th scope="colgroup" colSpan={2} className={styles.group}>Факт</th>
      </tr>
      <tr data-fact-row="state">
        <th scope="row">Состояние</th>
        <td data-chip-state={chip.state}>{CHIP_STATE_LABELS[chip.state]}{chip.reused ? ' · взят из исходного прогона' : ''}</td>
      </tr>
      {timed ? (
        <>
          <tr data-fact-row="started"><th scope="row">Начало</th><td>{formatInstant(chip.startedAt)}</td></tr>
          <tr data-fact-row="finished"><th scope="row">Окончание</th><td>{formatInstant(chip.finishedAt)}</td></tr>
          <tr data-fact-row="elapsed">
            <th scope="row">Длительность</th>
            <td>{chip.reused ? 'из прогона' : formatElapsed(chip.elapsedMs)}</td>
          </tr>
        </>
      ) : null}
      {chip.errorCode === null ? null : (
        <tr data-fact-row="error"><th scope="row">Код ошибки</th><td><code>{chip.errorCode}</code></td></tr>
      )}
    </tbody>
  );
}

function Procedures({ procedures }: { readonly procedures: readonly ProcedureReading[] }) {
  if (procedures.length === 0) return null;
  return (
    <ol className={styles.procedures} aria-label="План полного анализа" data-extended-procedure-plan="">
      {procedures.map((procedure) => (
        <li key={procedure.id} data-extended-procedure={procedure.id} data-procedure-status={procedure.status}>
          <strong>{procedure.title === '' ? 'Название процедуры не передано' : procedure.title}</strong> · {PROCEDURE_STATUS_LABELS[procedure.status]}
          {procedure.reason !== null && procedure.status !== 'completed' ? (
            <p>{procedureReasonSentence(procedure.reason, procedure.dependency, procedure.status, procedure.errorCode)}</p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}

export function RunStagesDialog({ status, chips, selected, onSelect, onClose, reusedStageIds, showServer, staticOpen = false }: RunStagesDialogProps) {
  const dialog = useModalDialog(staticOpen, onClose);
  const titleId = useId();
  const chipTitleId = useId();

  const chip = chips.find((candidate) => candidate.definition.id === selected) ?? chips[0] ?? null;
  const executor = showServer ? runExecutorLine(status) : null;
  const preset = runPresetLine(status);
  const algorithm = chip === null ? null : CHIP_ALGORITHMS[chip.definition.id];

  return (
    <dialog
      ref={dialog}
      className={styles.dialog}
      open={staticOpen ? true : undefined}
      aria-labelledby={titleId}
      data-run-stages-dialog=""
    >
      <header className={styles.bar}>
        <h2 id={titleId} className={styles.title}>Этапы анализа раздела</h2>
        <button type="button" className="am-button am-button--quiet am-button--small" data-run-stages-close="" onClick={onClose}>
          Закрыть
        </button>
      </header>
      <div className={styles.body}>
        <nav className={styles.list} aria-label="Этапы прогона">
          <ul>
            {chips.map((candidate) => {
              const id = candidate.definition.id;
              const took = candidate.reused ? 'из прогона' : candidate.elapsedMs === null ? null : formatElapsed(candidate.elapsedMs);
              return (
                <li key={id}>
                  <button
                    type="button"
                    className={styles.item}
                    data-stage-item={id}
                    data-chip-state={candidate.state}
                    aria-current={chip !== null && id === chip.definition.id ? 'true' : undefined}
                    onClick={() => onSelect(id)}
                  >
                    <span className={styles.itemName}>{candidate.definition.short}</span>
                    <span className={styles.itemState}>
                      {CHIP_STATE_LABELS[candidate.state]}{took === null ? '' : ` · ${took}`}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {chip === null || algorithm === null ? (
          <p className={styles.detail} data-stage-table-empty>Сведения об этапах пока не поступили.</p>
        ) : (
          <section className={styles.detail} aria-labelledby={chipTitleId} data-run-stage-detail={chip.definition.id}>
            <h3 id={chipTitleId} className={styles.chipTitle}>{chip.definition.full}</h3>
            <p className={styles.summary}>{algorithm.summary}</p>

            {executor === null && preset === null ? null : (
              <dl className={styles.facts}>
                {executor === null ? null : <><dt>Исполнитель</dt><dd data-run-executor>{runExecutorValue(executor)}</dd></>}
                {preset === null ? null : <><dt>Пресет</dt><dd data-run-preset>{runPresetValue(preset)}</dd></>}
              </dl>
            )}

            <table className={styles.plan} data-plan-fact="">
              <caption>План + Факт</caption>
              <PlanRows chip={chip} status={status} showServer={showServer} />
              <FactRows chip={chip} />
            </table>
            {chip.stages.length > 0 ? null : (
              <p className={styles.note}>Время и токены по этому этапу сервер пока не передаёт.</p>
            )}

            {chip.stages.length === 0 ? null : (
              <section aria-label="Подробности этапов">
                <StageTable rows={chip.stages} {...(reusedStageIds === undefined ? {} : { reused: reusedStageIds })} />
              </section>
            )}
            <Procedures procedures={chip.procedures} />

            <details className={styles.how} data-stage-algorithm={chip.definition.id}>
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

            <div className={styles.start}>
              <StartRunFromStageControl
                runId={status.run_id}
                stageIds={chip.definition.stageIds.filter(isStageId)}
                label="Запустить с этого этапа"
              />
            </div>
          </section>
        )}
      </div>
    </dialog>
  );
}
