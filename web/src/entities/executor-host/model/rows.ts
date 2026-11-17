/**
 * What a server row says (`HOSTS-WEB-01`, plan 2026-11-09 §7.2), as pure functions of a `listExecutorHosts` answer.
 *
 * The card is: a dot and the word of the state, the name, the switch «Использовать», the last signal, the models without prefixes,
 * the mark «API» on a paid model only, a load «2/3», what it is doing now (`UIP-S15-03`) and the menu «⋮». A server with no
 * contact is a grey card «нет связи с 14:02»; a server with no usable model says «нет доступных моделей». **A model that cannot be used now is not a chip** (plan §6): the contract lists only usable models,
 * and this module drops anything else it is handed, so a list never draws what is unavailable.
 */

import type { ExecutorHost, ExecutorHostList, ExecutorHostModel } from '@/shared/api';

import { modelLabel } from './models';

export interface ModelChip {
  readonly modelId: string;
  /** «Opus 5.5». */
  readonly label: string;
  /** Paid: no subscription serves it on this server, only a key. */
  readonly api: boolean;
  /** Every slot of the provider is in use: the model can be used, the server has no free place for it. */
  readonly busy: boolean;
}

/** The chips of a server: one per usable model, in the order the server lists them. */
export function modelChips(models: readonly ExecutorHostModel[]): readonly ModelChip[] {
  const byModel = new Map<string, { api: boolean; busy: boolean }>();
  for (const model of models) {
    // The type allows only the two usable states; a value the contract may add later is not a usable model.
    if (model.state !== 'available' && model.state !== 'busy') continue;
    const seen = byModel.get(model.model_id);
    const api = model.access === 'api';
    const busy = model.state === 'busy';
    // The same model served by a subscription and by a key is a subscription model, and free if either is free.
    byModel.set(model.model_id, seen === undefined ? { api, busy } : { api: seen.api && api, busy: seen.busy && busy });
  }
  return [...byModel].map(([modelId, flags]) => ({ modelId, label: modelLabel(modelId), ...flags }));
}

export type HostRowTone = 'ok' | 'busy' | 'offline';

/** How many tasks a card names under «Сейчас:»; the rest of them are «и ещё N». */
export const WORK_SHOWN = 3;

/**
 * One thing a server is doing now, as a card says it (`UIP-S15-03`, `Г12-B`): the document and where to open it, the stage as the
 * code names it, and since when. The stage is the code, not a word: the word is the layout's (`rowOfStageKey`), and this entity
 * does not read that one (`stage-layout` reads this one). Nothing of how it is done — no model, no run, no task number.
 */
export interface HostWorkReading {
  readonly key: string;
  readonly projectUid: string;
  readonly documentUid: string;
  readonly title: string;
  /** The stage as the server named it; `null` when it named none. */
  readonly stageKey: string | null;
  readonly since: string;
}

export interface HostRowReading {
  readonly hostId: string;
  readonly name: string;
  readonly tone: HostRowTone;
  readonly enabled: boolean;
  readonly chips: readonly ModelChip[];
  /** «2/3», the slots in use of all. */
  readonly load: string;
  readonly slotsInUse: number;
  readonly slotsTotal: number;
  /** An offline row: the model chips are not drawn, the row says when the contact was lost. */
  readonly noContact: boolean;
  /** An online row with nothing usable on it. */
  readonly noModels: boolean;
  /** The last time the server was heard from, as the server says it; absent for a server that has never been in touch. */
  readonly lastSeen: string | undefined;
  /** What the server is doing now, oldest first, at most `WORK_SHOWN`. A server out of contact is not known to run anything. */
  readonly work: readonly HostWorkReading[];
  /** How many more tasks than `work` names. */
  readonly workMore: number;
}

export function hostRowReading(host: ExecutorHost): HostRowReading {
  const noContact = host.state === 'offline';
  const chips = noContact ? [] : modelChips(host.models);
  // `current_work` is set by the list and left out by every other answer: absent is nothing to say, never a guess.
  const all = noContact ? [] : (host.current_work ?? []);
  return {
    hostId: host.host_id,
    name: host.display_name,
    tone: noContact ? 'offline' : host.state === 'busy' ? 'busy' : 'ok',
    enabled: host.enabled,
    chips,
    load: `${host.slots_in_use}/${host.slots_total}`,
    slotsInUse: host.slots_in_use,
    slotsTotal: host.slots_total,
    noContact,
    noModels: !noContact && chips.length === 0,
    lastSeen: host.last_seen_at,
    work: all.slice(0, WORK_SHOWN).map((item, index) => ({
      key: `${item.document_uid}:${item.stage_key ?? ''}:${item.since}:${index}`,
      projectUid: item.project_uid,
      documentUid: item.document_uid,
      title: item.document_title,
      stageKey: item.stage_key === undefined || item.stage_key === '' ? null : item.stage_key,
      since: item.since,
    })),
    workMore: Math.max(0, all.length - WORK_SHOWN),
  };
}

/** The servers the screen lists: not the archived ones («Удалить» archives, and an archived server is gone from the list). */
export function liveHosts(list: ExecutorHostList): readonly ExecutorHost[] {
  return list.items.filter((host) => host.archived_at === undefined);
}

/**
 * The models some server can serve now: what the layout editor offers beside the current one. A server that is off, out of
 * contact or archived serves nothing, whatever its last report listed.
 */
export function availableModelIds(list: ExecutorHostList | undefined): readonly string[] {
  if (list === undefined) return [];
  const ids = new Set<string>();
  for (const host of liveHosts(list)) {
    if (!host.enabled || host.state === 'offline') continue;
    for (const chip of modelChips(host.models)) ids.add(chip.modelId);
  }
  return [...ids];
}
