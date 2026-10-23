'use client';

/**
 * «Токены клиента» (`issueRunnerToken`, `revokeRunnerToken`, `EXEC-PULL-01`): the credential a
 * `pull` connection's client — a Claude Code session or an unattended agent — shows to the
 * stand on every call.
 *
 * **The token is shown once.** The stand keeps only a one-way hash, so no screen and no
 * operation can show the value again; a lost value is revoked and replaced. The value lives in
 * this component's state from the moment it is issued until the person closes the box (the
 * mutation keeps no copy, `gcTime: 0`), and nowhere else: not in the address, not in storage,
 * not in a log. The box says so, offers a copy button, and tells the person that the value goes
 * into an environment variable on the client's side and never into a file.
 *
 * What the panel shows afterwards is what the server remembers: the visible prefix, when the
 * token was made and when it expires, when and from where it was last seen, and whether it was
 * revoked. «На связи» means a call from a runner of this connection less than a minute ago;
 * the number of open tasks is what is waiting for a runner, or held by one, right now.
 */

import { useState } from 'react';

import type {
  ExecutorConnection,
  ExecutorConnectionDetail,
  IssuedRunnerToken,
  RunnerTokenMetadata,
} from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import {
  RUNNER_ONLINE_WINDOW_MS,
  RUNNER_TOKEN_STATE_LABELS,
  connectionRunnerIsOnline,
  connectionFailure,
  runnerTokenIsLive,
  runnerTokenIsOnline,
  runnerTokenState,
  sortedRunnerTokens,
} from '@/entities/executor-connection';
import { formatInstant } from '@/shared/lib';

import { useCommandKey } from '../model/use-command-key';
import { useIssueRunnerToken, useRevokeRunnerToken } from '../model/use-manage-executor-connection';
import { CommandFailure } from './command-failure';

/** The lifetime offered by default; the stand accepts 1 to 365 days. */
export const DEFAULT_TOKEN_DAYS = 30;
const MIN_TOKEN_DAYS = 1;
const MAX_TOKEN_DAYS = 365;

export interface RunnerTokenPanelProps {
  readonly connection: ExecutorConnection;
  /** The connection's detail; the tokens and the open tasks come from it. */
  readonly detail: ExecutorConnectionDetail | undefined;
  /** An administrator: the controls are drawn. The server still checks every write. */
  readonly canManage: boolean;
  /** The instant «на связи» is judged against; the clock of the page, injectable for a test. */
  readonly nowMs?: number | undefined;
}

function Moment({ at }: { readonly at: string }) {
  return <time dateTime={at}>{formatInstant(at)}</time>;
}

function CopyBox({ value }: { readonly value: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      // No clipboard permission: the text stays selectable in the box above.
      setCopied(false);
    }
  }
  return (
    <div className="am-form__field">
      <textarea
        readOnly
        rows={2}
        value={value}
        spellCheck={false}
        aria-label="Значение токена"
        data-executor-runner-token-value
        onFocus={(event) => event.currentTarget.select()}
      />
      <div className="am-form__row">
        <button className="am-button am-button--quiet am-button--small" type="button" data-executor-runner-token-copy onClick={() => void copy()}>
          Скопировать
        </button>
        {copied ? <span role="status" className="am-form__hint">Скопировано.</span> : null}
      </div>
    </div>
  );
}

/**
 * The box a freshly issued token appears in. A view of its own so that the language guard and the
 * tests can render it without pressing anything; the panel mounts it with the value it was given.
 */
export function IssuedTokenView({
  issued, onClose,
}: { readonly issued: IssuedRunnerToken; readonly onClose: () => void }) {
  return (
    <section role="group" aria-label="Выпущенный токен" data-executor-runner-token-shown>
      <p className="am-note" role="alert">
        <strong>Токен показан один раз и больше не будет показан.</strong> Скопируйте его сейчас и
        передайте клиенту: сеансу Claude Code или агенту. Стенд хранит только необратимый отпечаток,
        поэтому потерянный токен восстановить нельзя: его отзывают и выпускают новый.
      </p>
      <CopyBox value={issued.token} />
      <p className="am-form__hint">
        Действует до <Moment at={issued.runner_token.expires_at} />. Клиент получает токен через
        переменную окружения: не записывайте его в файл, в адрес и в сообщение. Как подключить клиента,
        описано в руководстве по установке клиента.
      </p>
      <button className="am-button" type="button" data-executor-runner-token-close onClick={onClose}>
        Я скопировал токен, закрыть
      </button>
    </section>
  );
}

function TokenRow({
  token, nowMs, canManage, onRevoke, revoking,
}: {
  readonly token: RunnerTokenMetadata;
  readonly nowMs: number;
  readonly canManage: boolean;
  readonly onRevoke: (token: RunnerTokenMetadata) => void;
  readonly revoking: boolean;
}) {
  const state = runnerTokenState(token, nowMs);
  const online = runnerTokenIsOnline(token, nowMs);
  return (
    <li data-executor-runner-token={token.token_id} data-executor-runner-token-state={state} data-executor-runner-token-online={online ? 'yes' : 'no'}>
      <code>{token.token_prefix}…</code>{' '}
      <span className={`am-badge am-badge--${state === 'active' ? 'ok' : 'inert'}`}>{RUNNER_TOKEN_STATE_LABELS[state]}</span>
      {online ? <> <span className="am-badge am-badge--ok">на связи</span></> : null}
      <br />
      выпущен <Moment at={token.created_at} />, автор <code>{token.created_by}</code>; срок действия до{' '}
      <Moment at={token.expires_at} />
      {token.revoked_at !== undefined ? <>; отозван <Moment at={token.revoked_at} />{token.revoked_by !== undefined ? <>, автор <code>{token.revoked_by}</code></> : null}</> : null}
      <br />
      {token.last_seen_at !== undefined ? (
        <>
          последнее обращение <Moment at={token.last_seen_at} />
          {token.last_seen_address !== undefined ? <>, с адреса <code>{token.last_seen_address}</code></> : null}
        </>
      ) : (
        'обращений ещё не было'
      )}
      {canManage && runnerTokenIsLive(token, nowMs) ? (
        <>
          {' '}
          <button
            className="am-button am-button--quiet am-button--small"
            type="button"
            data-executor-runner-token-revoke={token.token_id}
            disabled={revoking}
            onClick={() => onRevoke(token)}
          >
            Отозвать
          </button>
        </>
      ) : null}
    </li>
  );
}

export function RunnerTokenPanel({ connection, detail, canManage, nowMs }: RunnerTokenPanelProps) {
  const issue = useIssueRunnerToken();
  const revoke = useRevokeRunnerToken();
  const issueKeys = useCommandKey();
  const revokeKeys = useCommandKey();
  const [days, setDays] = useState(String(DEFAULT_TOKEN_DAYS));
  const [shown, setShown] = useState<IssuedRunnerToken | null>(null);
  const [asking, setAsking] = useState<RunnerTokenMetadata | null>(null);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);

  const now = nowMs ?? Date.now();
  const archived = connection.archived_at !== undefined;
  const tokens = sortedRunnerTokens(detail?.runner_tokens ?? []);
  const online = connectionRunnerIsOnline(detail, now);
  const openTasks = detail?.open_task_count ?? 0;
  const parsedDays = Number(days);
  const daysValid = Number.isInteger(parsedDays) && parsedDays >= MIN_TOKEN_DAYS && parsedDays <= MAX_TOKEN_DAYS;

  async function press() {
    setFailure(null);
    try {
      // A repeat of an issue can never show the value again (the stand answers `token_shown_once`),
      // so every press is a new intent and the key is released whatever the outcome.
      const issued = await issue.mutateAsync({
        connectionId: connection.connection_id,
        expiresInDays: parsedDays,
        idempotencyKey: issueKeys.keyFor(`${connection.connection_id}:${parsedDays}`),
      });
      issueKeys.release();
      issue.reset();
      setShown(issued);
    } catch (error) {
      issueKeys.release();
      setFailure(connectionFailure(error, true));
    }
  }

  async function confirmRevoke(token: RunnerTokenMetadata) {
    setFailure(null);
    try {
      await revoke.mutateAsync({
        connectionId: connection.connection_id,
        tokenId: token.token_id,
        idempotencyKey: revokeKeys.keyFor(token.token_id),
      });
      revokeKeys.release();
      setAsking(null);
    } catch (error) {
      const failed = connectionFailure(error, true);
      if (failed.kind !== 'unknown_outcome') revokeKeys.release();
      setFailure(failed);
    }
  }

  return (
    <section
      className="am-section"
      aria-label="Токены клиента"
      data-executor-runner-panel={connection.connection_id}
      data-executor-runner-online={online ? 'yes' : 'no'}
      data-executor-open-tasks={openTasks}
    >
      <h3>Токены клиента</h3>
      <p>
        {online ? (
          <span className="am-badge am-badge--ok" data-executor-online-badge>на связи</span>
        ) : (
          <span className="am-badge am-badge--inert" data-executor-online-badge>не на связи</span>
        )}{' '}
        {online
          ? 'Клиент обращался к стенду меньше минуты назад.'
          : `Клиент не обращался к стенду последние ${RUNNER_ONLINE_WINDOW_MS / 1000} секунд.`}{' '}
        Заданий в очереди или в работе у клиента: <strong>{openTasks}</strong>.
      </p>
      <p className="am-form__hint">
        Состояние читается при открытии страницы, при возврате на вкладку и по кнопке «Обновить».
        Пока клиент думает над заданием, единственный процесс стенда ждёт его ответа, и очередь за ним
        ждёт тоже. Если никто не взял задание до конца срока ответа, обращение к модели завершается
        ошибкой «ни один клиент не на связи» и не переходит на другое подключение.
      </p>

      {shown !== null ? (
        <IssuedTokenView issued={shown} onClose={() => setShown(null)} />
      ) : null}

      {tokens.length === 0 ? (
        <p data-executor-runner-tokens="none">Токенов ещё нет{canManage && !archived ? ': выпустите первый кнопкой ниже' : ''}.</p>
      ) : (
        <ul aria-label="Выпущенные токены" data-executor-runner-tokens={tokens.length}>
          {tokens.map((token) => (
            <TokenRow
              key={token.token_id}
              token={token}
              nowMs={now}
              canManage={canManage}
              revoking={revoke.isPending}
              onRevoke={(picked) => { setAsking(picked); setFailure(null); }}
            />
          ))}
        </ul>
      )}

      {asking !== null ? (
        <div role="group" aria-label="Подтверждение отзыва токена" data-executor-runner-token-confirm={asking.token_id}>
          <p className="am-note">
            Отозвать токен <code>{asking.token_prefix}…</code>? Следующее же обращение клиента с этим
            токеном будет отклонено, а задание, которое клиент держит, вернётся в очередь или истечёт.
          </p>
          <button className="am-button" type="button" disabled={revoke.isPending} onClick={() => void confirmRevoke(asking)}>
            {failure?.kind === 'unknown_outcome' ? 'Повторить с тем же ключом' : 'Подтвердить отзыв'}
          </button>{' '}
          <button
            className="am-button am-button--quiet"
            type="button"
            disabled={revoke.isPending}
            onClick={() => { setAsking(null); setFailure(null); revokeKeys.release(); }}
          >
            Отмена
          </button>
        </div>
      ) : null}

      {canManage && !archived ? (
        <div className="am-form__row" data-executor-runner-issue>
          <label>
            Срок действия, дней{' '}
            <input
              type="number"
              inputMode="numeric"
              min={MIN_TOKEN_DAYS}
              max={MAX_TOKEN_DAYS}
              value={days}
              onChange={(event) => setDays(event.target.value)}
              data-executor-runner-days
            />
          </label>{' '}
          <button
            className="am-button"
            type="button"
            data-executor-runner-issue-button={connection.connection_id}
            disabled={issue.isPending || !daysValid || shown !== null}
            onClick={() => void press()}
          >
            Выпустить токен
          </button>
          {!daysValid ? (
            <span className="am-form__hint" role="status">Срок: целое число дней от {MIN_TOKEN_DAYS} до {MAX_TOKEN_DAYS}.</span>
          ) : null}
        </div>
      ) : null}
      {failure !== null ? <CommandFailure failure={failure} /> : null}
    </section>
  );
}
