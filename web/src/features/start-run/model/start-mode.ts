/**
 * The three ways a run is started, and the one selector each sends (`EXEC2-WEB-GROUPS-01`,
 * ADR-0026 decisions 12 to 14).
 *
 * - «Автоматически (по типу задачи)»: no selector. The stand routes the run: by the rule of its kind of
 *   work when the routing mode is `rules`, by the legacy Primary/Standby route otherwise.
 * - «Группа исполнителей»: `executor_group_id`. The stand admits the run on the group; the connection and
 *   the model are fixed when the work is sent, and before that only the planned model is known.
 * - «Конкретное подключение»: `preset_id` when a preset is chosen (it names the connection), otherwise
 *   `executor_connection_id`. The run goes on that connection and on no other.
 *
 * **The three are exclusive.** The contract refuses a start that names a group together with a
 * connection or a preset, and a preset together with a connection. `startSelectors` is the one place
 * the choice becomes selectors, and it returns **at most one**, whatever the control's state holds.
 *
 * **A mode that has not been filled in is not a start.** «Группа исполнителей» without a group, and
 * «Конкретное подключение» with neither a connection nor a preset, would send nothing — which is
 * «Автоматически» — while the screen says otherwise. That is a silent fallback, so such a choice is
 * incomplete and the control keeps the start disabled and says what is missing.
 */

import type { ExecutorConnectionId, ExecutorGroupId, PresetId } from '@/shared/api';

export const START_MODES = ['auto', 'group', 'connection'] as const;

export type StartMode = (typeof START_MODES)[number];

export const START_MODE_LABELS: Readonly<Record<StartMode, string>> = {
  auto: 'Автоматически (по типу задачи)',
  group: 'Группа исполнителей',
  connection: 'Конкретное подключение',
};

export const START_MODE_HINTS: Readonly<Record<StartMode, string>> = {
  auto: 'Исполнителя выбирает стенд: по правилу вида работы, когда включены правила, иначе по назначению подключения. Вручную ничего не передаётся.',
  group: 'Прогон принимает выбранная группа. Подключение и модель фиксируются при отправке в работу; до этого показана только плановая модель.',
  connection: 'Прогон идёт только на выбранном подключении или на подключении выбранного пресета. Вместо него другое подключение не подставляется.',
};

/** What a mode without its choice is missing, in words. */
export const START_CHOICE_MISSING: Readonly<Record<'group' | 'connection', string>> = {
  group: 'Выберите группу или переключитесь на «Автоматически (по типу задачи)»: без группы прогон нельзя запустить как групповой.',
  connection: 'Выберите подключение или пресет либо переключитесь на «Автоматически (по типу задачи)»: без выбора прогон нельзя запустить как «Конкретное подключение».',
};

export interface StartChoice {
  readonly mode: StartMode;
  readonly groupId: ExecutorGroupId | null;
  readonly connectionId: ExecutorConnectionId | null;
  readonly presetId: PresetId | null;
}

export const AUTOMATIC_CHOICE: StartChoice = { mode: 'auto', groupId: null, connectionId: null, presetId: null };

/** The three selectors of a start; at most one is not `null`. */
export interface StartSelectors {
  readonly executorGroupId: ExecutorGroupId | null;
  readonly executorConnectionId: ExecutorConnectionId | null;
  readonly presetId: PresetId | null;
}

/**
 * The selectors a choice sends: none for «Автоматически», the group for «Группа исполнителей», the
 * preset if there is one and otherwise the connection for «Конкретное подключение». Whatever else the
 * choice holds is not sent, so a leftover from another mode never reaches the request.
 */
export function startSelectors(choice: StartChoice): StartSelectors {
  switch (choice.mode) {
    case 'group':
      return { executorGroupId: choice.groupId, executorConnectionId: null, presetId: null };
    case 'connection':
      return choice.presetId !== null
        ? { executorGroupId: null, executorConnectionId: null, presetId: choice.presetId }
        : { executorGroupId: null, executorConnectionId: choice.connectionId, presetId: null };
    case 'auto':
      return { executorGroupId: null, executorConnectionId: null, presetId: null };
  }
}

/** How many selectors a choice sends: zero or one, by construction. */
export function selectorCount(choice: StartChoice): number {
  const selectors = startSelectors(choice);
  return [selectors.executorGroupId, selectors.executorConnectionId, selectors.presetId]
    .filter((value) => value !== null).length;
}

/** True when the choice may be sent: «Автоматически», or a mode whose own choice has been made. */
export function startChoiceComplete(choice: StartChoice): boolean {
  switch (choice.mode) {
    case 'auto':
      return true;
    case 'group':
      return choice.groupId !== null;
    case 'connection':
      return choice.connectionId !== null || choice.presetId !== null;
  }
}

/**
 * The choice after the person picks a mode with the radio: everything that belongs to another mode is
 * dropped, so it cannot come back when the person returns, and cannot be sent from here.
 */
export function chooseMode(choice: StartChoice, mode: StartMode): StartChoice {
  switch (mode) {
    case 'auto':
      return AUTOMATIC_CHOICE;
    case 'group':
      return { mode, groupId: choice.mode === 'group' ? choice.groupId : null, connectionId: null, presetId: null };
    case 'connection':
      return {
        mode,
        groupId: null,
        connectionId: choice.mode === 'connection' ? choice.connectionId : null,
        presetId: choice.mode === 'connection' ? choice.presetId : null,
      };
  }
}
