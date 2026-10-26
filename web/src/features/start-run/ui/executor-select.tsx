'use client';

/**
 * «Исполнитель» — the one choice the start-run control offers (`EXEC-PAR-WEB-01`).
 *
 * The options are «По умолчанию (маршрут)» and the connections of `entities/executor-connection`,
 * each with its kind, the model its current settings pin and the state of its last probe. A
 * connection that cannot serve now is listed **disabled, with the reason**, not hidden: a person
 * who looks for an executor and does not find it cannot tell a missing connection from one that
 * needs its key checked, and the sentence says what the administrator has to do. An archived
 * connection is not listed — it is retired — unless it is the one chosen, so a choice that stops
 * being usable between choosing and starting stays visible instead of silently turning into
 * another option.
 *
 * It is presentational: the list is read by the control, with the existing hooks, and arrives as
 * `reading`. When the list cannot be read the select says so and keeps its default option, so a
 * start on the route still works. It never lists, and never selects, an executor on the person's
 * behalf.
 *
 * Nothing rendered is a key, an address or a token: the labels are names, kinds, models and probe
 * sentences (`entities/executor-connection/model/start-choice.ts`).
 */

import type { ExecutorConnectionId } from '@/shared/api';
import { LoadingState } from '@/shared/ui';
import type { ExecutorChoice } from '@/entities/executor-connection';
import { choiceCanServe, executorChoiceLabel } from '@/entities/executor-connection';

import { chosenExecutor } from '../model/start-run-intent';

export type ExecutorListReading =
  | { readonly phase: 'loading' }
  | {
      readonly phase: 'failed';
      readonly detail: string;
      readonly correlationId: string | null;
      readonly onRetry: () => void;
    }
  | { readonly phase: 'ready'; readonly choices: readonly ExecutorChoice[] };

export interface ExecutorSelectViewProps {
  /** The DOM id the label points at. */
  readonly id: string;
  readonly reading: ExecutorListReading;
  /** The chosen connection, or `null` for «По умолчанию (маршрут)». */
  readonly value: ExecutorConnectionId | null;
  /** True while a start is in flight: the choice is the one that was sent. */
  readonly disabled: boolean;
  readonly onChange: (next: ExecutorConnectionId | null) => void;
}

export const DEFAULT_EXECUTOR_LABEL = 'По умолчанию (маршрут)';

/** The listed choices: no archived connection, except the one already chosen. */
function listed(choices: readonly ExecutorChoice[], value: ExecutorConnectionId | null): ExecutorChoice[] {
  return choices.filter((choice) => !choice.archived || choice.connectionId === value);
}

export function ExecutorSelectView({ id, reading, value, disabled, onChange }: ExecutorSelectViewProps) {
  const choices = reading.phase === 'ready' ? listed(reading.choices, value) : [];
  // A choice the list no longer holds (the connection vanished from a later read) stays selected
  // and visible, disabled, rather than letting the browser show the first option in its place.
  const chosenGone = value !== null && !choices.some((choice) => choice.connectionId === value);

  return (
    <div className="am-form__field" data-executor-select>
      <label htmlFor={id}>Исполнитель</label>
      <select
        id={id}
        value={value ?? ''}
        disabled={disabled}
        onChange={(event) => onChange(chosenExecutor(event.target.value))}
      >
        <option value="">{DEFAULT_EXECUTOR_LABEL}</option>
        {choices.map((choice) => (
          <option key={choice.connectionId} value={choice.connectionId} disabled={!choiceCanServe(choice)}>
            {executorChoiceLabel(choice)}
          </option>
        ))}
        {chosenGone ? (
          <option value={value} disabled>
            Выбранный исполнитель больше не в списке
          </option>
        ) : null}
      </select>

      {reading.phase === 'loading' ? <LoadingState what="исполнители" /> : null}

      {reading.phase === 'failed' ? (
        <>
          <p className="am-form__hint" role="status" data-executor-list-failure>
            Список исполнителей не прочитан. {reading.detail} Прогон можно запустить на исполнителе по
            умолчанию.
          </p>
          {reading.correlationId === null ? null : (
            <p className="am-form__hint">
              Идентификатор корреляции <code>{reading.correlationId}</code>
            </p>
          )}
          <div>
            <button
              type="button"
              className="am-button am-button--quiet am-button--small"
              onClick={reading.onRetry}
            >
              Прочитать список снова
            </button>
          </div>
        </>
      ) : null}

      {reading.phase === 'ready' ? (
        <p className="am-form__hint" data-executor-hint={value === null ? 'default' : 'chosen'}>
          {value === null
            ? 'Без выбора прогон идёт на исполнителе по назначению стенда.'
            : 'Прогон пойдёт только на выбранном исполнителе. Если он не сможет выполнить прогон, другой исполнитель не подставляется.'}
          {choices.length === 0 ? ' Подключений для выбора пока нет.' : ''}
        </p>
      ) : null}
    </div>
  );
}
