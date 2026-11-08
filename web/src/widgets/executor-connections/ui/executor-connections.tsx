'use client';

/**
 * «Подключения» (`EXEC-HTTP-01`): where the stand sends model work, and what is known about each
 * connection without its key.
 *
 * Any role reads the list (`R-80`); only an administrator is shown the controls, and the server
 * checks every write. Above the list sits the notice of connection changes in the last seven
 * days (plan T-1): a stolen administrator session redirects a connection by changing it, so the
 * recent changes are hard to miss. Below it, an administrator can add a connection.
 *
 * `EXEC2-WEB-CAP-01` (`R-149a`): under the notice of changes stands the notice that client
 * documents are not checked, so capacity above one and groups are for test data. It is drawn for
 * every role and whether or not the list is empty, because it qualifies what the list lets an
 * administrator set, not what one connection holds.
 *
 * `EXEC2-WEB-WIZARD-01`: below the list, «Добавить подключение» opens the wizard
 * (`features/connect-remote-agent`) — a remote Ubuntu agent, installed over SSH or by one command, or
 * an API provider (the OpenRouter preset) — and keeps the older form with every field one button away.
 * The wizard is closed until the button is pressed, so an empty list shows the button and the
 * empty-state sentence that points at it.
 *
 * The key form is a **slot**. It is rendered on the server by the route (a server component,
 * `features/set-executor-secret`) and arrives here as an element, so this client component
 * never touches the key: it only decides where on the page the form sits.
 */

import type { ReactNode } from 'react';

import type { Role } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { canExecute, executionFailure } from '@/entities/execution';
import {
  CHANGE_LABELS,
  CHANGE_WINDOW_DAYS,
  CLIENT_DOCUMENTS_NOTICE,
  WORK_KIND_LABELS,
  recentChanges,
  useExecutorConnectionDetails,
  useExecutorConnections,
  useExecutorRoutes,
} from '@/entities/executor-connection';
import { ConnectWizardLauncher } from '@/features/connect-remote-agent';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import { ConnectionCard } from './connection-card';
import styles from './executor-connections.module.css';

export interface ExecutorConnectionsProps {
  readonly roles: readonly Role[];
  /** The connection the key form was opened for, from the address. */
  readonly secretConnectionId?: string | null | undefined;
  /** The server-rendered key form for `secretConnectionId`. */
  readonly secretForm?: ReactNode | undefined;
}

/** The newest changes shown in the open; the rest of the ten are one click away. */
const VISIBLE_CHANGES = 3;

function ChangeLine({ change }: { readonly change: ReturnType<typeof recentChanges>[number] }) {
  return (
    <li>
      <time dateTime={change.at}>{formatInstant(change.at)}</time>: {CHANGE_LABELS[change.kind]} «{change.subject}»
      {change.revisionNo !== null ? `, версия ${change.revisionNo}` : ''}
      {change.by !== null ? <>, автор <code>{change.by}</code></> : null}
    </li>
  );
}

function ChangesNotice({ changes }: { readonly changes: ReturnType<typeof recentChanges> }) {
  if (changes.length === 0) {
    return (
      <p role="status" className="am-note" data-executor-changes="0">
        За последние {CHANGE_WINDOW_DAYS} дней подключения не менялись.
      </p>
    );
  }
  return (
    <section className={`am-note ${styles.changes}`} role="status" aria-label="Изменения подключений" data-executor-changes={changes.length}>
      <p>
        <strong>За последние {CHANGE_WINDOW_DAYS} дней подключения менялись: {changes.length}.</strong>{' '}
        Проверьте, что это сделали вы или ваши коллеги: подмену адреса подключения проще всего заметить здесь.
      </p>
      <ul>
        {changes.slice(0, VISIBLE_CHANGES).map((change, index) => <ChangeLine key={`${change.kind}-${change.at}-${index}`} change={change} />)}
      </ul>
      {changes.length > VISIBLE_CHANGES ? (
        <details className={styles.moreChanges} data-executor-changes-more={Math.min(changes.length, 10) - VISIBLE_CHANGES}>
          <summary>Ещё изменений: {Math.min(changes.length, 10) - VISIBLE_CHANGES}</summary>
          <ul>
            {changes.slice(VISIBLE_CHANGES, 10).map((change, index) => (
              <ChangeLine key={`${change.kind}-${change.at}-${index + VISIBLE_CHANGES}`} change={change} />
            ))}
          </ul>
        </details>
      ) : null}
      {changes.length > 10 ? <p>Показаны десять последних.</p> : null}
    </section>
  );
}

export function ExecutorConnections({ roles, secretConnectionId = null, secretForm }: ExecutorConnectionsProps) {
  const list = useExecutorConnections();
  const items = list.data?.items ?? [];
  const reading = useExecutorConnectionDetails(items.map((item) => item.connection_id));
  const routes = useExecutorRoutes();
  const canManage = canExecute(roles, 'connections');

  if (list.isPending) return <LoadingState what="подключения" />;
  if (list.isError) {
    const failure = executionFailure(list.error, false);
    return (
      <div data-executor-read-failure={failure.kind}>
        <ErrorState title="Подключения не прочитаны" detail={failure.detail} correlationId={failure.correlationId} onRetry={() => void list.refetch()} />
      </div>
    );
  }

  const pinnedModels = list.data.pinned_models;
  const changes = recentChanges(items, reading.details, routes.data?.items ?? [], list.dataUpdatedAt, (work) => WORK_KIND_LABELS[work]);
  const keyTarget = secretConnectionId === null ? undefined : items.find((item) => item.connection_id === secretConnectionId);

  return (
    <div className={styles.panel} data-executor-connections>
      <ChangesNotice changes={changes} />
      <p className="am-note" data-executor-list-notice="client-documents">{CLIENT_DOCUMENTS_NOTICE}</p>

      {canManage && secretConnectionId !== null && secretForm !== undefined ? (
        <section className="am-section" aria-label="Ввод ключа подключения" data-executor-secret-section={secretConnectionId}>
          <h2>Ключ подключения{keyTarget !== undefined ? ` «${keyTarget.display_name}»` : ''}</h2>
          {keyTarget === undefined ? (
            <p className="am-note" role="status" data-executor-secret-target="missing">
              Такого подключения нет в списке. Обновите страницу или выберите подключение ниже.
            </p>
          ) : keyTarget.kind !== 'http_api' || keyTarget.archived_at !== undefined ? (
            <p className="am-note" role="status" data-executor-secret-target="none">
              Вводимый ключ есть только у живых подключений вида «HTTP API». Ключ SSH создаётся
              кнопкой «Создать ключ» в карточке подключения.
            </p>
          ) : (
            secretForm
          )}
          <p><a href="/workers?tab=connections">Закрыть форму ключа</a></p>
        </section>
      ) : null}

      {items.length === 0 ? (
        <EmptyState
          title="Подключений нет"
          detail={canManage
            ? 'Добавьте первое подключение кнопкой ниже: удалённого агента или API-провайдера. Затем модель из закреплённых, вход или ключ и проверка.'
            : 'Администратор ещё не добавил ни одного подключения.'}
        />
      ) : (
        <ol className={styles.list} aria-label="Подключения" data-executor-list>
          {items.map((connection) => (
            <ConnectionCard
              key={connection.connection_id}
              connection={connection}
              detail={reading.details.get(connection.connection_id)}
              detailFailed={reading.failed}
              pinnedModels={pinnedModels}
              canManage={canManage}
            />
          ))}
        </ol>
      )}

      {canManage ? <ConnectWizardLauncher pinnedModels={pinnedModels} /> : null}
    </div>
  );
}
