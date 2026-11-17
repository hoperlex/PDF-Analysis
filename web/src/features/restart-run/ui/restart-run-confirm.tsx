'use client';

/**
 * `RUN-RESTART-01`: the open confirmation of «Перезапустить с этого этапа», drawn from plain data so a test and a preview can show it as
 * the screen does. Four things and two buttons: which chips are taken ready and which are computed again, what happens to the old run
 * and to the expert's decisions, the price and the consent (the one `CostApproval`, passed in), and, from the critic on, the one warning
 * about the norms.
 */

import type { ReactNode } from 'react';

import type { RestartPoint } from '@/shared/api';

import { pointName, pointNames, takesNorms } from '../model/points';

import styles from './restart-run-confirm.module.css';

/** What a restart does to the run it starts from (`R-155a`, `R-155b`, `R-155g`). */
export const RESTART_CONSEQUENCE =
  'Старый прогон будет удалён после публикации нового. Решения эксперта перенесутся на находки, которые повторятся дословно.';

/** Where a restart from the critic or later can stop (`restart_request_changed` at «Нормы»). */
export const RESTART_NORMS_WARNING =
  'Если поиск норм даст другой результат, перезапуск остановится на этапе «Нормы» — тогда перезапустите с «Норм».';

export interface RestartRunConfirmProps {
  readonly point: RestartPoint;
  /** The chips taken ready, or `null` while the price is not read. */
  readonly taken: readonly RestartPoint[] | null;
  /** The chips computed again, or `null` while the price is not read. */
  readonly computed: readonly RestartPoint[] | null;
  /** The price is being read. */
  readonly loading: boolean;
  /** The price and the consent (`CostApproval`), drawn once the price is read. */
  readonly cost: ReactNode;
  /** The sentence of a refusal or a failure, or `null`. */
  readonly failure: string | null;
  /** The command is on its way. */
  readonly sending: boolean;
  /** The consent is given and the price is read. */
  readonly canSend: boolean;
  readonly onSend: () => void;
  readonly onCancel: () => void;
}

export function RestartRunConfirm({
  point, taken, computed, loading, cost, failure, sending, canSend, onSend, onCancel,
}: RestartRunConfirmProps) {
  return (
    <section
      className={styles.confirm}
      role="group"
      aria-label={`Перезапуск с этапа «${pointName(point)}»`}
      data-run-restart="dialog"
      data-restart-point={point}
    >
      {loading ? <p className={styles.note} role="status">Загрузка: оценка стоимости перезапуска</p> : null}
      {taken === null || computed === null ? null : (
        <dl className={styles.plan} data-restart-plan="">
          {taken.length === 0 ? null : (
            <>
              <dt>Берётся готовым</dt>
              <dd data-restart-taken="">{pointNames(taken)}</dd>
            </>
          )}
          <dt>Выполняется заново</dt>
          <dd data-restart-computed="">{pointNames(computed)}</dd>
        </dl>
      )}
      <p className={styles.note} data-restart-consequence="">{RESTART_CONSEQUENCE}</p>
      {takesNorms(point) ? <p className={styles.warning} data-restart-norms-warning="">{RESTART_NORMS_WARNING}</p> : null}
      {cost}
      {failure === null ? null : <p className={styles.failure} role="alert" data-restart-failure="">{failure}</p>}
      <div className={styles.buttons}>
        <button type="button" className="am-button" disabled={sending || loading || !canSend} data-restart-send="" onClick={onSend}>
          Перезапустить
        </button>
        <button type="button" className="am-button am-button--quiet" disabled={sending} data-restart-cancel="" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </section>
  );
}
