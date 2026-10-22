'use client';

/**
 * «Назначения» (`EXEC-HTTP-01`, plan §2): which connection serves which kind of model work.
 *
 * Today exactly one stage calls a model, so there is one route, «Анализ текста». It names a
 * primary connection and, only if an administrator wants one, a standby.
 *
 * **Only a connection that can serve is offered.** A connection is selectable when its current
 * settings have a finished `ok` probe on the current key; every other connection is shown
 * disabled with the reason beside it, so the person sees what to do next instead of an empty
 * list. The server checks the rule again on every write.
 *
 * **The standby is never an implicit fallback.** It is used only when a run starts, and only when
 * the primary has no `ok` probe on its current key or has been archived; a failure in the middle
 * of a run never switches connections. Each use is journaled, and the run's event says
 * «резервное подключение». The editor says so in words, because a standby that someone believes
 * is a retry would hide a failing primary.
 */

import { useState } from 'react';
import type { FormEvent } from 'react';

import type { ExecutorConnection, ExecutorConnectionId, ExecutorRoute, ExecutorWorkKind, Role } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { canExecute } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';
import { executionFailure } from '@/entities/execution';
import {
  KIND_LABELS,
  ROUTE_BLOCKER_SENTENCES,
  WORK_KIND_LABELS,
  connectionFailure,
  currentRevision,
  routeBlocker,
  useExecutorConnectionDetails,
  useExecutorConnections,
  useExecutorRoutes,
} from '@/entities/executor-connection';
import type { RouteBlocker } from '@/entities/executor-connection';
import { CommandFailure, useCommandKey, useSetExecutorRoute } from '@/features/manage-executor-connection';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import styles from './executor-routes.module.css';

export interface ExecutorRoutesProps {
  readonly roles: readonly Role[];
}

/** The kinds of model work that have a route editor. */
const WORK_KINDS: readonly ExecutorWorkKind[] = ['text_analysis'];

interface Choice {
  readonly connection: ExecutorConnection;
  /** `null` when the connection can serve now. */
  readonly blocker: RouteBlocker | null;
  /** The connection has not had its settings read yet, so the answer is not known. */
  readonly known: boolean;
}

function nameOf(connections: readonly ExecutorConnection[], id: ExecutorConnectionId | undefined): string {
  if (id === undefined) return '—';
  return connections.find((item) => item.connection_id === id)?.display_name ?? id;
}

function RouteSummary({
  route, connections,
}: { readonly route: ExecutorRoute | undefined; readonly connections: readonly ExecutorConnection[] }) {
  if (route === undefined) {
    return <p data-executor-route="none">Подключение не назначено: прогон не начнётся и сообщит об этом.</p>;
  }
  return (
    <dl data-executor-route={route.work_kind}>
      <dt>Основное</dt>
      <dd>{nameOf(connections, route.primary_connection_id)}</dd>
      <dt>Резервное</dt>
      <dd>{route.standby_connection_id === undefined ? 'не задано' : nameOf(connections, route.standby_connection_id)}</dd>
      <dt>Назначено</dt>
      <dd><time dateTime={route.set_at}>{formatInstant(route.set_at)}</time>, автор <code>{route.set_by}</code></dd>
    </dl>
  );
}

function RouteEditor({
  workKind, route, choices,
}: {
  readonly workKind: ExecutorWorkKind;
  readonly route: ExecutorRoute | undefined;
  readonly choices: readonly Choice[];
}) {
  const save = useSetExecutorRoute();
  const keys = useCommandKey();
  const [primary, setPrimary] = useState<string>(route?.primary_connection_id ?? '');
  const [withStandby, setWithStandby] = useState(route?.standby_connection_id !== undefined);
  const [standby, setStandby] = useState<string>(route?.standby_connection_id ?? '');
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const [saved, setSaved] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaved(false);
    if (primary === '') {
      setProblem('Выберите основное подключение.');
      return;
    }
    if (withStandby && standby === '') {
      setProblem('Выберите резервное подключение или уберите отметку.');
      return;
    }
    if (withStandby && standby === primary) {
      setProblem('Резервное подключение должно отличаться от основного.');
      return;
    }
    setProblem(null);
    setFailure(null);
    const standbyId = withStandby ? (standby as ExecutorConnectionId) : null;
    try {
      await save.mutateAsync({
        workKind,
        primary: primary as ExecutorConnectionId,
        standby: standbyId,
        idempotencyKey: keys.keyFor(JSON.stringify([workKind, primary, standbyId])),
      });
      keys.release();
      setSaved(true);
    } catch (error) {
      const failed = connectionFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  const option = (choice: Choice) => (
    <option key={choice.connection.connection_id} value={choice.connection.connection_id} disabled={choice.blocker !== null || !choice.known}>
      {choice.connection.display_name} ({KIND_LABELS[choice.connection.kind]})
      {choice.blocker !== null ? ` — недоступно: ${ROUTE_BLOCKER_SENTENCES[choice.blocker]}` : ''}
    </option>
  );
  const blocked = choices.filter((choice) => choice.blocker !== null);

  return (
    <form className="am-form" onSubmit={(event) => void submit(event)} data-executor-route-form={workKind}>
      <div className="am-form__field">
        <label htmlFor={`executor-route-primary-${workKind}`}>Основное подключение</label>
        <select id={`executor-route-primary-${workKind}`} value={primary} onChange={(event) => setPrimary(event.target.value)} required>
          <option value="">Выберите подключение</option>
          {choices.map(option)}
        </select>
      </div>
      <label className="am-form__field">
        <span>
          <input type="checkbox" checked={withStandby} onChange={(event) => setWithStandby(event.target.checked)} />{' '}
          Задать резервное подключение
        </span>
      </label>
      {withStandby ? (
        <div className="am-form__field" data-executor-standby>
          <label htmlFor={`executor-route-standby-${workKind}`}>Резервное подключение</label>
          <select id={`executor-route-standby-${workKind}`} value={standby} onChange={(event) => setStandby(event.target.value)} required>
            <option value="">Выберите подключение</option>
            {choices.map(option)}
          </select>
          <p className="am-form__hint">
            Резервное подключение берётся только при старте прогона и только если у основного нет
            успешной проверки на текущем ключе или оно в архиве. Сбой посреди прогона подключение
            не меняет, а каждый случай использования резерва записывается в журнал: в событии
            прогона будет написано «резервное подключение».
          </p>
        </div>
      ) : null}
      {blocked.length > 0 ? (
        <div className="am-note" data-executor-blocked={blocked.length}>
          Недоступны для выбора, пока не выполнено условие: подключение должно быть живым, с
          сохранёнными настройками, введённым ключом и успешной проверкой на текущем ключе.
          <ul className={styles.reasons}>
            {blocked.map((choice) => (
              <li key={choice.connection.connection_id}>
                «{choice.connection.display_name}»: {choice.blocker === null ? '' : ROUTE_BLOCKER_SENTENCES[choice.blocker]}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {problem !== null ? <p className="am-form__problem" role="alert" data-executor-problem>{problem}</p> : null}
      <div className="am-form__row">
        <button className="am-button" type="submit" disabled={save.isPending}>Сохранить назначение</button>
      </div>
      {saved ? <p className="am-note" role="status" data-executor-route-saved>Назначение сохранено. Оно действует для прогонов, которые начнутся после этого.</p> : null}
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </form>
  );
}

export function ExecutorRoutes({ roles }: ExecutorRoutesProps) {
  const list = useExecutorConnections();
  const routes = useExecutorRoutes();
  const items = list.data?.items ?? [];
  const reading = useExecutorConnectionDetails(items.map((item) => item.connection_id));
  const canManage = canExecute(roles, 'connections');

  if (list.isPending || routes.isPending) return <LoadingState what="назначения" />;
  if (list.isError || routes.isError) {
    const failure = executionFailure(list.error ?? routes.error, false);
    return (
      <div data-executor-routes-read-failure={failure.kind}>
        <ErrorState
          title="Назначения не прочитаны"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={() => { void list.refetch(); void routes.refetch(); }}
        />
      </div>
    );
  }

  const choices: Choice[] = items.map((connection) => {
    const detail = reading.details.get(connection.connection_id);
    const revision = detail === undefined ? undefined : currentRevision(connection, detail.revisions);
    return {
      connection,
      blocker: detail === undefined ? 'not_probed' : routeBlocker(connection, revision),
      known: detail !== undefined,
    };
  });
  const live = choices.filter((choice) => choice.connection.archived_at === undefined);

  return (
    <div className={styles.panel} data-executor-routes>
      {WORK_KINDS.map((workKind) => {
        const route = routes.data.items.find((item) => item.work_kind === workKind);
        return (
          <section key={workKind} className="am-section" aria-label={WORK_KIND_LABELS[workKind]}>
            <h2>{WORK_KIND_LABELS[workKind]}</h2>
            <p>Кто отвечает на запросы к модели на этапе «{WORK_KIND_LABELS[workKind]}».</p>
            <RouteSummary route={route} connections={items} />
            {live.length === 0 ? (
              <EmptyState
                title="Нет подключений для назначения"
                detail="Сначала добавьте подключение на вкладке «Подключения», введите ключ и проверьте его."
              />
            ) : canManage ? (
              <RouteEditor key={`${route?.set_at ?? 'none'}`} workKind={workKind} route={route} choices={live} />
            ) : (
              <p className="am-note" data-executor-routes-readonly>Назначения меняет администратор.</p>
            )}
          </section>
        );
      })}
    </div>
  );
}
