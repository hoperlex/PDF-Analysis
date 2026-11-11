'use client';

/** @jsxRuntime automatic */

/**
 * «Этапы анализа раздела» (`RUN-SCREEN-01a`, plan §9.4): the run's chips on the left, the chosen one on the right.
 *
 * The right side is one table, «План + Факт». **The plan** is one line for each cell the run froze for the chip (`getRunStages`,
 * `RUN-STAGES-WEB-01`): its part (the one answer, or the legs and the judge of an ensemble), the model, the effort, the answer
 * limit and, for the reader who may see it, the server and how it is paid. **The fact** is what the journal and the stage results
 * say of the chip: its state, the calls that succeeded, failed and repeated, the tokens (those a subscription served said so), the
 * cost, start, end, duration, the last error code and the batches planned and completed.
 *
 * A run that froze no stage plan (`plan_source` `run_binding`) has one line, **the run's model**, labelled so as it always was;
 * and while the stages are still being read, or could not be, the window draws what it drew before the answer existed: the run's
 * model, the executor and the chip's own state and times from the run reading. It never draws a blank or a figure it was not
 * told; when the read failed it says so in a line.
 *
 * **Nothing is said twice** (the owner's minimisation priority). The model is its short name, with the pin in the tooltip, and no
 * executor line above the table: the plan rows already say the model and the server. Under the table, the table of the chip's code
 * stages (`StageTable`) is drawn only for a chip that has two or more (the preparation has three); a chip with one has its state and
 * its times in «Факт» already. The extended review's planned procedures («План полного анализа», moved here from the review panel)
 * keep their place, and are left out only where the answer is read and there is a single procedure, which «Факт» says as well. The
 * memo «Как устроен этап» is collapsed, and «Запустить с этого этапа» is for the stages a new run may be started from.
 *
 * A native modal `<dialog>`, as the pair viewer and the review's full-screen view are: the browser keeps focus inside, Esc closes it
 * (the `close` event calls `onClose`), the page behind is inert, and focus returns to the chip that opened it. Where `showModal` is
 * missing, or the harness asks for `staticOpen` (the static render, the contrast census), it is drawn open as it is.
 *
 * The server and its access are the dispatcher's information (`R-150w`): the reader who may not see them (`showServer` false) is
 * shown the model and the stages, and no executor line and no server on a cell (the answer omits them for the viewer as well).
 */

import { useId } from 'react';

import type { RunStage, RunStageFacts, RunStatus, StageId } from '@/shared/api';
import { STAGE_ID_VALUES } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import {
  CHIP_STATE_LABELS,
  StageTable,
  chipPagesText,
  elapsedMs,
  formatElapsed,
  groupDigits,
  runExecutorLine,
  runPresetLine,
  runPresetValue,
  shortModelName,
  stageOfChip,
} from '@/entities/audit-run';
import type {
  ProcedureReading,
  ProcedureStatus,
  RunChip,
  RunChipDefinition,
  RunStagesView,
  StageActivity,
} from '@/entities/audit-run';
import { procedureReasonSentence } from '@/widgets/extended-review';
import { StartRunFromStageControl } from '@/features/start-run-from-stage';

import { CHIP_ALGORITHMS } from '../model/chip-algorithms';
import { callsText, cellLines, costText, hasModelWork, tokensText } from '../model/stage-cells';
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
  /** The stages of the run (`useRunStages`); absent, or not read yet, the window draws what the run reading says. */
  readonly stages?: RunStagesView | undefined;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
  /**
   * `RUN-STAGE-PROGRESS-01`: the code stages under way, from the execution journal (`stageActivity`). A chip at work names
   * the pages its stage has read, and its stage table says «идёт» for a stage that has no result yet.
   */
  readonly activity?: ReadonlyMap<string, StageActivity> | undefined;
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
              : <strong title={model}>{short}</strong>}
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

/** Plan rows of a run with a stage plan: one line for each cell, as the run froze it. */
function PlanCellRows({ stage, showServer }: { readonly stage: RunStage; readonly showServer: boolean }) {
  return (
    <tbody>
      <tr>
        <th scope="colgroup" colSpan={2} className={styles.group}>План</th>
      </tr>
      {cellLines(stage.plan, showServer).map((line) => {
        const parts = [line.effort, line.server].filter((part): part is string => part !== null);
        return (
          <tr key={line.key} data-plan-row="cell" data-plan-cell={line.key} data-stage-role={line.role}>
            <th scope="row">{line.roleLabel}</th>
            <td>
              {line.model === null ? '—' : <strong title={line.pin ?? undefined}>{line.model}</strong>}
              {parts.length === 0 ? null : ` · ${parts.join(' · ')}`}
            </td>
          </tr>
        );
      })}
    </tbody>
  );
}

/** The fact of a chip as the journal and the stage results say it. */
function StageFactRows({ chip, facts }: { readonly chip: RunChip; readonly facts: RunStageFacts }) {
  const reused = facts.reused_from_run_id !== undefined || chip.reused;
  const cost = costText(facts);
  const error = facts.last_error_code ?? chip.errorCode;
  const timed = facts.started_at !== undefined || chip.stages.length > 0;
  return (
    <tbody>
      <tr>
        <th scope="colgroup" colSpan={2} className={styles.group}>Факт</th>
      </tr>
      <tr data-fact-row="state">
        <th scope="row">Состояние</th>
        <td data-chip-state={facts.state}>{CHIP_STATE_LABELS[facts.state]}{reused ? ' · взят из исходного прогона' : ''}</td>
      </tr>
      {facts.planned === undefined && facts.completed === undefined ? null : (
        <tr data-fact-row="progress">
          <th scope="row">Выполнено</th>
          <td>
            {facts.completed === undefined ? '—' : groupDigits(facts.completed)}
            {facts.planned === undefined ? '' : ` из ${groupDigits(facts.planned)}`}
          </td>
        </tr>
      )}
      {!chip.definition.callsModel && !hasModelWork(facts) ? null : (
        <>
          <tr data-fact-row="calls"><th scope="row">Обращения</th><td>{callsText(facts)}</td></tr>
          <tr data-fact-row="tokens"><th scope="row">Токены</th><td>{tokensText(facts)}</td></tr>
        </>
      )}
      {cost === null ? null : <tr data-fact-row="cost"><th scope="row">Стоимость</th><td>{cost}</td></tr>}
      {timed ? (
        <>
          <tr data-fact-row="started"><th scope="row">Начало</th><td>{formatInstant(facts.started_at)}</td></tr>
          <tr data-fact-row="finished"><th scope="row">Окончание</th><td>{formatInstant(facts.finished_at)}</td></tr>
          <tr data-fact-row="elapsed">
            <th scope="row">Длительность</th>
            <td>{reused ? 'из прогона' : formatElapsed(elapsedMs(facts.started_at, facts.finished_at))}</td>
          </tr>
        </>
      ) : null}
      {error === null ? null : <tr data-fact-row="error"><th scope="row">Код ошибки</th><td><code>{error}</code></td></tr>}
      {facts.reason === undefined ? null : (
        // The extended review's own reason, said in the words the plan list uses for it (`procedureReasonSentence`), never as the bare code.
        <tr data-fact-row="reason"><th scope="row">Причина</th><td>{procedureReasonSentence(facts.reason, null, facts.state)}</td></tr>
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

export function RunStagesDialog({
  status, chips, selected, onSelect, onClose, reusedStageIds, showServer, stages, staticOpen = false, activity,
}: RunStagesDialogProps) {
  const dialog = useModalDialog(staticOpen, onClose);
  const titleId = useId();
  const chipTitleId = useId();

  const chip = chips.find((candidate) => candidate.definition.id === selected) ?? chips[0] ?? null;
  const preset = runPresetLine(status);
  const algorithm = chip === null ? null : CHIP_ALGORITHMS[chip.definition.id];
  // What the answer says of this chip: its plan cells and its facts. `null` while it is not read, or where it does not list the chip.
  const read = stages?.phase === 'read' ? stages.stages : null;
  const stage = chip === null ? null : stageOfChip(read, chip.definition.id);
  // One line for each cell, but only for a run that froze a plan; a run that started on the route has one line, «модель прогона».
  const cells = read?.plan_source === 'stage_plan' && stage !== null && stage.plan.length > 0 ? stage : null;

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
              const pages = candidate.state === 'running' && activity !== undefined
                ? chipPagesText(activity, candidate.definition.stageIds)
                : null;
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
                      {CHIP_STATE_LABELS[candidate.state]}{pages === null ? '' : ` · ${pages}`}{took === null ? '' : ` · ${took}`}
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

            {preset === null ? null : (
              <dl className={styles.facts}>
                <dt>Пресет</dt>
                <dd data-run-preset>{runPresetValue(preset)}</dd>
              </dl>
            )}

            {stages?.phase !== 'error' ? null : (
              <p className={styles.note} role="status" data-run-stages-failed="">
                Модели по этапам прочитать не удалось: показана модель прогона.
              </p>
            )}
            <table className={styles.plan} data-plan-fact="" data-plan-source={stage === null ? undefined : read?.plan_source}>
              <caption>План + Факт</caption>
              {cells === null ? <PlanRows chip={chip} status={status} showServer={showServer} /> : <PlanCellRows stage={cells} showServer={showServer} />}
              {stage === null ? <FactRows chip={chip} /> : <StageFactRows chip={chip} facts={stage.facts} />}
            </table>
            {stage !== null || chip.stages.length > 0 ? null : (
              <p className={styles.note}>Время и токены по этому этапу сервер пока не передаёт.</p>
            )}

            {chip.stages.length < 2 ? null : (
              <section aria-label="Подробности этапов">
                <StageTable
                  rows={chip.stages}
                  {...(reusedStageIds === undefined ? {} : { reused: reusedStageIds })}
                  {...(activity === undefined ? {} : { activity })}
                />
              </section>
            )}
            {stage !== null && chip.procedures.length === 1 ? null : <Procedures procedures={chip.procedures} />}

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
