'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { ComparisonBox, ProjectUid, StageChangeCard, StageLinkInput, StageLinkRevision, StageSheetPassport, VersionPageProfile } from '@/shared/api';
import {
  ApiError, applyStageSheetMap, failureMessage, getStageChainRun, getStageSheetMap, getStageSheetMapRevision, getVersionPageProfile,
  listStageSheetMapHistory, listStageSheetPassports, listStageSheetSuggestions,
  newIdempotencyKey,
} from '@/shared/api';
import { useStagePairs } from '@/entities/stage-pair';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import {
  evidenceNeedsRecompute, StageTextEvidence, STAGE_TEXT_KEYS, useStageTextEvidence,
} from '@/widgets/stage-text-evidence';
import type { PageTextProvider } from '@/widgets/stage-text-evidence';

import { addUnpaired, applyTextHint, moveSheet, unlinkRow } from '../model/draft';
import { acceptedSameFragments } from '../model/ai-masks';
import { readAiReviews } from '../api/read-ai-reviews';
import { focusedRow } from '../model/navigation';
import type { StageMapFocus } from '../model/navigation';
import { StagePairViewer } from './stage-pair-viewer';
import type { StageViewerFocus } from './stage-pair-viewer';
import styles from './stage-sheet-map.module.css';

const PAGE_LIMIT = 100;

async function allPassports(pairId: string): Promise<StageSheetPassport[]> {
  const items: StageSheetPassport[] = [];
  let cursor: string | undefined;
  do {
    const page = (await listStageSheetPassports({
      path: { stage_pair_id: pairId },
      query: { limit: PAGE_LIMIT, ...(cursor === undefined ? {} : { cursor }) },
    })).data;
    items.push(...page.items);
    if (items.length > 1000) throw new Error('В этой паре больше 1000 листов. Разбейте сборку на меньшие пары.');
    cursor = page.page.next_cursor ?? undefined;
  } while (cursor !== undefined);
  return items;
}

function label(page: StageSheetPassport): string {
  return `стр. ${page.page_number}${page.sheet_number === undefined ? '' : ` · л. ${page.sheet_number}`}`
    + `${page.sheet_type === undefined ? '' : ` · ${page.sheet_type}`}`
    + `${page.building === undefined ? '' : ` · корпус ${page.building}`}`
    + `${page.floor === undefined ? '' : ` · ${page.floor}`}`;
}

function PairMap({ pairId, mayAct, textProvider, runId, focus: externalFocus, onClearFocus, onReviewCreated }: {
  readonly pairId: string; readonly mayAct: boolean; readonly textProvider: PageTextProvider | undefined;
  readonly runId: string | undefined; readonly focus: StageMapFocus | undefined; readonly onClearFocus: (() => void) | undefined;
  readonly onReviewCreated: ((card: StageChangeCard) => void) | undefined;
}) {
  const cache = useQueryClient();
  const passports = useQuery({
    queryKey: ['stage-sheet-map', pairId, 'passports'],
    queryFn: () => allPassports(pairId), retry: false,
  });
  const suggestions = useQuery({
    queryKey: ['stage-sheet-map', pairId, 'suggestions'],
    queryFn: async () => (await listStageSheetSuggestions({
      path: { stage_pair_id: pairId }, query: { limit: 100 },
    })).data, retry: false,
  });
  const current = useQuery<StageLinkRevision | null>({
    queryKey: ['stage-sheet-map', pairId, 'current'],
    queryFn: async () => {
      try { return (await getStageSheetMap({ path: { stage_pair_id: pairId } })).data; }
      catch (failure) {
        if (failure instanceof ApiError && failure.status === 404) return null;
        throw failure;
      }
    }, retry: false,
  });
  const history = useQuery({
    queryKey: ['stage-sheet-map', pairId, 'history'],
    queryFn: async () => (await listStageSheetMapHistory({
      path: { stage_pair_id: pairId }, query: { limit: 20 },
    })).data, retry: false,
  });
  const [draft, setDraft] = useState<StageLinkInput[]>([]);
  const [dirty, setDirty] = useState(false);
  const [left, setLeft] = useState('');
  const [right, setRight] = useState('');
  const [leftSearch, setLeftSearch] = useState('');
  const [rightSearch, setRightSearch] = useState('');
  const [saving, setSaving] = useState(false);
  const [commandError, setCommandError] = useState<unknown | null>(null);
  const held = useRef<{ signature: string; key: string } | null>(null);
  const [focus, setFocus] = useState<StageViewerFocus | undefined>();
  const evidenceRevisionId = externalFocus?.revisionId ?? current.data?.revision_id;
  const historical = externalFocus !== undefined && externalFocus.revisionId !== current.data?.revision_id;
  const snapshot = useQuery({ queryKey: ['stage-evidence-revision', externalFocus?.revisionId ?? 'none'],
    queryFn: async () => {
      const value = (await getStageSheetMapRevision({ path: { stage_link_revision_id: externalFocus!.revisionId } })).data;
      if (value.pair_id !== pairId) throw new Error('Карта относится к другой паре.');
      return value;
    }, enabled: externalFocus !== undefined, retry: false, staleTime: Infinity });
  const run = useQuery({ queryKey: ['stage-full-run', runId ?? ''],
    queryFn: async () => (await getStageChainRun({ path: { stage_chain_run_id: runId! } })).data,
    enabled: runId !== undefined, retry: false });
  const aiReady = run.data?.pair_id === pairId && run.data.with_ai === true
    && (run.data.steps.some((step) => step.step_no === 4 && step.state === 'completed') || run.data.state === 'completed');
  const reviews = useQuery({ queryKey: ['stage-map-ai-reviews', runId ?? ''], queryFn: () => readAiReviews(runId!), enabled: aiReady, retry: false });
  useEffect(() => { if (aiReady) void reviews.refetch(); }, [aiReady, runId, reviews.refetch]);
  const text = useStageTextEvidence(pairId, evidenceRevisionId);
  const aiCurrent = aiReady && !run.data?.stale && (run.data?.effective_link_revision_id ?? run.data?.link_revision_id) === evidenceRevisionId;
  const aiIds = aiCurrent ? acceptedSameFragments(text.data?.fragments ?? [], reviews.data ?? []) : [];
  const maskedIds = dirty || run.data?.stale === true ? [] : [...new Set([
    ...(text.data?.exclusions.flatMap((item) => [item.left_fragment_id, item.right_fragment_id]) ?? []), ...aiIds,
  ])];
  const reviewRunId = !historical && !dirty && run.data?.pair_id === pairId && run.data.kind === 'full' && !run.data.stale
    && (run.data.effective_link_revision_id ?? run.data.link_revision_id) === evidenceRevisionId ? run.data.run_id : undefined;
  const viewerEvidence = text.data === undefined ? undefined : { ...text.data, aiSameFragmentIds: aiIds };
  const beforeExternal = useRef<{ left: string; right: string } | null>(null);
  const rowNodes = useRef(new Map<number, HTMLLIElement>());
  const displayRows = historical ? snapshot.data?.items ?? [] : draft;
  const selectedRow = focusedRow(displayRows, externalFocus);
  useEffect(() => {
    if (externalFocus !== undefined) {
      if (beforeExternal.current === null) beforeExternal.current = { left, right };
      setLeft(externalFocus.leftProfileId ?? ''); setRight(externalFocus.rightProfileId ?? '');
      setLeftSearch(''); setRightSearch('');
      setFocus({ token: externalFocus.token,
        ...(externalFocus.leftBox === undefined ? {} : { left: externalFocus.leftBox }),
        ...(externalFocus.rightBox === undefined ? {} : { right: externalFocus.rightBox }) });
    } else if (beforeExternal.current !== null) {
      setLeft(beforeExternal.current.left || draft[0]?.left_profile_id || '');
      setRight(beforeExternal.current.right || draft[0]?.right_profile_id || ''); beforeExternal.current = null; setFocus(undefined);
    }
    // External navigation is an event; manual page selections do not reapply it.
  }, [externalFocus]);
  useEffect(() => { if (selectedRow !== undefined) rowNodes.current.get(selectedRow)?.scrollIntoView?.({ block: 'nearest' }); }, [selectedRow, externalFocus?.token, displayRows.length]);
  const leftStored = useQuery({ queryKey: ['stage-view-profile', left || 'none'],
    queryFn: async () => (await getVersionPageProfile({ path: { comparison_page_profile_id: left } })).data,
    enabled: externalFocus !== undefined && left !== '', retry: false });
  const rightStored = useQuery({ queryKey: ['stage-view-profile', right || 'none'],
    queryFn: async () => (await getVersionPageProfile({ path: { comparison_page_profile_id: right } })).data,
    enabled: externalFocus !== undefined && right !== '', retry: false });
  const storedPassport = (profile: VersionPageProfile | undefined, side: 'left' | 'right'): StageSheetPassport | undefined => {
    if (profile === undefined || run.data?.pair_id !== pairId || !run.data.pinned_version_uids.includes(profile.version_uid)) return undefined;
    return { profile_id: profile.page_profile_id, version_uid: profile.version_uid, page_number: profile.page_number, side };
  };

  useEffect(() => {
    if (current.isSuccess && !dirty) {
      setDraft(current.data?.items.map((item) => ({
        relation: item.relation,
        ...(item.left_profile_id === undefined ? {} : { left_profile_id: item.left_profile_id }),
        ...(item.right_profile_id === undefined ? {} : { right_profile_id: item.right_profile_id }),
      })) ?? []);
      const first = current.data?.items[0];
      if (first !== undefined) {
        setLeft((selected) => selected || first.left_profile_id || '');
        setRight((selected) => selected || first.right_profile_id || '');
      }
    }
  }, [current.data, current.isSuccess, dirty]);

  const snapshotIds = new Set(snapshot.data?.items.flatMap((item) => [item.left_profile_id, item.right_profile_id]).filter((id): id is string => id !== undefined));
  const visiblePassports = (passports.data ?? []).filter((page) => !historical || snapshotIds.has(page.profile_id));
  const leftPages = visiblePassports.filter((page) => page.side === 'left');
  const rightPages = visiblePassports.filter((page) => page.side === 'right');
  const oldLeft = storedPassport(leftStored.data, 'left');
  const oldRight = storedPassport(rightStored.data, 'right');
  if (oldLeft !== undefined && !leftPages.some((page) => page.profile_id === oldLeft.profile_id)) leftPages.push(oldLeft);
  if (oldRight !== undefined && !rightPages.some((page) => page.profile_id === oldRight.profile_id)) rightPages.push(oldRight);
  const leftPage = leftPages.find((page) => page.profile_id === left);
  const rightPage = rightPages.find((page) => page.profile_id === right);
  const showLeft = leftPages.filter((page) => page.profile_id === left || label(page).toLocaleLowerCase().includes(leftSearch.toLocaleLowerCase()));
  const showRight = rightPages.filter((page) => page.profile_id === right || label(page).toLocaleLowerCase().includes(rightSearch.toLocaleLowerCase()));
  const names = new Map((passports.data ?? []).map((page) => [page.profile_id, label(page)]));
  const failure = passports.error ?? suggestions.error ?? current.error ?? history.error ?? snapshot.error ?? run.error ?? reviews.error ?? leftStored.error ?? rightStored.error;
  const readFailure = failure === null ? null : failureMessage(failure);
  const actFailure = commandError === null ? null : failureMessage(commandError);

  const add = (row: StageLinkInput) => {
    if (draft.some((item) => item.left_profile_id === row.left_profile_id
      && item.right_profile_id === row.right_profile_id && item.relation === row.relation)) return;
    setDraft((items) => [...items.filter((item) => !(
      (item.relation === 'only_left' && item.left_profile_id === row.left_profile_id)
      || (item.relation === 'only_right' && item.right_profile_id === row.right_profile_id)
    )), row]);
    setDirty(true);
  };
  const focusPages = (leftProfileId?: string, rightProfileId?: string,
    leftBox?: ComparisonBox, rightBox?: ComparisonBox) => {
    setLeft(leftProfileId ?? '');
    setRight(rightProfileId ?? '');
    setFocus((prior) => ({ token: (prior?.token ?? 0) + 1,
      ...(leftBox === undefined ? {} : { left: leftBox }),
      ...(rightBox === undefined ? {} : { right: rightBox }) }));
  };
  const save = async () => {
    if (draft.length === 0 || historical) return;
    const signature = JSON.stringify([pairId, current.data?.revision_id ?? null, draft]);
    if (held.current?.signature !== signature) held.current = { signature, key: newIdempotencyKey() };
    setSaving(true);
    setCommandError(null);
    try {
      const answer = await applyStageSheetMap({
        path: { stage_pair_id: pairId },
        body: {
          items: draft,
          ...(current.data === null || current.data === undefined
            ? {} : { base_revision_id: current.data.revision_id }),
        },
        idempotencyKey: held.current.key,
      });
      held.current = null;
      setDirty(false);
      cache.setQueryData(['stage-sheet-map', pairId, 'current'], answer.data);
      await cache.invalidateQueries({ queryKey: ['stage-sheet-map', pairId, 'history'] });
    } catch (error) { setCommandError(error); }
    finally { setSaving(false); }
  };

  return <div className={styles.workbench}>
    {externalFocus === undefined ? null : <div role="status" className={styles.focusNotice}>
      <p>{historical ? 'Показана сохранённая карта выбранного запуска. Изменения состава здесь недоступны.' : 'Открыто свидетельство выбранного запуска.'}</p>
      {dirty ? <p>Черновик текущей карты сохранён в этой вкладке.</p> : null}
      {onClearFocus === undefined ? null : <button type="button" className="am-button" onClick={onClearFocus}>Вернуться к текущей карте</button>}
    </div>}
    {passports.isPending || suggestions.isPending || current.isPending
      ? <LoadingState what="листы пары стадий" /> : null}
    {readFailure === null ? null : <ErrorState title="Карта листов не открылась" detail={readFailure.detail} correlationId={readFailure.correlationId} />}
    <div className={styles.panes}>
      <div className={styles.pane}>
        <label>Лист П
          <input value={leftSearch} onChange={(event) => setLeftSearch(event.target.value)} placeholder="Найти лист по штампу" />
          <select value={left} onChange={(event) => { setLeft(event.target.value); setFocus(undefined); }}>
            <option value="">Пусто</option>
            {showLeft.map((page) => <option key={page.profile_id} value={page.profile_id}>{label(page)}</option>)}
          </select>
        </label>
      </div>
      <div className={styles.pane}>
        <label>Лист Р
          <input value={rightSearch} onChange={(event) => setRightSearch(event.target.value)} placeholder="Найти лист по штампу" />
          <select value={right} onChange={(event) => { setRight(event.target.value); setFocus(undefined); }}>
            <option value="">Пусто</option>
            {showRight.map((page) => <option key={page.profile_id} value={page.profile_id}>{label(page)}</option>)}
          </select>
        </label>
      </div>
    </div>
    <StagePairViewer leftPage={leftPage} rightPage={rightPage} evidence={viewerEvidence} stale={dirty || run.data?.stale === true}
      {...(focus === undefined ? {} : { focus })}
      {...(textProvider === undefined ? {} : { textProvider })} />
    {mayAct && !historical && current.isSuccess && passports.isSuccess ? <div className={styles.actions}>
      <button type="button" className="am-button" disabled={left === '' || right === ''} onClick={() => add({ relation: 'paired', left_profile_id: left, right_profile_id: right })}>Добавить связь</button>
      <button type="button" className="am-button" disabled={left === ''} onClick={() => { setDraft((items) => addUnpaired(items, 'left', left)); setDirty(true); }}>Без пары слева</button>
      <button type="button" className="am-button" disabled={right === ''} onClick={() => { setDraft((items) => addUnpaired(items, 'right', right)); setDirty(true); }}>Без пары справа</button>
      <button type="button" className="am-button" disabled={suggestions.data?.items.length === 0} onClick={() => {
        const high = suggestions.data?.items.filter((item) => item.confidence === 'high') ?? [];
        if (high.length === 0) return;
        let accepted: StageLinkInput[] = high.map((item) => ({ relation: 'paired', left_profile_id: item.left_profile_id, right_profile_id: item.right_profile_id }));
        for (const page of passports.data ?? []) accepted = addUnpaired(accepted, page.side, page.profile_id);
        setDraft(accepted);
        setDirty(true);
      }}>Принять видимые точные подсказки</button>
    </div> : null}
    <p>Подсказки не меняют карту. Высокая уверенность: {suggestions.data?.items.filter((item) => item.confidence === 'high').length ?? 0}; проверить: {suggestions.data?.items.filter((item) => item.confidence === 'review').length ?? 0}.</p>
    {draft.length === 0 ? <EmptyState title="Карта листов пока пуста" detail="Выберите листы и подтвердите первую связь." /> : null}
    <ol className={styles.rows}>
      {displayRows.map((row, index) => <li key={`${index}:${row.left_profile_id ?? ''}:${row.right_profile_id ?? ''}`} className={styles.row}
        ref={(node) => { if (node === null) rowNodes.current.delete(index); else rowNodes.current.set(index, node); }}
        data-stage-map-row={index} data-stage-focused-row={index === selectedRow ? 'true' : undefined}>
        <span>П: {row.left_profile_id === undefined ? 'Пусто' : names.get(row.left_profile_id) ?? row.left_profile_id}</span>
        <span>Р: {row.right_profile_id === undefined ? 'Пусто' : names.get(row.right_profile_id) ?? row.right_profile_id}</span>
        {mayAct && !historical ? <div className={styles.actions}>
          <button type="button" className="am-button" onClick={() => focusPages(row.left_profile_id, row.right_profile_id)}>Открыть связь ↗</button>
          <button type="button" className="am-button" disabled={left === ''} onClick={() => { setDraft((items) => moveSheet(addUnpaired(items, 'left', left), 'left', left, index)); setDirty(true); }}>Перенести П сюда</button>
          <button type="button" className="am-button" disabled={right === ''} onClick={() => { setDraft((items) => moveSheet(addUnpaired(items, 'right', right), 'right', right, index)); setDirty(true); }}>Перенести Р сюда</button>
          <button type="button" className="am-button" disabled={row.relation !== 'paired'} onClick={() => { setDraft((items) => unlinkRow(items, index)); setDirty(true); }}>Удалить связь</button>
        </div> : <button type="button" className="am-button" onClick={() => focusPages(row.left_profile_id, row.right_profile_id)}>Открыть связь ↗</button>}
      </li>)}
    </ol>
    {mayAct && !historical ? <button type="button" className="am-button" disabled={!dirty || saving || draft.length === 0} onClick={() => void save()}>Сохранить решение эксперта</button> : null}
    {actFailure === null ? null : <ErrorState title="Карта не сохранена" detail={actFailure.detail} correlationId={actFailure.correlationId} />}
    <p>Текущая ревизия: {current.data?.revision_no ?? 'нет'}.</p>
    {history.data?.items.length ? <details><summary>История карты</summary><ol>
      {history.data.items.map((item) => <li key={item.revision_id}>Ревизия {item.revision_no} · {item.items.length} строк</li>)}
    </ol></details> : null}
    {aiIds.length === 0 ? null : <p>Совпадения после ИИ-ревизии: {aiIds.length} фрагментов. Исходные различия доступны ниже.</p>}
    <StageTextEvidence revisionId={evidenceRevisionId} mayAct={mayAct && !historical} dirty={dirty || historical}
      evidence={text.data} loading={text.isFetching} needsRecompute={evidenceNeedsRecompute(text.error)}
      maskedFragmentIds={maskedIds} {...(reviewRunId === undefined ? {} : { runId: reviewRunId })}
      {...(onReviewCreated === undefined ? {} : { onReviewCreated })}
      error={text.error} names={names}
      onCompleted={() => { void cache.invalidateQueries({ queryKey: STAGE_TEXT_KEYS.evidence(pairId, current.data?.revision_id) }); }}
      onFocus={focusPages}
      onHint={(leftId, rightId, mode) => {
        setDraft((items) => applyTextHint(items, leftId, rightId, mode));
        setDirty(true);
        focusPages(leftId, rightId);
      }} />
  </div>;
}

export interface StageSheetMapProps {
  readonly projectUid: ProjectUid;
  readonly mayAct: boolean;
  readonly textProvider?: PageTextProvider;
  readonly pairId?: string;
  readonly onPairChange?: (pairId: string) => void;
  readonly runId?: string;
  readonly focus?: StageMapFocus;
  readonly onClearFocus?: () => void;
  readonly onReviewCreated?: (card: StageChangeCard) => void;
}

export function StageSheetMap({ projectUid, mayAct, textProvider, pairId: controlledPairId, onPairChange, runId, focus, onClearFocus, onReviewCreated }: StageSheetMapProps) {
  const [pages, setPages] = useState<string[]>([]);
  const [selected, setSelected] = useState('');
  const pairs = useStagePairs(controlledPairId === undefined ? projectUid : null, pages.at(-1));
  const pairId = controlledPairId ?? (selected || (pairs.data?.items.length === 1 ? pairs.data.items[0]!.pair_id : ''));
  const pairFailure = pairs.error === null ? null : failureMessage(pairs.error);
  return <section className={styles.workbench} aria-labelledby="stage-map-heading">
    <h2 id="stage-map-heading">Сопоставление листов</h2>
    {controlledPairId === undefined && pairs.isPending ? <LoadingState what="пары стадий" /> : null}
    {pairFailure === null ? null : <ErrorState title="Пары не открылись" detail={pairFailure.detail} correlationId={pairFailure.correlationId} />}
    {controlledPairId === undefined ? <><label>Пара стадий
      <select value={pairId} onChange={(event) => { setSelected(event.target.value); onPairChange?.(event.target.value); }}>
        <option value="">— выберите —</option>
        {pairs.data?.items.map((pair) => <option key={pair.pair_id} value={pair.pair_id}>
          {pair.left_document_uid} → {pair.right_document_uid ?? pair.assembly_id}
        </option>)}
      </select>
    </label>
    {pairs.data === undefined ? null : <div className={styles.actions}>
      <button type="button" className="am-button" disabled={pages.length === 0} onClick={() => { setPages((held) => held.slice(0, -1)); setSelected(''); }}>Назад</button>
      <button type="button" className="am-button" disabled={pairs.data.page.next_cursor === null} onClick={() => {
        const next = pairs.data?.page.next_cursor;
        if (next !== null && next !== undefined) { setPages((held) => [...held, next]); setSelected(''); }
      }}>Далее</button>
    </div>}</> : null}
    {focus !== undefined && (focus.pairId !== pairId || (runId !== undefined && focus.runId !== runId))
      ? <ErrorState title="Свидетельство относится к другому сравнению" detail="Выберите запуск и откройте место заново." /> : null}
    {pairId === '' ? <EmptyState title="Выберите пару стадий" detail="Карта листов относится к одной подтверждённой паре." />
      : <PairMap key={pairId} pairId={pairId} mayAct={mayAct} textProvider={textProvider} runId={runId} focus={focus?.pairId === pairId && (runId === undefined || focus.runId === runId) ? focus : undefined} onClearFocus={onClearFocus} onReviewCreated={onReviewCreated} />}
  </section>;
}
