/**
 * What the start-run control offers as «Исполнитель» (`EXEC-PAR-WEB-01`): the connections a run
 * can be started on, each with the part of its current settings a person chooses by.
 *
 * **There is one definition of «can serve now», and it is not here.** `routeBlocker` in
 * `./readiness.ts` is the rule «Назначения» already applies: a served kind, a finished `ok` probe
 * of the current settings on the current key, not archived. This module asks it and words the
 * answer; a connection it blocks is listed disabled, with the reason, so the person sees what an
 * administrator has to do instead of an executor that is missing. The server checks the same rule
 * again when the run starts, and an explicit choice is never replaced by another executor.
 *
 * Nothing here is a key, an address or a token: the label carries the name an administrator gave
 * the connection, its kind, the model its current settings pin, and the state of the last probe.
 */

import type {
  ExecutorConnection,
  ExecutorConnectionDetail,
  ExecutorConnectionId,
  ExecutorKind,
  ExecutorProbeState,
  ExecutorRevision,
} from '@/shared/api';

import type { RouteBlocker } from './readiness';
import { ROUTE_BLOCKER_SENTENCES, currentRevision, routeBlocker } from './readiness';
import { KIND_LABELS, PROBE_OUTCOME_SENTENCES } from './vocabulary';

/** Why a connection is not offered: a readiness blocker, or its settings have not been read. */
export type ChoiceBlocker = RouteBlocker | 'unread';

export const CHOICE_BLOCKER_SENTENCES: Readonly<Record<ChoiceBlocker, string>> = {
  ...ROUTE_BLOCKER_SENTENCES,
  unread: 'настройки подключения не прочитаны',
};

/** The state of a probe that has not finished; a finished one is worded by its outcome. */
const OPEN_PROBE_SENTENCES: Readonly<Record<Exclude<ExecutorProbeState, 'finished'>, string>> = {
  requested: 'запрошена, ждёт процесс',
  running: 'выполняется',
};

export interface ExecutorChoice {
  readonly connectionId: ExecutorConnectionId;
  readonly name: string;
  readonly kind: ExecutorKind;
  readonly archived: boolean;
  /** The model the current settings pin, or `null` when the connection has no settings yet. */
  readonly model: string | null;
  /** The last probe in words, or `null` when the current settings have never been probed. */
  readonly probe: string | null;
  /** `null` exactly when a run can start on this connection now. */
  readonly blocker: ChoiceBlocker | null;
}

function probeSentence(revision: ExecutorRevision | undefined): string | null {
  const probe = revision?.latest_probe;
  if (probe === undefined) return null;
  if (probe.state !== 'finished') return OPEN_PROBE_SENTENCES[probe.state];
  return probe.outcome === undefined ? null : PROBE_OUTCOME_SENTENCES[probe.outcome];
}

/**
 * Every connection as a choice, in the order the list came in. `details` holds the connections
 * whose settings were read; an archived connection is judged without them, any other connection
 * absent from it is `unread` and is not offered.
 */
export function executorChoices(
  connections: readonly ExecutorConnection[],
  details: ReadonlyMap<string, ExecutorConnectionDetail>,
): ExecutorChoice[] {
  return connections.map((connection) => {
    const detail = details.get(connection.connection_id);
    const revision = detail === undefined ? undefined : currentRevision(connection, detail.revisions);
    const archived = connection.archived_at !== undefined;
    return {
      connectionId: connection.connection_id,
      name: connection.display_name,
      kind: connection.kind,
      archived,
      model: revision?.pin_id ?? null,
      probe: probeSentence(revision),
      blocker: archived || detail !== undefined ? routeBlocker(connection, revision) : 'unread',
    };
  });
}

/** True exactly when a run can start on this connection now. */
export function choiceCanServe(choice: ExecutorChoice): boolean {
  return choice.blocker === null;
}

/**
 * The text of one option: the name, the kind, the pinned model and the last probe, and for a
 * connection that cannot serve, why — the same sentence «Назначения» gives.
 */
export function executorChoiceLabel(choice: ExecutorChoice): string {
  const parts = [`${choice.name} (${KIND_LABELS[choice.kind]})`];
  if (choice.model !== null) parts.push(`модель «${choice.model}»`);
  parts.push(choice.probe === null ? 'проверок не было' : `проверка: ${choice.probe}`);
  const head = parts.join(' · ');
  return choice.blocker === null ? head : `${head} — недоступно: ${CHOICE_BLOCKER_SENTENCES[choice.blocker]}`;
}
