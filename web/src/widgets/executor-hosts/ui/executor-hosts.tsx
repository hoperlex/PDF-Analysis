'use client';

/**
 * «Серверы» (`HOSTS-WEB-01`, ADR-0028, plan 2026-11-09 §6 and §7.2): the servers the stand sends model work to, one line each.
 *
 * ```
 * На связи 2 из 3 · свободно 3 из 5
 * ● adm1.hlab.kz  [Использовать ◉]  Opus 5.5 · Sonnet 5.5 · gpt-6-sol  ▮▮▯ 2/3  ⋮
 * ```
 *
 * **What a row holds, and for whom.** An expert reads: the dot, the name, the models, the load. An administrator is also drawn
 * the switch «Использовать» and the menu «⋮» of two items, «Подробнее» and «Удалить», and the button «Подключить сервер». The
 * server checks every write again; what is hidden here is only a hint. **An unavailable model is not drawn** (plan §6): a
 * server with no contact is a grey row «нет связи с ЧЧ:ММ», one with no usable model says «нет доступных моделей», and the
 * reasons are shown only in «Подробнее» (administrator) and where an action is blocked or a run waits.
 *
 * The list is read on the operational-list cadence (10 s while the tab is visible) and says when it was last read. The
 * viewer reads none of it (`R-150w`): the read is not enabled for a role that is neither an expert nor an administrator.
 * The `D-291` warning stays, one line, while the debt is open.
 */

import { useState } from 'react';

import type { ExecutorHost, ExecutorHostList, Role } from '@/shared/api';
import { UpdateTime, canExecute, executionFailure } from '@/entities/execution';
import {
  API_MARK,
  API_MARK_HINT,
  CLIENT_DOCUMENTS_LINE,
  HOST_STATE_LABELS,
  MENU_DELETE,
  MENU_DETAILS,
  MENU_LABEL,
  NO_MODELS,
  SERVERS_EMPTY,
  SERVERS_EMPTY_ADMIN,
  hostRowReading,
  liveHosts,
  mayReadHosts,
  noContactSentence,
  summarySentence,
  useExecutorHosts,
} from '@/entities/executor-host';
import type { HostRowReading } from '@/entities/executor-host';
import {
  ConnectServer,
  DeleteHostControl,
  HostDetails,
  HostEnabledSwitch,
} from '@/features/manage-executor-host';
import { EmptyState, ErrorState, LoadingState, Menu, UnsupportedState } from '@/shared/ui';

import styles from './executor-hosts.module.css';

const TONE_CLASS = { ok: styles.dotOk, busy: styles.dotBusy, offline: styles.dotOffline } as const;

export interface HostRowProps {
  readonly host: ExecutorHost;
  /** An administrator: drawn the switch, the menu and what they open. */
  readonly admin: boolean;
  /** Test seam: the row starts with «Подробнее» or the confirmation of «Удалить» open. */
  readonly initialPanel?: 'details' | 'delete' | null | undefined;
}

export function HostRow({ host, admin, initialPanel = null }: HostRowProps) {
  const reading: HostRowReading = hostRowReading(host);
  const [panel, setPanel] = useState<'details' | 'delete' | null>(initialPanel);

  return (
    <li className={`${styles.row} ${reading.noContact ? styles.rowOffline : ''}`} data-host-row={reading.hostId} data-host-state={host.state} data-host-tone={reading.tone}>
      <span className={`${styles.dot} ${TONE_CLASS[reading.tone]}`} role="img" aria-label={HOST_STATE_LABELS[host.state]}>●</span>
      <span className={styles.name}>{reading.name}</span>
      {admin ? <HostEnabledSwitch hostId={host.host_id} name={reading.name} enabled={reading.enabled} /> : null}
      {reading.noContact ? (
        <span className={styles.note} data-host-no-contact>{noContactSentence(host.last_seen_at)}</span>
      ) : reading.noModels ? (
        <span className={styles.note} data-host-no-models>{NO_MODELS}</span>
      ) : (
        <ul className={styles.models} aria-label="Модели сервера">
          {reading.chips.map((chip) => (
            <li key={chip.modelId} className={`${styles.model} ${chip.busy ? styles.modelBusy : ''}`} data-host-model={chip.modelId}>
              {chip.label}
              {chip.api ? <span className={styles.api} title={API_MARK_HINT} data-host-api>{API_MARK}</span> : null}
            </li>
          ))}
        </ul>
      )}
      {reading.noContact ? null : (
        <span className={styles.load} data-host-load={reading.load}>
          <meter className={styles.meter} min={0} max={Math.max(reading.slotsTotal, 1)} value={reading.slotsInUse} aria-label="Занято мест" />
          {reading.load}
        </span>
      )}
      {admin ? (
        <Menu
          label={`${MENU_LABEL}: ${reading.name}`}
          trigger={<span aria-hidden="true">⋮</span>}
          items={[
            { kind: 'action', label: MENU_DETAILS, onChoose: () => setPanel((was) => (was === 'details' ? null : 'details')) },
            { kind: 'action', label: MENU_DELETE, onChoose: () => setPanel('delete') },
          ]}
        />
      ) : null}
      {admin && panel === 'details' ? <div className={styles.extra}><HostDetails hostId={host.host_id} /></div> : null}
      {admin && panel === 'delete' ? (
        <div className={styles.extra}>
          <DeleteHostControl hostId={host.host_id} name={reading.name} onClose={() => setPanel(null)} />
        </div>
      ) : null}
    </li>
  );
}

export interface ExecutorHostsViewProps {
  readonly list: ExecutorHostList;
  readonly admin: boolean;
}

/** The summary and the rows of a read list; the pure part of the screen. */
export function ExecutorHostsView({ list, admin }: ExecutorHostsViewProps) {
  const hosts = liveHosts(list);
  return (
    <>
      <p className={styles.summary} data-hosts-summary>
        {summarySentence(list.online, list.total, list.slots_free, list.slots_total)}
      </p>
      {hosts.length === 0 ? (
        <EmptyState title={admin ? SERVERS_EMPTY_ADMIN : SERVERS_EMPTY} />
      ) : (
        <ul className={styles.list} data-hosts-list>
          {hosts.map((host) => <HostRow key={host.host_id} host={host} admin={admin} />)}
        </ul>
      )}
    </>
  );
}

export interface ExecutorHostsProps {
  readonly roles: readonly Role[];
}

export function ExecutorHosts({ roles }: ExecutorHostsProps) {
  const readable = mayReadHosts(roles);
  const admin = canExecute(roles, 'connections');
  const hosts = useExecutorHosts(readable);

  if (!readable) {
    return <UnsupportedState title="Серверы недоступны" detail="Серверы показываются экспертам и администраторам." />;
  }
  const failure = hosts.error === null ? null : executionFailure(hosts.error, false);

  return (
    <div className={styles.panel} data-executor-hosts>
      <div className={styles.bar}>
        <p className="am-note" data-hosts-notice="client-documents">{CLIENT_DOCUMENTS_LINE}</p>
        {admin ? <ConnectServer /> : null}
      </div>
      <UpdateTime dataUpdatedAt={hosts.dataUpdatedAt} failed={hosts.isError} />
      {hosts.isPending ? <LoadingState what="серверы" /> : null}
      {failure === null ? null : (
        <div data-hosts-read-failure={failure.kind}>
          <ErrorState
            title={hosts.data === undefined ? 'Серверы не прочитаны' : 'Серверы не обновились'}
            detail={failure.detail}
            correlationId={failure.correlationId}
            onRetry={() => void hosts.refetch()}
          />
        </div>
      )}
      {hosts.data === undefined ? null : <ExecutorHostsView list={hosts.data} admin={admin} />}
    </div>
  );
}
