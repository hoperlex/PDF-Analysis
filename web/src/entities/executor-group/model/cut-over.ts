/**
 * The cut-over from the legacy routes to rules, in words and in the request it confirms
 * (`EXEC2-WEB-GROUPS-01`, ADR-0026 decision 17).
 *
 * The server proposes (`previewExecutorRouting`): per work kind, a one-member group made from the
 * primary of the legacy route. A standby is shown and **never converted into a member**; a route
 * that cannot become a group is flagged with its reason; a work kind with no route gets no rule.
 * The administrator confirms the proposal line by line: the request carries the `preview_digest`
 * that was shown and a `mapping` naming each `ready` work kind and the group to create for it. The
 * groups, the rules and the mode are then created in one transaction, and a digest that is no
 * longer the one now computed is refused as stale.
 *
 * The way back is `legacy`: it takes neither the digest nor the mapping, touches neither groups nor
 * rules, and leaves work already admitted by rules to finish on its own group revisions. It is
 * never read through a legacy route.
 */

import type {
  ExecutorRoutingMappingEntry,
  ExecutorRoutingPreview,
  ExecutorRoutingPreviewItem,
  ExecutorWorkKind,
} from '@/shared/api';
import { EXECUTOR_WORK_KIND_VALUES } from '@/shared/api';

/** The label of the button that opens the proposal. */
export const CUT_OVER_LABEL = 'Перейти на правила';

/**
 * The label of the button that asks to go back to the legacy routes. The task worded it «Вернуться к Primary/Standby»;
 * the rendered-language guard (R-18) refuses the two English words on a screen, and the routes tab already says the
 * same pair in Russian («основное» and «резервное» подключение), so the label does too (`EXEC2-FIX-WEB`).
 */
export const ROLLBACK_LABEL = 'Вернуться к основному и резервному подключению';

/** The checkbox that makes the confirmation explicit. */
export const MAPPING_CONFIRMATION_LABEL = 'Я проверил соответствие и подтверждаю переход';

/** The button that sends the confirmed mapping. */
export const CUT_OVER_CONFIRM_LABEL = 'Подтвердить переход на правила';

/** The button that sends the rollback after its confirmation. */
export const ROLLBACK_CONFIRM_LABEL = 'Подтвердить возврат';

/**
 * What the rollback says before it is sent. The last sentence is the one the owner asked for:
 * work already admitted stays on its group.
 */
export const ROLLBACK_CONFIRMATION =
  'Вернуться к основным и резервным подключениям? Новая работа пойдёт по назначениям, а группы и правила сохранятся, но не будут использоваться. Работа, которую уже приняли по правилам или на группу, остаётся на своей группе и дойдёт до конца там: назначения её не перечитывают.';

/** What the confirmation of the cut-over states, so the administrator signs the actual effect. */
export const CUT_OVER_CONFIRMATION =
  'Подтверждение создаст перечисленные группы из одного подключения, правила по ним и включит режим правил одним действием. Резервные подключения в состав групп не переходят. Работа, принятая до перехода, идёт как шла.';

export const NO_READY_ITEMS =
  'Переносить нечего: ни у одного вида работы нет назначения, которое можно сделать группой. Подтвердить переход нельзя.';

/** The preview items in the contract's order of work kinds, one per known kind the server returned. */
export function previewItems(preview: ExecutorRoutingPreview): ExecutorRoutingPreviewItem[] {
  const order = (kind: ExecutorWorkKind): number => EXECUTOR_WORK_KIND_VALUES.indexOf(kind);
  return preview.items
    .filter((item) => order(item.work_kind) >= 0)
    .sort((a, b) => order(a.work_kind) - order(b.work_kind));
}

/** The items the cut-over would convert. */
export function readyItems(preview: ExecutorRoutingPreview): ExecutorRoutingPreviewItem[] {
  return previewItems(preview).filter((item) => item.status === 'ready');
}

/**
 * The mapping the confirmation carries: each `ready` work kind and the name the server proposed
 * for its group. A `ready` item without a proposed name is left out, and the server then refuses
 * the mapping as incomplete: no name is invented here.
 */
export function cutOverMapping(preview: ExecutorRoutingPreview): ExecutorRoutingMappingEntry[] {
  const entries: ExecutorRoutingMappingEntry[] = [];
  for (const item of readyItems(preview)) {
    if (item.proposed_group_name === undefined) continue;
    entries.push({ work_kind: item.work_kind, group_display_name: item.proposed_group_name });
  }
  return entries;
}

/** True when the proposal has something to convert and every `ready` item can be named. */
export function cutOverCanBeConfirmed(preview: ExecutorRoutingPreview): boolean {
  const ready = readyItems(preview);
  return ready.length > 0 && cutOverMapping(preview).length === ready.length;
}
