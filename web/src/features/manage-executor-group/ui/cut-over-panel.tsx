'use client';

/**
 * The cut-over panel of «Правила» (`EXEC2-WEB-GROUPS-01`, ADR-0026 decision 17): the way from the
 * legacy Primary/Standby routes to rules, and back. Administrators only; the server checks again.
 *
 * **Forward, in three steps, none of which writes until the last.**
 *
 * 1. «Перейти на правила» reads the proposal (`previewExecutorRouting`) and writes nothing: per
 *    work kind a one-member group made from the primary of its legacy route. A standby is shown and
 *    **never becomes a member**; a route that cannot become a group is flagged with its reason; a
 *    work kind with no route gets no rule, and the panel says what that costs.
 * 2. The administrator confirms the mapping explicitly: a checkbox that says the table was read, and
 *    only then a button. The button is disabled while the proposal is being read again, and when
 *    nothing can be converted.
 * 3. «Подтвердить переход на правила» sends `setExecutorRoutingMode` with `rules`, the digest that was
 *    shown and the mapping of the `ready` work kinds. A proposal that changed in the meantime is
 *    refused as stale and the panel offers to read it again; it never sends a digest it did not show.
 *
 * **Back.** «Вернуться к основному и резервному подключению» (`ROLLBACK_LABEL`) asks first and says what stays: groups and rules are kept
 * and unused, and work already admitted by rules or a group finishes on its own group and is never
 * read again through a legacy route. Then it sends `legacy`, which takes neither digest nor mapping.
 *
 * Both operations are served by `EXEC2-CUTOVER-01`. Until then the server refuses them, and the
 * refusal is shown as it came, with its correlation id: the panel offers nothing in its place.
 */

import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import type { ExecutorConnection, ExecutorRoutingMode, ExecutorRoutingPreview, SetExecutorRoutingModeRequest } from '@/shared/api';
import type { ExecutionFailure } from '@/entities/execution';
import { WORK_KIND_LABELS } from '@/entities/executor-connection';
import {
  CUT_OVER_CONFIRMATION,
  CUT_OVER_CONFIRM_LABEL,
  CUT_OVER_LABEL,
  MAPPING_CONFIRMATION_LABEL,
  NO_READY_ITEMS,
  PREVIEW_ISSUE_SENTENCES,
  PREVIEW_STATUS_LABELS,
  ROLLBACK_CONFIRMATION,
  ROLLBACK_CONFIRM_LABEL,
  ROLLBACK_LABEL,
  cutOverCanBeConfirmed,
  cutOverMapping,
  executorRoutingPreviewKey,
  groupFailure,
  previewItems,
  useExecutorRoutingPreview,
} from '@/entities/executor-group';
import { useCommandKey } from '@/features/manage-executor-connection';
import { ErrorState, LoadingState } from '@/shared/ui';

import { useSetExecutorRoutingMode } from '../model/use-manage-executor-group';
import { GroupCommandFailure } from './group-command-failure';
import styles from './cut-over-panel.module.css';

export interface CutOverPanelProps {
  /** The routing mode now: the panel offers the move to the other one. */
  readonly mode: ExecutorRoutingMode;
  /** The connections, to name the primary and the standby of each legacy route. */
  readonly connections: readonly ExecutorConnection[];
}

function nameOf(connections: readonly ExecutorConnection[], id: string | undefined): string {
  if (id === undefined) return '—';
  return connections.find((item) => item.connection_id === id)?.display_name ?? 'подключение не найдено';
}

/** The proposal as a table: a view driven by props, so a census screen can draw it without pressing the button that opens it. */
export function CutOverPreviewTable({
  preview, connections,
}: { readonly preview: ExecutorRoutingPreview; readonly connections: readonly ExecutorConnection[] }) {
  const items = previewItems(preview);
  return (
    // A table wider than its box scrolls inside it, and Tab reaches the box.
    <div className={styles.previewWrap} role="region" aria-label="Предложение перехода, таблица" tabIndex={0}>
      <table data-cut-over-preview={items.length}>
        <caption>Предложение: что станет с назначением каждого вида работы</caption>
        <thead>
          <tr>
            <th scope="col">Вид работы</th>
            <th scope="col">Основное подключение</th>
            <th scope="col">Резервное подключение</th>
            <th scope="col">Что произойдёт</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.work_kind} data-cut-over-item={item.work_kind} data-cut-over-status={item.status}>
              <th scope="row">{WORK_KIND_LABELS[item.work_kind]}</th>
              <td>
                {nameOf(connections, item.primary_connection_id)}
                {item.pin_id === undefined ? '' : `, модель «${item.pin_id}»`}
              </td>
              <td>
                {item.standby_connection_id === undefined
                  ? '—'
                  : `${nameOf(connections, item.standby_connection_id)}: в группу не переходит`}
              </td>
              <td>
                {PREVIEW_STATUS_LABELS[item.status]}
                {item.status === 'ready' && item.proposed_group_name !== undefined
                  ? `: группа «${item.proposed_group_name}»`
                  : ''}
                {item.incompatible_reason === undefined ? '' : `: ${PREVIEW_ISSUE_SENTENCES[item.incompatible_reason]}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PreviewFlags({ preview }: { readonly preview: ExecutorRoutingPreview }) {
  const items = previewItems(preview);
  const standbys = items.filter((item) => item.standby_connection_id !== undefined).length;
  const incompatible = items.filter((item) => item.status === 'incompatible').length;
  const noRoute = items.filter((item) => item.status === 'no_route').length;
  return (
    <>
      {standbys > 0 ? (
        <p className="am-note" data-cut-over-flag="standby">
          Резервных подключений в предложении: {standbys}. Они показаны и в состав групп не переходят: резервное
          подключение не станет участником группы само.
        </p>
      ) : null}
      {incompatible > 0 ? (
        <p className="am-note" role="status" data-cut-over-flag="incompatible">
          Не переносятся: {incompatible}. Для них правила не появится, пока вы не исправите подключение и не откроете
          предложение заново.
        </p>
      ) : null}
      {noRoute > 0 ? (
        <p className="am-note" role="status" data-cut-over-flag="no_route">
          Без назначения: {noRoute}. После перехода работа этих видов будет отказывать, пока вы не назначите им группу
          на этой вкладке.
        </p>
      ) : null}
    </>
  );
}

export function CutOverPanel({ mode, connections }: CutOverPanelProps) {
  const client = useQueryClient();
  const setMode = useSetExecutorRoutingMode();
  const keys = useCommandKey();
  const [open, setOpen] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [asking, setAsking] = useState(false);
  const [failure, setFailure] = useState<ExecutionFailure | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const preview = useExecutorRoutingPreview(open && mode === 'legacy');
  // A `const` of its own: a narrowing of `preview.data` would not survive into the handlers below.
  const proposal = preview.data;
  const readFailure = preview.isError && proposal === undefined ? groupFailure(preview.error, false) : null;
  const busy = setMode.isPending;

  function closePreview() {
    setOpen(false);
    setConfirmed(false);
    setFailure(null);
    // The proposal is bound by its digest: a closed panel keeps none, so a reopened one reads it afresh.
    client.removeQueries({ queryKey: executorRoutingPreviewKey() });
  }

  async function send(body: SetExecutorRoutingModeRequest, finished: (groups: number) => string) {
    setFailure(null);
    setDone(null);
    try {
      const result = await setMode.mutateAsync({ body, idempotencyKey: keys.keyFor(JSON.stringify(body)) });
      keys.release();
      setDone(finished(result.groups.length));
      setOpen(false);
      setConfirmed(false);
      setAsking(false);
      client.removeQueries({ queryKey: executorRoutingPreviewKey() });
    } catch (error) {
      const failed = groupFailure(error, true);
      if (failed.kind !== 'unknown_outcome') keys.release();
      setFailure(failed);
    }
  }

  function confirmCutOver(shown: ExecutorRoutingPreview) {
    if (!confirmed || !cutOverCanBeConfirmed(shown) || preview.isFetching) return;
    void send(
      { mode: 'rules', preview_digest: shown.preview_digest, mapping: cutOverMapping(shown) },
      (groups) => `Включены правила. Создано групп: ${groups}. Работа, принятая до перехода, идёт как шла.`,
    );
  }

  function confirmRollback() {
    void send(
      { mode: 'legacy' },
      () => 'Возвращены основное и резервное подключения. Группы и правила сохранены и не используются. Работа, принятая по правилам, дойдёт до конца на своей группе.',
    );
  }

  const doneNote = done === null ? null : <p className="am-note" role="status" data-cut-over-done>{done}</p>;

  if (mode === 'rules') {
    return (
      <div className={styles.panel} data-cut-over-panel="rules">
        {doneNote}
        {asking ? (
          <div role="group" aria-label="Подтверждение возврата к основным и резервным подключениям" data-cut-over-rollback="asking">
            <p className="am-note">{ROLLBACK_CONFIRMATION}</p>
            <div className={styles.actions}>
              <button className="am-button" type="button" disabled={busy} onClick={confirmRollback}>
                {failure?.kind === 'unknown_outcome' ? 'Повторить с тем же ключом' : ROLLBACK_CONFIRM_LABEL}
              </button>
              <button
                className="am-button am-button--quiet"
                type="button"
                disabled={busy}
                onClick={() => {
                  setAsking(false);
                  setFailure(null);
                  keys.release();
                }}
              >
                Отмена
              </button>
            </div>
          </div>
        ) : (
          <div>
            <button className="am-button am-button--quiet" type="button" onClick={() => { setAsking(true); setDone(null); }}>
              {ROLLBACK_LABEL}
            </button>
          </div>
        )}
        {failure !== null ? <GroupCommandFailure failure={failure} /> : null}
      </div>
    );
  }

  return (
    <div className={styles.panel} data-cut-over-panel="legacy">
      {doneNote}
      {!open ? (
        <div>
          <button className="am-button" type="button" onClick={() => { setOpen(true); setDone(null); }}>
            {CUT_OVER_LABEL}
          </button>
        </div>
      ) : (
        <>
          {proposal === undefined && !preview.isError ? <LoadingState what="предложение перехода" /> : null}
          {readFailure === null ? null : (
            <div data-cut-over-read-failure={readFailure.kind}>
              <ErrorState
                title="Предложение перехода не прочитано"
                detail={readFailure.detail}
                correlationId={readFailure.correlationId}
                onRetry={() => void preview.refetch()}
              />
            </div>
          )}
          {proposal === undefined ? (
            <div className={styles.actions}>
              <button className="am-button am-button--quiet" type="button" disabled={busy} onClick={closePreview}>
                Отмена
              </button>
            </div>
          ) : (
            <>
              <CutOverPreviewTable preview={proposal} connections={connections} />
              <PreviewFlags preview={proposal} />
              {cutOverCanBeConfirmed(proposal) ? (
                <>
                  <p className="am-note" data-cut-over-confirmation>{CUT_OVER_CONFIRMATION}</p>
                  <label className={styles.check}>
                    <input
                      type="checkbox"
                      checked={confirmed}
                      disabled={busy || preview.isFetching}
                      onChange={(event) => setConfirmed(event.target.checked)}
                    />
                    {MAPPING_CONFIRMATION_LABEL}
                  </label>
                </>
              ) : (
                <p className="am-note" role="status" data-cut-over-nothing>{NO_READY_ITEMS}</p>
              )}
              <div className={styles.actions}>
                <button
                  className="am-button"
                  type="button"
                  disabled={busy || preview.isFetching || !confirmed || !cutOverCanBeConfirmed(proposal)}
                  onClick={() => confirmCutOver(proposal)}
                >
                  {failure?.kind === 'unknown_outcome' ? 'Повторить с тем же ключом' : CUT_OVER_CONFIRM_LABEL}
                </button>
                <button
                  className="am-button am-button--quiet"
                  type="button"
                  disabled={busy || preview.isFetching}
                  onClick={() => {
                    setConfirmed(false);
                    setFailure(null);
                    void preview.refetch();
                  }}
                >
                  Прочитать предложение заново
                </button>
                <button className="am-button am-button--quiet" type="button" disabled={busy} onClick={closePreview}>
                  Отмена
                </button>
              </div>
            </>
          )}
          {failure !== null ? <GroupCommandFailure failure={failure} /> : null}
        </>
      )}
    </div>
  );
}
