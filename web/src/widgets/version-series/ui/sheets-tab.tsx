'use client';

/**
 * Tab «Сравнение листов» for one document set (plan §1.1; `frontend/static/js/version-comparison.js:93-158`,
 * `:347-430`): the header with «· версий: N», «Применить сопоставления (N)», «Отменить правку» and «Порядок версий»;
 * the block «Сводка переходов»; the matrix «Лист \ версия» with its draft of manual edits; the history of the saved
 * edits and the ones that no longer apply; and, when a pair is opened, the viewer.
 *
 * {@link SheetsTabView} is the whole markup, driven by props, so every state can be rendered by the static harness;
 * {@link SheetsTab} reads the matrix, the series and the pairs, keeps the draft, and sends the commands. The viewer is
 * a slot: `widgets/comparison-viewer` is a sibling widget, so the page that composes both hands `renderViewer` in.
 */

import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';

import type {
  ComparisonMatrix,
  ComparisonMatrixCell,
  ComparisonMatrixEdit,
  ComparisonMatrixRow,
  ComparisonSeries,
  ComparisonSheetPair,
  ComparisonTransition,
  DocumentUid,
  ProjectUid,
} from '@/shared/api';
import { EmptyState, LoadingState } from '@/shared/ui';
import { useVersionList } from '@/entities/document-version';
import type { ComparisonFailure, Draft, DraftEdit, GestureResult, Sides } from '@/entities/version-series';
import {
  EMPTY_DRAFT,
  MODULE_OFF_DETAIL,
  MODULE_OFF_TITLE,
  addEdit,
  adjacentSides,
  answerClick,
  baseRevisionOf,
  columnNames,
  comparisonFailure,
  defaultSides,
  isStale,
  openablePairs,
  pairOfRow,
  rebase,
  removeAt,
  removeLast,
  requestOf,
  touchedPages,
  transitionOf,
  useAppendOrder,
  useApplyMatrixEdits,
  useComparisonEdits,
  useComparisonMatrix,
  useLatestOrder,
  useLatestSeries,
  usePageProfile,
  usePrepareMatrix,
  useSeriesAct,
  useSheetPair,
  useSheetPairs,
  useStartSeries,
  useUndoMatrixEdit,
  validSides,
} from '@/entities/version-series';

import { DraftPanel, EditHistory } from './draft-panel';
import { MatrixState } from './matrix-state';
import { FailureState } from './module-state';
import { SheetMatrix } from './sheet-matrix';
import { TransitionSummary } from './transition-summary';
import { VersionOrderDialog } from './version-order-dialog';
import type { OrderRow } from './version-order-dialog';
import styles from './version-series.module.css';

/** What the page that composes this tab hands in to draw the viewer of one pair. */
export interface ViewerSlotProps {
  readonly pair: ComparisonSheetPair;
  readonly rasterSize?: { readonly widthPx: number; readonly heightPx: number };
  readonly navigation: {
    readonly onPrevious?: () => void;
    readonly onNext?: () => void;
    readonly onClose?: () => void;
  };
}

export type RenderViewer = (props: ViewerSlotProps) => ReactNode;

export interface SheetsTabViewProps {
  readonly heading: string;
  readonly matrix: ComparisonMatrix;
  readonly edits: readonly ComparisonMatrixEdit[];
  readonly names: ReadonlyMap<string, string>;
  readonly titles: ReadonlyMap<string, string>;
  readonly series: ComparisonSeries | null;
  readonly seriesFailure: ComparisonFailure | null;
  readonly seriesBusy: boolean;
  readonly pairs: readonly ComparisonSheetPair[] | null;
  readonly openTransitionId: string | null;
  readonly sides: Sides;
  readonly onSide: (side: 'a' | 'b', versionUid: string) => void;
  readonly onlyChanged: boolean;
  readonly onOnlyChanged: (on: boolean) => void;
  readonly draft: Draft;
  readonly notice: string | null;
  readonly dropped: readonly DraftEdit[];
  readonly draftFailure: ComparisonFailure | null;
  readonly applying: boolean;
  readonly mayEdit: boolean;
  readonly prepareBusy: boolean;
  readonly orderDialog: ReactNode;
  readonly viewer: ReactNode;
  readonly clickNote: string | null;
  readonly onPrepare: () => void;
  readonly onApply: () => void;
  readonly onUndo: () => void;
  readonly onRemoveDraft: (index: number) => void;
  readonly onOpenOrder: () => void;
  readonly onGesture: (result: GestureResult) => void;
  readonly onSheet: (row: ComparisonMatrixRow, cell: ComparisonMatrixCell) => void;
  readonly onOpenPair: (pair: ComparisonSheetPair) => void;
  readonly onOpenTransition: (transition: ComparisonTransition) => void;
  readonly onSeriesAct: (act: 'pause' | 'resume' | 'cancel' | 'finish') => void;
  readonly onStartSeries: () => void;
}

export function SheetsTabView(props: SheetsTabViewProps) {
  const { matrix, draft, mayEdit, sides } = props;
  const columns = matrix.columns ?? [];
  const hasRows = (matrix.rows ?? []).length > 0;
  const savedUndoable = props.edits.some((edit) => edit.status === 'applied' && edit.kind !== 'undo');
  const touched = touchedPages(draft);
  const chooseTwo = columns.length >= 2 && !validSides(sides, columns);
  const notCompared = validSides(sides, columns) && !adjacentSides(sides, columns);
  return (
    <div className={styles.sheets} data-comparison-sheets="" data-matrix-state={matrix.state}>
      <header className={styles.setHeader}>
        <h2 className={styles.setTitle}>{props.heading}</h2>
        <span className={styles.muted}>· версий: {columns.length}</span>
        <span className={styles.setActions}>
          {mayEdit && draft.edits.length > 0 ? (
            <>
              <button type="button" className="am-button" disabled={props.applying} onClick={props.onApply}>
                {props.applying ? 'Применяем…' : `Применить сопоставления (${draft.edits.length})`}
              </button>
              <button type="button" className="am-button am-button--quiet" disabled={props.applying} onClick={props.onUndo}>
                Отменить правку
              </button>
            </>
          ) : mayEdit && savedUndoable ? (
            <button
              type="button"
              className="am-button am-button--quiet"
              disabled={props.applying}
              title="Отменить последнюю сохранённую ручную правку сопоставления."
              onClick={props.onUndo}
            >
              Отменить последнюю правку
            </button>
          ) : null}
          {mayEdit ? (
            <button
              type="button"
              className="am-button am-button--quiet"
              disabled={draft.edits.length > 0}
              title={draft.edits.length > 0 ? 'Сначала примените или отмените правки сопоставления.' : 'Изменить порядок, в котором сравниваются версии.'}
              onClick={props.onOpenOrder}
            >
              Порядок версий
            </button>
          ) : null}
        </span>
      </header>

      {props.orderDialog}

      <MatrixState matrix={matrix} mayPrepare={mayEdit} busy={props.prepareBusy} onPrepare={props.onPrepare} />

      <TransitionSummary
        series={props.series}
        names={props.names}
        openTransitionId={props.openTransitionId}
        mayAct={mayEdit}
        busy={props.seriesBusy}
        failure={props.seriesFailure}
        notCompared={notCompared}
        chooseTwo={chooseTwo}
        onOpen={props.onOpenTransition}
        onAct={props.onSeriesAct}
        onStart={props.onStartSeries}
      />

      <DraftPanel
        draft={draft}
        names={props.names}
        notice={props.notice}
        dropped={props.dropped}
        failure={props.draftFailure}
        busy={props.applying}
        onRemove={props.onRemoveDraft}
      />

      {props.clickNote === null ? null : (
        <p className="am-note" role="status" data-click-note="">
          {props.clickNote}
        </p>
      )}

      {hasRows ? (
        <SheetMatrix
          matrix={matrix}
          names={props.names}
          titles={props.titles}
          sides={sides}
          onSide={props.onSide}
          pairs={props.pairs}
          onlyChanged={props.onlyChanged}
          onOnlyChanged={props.onOnlyChanged}
          touched={touched}
          mayEdit={mayEdit}
          locked={props.applying}
          onGesture={props.onGesture}
          onSheet={props.onSheet}
          onOpenPair={props.onOpenPair}
        />
      ) : matrix.state === 'ready' ? (
        <EmptyState title="В сопоставлении нет листов." detail="В версиях комплекта нет страниц, которые можно сопоставить." />
      ) : null}

      <EditHistory edits={props.edits} orphanedIds={matrix.orphaned_edit_ids ?? []} names={props.names} />

      {props.viewer === null ? null : (
        <section className={styles.viewerHost} aria-label="Просмотр пары листов" data-pair-viewer="">
          {props.viewer}
        </section>
      )}
    </div>
  );
}

export interface SheetsTabProps {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  /** The «шифр» of the set (or its title), for the heading. */
  readonly heading: string;
  /** An expert on a module that is on: the controls that change anything are drawn. */
  readonly mayEdit: boolean;
  readonly renderViewer: RenderViewer;
}

function profileIdOf(pair: ComparisonSheetPair): string | null {
  return pair.page_a?.page.page_profile_id ?? pair.page_b?.page.page_profile_id ?? null;
}

/** The viewer of one opened pair: reads the pair (and the raster of an added or removed sheet) and hands them to the slot. */
export function PairViewerSlot({
  pairId,
  siblings,
  renderViewer,
  onOpen,
  onClose,
}: {
  readonly pairId: string;
  readonly siblings: readonly ComparisonSheetPair[];
  readonly renderViewer: RenderViewer;
  readonly onOpen: (pairId: string) => void;
  readonly onClose: () => void;
}) {
  const pair = useSheetPair(pairId);
  const profile = usePageProfile(pair.data !== undefined && pair.data.canvas === undefined ? profileIdOf(pair.data) : null);
  if (pair.isPending) return <LoadingState what="пару листов" />;
  if (pair.isError) return <FailureState error={pair.error} title="Пара листов не открылась" onRetry={() => void pair.refetch()} />;
  const list = openablePairs(siblings);
  const index = list.findIndex((item) => item.sheet_pair_id === pairId);
  const previous = index > 0 ? list[index - 1] : undefined;
  const next = index >= 0 ? list[index + 1] : undefined;
  const raster = profile.data;
  const rasterSize =
    raster?.raster_width_px !== undefined && raster.raster_height_px !== undefined
      ? { widthPx: raster.raster_width_px, heightPx: raster.raster_height_px }
      : undefined;
  return (
    <>
      {renderViewer({
        pair: pair.data,
        ...(rasterSize === undefined ? {} : { rasterSize }),
        navigation: {
          ...(previous === undefined ? {} : { onPrevious: () => onOpen(previous.sheet_pair_id) }),
          ...(next === undefined ? {} : { onNext: () => onOpen(next.sheet_pair_id) }),
          onClose,
        },
      })}
    </>
  );
}

export function SheetsTab({ projectUid, documentUid, heading, mayEdit, renderViewer }: SheetsTabProps) {
  const matrix = useComparisonMatrix(projectUid, documentUid);
  const edits = useComparisonEdits(projectUid, documentUid);
  const versions = useVersionList(documentUid);
  const latestSeries = useLatestSeries(projectUid, documentUid);
  const latestOrder = useLatestOrder(projectUid, documentUid);
  const prepare = usePrepareMatrix();
  const apply = useApplyMatrixEdits();
  const undo = useUndoMatrixEdit();
  const start = useStartSeries();
  const seriesAct = useSeriesAct();
  const append = useAppendOrder();

  const [chosen, setChosen] = useState<{ a?: string; b?: string }>({});
  const [onlyChanged, setOnlyChanged] = useState(false);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [notice, setNotice] = useState<string | null>(null);
  const [dropped, setDropped] = useState<readonly DraftEdit[]>([]);
  const [orderOpen, setOrderOpen] = useState(false);
  const [openPairId, setOpenPairId] = useState<string | null>(null);
  const [clickNote, setClickNote] = useState<string | null>(null);

  const matrixData = matrix.data;
  const columns = matrixData?.columns ?? [];
  const fallback = defaultSides(columns);
  const known = new Set(columns.map((column) => column.version_uid));
  const sides: Sides = {
    a: chosen.a !== undefined && known.has(chosen.a) ? chosen.a : fallback.a,
    b: chosen.b !== undefined && known.has(chosen.b) ? chosen.b : fallback.b,
  };
  const names = columnNames(columns);
  const files = new Map((versions.data?.items ?? []).map((item) => [item.version_uid, item] as const));
  const titles = new Map(
    columns.map((column) => {
      const version = files.get(column.version_uid);
      return [column.version_uid, version?.source_filename ?? (version === undefined ? '' : `Версия ${version.version_ordinal}`)] as const;
    }),
  );
  const series = latestSeries.data ?? null;
  const transition =
    sides.a !== null && sides.b !== null ? transitionOf(series?.transitions, sides.a, sides.b) : null;
  const pairs = useSheetPairs(transition?.transition_id ?? null);

  // The matrix moved under the draft: rebase it on the matrix just read, and say what could not follow.
  const revision = matrixData?.revision;
  useEffect(() => {
    if (matrixData === undefined || !isStale(draft, matrixData.revision)) return;
    const rebased = rebase(draft, matrixData);
    setDraft(rebased.draft);
    setDropped(rebased.dropped);
    setNotice('Сопоставление изменилось, пока вы правили. Черновик перенесён на новую версию сопоставления; проверьте его и примените снова.');
    // The revision is the only thing that moves a draft's base.
  }, [revision?.matrix_id, revision?.edit_no]);

  if (matrix.isPending) return <LoadingState what="сопоставление листов" />;
  if (matrix.isError) {
    return <FailureState error={matrix.error} title="Сопоставление листов не открылось" onRetry={() => void matrix.refetch()} />;
  }
  const data = matrix.data;
  const commandError = apply.error ?? undo.error ?? null;
  const draftFailure = commandError === null ? null : comparisonFailure(commandError);
  const seriesError = start.error ?? seriesAct.error ?? null;
  const seriesFailure = seriesError === null ? null : comparisonFailure(seriesError);

  const onGesture = (result: GestureResult): void => {
    if ('refusal' in result) {
      setNotice(result.refusal);
      return;
    }
    if (data.revision === undefined) {
      setNotice('Сопоставление ещё не собрано: править пока нечего.');
      return;
    }
    const next = addEdit(draft, data.revision, result.edit);
    if (next === null) {
      setNotice('В черновике уже 500 правок. Примените их и продолжайте.');
      return;
    }
    apply.reset();
    setDraft(next);
    setDropped([]);
    setNotice(null);
  };

  const onApply = (): void => {
    const request = requestOf(draft);
    if (request === null) return;
    undo.reset();
    apply.mutate(
      { projectUid, documentUid, request },
      {
        onSuccess: () => {
          setDraft(EMPTY_DRAFT);
          setDropped([]);
          setNotice('Правки применены.');
        },
      },
    );
  };

  const onUndo = (): void => {
    if (draft.edits.length > 0) {
      setDraft(removeLast(draft));
      return;
    }
    if (data.revision === undefined) return;
    apply.reset();
    undo.mutate({ projectUid, documentUid, baseRevision: data.revision }, { onSuccess: () => setNotice('Последняя правка отменена.') });
  };

  const onSheet = (row: ComparisonMatrixRow, cell: ComparisonMatrixCell): void => {
    const answer = answerClick({
      columns,
      sides,
      names,
      transitionExists: transition !== null,
      pair: pairs.data === undefined ? null : pairOfRow(row, sides, pairs.data),
      versionUid: cell.version_uid,
    });
    if ('open' in answer) {
      setClickNote(null);
      setOpenPairId(answer.open.sheet_pair_id);
    } else {
      setClickNote(answer.note);
    }
  };

  const orderRows: OrderRow[] = columns.map((column) => ({
    versionUid: column.version_uid,
    name: names.get(column.version_uid) ?? '№?',
    file: titles.get(column.version_uid) ?? '',
    pages: column.page_count,
  }));

  return (
    <SheetsTabView
      heading={heading}
      matrix={data}
      edits={edits.data?.items ?? []}
      names={names}
      titles={titles}
      series={series}
      seriesFailure={seriesFailure}
      seriesBusy={start.isPending || seriesAct.isPending}
      pairs={pairs.data ?? null}
      openTransitionId={transition?.transition_id ?? null}
      sides={sides}
      onSide={(side, versionUid) => {
        setChosen((held) => ({ ...held, [side]: versionUid }));
        setClickNote(null);
        setOpenPairId(null);
      }}
      onlyChanged={onlyChanged}
      onOnlyChanged={setOnlyChanged}
      draft={draft}
      notice={notice}
      dropped={dropped}
      draftFailure={draftFailure}
      applying={apply.isPending || undo.isPending}
      mayEdit={mayEdit}
      prepareBusy={prepare.isPending}
      orderDialog={
        orderOpen ? (
          <VersionOrderDialog
            heading={heading}
            source={latestOrder.data?.source}
            rows={orderRows}
            pending={append.isPending}
            failure={append.error === null ? null : comparisonFailure(append.error)}
            onSave={(order) =>
              append.mutate(
                { projectUid, documentUid, baseRevisionNo: baseRevisionOf(latestOrder.data), versionUids: order },
                { onSuccess: () => setOrderOpen(false) },
              )
            }
            onCancel={() => {
              append.reset();
              setOrderOpen(false);
            }}
          />
        ) : null
      }
      viewer={
        openPairId === null ? null : (
          <PairViewerSlot
            pairId={openPairId}
            siblings={pairs.data ?? []}
            renderViewer={renderViewer}
            onOpen={setOpenPairId}
            onClose={() => setOpenPairId(null)}
          />
        )
      }
      clickNote={clickNote}
      onPrepare={() => prepare.mutate({ projectUid, documentUid })}
      onApply={onApply}
      onUndo={onUndo}
      onRemoveDraft={(index) => setDraft(removeAt(draft, index))}
      onOpenOrder={() => setOrderOpen(true)}
      onGesture={onGesture}
      onSheet={onSheet}
      onOpenPair={(pair) => {
        setClickNote(null);
        setOpenPairId(pair.sheet_pair_id);
      }}
      onOpenTransition={(item) => {
        setChosen({ a: item.source_version_uid, b: item.target_version_uid });
        setClickNote(null);
        setOpenPairId(null);
      }}
      onSeriesAct={(act) => {
        start.reset();
        seriesAct.mutate({ projectUid, documentUid, act, ...(series === null ? {} : { seriesId: series.series_id }) });
      }}
      onStartSeries={() => {
        seriesAct.reset();
        start.mutate({ projectUid, documentUid, restart: false, baseOrderRevisionNo: baseRevisionOf(latestOrder.data) });
      }}
    />
  );
}

/** The sentence a screen says when the module is off, before it asks anything. */
export function ModuleOffState() {
  return (
    <div data-comparison-module="off">
      <EmptyState title={MODULE_OFF_TITLE} detail={MODULE_OFF_DETAIL} />
    </div>
  );
}
