'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { StageChainRun, StageLinkRepair } from '@/shared/api';
import { failureMessage, getStageSheetMap, newIdempotencyKey, undoStageLinkRepair } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { ErrorState } from '@/shared/ui';

import { readRepairs } from '../api/reads';
import { IntentKey, STAGE_RUN_KEYS } from '../model/runs';
import styles from './stage-run-controls.module.css';

export function StageRepairHistory({ run, mayAct }: { readonly run: StageChainRun; readonly mayAct: boolean }) {
  const cache = useQueryClient();
  const [open, setOpen] = useState(false);
  const repairs = useQuery({ queryKey: ['stage-link-repairs', run.run_id], queryFn: () => readRepairs(run.run_id), enabled: open, retry: false });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState(false);
  const held = useRef(new IntentKey(newIdempotencyKey));
  const undo = async (repair: StageLinkRepair) => {
    if (busy || !mayAct || repair.state !== 'applied') return;
    setBusy(true); setError(null); setDone(false);
    try {
      const current = (await getStageSheetMap({ path: { stage_pair_id: run.pair_id } })).data;
      await undoStageLinkRepair({ path: { stage_link_repair_id: repair.repair_id },
        body: { base_revision_id: current.revision_id },
        idempotencyKey: held.current.for([repair.repair_id, current.revision_id]) });
      held.current.clear(); setDone(true);
      await Promise.all([
        cache.invalidateQueries({ queryKey: ['stage-link-repairs', run.run_id] }),
        cache.invalidateQueries({ queryKey: STAGE_RUN_KEYS.map(run.pair_id) }),
        cache.invalidateQueries({ queryKey: STAGE_RUN_KEYS.list(run.pair_id) }),
        cache.invalidateQueries({ queryKey: STAGE_RUN_KEYS.run(run.run_id) }),
        cache.invalidateQueries({ queryKey: ['stage-changes'] }),
        cache.invalidateQueries({ queryKey: ['stage-journal'] }),
        cache.invalidateQueries({ queryKey: ['stage-sheet-map', run.pair_id] }),
      ]);
    } catch (failure) { setError(failure); }
    finally { setBusy(false); }
  };
  const failure = error ?? repairs.error;
  const message = failure === null ? null : failureMessage(failure);
  return <details onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>Автоматические исправления связей</summary>
    {repairs.isFetching ? <p role="status">Открываем историю…</p> : null}
    {repairs.data?.length === 0 ? <p>Автоматических исправлений нет.</p> : null}
    {message === null ? null : <ErrorState title="История не открылась или откат не выполнен" detail={message.detail} correlationId={message.correlationId} />}
    <ul className={styles.repairs}>{repairs.data?.map((repair) => <li key={repair.repair_id}>
      {formatInstant(repair.created_at)} · {repair.state === 'applied' ? 'Применено' : repair.state === 'undone' ? 'Отменено' : 'Заменено ручным решением'}
      <p>Ревизии: <code>{repair.before_revision_id}</code> → <code>{repair.after_revision_id}</code></p>
      {mayAct && repair.state === 'applied' ? <button type="button" className="am-button" disabled={busy}
        onClick={() => void undo(repair)}>Откатить исправление</button> : null}
    </li>)}</ul>
    {done ? <p role="status">Исправление отменено. Обновите сравнение, чтобы увидеть пересчитанный результат.</p> : null}
  </details>;
}
