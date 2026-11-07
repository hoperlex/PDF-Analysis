'use client';

/**
 * «Правила» (`EXEC2-WEB-GROUPS-01`, ADR-0026 decisions 11 and 17): which group takes the work of
 * each kind, the routing mode that says whether the rules are read, and the way from the legacy
 * Primary/Standby routes to rules and back.
 *
 * Any role reads the rules and the mode (`listExecutorRoutingRules` is open to every role); only an
 * administrator is shown the editor and the cut-over, and the server checks every write.
 *
 * **Under the mode `legacy` the rules are stored and used by nothing.** The screen says so in a note
 * and shows the legacy routes beside it (the `legacyRoutes` slot: the page passes the existing routes
 * widget in its read-only form), so nobody believes a rule moved new work. Under `rules` the routes
 * become history on «Назначения», and the same panel offers the way back.
 *
 * The table has exactly one row per kind of model work. The routing mode is shown in words and as
 * `data-routing-mode`, its machine value.
 */

import type { ReactNode } from 'react';

import type { Role } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { canExecute } from '@/entities/execution';
import { useExecutorConnections } from '@/entities/executor-connection';
import {
  ROUTING_MODE_LABELS,
  groupFailure,
  ruleRows,
  useExecutorGroups,
  useExecutorRoutingRules,
} from '@/entities/executor-group';
import { CutOverPanel, RuleEditor } from '@/features/manage-executor-group';
import { ErrorState, LoadingState } from '@/shared/ui';

import styles from './executor-rules.module.css';
import { RulesTable } from './rules-table';

export interface ExecutorRulesProps {
  readonly roles: readonly Role[];
  /**
   * The legacy routes as history (the routes widget, read-only). Drawn under «Прежние назначения»
   * while the mode is `legacy`; under `rules` they are history on «Назначения» and not repeated here.
   */
  readonly legacyRoutes?: ReactNode | undefined;
}

export function ExecutorRules({ roles, legacyRoutes }: ExecutorRulesProps) {
  const rules = useExecutorRoutingRules();
  const groups = useExecutorGroups();
  const list = useExecutorConnections();
  const canManage = canExecute(roles, 'connections');

  if (rules.isPending || groups.isPending) return <LoadingState what="правила" />;
  if (rules.isError || groups.isError) {
    const failure = groupFailure(rules.error ?? groups.error, false);
    return (
      <div data-executor-rules-read-failure={failure.kind}>
        <ErrorState
          title="Правила не прочитаны"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={() => {
            void rules.refetch();
            void groups.refetch();
          }}
        />
      </div>
    );
  }

  const mode = rules.data.routing_mode.mode;
  const state = rules.data.routing_mode;
  const rows = ruleRows(rules.data.items, groups.data.items);
  const connections = list.data?.items ?? [];

  return (
    <div className={styles.panel} data-executor-rules>
      <section className={`am-section ${styles.section}`} aria-label="Режим маршрутизации" data-rules-mode-section>
        <h2>Режим маршрутизации</h2>
        <p data-routing-mode={mode}>
          Сейчас работу распределяют: {ROUTING_MODE_LABELS[mode]}.
          {state.changed_at === undefined ? null : (
            <>
              {' '}Режим изменён <time dateTime={state.changed_at}>{formatInstant(state.changed_at)}</time>
              {state.changed_by === undefined ? null : <>, автор <code>{state.changed_by}</code></>}.
            </>
          )}
        </p>
        {mode === 'legacy' ? (
          <p className="am-note" data-rules-legacy-note>
            Правила сохранены, но пока не используются: новая работа идёт по основному и резервному подключениям. Когда вы
            перейдёте на правила, группа вида работы заменит назначение.
          </p>
        ) : (
          <p className="am-note" data-rules-active-note>
            Правила действуют. Основное и резервное подключения не меняются: они остались историей на вкладке
            «Назначения». Вид работы без правила не запустится.
          </p>
        )}
      </section>

      <section className={`am-section ${styles.section}`} aria-label="Правила по видам работы" data-rules-section>
        <h2>Правила по видам работы</h2>
        <RulesTable rows={rows} mode={mode} />
        {canManage ? (
          <>
            <h3>Назначить группу виду работы</h3>
            <RuleEditor groups={groups.data.items} mode={mode} />
          </>
        ) : (
          <p className="am-note" data-rules-readonly>Правила меняет администратор.</p>
        )}
      </section>

      <section className={`am-section ${styles.section}`} aria-label="Переход между режимами" data-rules-cut-over-section>
        <h2>{mode === 'legacy' ? 'Переход на правила' : 'Возврат к основному и резервному подключениям'}</h2>
        {canManage ? (
          <CutOverPanel mode={mode} connections={connections} />
        ) : (
          <p className="am-note" data-rules-readonly>Режим меняет администратор.</p>
        )}
      </section>

      {mode === 'legacy' && legacyRoutes !== undefined ? (
        <section className={`am-section ${styles.section}`} aria-label="Прежние назначения" data-rules-legacy-routes>
          <h2>Прежние назначения</h2>
          <p className="am-note">
            Пока действует прежний режим, работу распределяют эти назначения. Менять их можно на вкладке «Назначения»; после
            перехода на правила они останутся там историей.
          </p>
          {legacyRoutes}
        </section>
      ) : null}
    </div>
  );
}
