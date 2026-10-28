/**
 * The block «Сводка переходов» (`frontend/static/js/version-comparison.js:124-158`): one row per adjacent
 * transition A → B with its progress, «Листов», «✓ ◐ ● ⚠», «Состав +N / −M», the verdict sentence and «Открыть».
 *
 * The verdict is built from the verdict codes of the contract and the counts of the transition's summary
 * (`verdictSentence`); it is arithmetic, never a model's text. Above the table the state of the series, how far
 * it got, and the commands: «Отменить» while it runs, «Продолжить» for a paused series, «Досчитать» for one that
 * stopped. A series whose stored input no longer matches the order, the matrix or the pages says
 * «Сохранённая сводка для прежнего порядка версий.» and why. A pair of versions that are not neighbours is never
 * compared, and the block says so instead of showing an empty row.
 */

import type { ComparisonSeries, ComparisonTransition } from '@/shared/api';
import type { ComparisonFailure, SeriesAct } from '@/entities/version-series';
import {
  SERIES_STALE_LABELS,
  SERIES_STATE_LABELS,
  STALE_SERIES_NOTE,
  TRANSITION_STATE_LABELS,
  UNDESCRIBED_FAILURE,
  canCancelSeries,
  continueOf,
  progressPercent,
  staleReasonsLine,
  verdictParts,
  NO_VERDICT_YET,
} from '@/entities/version-series';

import { CommandRefusal } from './module-state';
import styles from './version-series.module.css';

export const NOT_COMPARED_NOTE =
  'Пара собрана по цепочке через промежуточные версии и не сравнивалась: сравниваются только соседние версии.';
export const CHOOSE_TWO_NOTE = 'Выберите две разные версии.';
export const NO_SERIES_NOTE = 'Сравнение соседних версий этого комплекта ещё не запускалось.';

export interface TransitionSummaryProps {
  readonly series: ComparisonSeries | null;
  /** The name of a version in the comparison order: «V1», «V2». */
  readonly names: ReadonlyMap<string, string>;
  /** The transition shown in the matrix as the pair A → B, if any. */
  readonly openTransitionId: string | null;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly failure: ComparisonFailure | null;
  /** The sides A and B are two versions that are not neighbours. */
  readonly notCompared: boolean;
  /** The sides are not two different versions. */
  readonly chooseTwo: boolean;
  readonly onOpen: (transition: ComparisonTransition) => void;
  readonly onAct: (act: SeriesAct) => void;
  readonly onStart: () => void;
}

function nameOf(names: ReadonlyMap<string, string>, versionUid: string): string {
  return names.get(versionUid) ?? '№?';
}

function TransitionRow({
  transition,
  names,
  current,
  onOpen,
}: {
  readonly transition: ComparisonTransition;
  readonly names: ReadonlyMap<string, string>;
  readonly current: boolean;
  readonly onOpen: (transition: ComparisonTransition) => void;
}) {
  const { summary } = transition;
  const ran = transition.state === 'completed' || transition.verdict !== undefined;
  return (
    <tr className={current ? styles.currentRow : undefined} data-transition-state={transition.state}>
      <th scope="row" className={styles.transitionName}>
        {nameOf(names, transition.source_version_uid)} → {nameOf(names, transition.target_version_uid)}
      </th>
      <td className={styles.progressCell} title={TRANSITION_STATE_LABELS[transition.state]}>
        <progress
          className={styles.progress}
          value={progressPercent(transition.items_done, transition.items_total)}
          max={100}
          aria-label="Ход расчёта перехода"
        />
        <span className={styles.note}>
          {transition.items_total > 0
            ? `${transition.items_done} из ${transition.items_total}`
            : TRANSITION_STATE_LABELS[transition.state]}
        </span>
        {summary.failed > 0 ? <span className={styles.errorText}>ошибок: {summary.failed}</span> : null}
      </td>
      {ran ? (
        <>
          <td>{summary.compared}</td>
          <td>{summary.same}</td>
          <td>{summary.zones_only}</td>
          <td>{summary.different}</td>
          <td>{summary.needs_review}</td>
          <td>
            +{summary.added} / −{summary.removed}
          </td>
          <td className={styles.verdict}>
            {verdictParts(transition.verdict, summary).map((entry, index) => (
              <span key={entry.code} data-verdict-code={entry.code}>
                {index === 0 ? '' : '; '}
                {entry.text}
              </span>
            ))}
            {verdictParts(transition.verdict, summary).length === 0 ? NO_VERDICT_YET : null}
          </td>
        </>
      ) : (
        <td colSpan={7} className={styles.muted}>
          {TRANSITION_STATE_LABELS[transition.state]}
          {transition.failure_reason === undefined ? null : (
            <span data-failure-reason={transition.failure_reason}> · {UNDESCRIBED_FAILURE}</span>
          )}
        </td>
      )}
      <td>
        {transition.state === 'queued' ? null : (
          <button
            type="button"
            className="am-button am-button--small am-button--quiet"
            title="Показать в матрице этот переход: его версии станут выбранной парой «было → стало»."
            onClick={() => onOpen(transition)}
          >
            Открыть
          </button>
        )}
      </td>
    </tr>
  );
}

export function TransitionSummary({
  series,
  names,
  openTransitionId,
  mayAct,
  busy,
  failure,
  notCompared,
  chooseTwo,
  onOpen,
  onAct,
  onStart,
}: TransitionSummaryProps) {
  return (
    <section className={styles.block} aria-label="Сводка переходов" data-transition-summary="">
      {series === null ? (
        <>
          <p className={styles.blockHead}>
            <strong>Сводка переходов</strong>
            <span className={styles.muted}>{NO_SERIES_NOTE}</span>
            {mayAct ? (
              <button type="button" className="am-button am-button--small" disabled={busy} onClick={onStart}>
                Запустить
              </button>
            ) : null}
          </p>
          <CommandRefusal failure={failure} />
        </>
      ) : (
        <>
          <p className={styles.blockHead}>
            <strong>Сводка переходов</strong>
            <span className={styles.seriesState} data-series-state={series.state}>
              {SERIES_STATE_LABELS[series.state]}
            </span>
            <span className={styles.muted}>
              переходов готово: {series.transitions_done} из {series.transitions_total}
            </span>
            {mayAct && canCancelSeries(series.state) ? (
              <button
                type="button"
                className="am-button am-button--small am-button--quiet"
                disabled={busy}
                title="Остановить сравнение соседних версий. Уже посчитанные листы сохранятся."
                onClick={() => onAct('cancel')}
              >
                Отменить
              </button>
            ) : null}
            {mayAct && continueOf(series.state) === 'resume' ? (
              <button
                type="button"
                className="am-button am-button--small am-button--quiet"
                disabled={busy}
                title="Продолжить с того же места: посчитанное заново не считается."
                onClick={() => onAct('resume')}
              >
                Продолжить
              </button>
            ) : null}
            {mayAct && continueOf(series.state) === 'finish' ? (
              <button
                type="button"
                className="am-button am-button--small am-button--quiet"
                disabled={busy}
                title="Досчитать оставшиеся листы: посчитанное заново не считается."
                onClick={() => onAct('finish')}
              >
                Досчитать
              </button>
            ) : null}
          </p>
          <CommandRefusal failure={failure} />
          {(series.stale_reasons ?? []).length === 0 ? null : (
            <div className="am-note" data-series-stale="">
              <p>{STALE_SERIES_NOTE} {staleReasonsLine(series.stale_reasons)}</p>
              <ul className={styles.draftList}>
                {(series.stale_reasons ?? []).map((reason) => (
                  <li key={reason} data-series-stale-reason={reason}>
                    {SERIES_STALE_LABELS[reason]}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {series.failure_reason === undefined ? null : (
            <p className="am-note" data-failure-reason={series.failure_reason}>
              {UNDESCRIBED_FAILURE}
            </p>
          )}
          {(series.transitions ?? []).length === 0 ? null : (
            <div className={styles.scroller}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">Переход (было → стало)</th>
                    <th scope="col">Ход расчёта</th>
                    <th scope="col">Листов</th>
                    <th scope="col" title="Совпадает">✓</th>
                    <th scope="col" title="Изменены только служебные зоны">◐</th>
                    <th scope="col" title="Есть отличия">●</th>
                    <th scope="col" title="Нужна проверка">⚠</th>
                    <th scope="col">Состав</th>
                    <th scope="col">Вывод</th>
                    <th scope="col">
                      <span className={styles.visuallyHidden}>Действие</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {(series.transitions ?? []).map((transition) => (
                    <TransitionRow
                      key={transition.transition_id}
                      transition={transition}
                      names={names}
                      current={transition.transition_id === openTransitionId}
                      onOpen={onOpen}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      {chooseTwo ? <p className="am-note" data-choose-two="">{CHOOSE_TWO_NOTE}</p> : null}
      {notCompared ? <p className="am-note" data-not-compared="">{NOT_COMPARED_NOTE}</p> : null}
    </section>
  );
}
