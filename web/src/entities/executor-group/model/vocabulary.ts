/**
 * The words of «Группы» and «Правила» (`EXEC2-WEB-GROUPS-01`, ADR-0026 decisions 10, 11, 14, 15
 * and 17).
 *
 * Every table is a `Record` over the contract's own value set, so a value the contract adds is a
 * type error here until it has a Russian sentence, and a value the contract removes leaves a key
 * nothing can reach.
 */

import type {
  ExecutorGroupMemberIssue,
  ExecutorRoutingMode,
  ExecutorRoutingPreviewIssue,
  ExecutorRoutingPreviewStatus,
} from '@/shared/api';

/** The longest name of a group: as long as the name of a connection. */
export const GROUP_NAME_MAX_LENGTH = 120;

/** A group holds one to sixteen members (`range` on the field `members`). */
export const GROUP_MEMBERS_MIN = 1;
export const GROUP_MEMBERS_MAX = 16;

/**
 * Why dispatch would not choose a member of a group now (`ExecutorGroupMemberStatus`). The first
 * applicable reason, in the contract's order, is the one the server reports.
 */
export const MEMBER_ISSUE_SENTENCES: Readonly<Record<ExecutorGroupMemberIssue, string>> = {
  revision_changed:
    'настройки подключения изменились после того, как группа его запомнила; сохраните новую версию группы',
  connection_archived: 'подключение в архиве',
  not_served: 'этот вид подключения пока не обслуживается',
  probe_not_ok: 'у текущего ключа нет успешной проверки',
  runner_offline: 'клиент подключения не на связи',
  at_capacity: 'все места подключения заняты',
  host_disabled: 'сервер выключен переключателем «Использовать»',
  model_not_verified: 'агент сервера не подтвердил эту модель',
  model_cooling_down: 'сервер временно снял модель после отказа',
};

/** The mode in words; the machine value stays in `data-routing-mode`. */
export const ROUTING_MODE_LABELS: Readonly<Record<ExecutorRoutingMode, string>> = {
  legacy: 'основное и резервное подключения',
  rules: 'правила по видам работы',
};

/** What the cut-over would do with one work kind. */
export const PREVIEW_STATUS_LABELS: Readonly<Record<ExecutorRoutingPreviewStatus, string>> = {
  ready: 'станет группой из одного подключения',
  no_route: 'назначения нет, правила не будет',
  incompatible: 'перенести нельзя',
};

/** Why a legacy route cannot become a one-member group. */
export const PREVIEW_ISSUE_SENTENCES: Readonly<Record<ExecutorRoutingPreviewIssue, string>> = {
  connection_archived: 'основное подключение в архиве',
  no_revision: 'у основного подключения нет настроек',
  kind_not_served: 'этот вид подключения пока не обслуживается',
};

/**
 * The strategy of a group is one: the lowest used-to-capacity ratio wins, and a rotation kept in
 * the database breaks ties. Said once, beside the group, so nobody expects a round robin.
 */
export const STRATEGY_SENTENCE =
  'Работа идёт на подключение группы с наименьшей загрузкой; при равной загрузке подключения чередуются.';

/**
 * What a group does with a start (decisions 13 to 16): the group is fixed when the work is
 * accepted, the connection and the model are fixed only when the work is sent. Said wherever a
 * group is offered for a choice, so nobody reads the plan as a fact.
 */
export const GROUP_BINDING_SENTENCE =
  'Группа фиксируется при приёме работы, подключение и модель фиксируются при отправке в работу. До этого показана только плановая модель, а пока ни одно подключение группы не подходит, работа ждёт в очереди.';
