/**
 * The notice of connection changes in the last seven days (`EXEC-HTTP-01`, plan §4.3 T-1).
 *
 * A stolen administrator session redirects a connection by changing it, so every change is
 * an audit event on the server and the screen makes the recent ones hard to miss. The
 * contract exposes no event list for connections; the screen reads the changes from what the
 * reads already carry: a connection's creation and archiving, each revision, each secret
 * (when it was set and by whom — never its value) and each route.
 *
 * `asOf` is the instant the reads were taken (the query's `dataUpdatedAt`), passed in so
 * the window is the same on the server render and in the browser, and a test can fix it.
 */

import type {
  ExecutorConnection,
  ExecutorConnectionDetail,
  ExecutorRoute,
} from '@/shared/api';

export const CHANGE_WINDOW_DAYS = 7;
const DAY_MS = 24 * 60 * 60 * 1000;

export type ChangeKind = 'created' | 'revised' | 'secret_set' | 'archived' | 'route_set';

export interface ConnectionChange {
  readonly kind: ChangeKind;
  readonly at: string;
  readonly by: string | null;
  /** The connection's name, or the kind of work for a route. */
  readonly subject: string;
  /** The revision number for `revised`; `null` otherwise. */
  readonly revisionNo: number | null;
}

export const CHANGE_LABELS: Readonly<Record<ChangeKind, string>> = {
  created: 'Создано подключение',
  revised: 'Изменены настройки подключения',
  secret_set: 'Введён ключ подключения',
  archived: 'Подключение архивировано',
  route_set: 'Изменено назначение',
};

function within(at: string | undefined, asOf: number): at is string {
  if (at === undefined) return false;
  const moment = Date.parse(at);
  if (!Number.isFinite(moment)) return false;
  return moment <= asOf && asOf - moment <= CHANGE_WINDOW_DAYS * DAY_MS;
}

/**
 * Every change within the window, newest first. A connection whose detail has not been read
 * still contributes what the list carries (creation, archiving, its secrets); the revisions
 * join when the detail arrives.
 */
export function recentChanges(
  connections: readonly ExecutorConnection[],
  details: ReadonlyMap<string, ExecutorConnectionDetail>,
  routes: readonly ExecutorRoute[],
  asOf: number,
  labelOfWork: (workKind: ExecutorRoute['work_kind']) => string,
): readonly ConnectionChange[] {
  const found: ConnectionChange[] = [];
  for (const connection of connections) {
    const name = connection.display_name;
    if (within(connection.created_at, asOf)) {
      found.push({ kind: 'created', at: connection.created_at, by: connection.created_by, subject: name, revisionNo: null });
    }
    if (within(connection.archived_at, asOf)) {
      found.push({ kind: 'archived', at: connection.archived_at, by: null, subject: name, revisionNo: null });
    }
    for (const secret of connection.secrets) {
      if (within(secret.set_at, asOf)) {
        found.push({ kind: 'secret_set', at: secret.set_at, by: secret.set_by, subject: name, revisionNo: null });
      }
    }
    for (const revision of details.get(connection.connection_id)?.revisions ?? []) {
      if (within(revision.created_at, asOf)) {
        found.push({ kind: 'revised', at: revision.created_at, by: revision.created_by, subject: name, revisionNo: revision.revision_no });
      }
    }
  }
  for (const route of routes) {
    if (within(route.set_at, asOf)) {
      found.push({ kind: 'route_set', at: route.set_at, by: route.set_by, subject: labelOfWork(route.work_kind), revisionNo: null });
    }
  }
  return found.sort((left, right) => Date.parse(right.at) - Date.parse(left.at));
}
