/**
 * One connection on «Подключения» (`EXEC-HTTP-01`): what it is, which settings are current,
 * what is known about its key without the key, how it last answered a probe, and — for an
 * administrator — what can be done with it.
 *
 * The key is never here. The card shows that one exists, for what, when it was set and by whom,
 * and its last four characters; a key entered for another address than the current settings'
 * says so in words. The probe is shown with a Russian sentence for every outcome the contract
 * has, and with the model the answer named and how long it took when it passed.
 *
 * A `pull` connection (`EXEC-PULL-01`) has no key and no address: its card carries the panel of
 * runner tokens instead, with «на связи» and the number of open tasks.
 */

import { useState } from 'react';

import type {
  ExecutorConnection,
  ExecutorConnectionDetail,
  ExecutorPinnedModel,
  ExecutorProbe,
  ExecutorRevision,
  ExecutorSecretMetadata,
} from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import {
  BILLING_LABELS,
  FLAVOUR_LABELS,
  IDENTITY_BASIS_LABELS,
  KIND_LABELS,
  PROBE_OUTCOME_HINTS,
  PROBE_STATE_LABELS,
  PULL_CLIENT_LABELS,
  PURPOSE_LABELS,
  RATE_CHECK_LABELS,
  ROUTE_BLOCKER_SENTENCES,
  SSH_PROFILE_LABELS,
  TRANSPORT_LABELS,
  WORK_KIND_LABELS,
  connectionRunnerIsOnline,
  currentRevision,
  probeIsOnCurrentSecret,
  probeOutcomeSentence,
  requiredPurposes,
  routeBlocker,
  secretIsUnreadable,
  secretOfPurpose,
} from '@/entities/executor-connection';
import {
  ArchiveControl,
  HostKeyControl,
  ProbeButton,
  ReviseConnectionForm,
  RunnerTokenPanel,
  SshKeyControl,
} from '@/features/manage-executor-connection';
import { executorSecretScreenUrl } from '@/features/set-executor-secret';

import styles from './executor-connections.module.css';

export interface ConnectionCardProps {
  readonly connection: ExecutorConnection;
  /** The connection's detail; absent while it is read or when the read failed. */
  readonly detail: ExecutorConnectionDetail | undefined;
  readonly detailFailed: boolean;
  readonly pinnedModels: readonly ExecutorPinnedModel[];
  /** An administrator: the controls are drawn. The server still checks every write. */
  readonly canManage: boolean;
  /** The instant «на связи» is judged against; the page's clock, injectable for a test. */
  readonly nowMs?: number | undefined;
}

function Moment({ at }: { readonly at: string }) {
  return <time dateTime={at}>{formatInstant(at)}</time>;
}

function RevisionSummary({ revision }: { readonly revision: ExecutorRevision }) {
  return (
    <dl data-executor-revision={revision.revision_no}>
      <dt>Настройки</dt>
      <dd>
        версия {revision.revision_no}, сохранена <Moment at={revision.created_at} />, автор{' '}
        <code>{revision.created_by}</code>
      </dd>
      {revision.base_url !== undefined ? (<><dt>Адрес</dt><dd><code>{revision.base_url}</code></dd></>) : null}
      {revision.api_flavour !== undefined ? (<><dt>Формат запросов</dt><dd data-executor-flavour={revision.api_flavour}>{FLAVOUR_LABELS[revision.api_flavour]}</dd></>) : null}
      {revision.transport !== undefined ? (<><dt>Способ связи</dt><dd data-executor-transport={revision.transport}>{TRANSPORT_LABELS[revision.transport]}</dd></>) : null}
      {revision.ssh_host !== undefined ? (
        <>
          <dt>Узел SSH</dt>
          <dd><code>{revision.ssh_user !== undefined ? `${revision.ssh_user}@` : ''}{revision.ssh_host}:{revision.ssh_port}</code></dd>
        </>
      ) : null}
      {revision.ssh_profile !== undefined ? (<><dt>Профиль команды</dt><dd data-executor-ssh-profile={revision.ssh_profile}>{SSH_PROFILE_LABELS[revision.ssh_profile]}</dd></>) : null}
      {revision.ssh_host !== undefined ? (
        <>
          <dt>Отпечаток узла</dt>
          <dd>{revision.host_key_fingerprint !== undefined ? <code>{revision.host_key_fingerprint}</code> : 'не закреплён'}</dd>
        </>
      ) : null}
      {revision.pull_client !== undefined ? (<><dt>Клиент</dt><dd data-executor-pull-client={revision.pull_client}>{PULL_CLIENT_LABELS[revision.pull_client]}</dd></>) : null}
      {revision.answer_deadline_seconds !== undefined ? (<><dt>Срок ответа</dt><dd>{revision.answer_deadline_seconds} с</dd></>) : null}
      {revision.max_claimed_tasks !== undefined ? (<><dt>Заданий в работе</dt><dd>{revision.max_claimed_tasks}</dd></>) : null}
      <dt>Модель</dt>
      <dd>
        <code>{revision.pin_id}</code>; на шлюзе <code>{revision.gateway_model}</code>
      </dd>
      <dt>Тарификация</dt>
      <dd data-executor-billing={revision.billing}>{BILLING_LABELS[revision.billing]}</dd>
      <dt>Ожидание ответа</dt>
      <dd>{revision.timeout_seconds} с{revision.max_parallel_calls !== undefined ? `; параллельных вызовов ${revision.max_parallel_calls}` : ''}</dd>
      <dt>Документы заказчика</dt>
      <dd>{revision.allow_client_documents ? 'разрешены' : 'не отправляются'}</dd>
    </dl>
  );
}

function SecretLine({ secret, current }: { readonly secret: ExecutorSecretMetadata; readonly current: boolean }) {
  return (
    <li data-executor-secret={secret.purpose} data-executor-secret-readable={current ? 'yes' : 'no'}>
      {PURPOSE_LABELS[secret.purpose]}
      {secret.last4 !== '' ? <>: <code>…{secret.last4}</code></> : null}
      {' '}— введён <Moment at={secret.set_at} />, автор <code>{secret.set_by}</code>.
      {current ? null : (
        <strong> Ключ нужно ввести заново: он введён для прежнего адреса или запечатан ключом, которого на стенде больше нет.</strong>
      )}
      {secret.public_key !== undefined ? (
        <>
          <br />Открытый ключ: <code>{secret.public_key}</code>
        </>
      ) : null}
    </li>
  );
}

function SecretsSummary({ connection, revision }: { readonly connection: ExecutorConnection; readonly revision: ExecutorRevision | undefined }) {
  const purposes = requiredPurposes(connection, revision);
  if (purposes.length === 0) {
    return <p data-executor-secrets="none">У подключений этого вида нет вводимого ключа.</p>;
  }
  return (
    <div data-executor-secrets="some">
      <ul>
        {purposes.map((purpose) => {
          const secret = secretOfPurpose(connection, purpose);
          return secret === null ? (
            <li key={purpose} data-executor-secret={purpose} data-executor-secret-readable="missing">
              {PURPOSE_LABELS[purpose]}: ещё не введён.
            </li>
          ) : (
            <SecretLine key={purpose} secret={secret} current={!secretIsUnreadable(secret)} />
          );
        })}
      </ul>
    </div>
  );
}

function ProbeSummary({
  probe, connection, revision,
}: { readonly probe: ExecutorProbe | undefined; readonly connection: ExecutorConnection; readonly revision: ExecutorRevision }) {
  if (probe === undefined) return <p data-executor-probe-state="none">Текущие настройки ещё не проверяли.</p>;
  if (probe.state !== 'finished' || probe.outcome === undefined) {
    return (
      <p data-executor-probe-state={probe.state}>
        {PROBE_STATE_LABELS[probe.state]}; запрошена <Moment at={probe.requested_at} />.
      </p>
    );
  }
  const passed = probe.outcome === 'ok';
  const hint = PROBE_OUTCOME_HINTS[probe.outcome];
  return (
    <div data-executor-probe-state="finished" data-executor-probe-outcome={probe.outcome}>
      <p>
        <span className={`am-badge am-badge--${passed ? 'ok' : 'failed'}`}>{probeOutcomeSentence(probe.outcome)}</span>
        {probe.finished_at !== undefined ? <> проверено <Moment at={probe.finished_at} /></> : null}
      </p>
      {probe.reported_model !== undefined || probe.latency_ms !== undefined || probe.rate_check !== undefined ? (
        <p>
          {probe.reported_model !== undefined ? (
            <>
              Модель в ответе: <code>{probe.reported_model}</code>
              {probe.identity_basis !== undefined ? <> (<span data-executor-identity-basis={probe.identity_basis}>{IDENTITY_BASIS_LABELS[probe.identity_basis]}</span>)</> : null}.{' '}
            </>
          ) : null}
          {probe.latency_ms !== undefined ? `Ответ за ${probe.latency_ms} мс. ` : null}
          {probe.rate_check !== undefined ? <>Сверка стоимости: <span data-executor-rate-check={probe.rate_check}>{RATE_CHECK_LABELS[probe.rate_check]}</span>.</> : null}
        </p>
      ) : null}
      {hint !== undefined ? <p className="am-form__hint">{hint}</p> : null}
      {probe.detail !== undefined && probe.detail !== '' ? <p className="am-form__hint">Подробности: {probe.detail}</p> : null}
      {passed && !probeIsOnCurrentSecret(probe, connection, revision) ? (
        <p className="am-note" role="status">Проверка прошла на прежнем ключе: проверьте подключение ещё раз.</p>
      ) : null}
    </div>
  );
}

export function ConnectionCard({ connection, detail, detailFailed, pinnedModels, canManage, nowMs }: ConnectionCardProps) {
  const [editing, setEditing] = useState(false);
  const archived = connection.archived_at !== undefined;
  const revisions = detail?.revisions ?? [];
  const revision = currentRevision(connection, revisions);
  const blocker = routeBlocker(connection, revision);
  const probe = revision?.latest_probe;
  const hostKeyObserved =
    probe !== undefined && probe.observed_host_key !== undefined &&
    (probe.outcome === 'host_key_unpinned' || probe.outcome === 'host_key_changed');
  const holdsSshKey = secretOfPurpose(connection, 'ssh_private_key') !== null;
  const holdsKey = connection.secrets.length > 0;
  const needsSshKey = requiredPurposes(connection, revision).includes('ssh_private_key');
  const takesApiKey = connection.kind === 'http_api';
  const pulls = connection.kind === 'pull';
  const runnerOnline = pulls && connectionRunnerIsOnline(detail, nowMs ?? Date.now());

  return (
    <li
      className={styles.card}
      data-executor-connection={connection.connection_id}
      data-executor-kind={connection.kind}
      data-executor-archived={archived ? 'yes' : 'no'}
    >
      <div className={styles.heading}>
        <strong>{connection.display_name}</strong>
        <span>{KIND_LABELS[connection.kind]}</span>
        {runnerOnline && !archived ? (
          <span className="am-badge am-badge--ok" data-executor-heading-online="yes">на связи</span>
        ) : null}
        {archived ? (
          <span className="am-badge am-badge--inert">в архиве</span>
        ) : blocker === null ? (
          <span className="am-badge am-badge--ok" data-executor-ready="yes">готово к назначению</span>
        ) : (
          <span className="am-badge am-badge--degraded" data-executor-ready="no" data-executor-blocker={blocker}>
            не готово: {ROUTE_BLOCKER_SENTENCES[blocker]}
          </span>
        )}
      </div>
      <p className={styles.identity}>Подключение <code>{connection.connection_id}</code>, создано <Moment at={connection.created_at} />, автор <code>{connection.created_by}</code></p>
      {connection.routed_work_kinds.length > 0 ? (
        <p data-executor-routed>Назначено: {connection.routed_work_kinds.map((work) => WORK_KIND_LABELS[work]).join(', ')}.</p>
      ) : null}

      {revision !== undefined ? <RevisionSummary revision={revision} /> : detail === undefined ? (
        <p data-executor-revision-state={detailFailed ? 'failed' : 'pending'}>
          {detailFailed ? 'Настройки подключения не прочитаны. Обновите страницу.' : 'Настройки подключения читаются…'}
        </p>
      ) : (
        <p data-executor-revision-state="none">Настройки ещё не заданы{canManage ? ': сохраните их кнопкой «Изменить настройки»' : ''}.</p>
      )}

      <SecretsSummary connection={connection} revision={revision} />
      {revision !== undefined ? <ProbeSummary probe={probe} connection={connection} revision={revision} /> : null}
      {pulls && !archived ? <RunnerTokenPanel connection={connection} detail={detail} canManage={canManage} nowMs={nowMs} /> : null}

      {canManage && !archived ? (
        <>
          <div className={styles.actions}>
            <button className="am-button am-button--quiet" type="button" disabled={detail === undefined} onClick={() => setEditing((now) => !now)}>
              {editing ? 'Скрыть настройки' : 'Изменить настройки'}
            </button>
            {takesApiKey && revision !== undefined ? (
              <a className="am-button am-button--quiet" href={executorSecretScreenUrl(connection.connection_id)} data-executor-key-link>
                {secretOfPurpose(connection, 'api_key') === null ? 'Ввести ключ' : 'Заменить ключ'}
              </a>
            ) : null}
            {revision !== undefined ? (
              <ProbeButton
                connectionId={connection.connection_id}
                revisionId={revision.revision_id}
                open={probe !== undefined && probe.state !== 'finished'}
              />
            ) : null}
            <ArchiveControl connectionId={connection.connection_id} name={connection.display_name} />
          </div>
          {needsSshKey && revision !== undefined ? (
            <div className={styles.actions}>
              <SshKeyControl connectionId={connection.connection_id} hasKey={holdsSshKey} />
            </div>
          ) : null}
          {hostKeyObserved && revision !== undefined && probe?.observed_host_key !== undefined ? (
            <HostKeyControl
              connectionId={connection.connection_id}
              revision={revision}
              observedHostKey={probe.observed_host_key}
              changed={probe.outcome === 'host_key_changed'}
            />
          ) : null}
          {editing && detail !== undefined ? (
            <ReviseConnectionForm
              connection={connection}
              revision={revision}
              pinnedModels={pinnedModels}
              holdsKey={holdsKey}
              onClose={() => setEditing(false)}
            />
          ) : null}
        </>
      ) : null}

      {detail !== undefined && detail.revisions.length > 0 ? (
        <details className={styles.history}>
          <summary>История настроек и проверок</summary>
          <ol>
            {[...detail.revisions].sort((left, right) => right.revision_no - left.revision_no).map((item) => (
              <li key={item.revision_id}>
                Версия {item.revision_no}, <Moment at={item.created_at} />, автор <code>{item.created_by}</code>
                {item.latest_probe?.outcome !== undefined ? `; проверка: ${probeOutcomeSentence(item.latest_probe.outcome)}` : ''}
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </li>
  );
}
