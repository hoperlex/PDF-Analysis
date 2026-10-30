'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { StageChainRun } from '@/shared/api';
import { failureMessage, getStageChainRun, getStagePair, getStageSheetMapRevision, getVersionPageProfile } from '@/shared/api';
import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';
import { formatInstant } from '@/shared/lib';
import { ErrorState, LoadingState } from '@/shared/ui';
import { StageChanges, StageJournal } from '@/widgets/stage-changes';
import type { OpenStageEvidence, OpenStageRawDifference } from '@/widgets/stage-changes';
import { StagePairCatalog } from '@/widgets/stage-pair-catalog';
import { StageRunControls } from '@/widgets/stage-run-controls';
import { StageSheetMap } from '@/widgets/stage-sheet-map';
import type { StageMapFocus } from '@/widgets/stage-sheet-map';

import { readStagePairs, readStageRunOptions, storedPageText } from '../api/workspace';
import { assertRunRevision, evidenceFocus, rawFocus } from '../model/navigation';
import { StageUploadPanel } from './stage-upload-panel';
import styles from './stage-workspace.module.css';

type Tab = 'documentation' | 'sheets' | 'changes' | 'journal';
const TABS: ReadonlyArray<{ key: Tab; label: string }> = [
  { key: 'documentation', label: '1. Загрузка документации' }, { key: 'sheets', label: '2. Сопоставление листов' },
  { key: 'changes', label: '3. Изменения проекта' }, { key: 'journal', label: '4. Отчёт' },
];
const STATES: Readonly<Record<StageChainRun['state'], string>> = {
  queued: 'В очереди', running: 'Выполняется', paused: 'Приостановлено', completed: 'Завершено', failed: 'Ошибка', cancelled: 'Отменено',
};

export function StageWorkspace({ projectUid, mayAct }: { readonly projectUid: string; readonly mayAct: boolean }) {
  const cache = useQueryClient();
  const [tab, setTab] = useState<Tab>('documentation');
  const [visitedSheets, setVisitedSheets] = useState(false);
  const [chosenPair, setChosenPair] = useState('');
  const [chosenRun, setChosenRun] = useState<string | null>(null);
  const [focus, setFocus] = useState<StageMapFocus | undefined>();
  const [focusedCardId, setFocusedCardId] = useState<string | undefined>();
  const [navigating, setNavigating] = useState(false);
  const [navigationError, setNavigationError] = useState<unknown>(null);
  const requestToken = useRef(0);
  useEffect(() => () => { requestToken.current += 1; }, []);
  const pairs = useQuery({ queryKey: [...STAGE_PAIR_KEYS.projectPairs(projectUid), 'workspace'],
    queryFn: () => readStagePairs(projectUid), retry: false });
  const pairId = chosenPair || (pairs.data?.length === 1 ? pairs.data[0]!.pair_id : '');
  const listedPair = pairs.data?.find((item) => item.pair_id === pairId && item.project_uid === projectUid);
  const selectedPair = useQuery({ queryKey: ['stage-workspace-pair', projectUid, pairId],
    queryFn: async () => {
      const value = (await getStagePair({ path: { stage_pair_id: pairId } })).data;
      if (value.project_uid !== projectUid) throw new Error('Пара относится к другому проекту.');
      return value;
    }, enabled: pairId !== '' && listedPair === undefined, retry: false });
  const pair = listedPair ?? selectedPair.data;
  const runs = useQuery({ queryKey: ['stage-full-runs', pairId], queryFn: () => readStageRunOptions(pairId),
    enabled: pair !== undefined, retry: false });
  const fullRuns = runs.data?.filter((item) => item.kind === 'full') ?? [];
  const runId = pair === undefined ? '' : chosenRun ?? fullRuns[0]?.run_id ?? '';
  const run = useQuery({ queryKey: ['stage-full-run', runId],
    queryFn: async () => (await getStageChainRun({ path: { stage_chain_run_id: runId } })).data,
    enabled: runId !== '' && pair !== undefined, retry: false });
  const coherentRun = run.data?.pair_id === pairId && run.data.kind === 'full' ? run.data : undefined;
  const selection = useRef({ pairId, runId });
  selection.current = { pairId, runId };
  const choosePair = (next: string) => {
    requestToken.current += 1; setChosenPair(next); setChosenRun(null); setFocus(undefined); setFocusedCardId(undefined); setNavigationError(null); setNavigating(false);
  };
  const chooseRun = (next: string) => {
    requestToken.current += 1; setChosenRun(next); setFocus(undefined); setFocusedCardId(undefined); setNavigationError(null); setNavigating(false);
  };
  const selectKnownRun = (value: StageChainRun, showChanges: boolean) => {
    if (value.kind !== 'full') { setNavigationError(new Error('Выберите полный запуск этой пары.')); return; }
    cache.setQueryData(['stage-full-run', value.run_id], value);
    if (selection.current.pairId !== value.pair_id || selection.current.runId !== value.run_id) {
      requestToken.current += 1; setFocus(undefined); setFocusedCardId(undefined); setNavigating(false);
    }
    setChosenPair(value.pair_id); setChosenRun(value.run_id);
    void cache.invalidateQueries({ queryKey: ['stage-full-runs', value.pair_id] });
    if (showChanges) setTab('changes');
  };
  const openRun = async (nextRunId: string, nextPairId: string) => {
    const token = ++requestToken.current;
    setNavigationError(null); setNavigating(true);
    try {
      const result = await cache.fetchQuery({ queryKey: ['stage-full-run', nextRunId],
        queryFn: async () => (await getStageChainRun({ path: { stage_chain_run_id: nextRunId } })).data });
      if (result.pair_id !== nextPairId) throw new Error('Запуск относится к другой паре.');
      if (token !== requestToken.current) return;
      setNavigating(false);
      selectKnownRun(result, true);
    } catch (error) { if (token === requestToken.current) setNavigationError(error); }
    finally { if (token === requestToken.current) setNavigating(false); }
  };
  const navigate = async (sourceRunId: string, make: (value: StageChainRun, revision: Awaited<ReturnType<typeof getStageSheetMapRevision>>['data'], token: number) => StageMapFocus) => {
    const token = ++requestToken.current;
    const scope = { ...selection.current };
    setNavigating(true); setNavigationError(null);
    try {
      if (!pair || sourceRunId !== scope.runId) throw new Error('Выберите запуск, которому принадлежит свидетельство.');
      const value = await cache.fetchQuery({ queryKey: ['stage-full-run', sourceRunId],
        queryFn: async () => (await getStageChainRun({ path: { stage_chain_run_id: sourceRunId } })).data });
      const revisionId = value.effective_link_revision_id ?? value.link_revision_id;
      const revision = await cache.fetchQuery({ queryKey: ['stage-evidence-revision', revisionId],
        queryFn: async () => (await getStageSheetMapRevision({ path: { stage_link_revision_id: revisionId } })).data, staleTime: Infinity });
      assertRunRevision(value, revision, scope.pairId);
      const target = make(value, revision, token);
      const profileIds = [...new Set([target.leftProfileId, target.rightProfileId].filter((id): id is string => id !== undefined))];
      await Promise.all(profileIds.map(async (profileId) => {
        const profile = await cache.fetchQuery({ queryKey: ['stage-view-profile', profileId],
          queryFn: async () => (await getVersionPageProfile({ path: { comparison_page_profile_id: profileId } })).data, staleTime: Infinity });
        if (!value.pinned_version_uids.includes(profile.version_uid) || profile.page_profile_id !== profileId) throw new Error('Лист не принадлежит сохранённому запуску.');
      }));
      if (token !== requestToken.current) return;
      setFocus(target); setVisitedSheets(true); setTab('sheets');
    } catch (error) { if (token === requestToken.current) setNavigationError(error); }
    finally { if (token === requestToken.current) setNavigating(false); }
  };
  const onOpenEvidence: OpenStageEvidence = (evidence, card) => { void navigate(card.run_id,
    (value, revision, token) => evidenceFocus(value, revision, evidence, card, token)); };
  const onOpenRawDifference: OpenStageRawDifference = (difference, left, right) => {
    void navigate(runId, (value, revision, token) => {
      if (difference.revision_id !== revision.revision_id) throw new Error('Различие относится к другой карте листов.');
      return rawFocus(value, revision, left, right, token);
    });
  };
  const error = navigationError ?? pairs.error ?? selectedPair.error ?? runs.error ?? run.error;
  const message = error === null ? null : failureMessage(error);
  const runOptions = coherentRun !== undefined && !runs.data?.some((item) => item.run_id === coherentRun.run_id)
    ? [coherentRun, ...fullRuns] : fullRuns;
  const pairOptions = pair !== undefined && !pairs.data?.some((item) => item.pair_id === pair.pair_id)
    ? [pair, ...(pairs.data ?? [])] : pairs.data ?? [];
  return <div className={styles.workspace} data-stage-workspace={projectUid}>
    <div className={styles.selection}>
      <label>Пара стадий<select data-stage-pair-select="" value={pairId} onChange={(event) => choosePair(event.target.value)}>
        <option value="">— выберите —</option>{pairOptions.map((item) => <option key={item.pair_id} value={item.pair_id}>
          {item.left_document_uid} → {item.right_document_uid ?? item.assembly_id}</option>)}
      </select></label>
      <label>Запуск сравнения<select data-stage-run-select="" value={runId} disabled={pair === undefined} onChange={(event) => chooseRun(event.target.value)}>
        <option value="">— выберите —</option>{runOptions.map((item) => <option key={item.run_id} value={item.run_id}>
          {formatInstant(item.created_at)} · {STATES[item.state]}{item.stale ? ' · устарел' : ''}</option>)}
      </select></label>
    </div>
    {pairs.isPending || (pairId !== '' && pair === undefined && selectedPair.isPending)
      || (pair !== undefined && runs.isPending) || (runId !== '' && run.isPending) ? <LoadingState what="пары и запуски сравнения" /> : null}
    {message === null ? null : <ErrorState title="Не удалось открыть выбранное сравнение или место на чертеже" detail={message.detail} correlationId={message.correlationId} />}
    {run.data !== undefined && coherentRun === undefined ? <ErrorState title="Выбранный запуск недоступен для полного отчёта" detail="Выберите полный запуск этой пары." /> : null}
    {navigating ? <p role="status">Открываем сохранённое место на чертеже…</p> : null}
    {pair === undefined || (runId !== '' && coherentRun === undefined) ? null : <StageRunControls pairId={pair.pair_id} mayAct={mayAct && pair.state === 'confirmed'}
      {...(coherentRun === undefined ? {} : { runId: coherentRun.run_id })} onRunChange={(value) => selectKnownRun(value, false)} />}
    <div role="tablist" aria-label="Разделы сравнения стадий" className={styles.tabs}>
      {TABS.map((item) => <button key={item.key} id={`stage-tab-${item.key}`} type="button" role="tab" data-stage-tab={item.key}
        aria-controls={`stage-panel-${item.key}`} aria-selected={tab === item.key} className="am-button"
        onClick={() => { setTab(item.key); if (item.key === 'sheets') setVisitedSheets(true); }}>{item.label}</button>)}
    </div>
    {tab === 'documentation' ? <section className={styles.panel} role="tabpanel" id="stage-panel-documentation" aria-labelledby="stage-tab-documentation">
      <StageUploadPanel projectUid={projectUid} mayAct={mayAct} />
      <StagePairCatalog projectUid={projectUid} mayAct={mayAct} onRunChange={(value) => selectKnownRun(value, true)} onOpenRun={(id, owner) => { void openRun(id, owner); }} />
    </section> : null}
    {visitedSheets ? <section className={styles.panel} hidden={tab !== 'sheets'} role="tabpanel" id="stage-panel-sheets" aria-labelledby="stage-tab-sheets">
      <StageSheetMap projectUid={projectUid} mayAct={mayAct && pair?.state === 'confirmed'} pairId={pairId}
        onPairChange={choosePair} textProvider={storedPageText} {...(coherentRun === undefined ? {} : { runId: coherentRun.run_id })}
        {...(focus === undefined ? {} : { focus })} onClearFocus={() => setFocus(undefined)}
        onReviewCreated={(card) => { if (card.run_id === selection.current.runId) { setFocusedCardId(card.card_id); setTab('changes'); } }} />
    </section> : null}
    {tab === 'changes' ? <section className={styles.panel} role="tabpanel" id="stage-panel-changes" aria-labelledby="stage-tab-changes" data-stage-selected-run={coherentRun?.run_id}>
      <StageChanges runId={coherentRun?.run_id} mayAct={mayAct && pair?.state === 'confirmed'} onOpenEvidence={onOpenEvidence} onOpenRawDifference={onOpenRawDifference}
        {...(focusedCardId === undefined ? {} : { focusCardId: focusedCardId })} />
    </section> : null}
    {tab === 'journal' ? <section className={styles.panel} role="tabpanel" id="stage-panel-journal" aria-labelledby="stage-tab-journal" data-stage-selected-run={coherentRun?.run_id}>
      <StageJournal runId={coherentRun?.run_id} mayAct={mayAct} onOpenEvidence={onOpenEvidence} />
    </section> : null}
  </div>;
}
