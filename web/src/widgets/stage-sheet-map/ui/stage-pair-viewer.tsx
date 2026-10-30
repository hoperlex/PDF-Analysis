'use client';

import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { HTMLAttributes } from 'react';

import type { ComparisonBox, ComparisonSheetPair, StageSheetPassport, VersionPageProfile } from '@/shared/api';
import { failureMessage, getVersionPageProfile } from '@/shared/api';
import {
  ComparisonViewerView, initialState, reduce,
} from '@/widgets/comparison-viewer';
import type { ViewerAction, ViewerContext, ViewerGeometry, ViewerState } from '@/widgets/comparison-viewer';
import { pageText, provenFragments, searchPageText } from '@/widgets/stage-text-evidence';
import type { PageTextProvider, StageTextEvidenceData } from '@/widgets/stage-text-evidence';

import { profileGeometry, synchroniseView } from '../model/viewer';
import { useStageTiles } from '../model/use-stage-tiles';
import styles from './stage-pair-viewer.module.css';

type Side = 'left' | 'right';
type ViewData = Omit<ComparisonSheetPair, 'sheet_pair_id' | 'transition_id'>;
type Views = Readonly<Record<Side, ViewerState>>;

export interface StageViewerFocus {
  readonly token: number;
  readonly left?: ComparisonBox;
  readonly right?: ComparisonBox;
}

export interface StagePairViewerProps {
  readonly leftPage: StageSheetPassport | undefined;
  readonly rightPage: StageSheetPassport | undefined;
  readonly evidence: StageTextEvidenceData | undefined;
  readonly stale: boolean;
  readonly focus?: StageViewerFocus;
  readonly textProvider?: PageTextProvider;
}

function contextOf(geometry: ViewerGeometry | null, side: Side): ViewerContext {
  return { raster: geometry?.raster ?? { widthPx: 1, heightPx: 1 }, dpi: geometry?.dpi ?? 72,
    differences: [], canOverlay: false, hasA: side === 'left', hasB: side === 'right' };
}

function viewData(page: StageSheetPassport, profile: VersionPageProfile | undefined, side: Side): ViewData {
  const selected = { page: { page_number: page.page_number, version_uid: page.version_uid,
    page_profile_id: page.profile_id },
    ...(page.sheet_number === undefined ? {} : { sheet_number: page.sheet_number }),
    ...(profile?.stamp?.sheet_name === undefined ? {} : { title: profile.stamp.sheet_name }),
    ...(profile === undefined ? {} : { scan: !profile.has_text_layer }),
  };
  return { state: 'queued', ...(side === 'left' ? { page_a: selected } : { page_b: selected }) };
}

function PagePane({ side, page, profile, geometry, context, state, dispatch,
  evidence, stale, textProvider, focusedBox }: {
  readonly side: Side;
  readonly page: StageSheetPassport | undefined;
  readonly profile: VersionPageProfile | undefined;
  readonly geometry: ViewerGeometry | null;
  readonly context: ViewerContext;
  readonly state: ViewerState;
  readonly dispatch: (action: ViewerAction) => void;
  readonly evidence: StageTextEvidenceData | undefined;
  readonly stale: boolean;
  readonly textProvider: PageTextProvider | undefined;
  readonly focusedBox: ComparisonBox | undefined;
}) {
  const title = side === 'left' ? 'П' : 'Р';
  const stage = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number } | null>(null);
  const [query, setQuery] = useState('');
  const [position, setPosition] = useState(0);
  const text = useQuery({
    queryKey: ['stage-profile-text', page?.profile_id ?? 'none'],
    queryFn: ({ signal }) => textProvider!(page!.profile_id, signal),
    enabled: textProvider !== undefined && page !== undefined, retry: false,
  });
  const items = textProvider === undefined
    ? pageText(evidence?.fragments ?? [], page?.profile_id ?? '') : text.data ?? [];
  const matches = searchPageText(items, query);
  const textReady = textProvider === undefined ? evidence !== undefined : text.isSuccess;
  const selected = matches.length === 0 ? undefined : matches[position % matches.length];
  const masks = stale ? [] : provenFragments(evidence, page?.profile_id ?? '', side);
  const tiles = useStageTiles(page?.profile_id, geometry, state);
  useEffect(() => { setQuery(''); setPosition(0); }, [page?.profile_id]);
  useEffect(() => {
    const available = textProvider === undefined
      ? pageText(evidence?.fragments ?? [], page?.profile_id ?? '') : text.data ?? [];
    const first = searchPageText(available, query)[0];
    if (first !== undefined) dispatch({ type: 'focus-box', box: first.box });
  }, [query, page?.profile_id, evidence, text.data, textProvider, dispatch]);
  useEffect(() => {
    const node = stage.current;
    if (node === null || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      const bounds = node.getBoundingClientRect();
      if (bounds.width > 0 && bounds.height > 0) dispatch({ type: 'viewport', viewport: { width: bounds.width, height: bounds.height } });
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [dispatch, page?.profile_id]);
  const focusMatch = (direction: -1 | 1) => {
    if (matches.length === 0) return;
    const index = (position + direction + matches.length) % matches.length;
    setPosition(index);
    dispatch({ type: 'focus-box', box: matches[index]!.box });
  };
  const handlers: HTMLAttributes<HTMLDivElement> = {
    onPointerDown: (event) => {
      event.currentTarget.setPointerCapture(event.pointerId);
      drag.current = { x: event.clientX, y: event.clientY };
    },
    onPointerMove: (event) => {
      if (drag.current === null) return;
      dispatch({ type: 'pan', dx: event.clientX - drag.current.x, dy: event.clientY - drag.current.y });
      drag.current = { x: event.clientX, y: event.clientY };
    },
    onPointerUp: (event) => { drag.current = null; event.currentTarget.releasePointerCapture(event.pointerId); },
    onPointerCancel: () => { drag.current = null; },
    onDoubleClick: () => dispatch({ type: 'fit' }),
    onWheel: (event) => {
      if (!event.ctrlKey) return;
      event.preventDefault();
      dispatch({ type: 'zoom', factor: event.deltaY < 0 ? 1.15 : 1 / 1.15 });
    },
  };
  const decorations = [...masks.map((item) => ({ id: `mask:${item.id}`, label: item.text,
    side: side === 'left' ? 'a' as const : 'b' as const, box: item.box })),
  ...(focusedBox === undefined ? [] : [{ id: 'focus:raw', label: 'Исходное различие',
    side: side === 'left' ? 'a' as const : 'b' as const, box: focusedBox }]),
  ...(selected === undefined ? [] : [{ id: `search:${selected.id}`, label: selected.text,
    side: side === 'left' ? 'a' as const : 'b' as const, box: selected.box }])];
  const textFailure = text.error === null ? null : failureMessage(text.error);
  if (page === undefined) return <section className={styles.pane}><h3>Лист {title}</h3><p>Лист не выбран.</p></section>;
  const data = viewData(page, profile, side);
  const renderProps = {
    pair: data, geometry, context, state, tiles, dispatch, stageRef: stage, paneHandlers: handlers,
    evidence: { items: decorations, index: decorations.length - 1, all: true },
    showEvidencePanels: false,
  };
  return <section className={styles.pane} aria-label={`Просмотр листа ${title}`}>
    <h3>Лист {title} · стр. {page.page_number}{page.sheet_number === undefined ? '' : ` · л. ${page.sheet_number}`}</h3>
    <div className={styles.search}>
      <label>Найти текст на листе {title}
        <input value={query} disabled={!textReady} onChange={(event) => { setQuery(event.target.value); setPosition(0); }}
          onKeyDown={(event) => { if (event.key === 'Enter') focusMatch(event.shiftKey ? -1 : 1); }} />
      </label>
      <button type="button" className="am-button" disabled={matches.length === 0} aria-label={`Предыдущее совпадение на листе ${title}`} onClick={() => focusMatch(-1)}>↑</button>
      <button type="button" className="am-button" disabled={matches.length === 0} aria-label={`Следующее совпадение на листе ${title}`} onClick={() => focusMatch(1)}>↓</button>
      <span role="status">{!textReady || query.trim() === '' ? '' : matches.length === 0 ? 'Совпадений нет' : `${position % matches.length + 1} из ${matches.length}`}</span>
      <button type="button" className="am-button" onClick={() => dispatch({ type: 'zoom', factor: 1 / state.view.zoom })}>1:1</button>
    </div>
    {profile?.word_count === 0 ? <p>Нет текста.</p> : evidence === undefined && textProvider === undefined
      ? <p>Чтобы искать текст на листе, пересчитайте сравнение.</p> : null}
    {textProvider !== undefined && text.isPending ? <p role="status">Открываем текст листа…</p> : null}
    {textFailure === null ? null : <p role="alert">Текст листа не открылся. {textFailure.detail}</p>}
    {geometry === null ? <p role="status">{profile === undefined ? 'Открываем изображение листа…' : 'Изображение листа пока недоступно.'}</p> : <>
      {/* Root narrows the pure view's data prop at integration; no canonical ID is invented. */}
      {/* @ts-expect-error root-owned ComparisonViewerData/showEvidencePanels public seam */}
      <ComparisonViewerView {...renderProps} />
    </>}
  </section>;
}

export function StagePairViewer({ leftPage, rightPage, evidence, stale, focus, textProvider }: StagePairViewerProps) {
  const leftProfile = useQuery({ queryKey: ['stage-view-profile', leftPage?.profile_id ?? 'none'],
    queryFn: async () => (await getVersionPageProfile({ path: { comparison_page_profile_id: leftPage!.profile_id } })).data,
    enabled: leftPage !== undefined, retry: false });
  const rightProfile = useQuery({ queryKey: ['stage-view-profile', rightPage?.profile_id ?? 'none'],
    queryFn: async () => (await getVersionPageProfile({ path: { comparison_page_profile_id: rightPage!.profile_id } })).data,
    enabled: rightPage !== undefined, retry: false });
  const leftGeometry = useMemo(() => profileGeometry(leftProfile.data), [leftProfile.data]);
  const rightGeometry = useMemo(() => profileGeometry(rightProfile.data), [rightProfile.data]);
  const leftContext = useMemo(() => contextOf(leftGeometry, 'left'), [leftGeometry]);
  const rightContext = useMemo(() => contextOf(rightGeometry, 'right'), [rightGeometry]);
  const [sync, setSync] = useState(true);
  const [views, setViews] = useState<Views>(() => ({ left: initialState(leftContext), right: initialState(rightContext) }));
  useEffect(() => { setViews({ left: initialState(leftContext), right: initialState(rightContext) }); },
    [leftContext, rightContext, leftPage?.profile_id, rightPage?.profile_id]);
  const dispatch = useCallback((side: Side, action: ViewerAction) => {
    setViews((held) => {
      const context = side === 'left' ? leftContext : rightContext;
      const sourceGeometry = side === 'left' ? leftGeometry : rightGeometry;
      const targetGeometry = side === 'left' ? rightGeometry : leftGeometry;
      const other = side === 'left' ? 'right' : 'left';
      const source = reduce(held[side], action, context);
      const target = sync && sourceGeometry !== null && targetGeometry !== null
        && ['pan', 'zoom', 'fit', 'focus-box'].includes(action.type)
        ? synchroniseView(source, sourceGeometry, held[other], targetGeometry) : held[other];
      return { ...held, [side]: source, [other]: target };
    });
  }, [leftContext, rightContext, leftGeometry, rightGeometry, sync]);
  const dispatchLeft = useCallback((action: ViewerAction) => dispatch('left', action), [dispatch]);
  const dispatchRight = useCallback((action: ViewerAction) => dispatch('right', action), [dispatch]);
  useEffect(() => {
    if (focus === undefined) return;
    setViews((held) => ({
      left: focus.left === undefined ? held.left : reduce(held.left, { type: 'focus-box', box: focus.left }, leftContext),
      right: focus.right === undefined ? held.right : reduce(held.right, { type: 'focus-box', box: focus.right }, rightContext),
    }));
  }, [focus, leftContext, rightContext]);
  const failure = leftProfile.error ?? rightProfile.error;
  return <div>
    <label className={styles.sync}><input type="checkbox" checked={sync} onChange={(event) => setSync(event.target.checked)} />Синхронный вид</label>
    {failure === null ? null : <p role="alert">Изображение листа не открылось. {failureMessage(failure).detail}</p>}
    <div className={styles.panes}>
      <PagePane side="left" page={leftPage} profile={leftProfile.data} geometry={leftGeometry} context={leftContext}
        state={views.left} dispatch={dispatchLeft} evidence={evidence} stale={stale} textProvider={textProvider} focusedBox={focus?.left} />
      <PagePane side="right" page={rightPage} profile={rightProfile.data} geometry={rightGeometry} context={rightContext}
        state={views.right} dispatch={dispatchRight} evidence={evidence} stale={stale} textProvider={textProvider} focusedBox={focus?.right} />
    </div>
  </div>;
}
