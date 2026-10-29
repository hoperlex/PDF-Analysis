'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { ProjectUid, StageLinkInput, StageLinkRevision, StageSheetPassport } from '@/shared/api';
import {
  ApiError, applyStageSheetMap, failureMessage, getStageSheetMap,
  listStageSheetMapHistory, listStageSheetPassports, listStageSheetSuggestions,
  newIdempotencyKey, streamVersionPagePreview,
} from '@/shared/api';
import { useStagePairs } from '@/entities/stage-pair';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import { addUnpaired, moveSheet, unlinkRow } from '../model/draft';
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

function Preview({ title, page }: { readonly title: string; readonly page: StageSheetPassport | undefined }) {
  const [image, setImage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setImage(null);
    setFailed(false);
    if (page === undefined) return;
    const controller = new AbortController();
    let url: string | null = null;
    void streamVersionPagePreview(
      { path: { comparison_page_profile_id: page.profile_id } }, { signal: controller.signal },
    ).then((answer) => {
      if (controller.signal.aborted) return;
      url = URL.createObjectURL(answer.data);
      setImage(url);
    }).catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => { controller.abort(); if (url !== null) URL.revokeObjectURL(url); };
  }, [page?.profile_id]);
  return <div className={styles.preview}>
    <strong>{title}</strong>
    {page === undefined ? <p>Лист не выбран.</p> : <p>{label(page)}</p>}
    {failed ? <p role="alert">Изображение листа не открылось.</p> : null}
    {image === null ? null : <img src={image} alt={`${title}: ${page === undefined ? '' : label(page)}`} />}
  </div>;
}

function PairMap({ pairId, mayAct }: { readonly pairId: string; readonly mayAct: boolean }) {
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

  useEffect(() => {
    if (current.isSuccess && !dirty) {
      setDraft(current.data?.items.map((item) => ({
        relation: item.relation,
        ...(item.left_profile_id === undefined ? {} : { left_profile_id: item.left_profile_id }),
        ...(item.right_profile_id === undefined ? {} : { right_profile_id: item.right_profile_id }),
      })) ?? []);
    }
  }, [current.data, current.isSuccess, dirty]);

  const leftPages = passports.data?.filter((page) => page.side === 'left') ?? [];
  const rightPages = passports.data?.filter((page) => page.side === 'right') ?? [];
  const leftPage = leftPages.find((page) => page.profile_id === left);
  const rightPage = rightPages.find((page) => page.profile_id === right);
  const showLeft = leftPages.filter((page) => page.profile_id === left || label(page).toLocaleLowerCase().includes(leftSearch.toLocaleLowerCase()));
  const showRight = rightPages.filter((page) => page.profile_id === right || label(page).toLocaleLowerCase().includes(rightSearch.toLocaleLowerCase()));
  const names = new Map((passports.data ?? []).map((page) => [page.profile_id, label(page)]));
  const failure = passports.error ?? suggestions.error ?? current.error ?? history.error;
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
  const save = async () => {
    if (draft.length === 0) return;
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
    {passports.isPending || suggestions.isPending || current.isPending
      ? <LoadingState what="листы пары стадий" /> : null}
    {readFailure === null ? null : <ErrorState title="Карта листов не открылась" detail={readFailure.detail} correlationId={readFailure.correlationId} />}
    <div className={styles.panes}>
      <div className={styles.pane}>
        <label>Лист П
          <input value={leftSearch} onChange={(event) => setLeftSearch(event.target.value)} placeholder="Найти лист по штампу" />
          <select value={left} onChange={(event) => setLeft(event.target.value)}>
            <option value="">Пусто</option>
            {showLeft.map((page) => <option key={page.profile_id} value={page.profile_id}>{label(page)}</option>)}
          </select>
        </label>
        <Preview title="П" page={leftPage} />
      </div>
      <div className={styles.pane}>
        <label>Лист Р
          <input value={rightSearch} onChange={(event) => setRightSearch(event.target.value)} placeholder="Найти лист по штампу" />
          <select value={right} onChange={(event) => setRight(event.target.value)}>
            <option value="">Пусто</option>
            {showRight.map((page) => <option key={page.profile_id} value={page.profile_id}>{label(page)}</option>)}
          </select>
        </label>
        <Preview title="Р" page={rightPage} />
      </div>
    </div>
    {mayAct && current.isSuccess && passports.isSuccess ? <div className={styles.actions}>
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
      {draft.map((row, index) => <li key={`${index}:${row.left_profile_id ?? ''}:${row.right_profile_id ?? ''}`} className={styles.row}>
        <span>П: {row.left_profile_id === undefined ? 'Пусто' : names.get(row.left_profile_id) ?? row.left_profile_id}</span>
        <span>Р: {row.right_profile_id === undefined ? 'Пусто' : names.get(row.right_profile_id) ?? row.right_profile_id}</span>
        {mayAct ? <div className={styles.actions}>
          <button type="button" className="am-button" disabled={left === ''} onClick={() => { setDraft((items) => moveSheet(addUnpaired(items, 'left', left), 'left', left, index)); setDirty(true); }}>Перенести П сюда</button>
          <button type="button" className="am-button" disabled={right === ''} onClick={() => { setDraft((items) => moveSheet(addUnpaired(items, 'right', right), 'right', right, index)); setDirty(true); }}>Перенести Р сюда</button>
          <button type="button" className="am-button" disabled={row.relation !== 'paired'} onClick={() => { setDraft((items) => unlinkRow(items, index)); setDirty(true); }}>Удалить связь</button>
        </div> : null}
      </li>)}
    </ol>
    {mayAct ? <button type="button" className="am-button" disabled={!dirty || saving || draft.length === 0} onClick={() => void save()}>Сохранить решение эксперта</button> : null}
    {actFailure === null ? null : <ErrorState title="Карта не сохранена" detail={actFailure.detail} correlationId={actFailure.correlationId} />}
    <p>Текущая ревизия: {current.data?.revision_no ?? 'нет'}.</p>
    {history.data?.items.length ? <details><summary>История карты</summary><ol>
      {history.data.items.map((item) => <li key={item.revision_id}>Ревизия {item.revision_no} · {item.items.length} строк</li>)}
    </ol></details> : null}
  </div>;
}

export function StageSheetMap({ projectUid, mayAct }: {
  readonly projectUid: ProjectUid;
  readonly mayAct: boolean;
}) {
  const [pages, setPages] = useState<string[]>([]);
  const [selected, setSelected] = useState('');
  const pairs = useStagePairs(projectUid, pages.at(-1));
  const pairId = selected || (pairs.data?.items.length === 1 ? pairs.data.items[0]!.pair_id : '');
  const pairFailure = pairs.error === null ? null : failureMessage(pairs.error);
  return <section className={styles.workbench} aria-labelledby="stage-map-heading">
    <h2 id="stage-map-heading">Сопоставление листов</h2>
    {pairs.isPending ? <LoadingState what="пары стадий" /> : null}
    {pairFailure === null ? null : <ErrorState title="Пары не открылись" detail={pairFailure.detail} correlationId={pairFailure.correlationId} />}
    <label>Пара стадий
      <select value={pairId} onChange={(event) => setSelected(event.target.value)}>
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
    </div>}
    {pairId === '' ? <EmptyState title="Выберите пару стадий" detail="Карта листов относится к одной подтверждённой паре." />
      : <PairMap key={pairId} pairId={pairId} mayAct={mayAct} />}
  </section>;
}
