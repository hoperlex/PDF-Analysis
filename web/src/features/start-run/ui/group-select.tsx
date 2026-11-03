'use client';

/**
 * «Группа» — the select drawn when a run is started on «Группа исполнителей» (`EXEC2-WEB-GROUPS-01`,
 * ADR-0026 decisions 12 to 14).
 *
 * The options are the groups that are not archived, each with the model it pins and the number of its
 * members; an archived group is not listed unless it is the one chosen, so a choice that stops being
 * usable between choosing and starting stays visible, disabled, instead of silently turning into
 * another option. There is no option that means «any group» and none is selected on the person's
 * behalf: with no group chosen the control keeps the start disabled (`../model/start-mode.ts`).
 *
 * The hint says what a group does with a start: it takes the run in, the connection and the model are
 * fixed only when the work is sent, and until then only the planned model is known. The `R-149a`
 * notice stands beside it, because the stand does not check whether a connection may receive client
 * documents.
 *
 * It is presentational, as the executor select is: `GroupSelect` reads the list and hands it over as
 * `reading`. Nothing rendered is an identifier, an address or a key.
 */

import type { ExecutorGroup, ExecutorGroupId } from '@/shared/api';
import { LoadingState } from '@/shared/ui';
import { CLIENT_DOCUMENTS_NOTICE } from '@/entities/executor-connection';
import { GROUP_BINDING_SENTENCE, groupFailure, useExecutorGroups } from '@/entities/executor-group';

export type GroupListReading =
  | { readonly phase: 'loading' }
  | {
      readonly phase: 'failed';
      readonly detail: string;
      readonly correlationId: string | null;
      readonly onRetry: () => void;
    }
  | { readonly phase: 'ready'; readonly groups: readonly ExecutorGroup[] };

export interface GroupSelectViewProps {
  /** The DOM id the label points at. */
  readonly id: string;
  readonly reading: GroupListReading;
  /** The chosen group, or `null` while none is chosen. */
  readonly value: ExecutorGroupId | null;
  /** True while a start is in flight: the choice is the one that was sent. */
  readonly disabled: boolean;
  readonly onChange: (next: ExecutorGroupId | null) => void;
}

export const GROUP_OPTION_NONE = 'Выберите группу';

export function chosenGroup(optionValue: string): ExecutorGroupId | null {
  return optionValue === '' ? null : optionValue;
}

/** «Основная группа · модель «…» · подключений: 2» — the name, the model, the size. */
export function groupOptionLabel(group: ExecutorGroup): string {
  const revision = group.current_revision;
  return `${group.display_name} · модель «${revision.pin_id}» · подключений: ${revision.members.length}`;
}

export function GroupSelectView({ id, reading, value, disabled, onChange }: GroupSelectViewProps) {
  const groups = reading.phase === 'ready'
    ? reading.groups.filter((group) => group.archived_at === undefined || group.group_id === value)
    : [];
  const chosen = groups.find((group) => group.group_id === value);
  const chosenGone = value !== null && chosen === undefined;

  return (
    <div className="am-form__field" data-group-select>
      <label htmlFor={id}>Группа</label>
      <select
        id={id}
        value={value ?? ''}
        disabled={disabled}
        onChange={(event) => onChange(chosenGroup(event.target.value))}
      >
        <option value="">{GROUP_OPTION_NONE}</option>
        {groups.map((group) => (
          <option key={group.group_id} value={group.group_id} disabled={group.archived_at !== undefined}>
            {group.archived_at === undefined ? groupOptionLabel(group) : `${groupOptionLabel(group)} — в архиве`}
          </option>
        ))}
        {chosenGone ? (
          <option value={value} disabled>
            Выбранной группы больше нет в списке
          </option>
        ) : null}
      </select>

      {reading.phase === 'loading' ? <LoadingState what="группы" /> : null}

      {reading.phase === 'failed' ? (
        <>
          <p className="am-form__hint" role="status" data-group-list-failure>
            Список групп не прочитан. {reading.detail} Прогон можно запустить в режиме «Автоматически (по типу задачи)».
          </p>
          {reading.correlationId === null ? null : (
            <p className="am-form__hint">
              Идентификатор корреляции <code>{reading.correlationId}</code>
            </p>
          )}
          <div>
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={reading.onRetry}>
              Прочитать группы снова
            </button>
          </div>
        </>
      ) : null}

      {reading.phase === 'ready' ? (
        <p className="am-form__hint" data-group-hint={value === null ? 'none' : 'chosen'}>
          {value === null
            ? GROUP_BINDING_SENTENCE
            : chosen === undefined
              ? 'Выбранной группы больше нет в списке. Обновите страницу или выберите другую.'
              : `Прогон принимает группа «${chosen.display_name}», модель «${chosen.current_revision.pin_id}». ${GROUP_BINDING_SENTENCE}`}
          {groups.length === 0 ? ' Групп для выбора пока нет.' : ''}
        </p>
      ) : null}
      <p className="am-form__hint" data-group-notice="client-documents">{CLIENT_DOCUMENTS_NOTICE}</p>
    </div>
  );
}

/** The select over the groups the stand has, read with `useExecutorGroups` (open to every role). */
export function GroupSelect(props: Omit<GroupSelectViewProps, 'reading'>) {
  const groups = useExecutorGroups();
  const failure = groups.data === undefined && groups.isError ? groupFailure(groups.error, false) : null;
  const reading: GroupListReading =
    failure !== null
      ? {
          phase: 'failed',
          detail: failure.detail,
          correlationId: failure.correlationId,
          onRetry: () => void groups.refetch(),
        }
      : groups.data === undefined
        ? { phase: 'loading' }
        : { phase: 'ready', groups: groups.data.items };
  return <GroupSelectView {...props} reading={reading} />;
}
