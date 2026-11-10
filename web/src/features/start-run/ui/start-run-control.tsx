'use client';

/**
 * Start one run over one published version with one button (`RUN-START-ONE-01a`, plan v3 §8, rulings
 * `R-153a`, `R-153f`).
 *
 * The control is «Запустить» and one line under it saying what will happen. It offers no choice of
 * executor, group or preset and no separate estimate: the request names no selector, so the server's
 * automatic route applies (`./../model/use-run-cost-approval.ts` holds the sequence). A click reads the
 * estimate; an estimate that charges nothing is agreed to by the click itself, and one that can charge
 * opens ONE dialog (`./start-run-cost-dialog.tsx`) with «Запустить» and «Отмена».
 *
 * «▾» beside the button holds the one other way to start, «Без денежного потолка (сбор статистики)»: the
 * start with `relaxed_limits: true`, which the temporary-statistics tick-box used to switch on. It is drawn
 * for exactly the accounts the control is drawn for (`R-150e`: those that may take an expert's action),
 * which are the accounts that saw the tick-box.
 *
 * **The readiness line.** It says «Маршрут: автоматически» until the widget that mounts the control passes the real line
 * («Набор: … · по подписке · Модели по этапам ▸», from `getRunStartReadiness`, `./readiness-line.tsx`) as `readinessNote`;
 * this control invents none of it.
 *
 * **Blocked.** The same widget passes `blockedReason` when the plan names a model no server has («Нет Opus 5.5 — Анализ блоков
 * · обратитесь к администратору»). The button is then inactive and the reason is said beside it; «▾» is not drawn, since its one
 * item is another way to start the same run, and a thing that cannot be done is not offered (`R-153f`).
 *
 * There is no provider-mode selector and, on failure, no offer to start the run "in recorded mode
 * instead" — the mode this deployment is configured for is shown on the run and never chosen here. A
 * refusal of the start is said as itself beside the button and carries a retry under the same key
 * (`./start-run-failure.tsx`). There is no cancel and no re-run carryover: `P3-WEB-01` rules both out.
 */

import type { ReactNode } from 'react';

import type { ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { ErrorState, LoadingState, Menu } from '@/shared/ui';
import { routes } from '@/shared/lib';
import type { RunFailure } from '@/entities/audit-run';
import { classifyRunFailure } from '@/entities/audit-run';
import { executionFailure } from '@/entities/execution';
import { useMayActAsExpert } from '@/entities/account';

import { useRunCostApproval } from '../model/use-run-cost-approval';

import { StartRunCostDialog, UNCAPPED_MEANING } from './start-run-cost-dialog';
import { StartRunFailureView } from './start-run-failure';
import styles from './start-run-control.module.css';

/** The readiness line until wave 2 supplies the real one. */
export const DEFAULT_READINESS_NOTE = 'Маршрут: автоматически';

/** The one other way to start, in the «▾» menu. */
export const UNCAPPED_START_LABEL = 'Без денежного потолка (сбор статистики)';

export interface StartRunControlProps {
  /** The project the version belongs to, for the link a classification refusal carries. */
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** Called with the 202 reading, so the screen can move to run progress. */
  readonly onStarted?: ((run: RunStatus) => void) | undefined;
  /**
   * The one line under the button, once `getRunStartReadiness` fills it
   * («Набор: … · по подписке · Модели по этапам ▸»). Absent: «Маршрут: автоматически».
   */
  readonly readinessNote?: ReactNode | undefined;
  /**
   * Why the start is not possible now (`READINESS-WEB-01`): a model of the plan that no server has. Present, the button is
   * inactive and this is said under the line; absent or `null`, the start is offered as before.
   */
  readonly blockedReason?: ReactNode | undefined;
}

function StartRunControlInner({ projectUid, versionUid, onStarted, readinessNote, blockedReason }: StartRunControlProps) {
  const blocked = blockedReason !== undefined && blockedReason !== null && blockedReason !== false;
  const flow = useRunCostApproval(versionUid, onStarted);
  const estimateFailure = flow.estimateError === null ? null : executionFailure(flow.estimateError, false);
  const failure: RunFailure | null = flow.startError === null ? null : classifyRunFailure(flow.startError);

  return (
    <div className="am-form" data-start-run-control>
      <div className={styles.startRow}>
        <button
          type="button"
          className="am-button"
          data-start-run-button=""
          disabled={flow.busy || flow.dialog !== null || flow.comparisonOnly || blocked}
          onClick={() => flow.start(false)}
        >
          Запустить
        </button>
        {blocked ? null : (
          <span className={styles.more} title={`${UNCAPPED_START_LABEL}. ${UNCAPPED_MEANING}`} data-start-run-more="">
            <Menu
              label="Другие способы запуска"
              trigger={<span aria-hidden="true">▾</span>}
              items={[{ kind: 'action', label: UNCAPPED_START_LABEL, onChoose: () => flow.start(true) }]}
            />
          </span>
        )}
      </div>
      <p className="am-note" data-start-readiness="">{readinessNote ?? DEFAULT_READINESS_NOTE}</p>
      {blocked ? <p className={`am-note ${styles.blocked}`} role="status" data-start-blocked="">{blockedReason}</p> : null}

      {flow.estimating ? <LoadingState what="оценка стоимости" /> : null}
      {estimateFailure === null ? null : (
        <ErrorState
          title={flow.comparisonOnly ? 'Сервер не принимает этот PDF' : 'Стоимость не оценена'}
          detail={flow.comparisonOnly
            ? 'На этом сервере анализ раздела для PDF без пакета портала недоступен. Сообщите администратору: требуется обновление сервера.'
            : estimateFailure.detail}
          correlationId={estimateFailure.correlationId}
        />
      )}
      {flow.comparisonOnly ? (
        <p className="am-note">
          <a href={routes.stageComparison()}>Сравнение стадий</a>{' · '}
          <a href={routes.versionComparison()}>Сравнение версий</a>
        </p>
      ) : null}

      {flow.starting && flow.dialog === null ? <LoadingState what="запрос на прогон" /> : null}
      {failure === null ? null : (
        <StartRunFailureView failure={failure} projectUid={projectUid} versionUid={versionUid} onRetry={flow.retry} />
      )}

      {flow.dialog === null ? null : (
        <StartRunCostDialog
          estimate={flow.dialog.estimate}
          relaxed={flow.dialog.relaxed}
          ceiling={flow.dialog.ceiling}
          changed={flow.dialog.changed}
          busy={flow.busy}
          onCeilingChange={flow.setCeiling}
          onConfirm={flow.confirm}
          onCancel={flow.cancel}
        />
      )}
    </div>
  );
}

/**
 * `R-150e`: offered only to an account that may take an expert's action; the server refuses it
 * to anyone else. While the account is not known yet the control stays drawn. It is mounted per
 * version, so an answer that arrives for the version just left finds nothing to start.
 */
export function StartRunControl(props: StartRunControlProps) {
  const mayAct = useMayActAsExpert();
  if (!mayAct) return <p className="am-note" data-expert-only="StartRunControl">Запускать анализ может эксперт.</p>;
  return <StartRunControlInner key={props.versionUid} {...props} />;
}
