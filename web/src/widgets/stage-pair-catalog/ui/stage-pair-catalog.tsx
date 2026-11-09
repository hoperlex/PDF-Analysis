'use client';

import { useCallback, useState } from 'react';

import type { DocumentUid, ProjectUid, StageChainRun, StagePair, StagePairSuggestion } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState, Table } from '@/shared/ui';
import type { TableColumn } from '@/shared/ui';
import {
  completenessLabel, documentCaption, suggestionReason, useConfirmStagePair, useSetStagePairCompleteness,
  useStageDocumentNames, useStagePairSuggestions, useStagePairs,
} from '@/entities/stage-pair';
import type { StageDocumentNames } from '@/entities/stage-pair';
import { RUN_WORDS, StageBatchControls, StageRunControls, useLatestPairRun } from '@/widgets/stage-run-controls';

import { withRowVisibility } from '../model/rows-in-view';
import { RowInView } from './row-in-view';
import { StageAssemblyCreator, StageAssemblyEditor } from './stage-assembly-editor';
import styles from './stage-pair-catalog.module.css';

/** A document by its title and section (`UI-B-85`); by its identifier only while the names are not read. */
function DocumentLink({ projectUid, uid, names }: { readonly projectUid: ProjectUid; readonly uid: DocumentUid; readonly names: StageDocumentNames | undefined }) {
  const caption = documentCaption(names, uid);
  return <a href={routes.document(projectUid, uid)} title={uid}>{caption === uid ? <code>{uid}</code> : caption}</a>;
}

type RunCell = 'method' | 'date' | 'changes' | 'review' | 'status';

/**
 * One cell of a pair's row that comes from its latest full run; the rows share the run reads with the controls under them.
 * A row reads its run only while it is in view (`inView`), so the catalog does not walk the runs of every pair it lists.
 */
function PairRunCell({ pairId, cell, inView }: { readonly pairId: string; readonly cell: RunCell; readonly inView: boolean }) {
  const { run, counts, runs } = useLatestPairRun(pairId, inView);
  if (runs.isPending) return <>…</>;
  if (run === undefined) {
    if (cell === 'status') return <span>Не запускалось</span>;
    return <>—</>;
  }
  switch (cell) {
    case 'method':
      return <>{run.engine === 'v3_native_text_experimental' ? 'V3 · эксперимент' : 'Цепочка'}{run.with_ai === false ? ' · без ИИ' : run.with_ai === true ? ' · с ИИ' : ''}</>;
    case 'date': return <>{formatInstant(run.created_at)}</>;
    case 'changes': return <>{counts.data?.project_changes ?? '—'}</>;
    case 'review': return <>{counts.data?.review ?? '—'}</>;
    case 'status':
      return <span>{RUN_WORDS[run.state]}{run.stale ? ' · устарел' : ''}</span>;
  }
}

export interface StagePairCatalogProps {
  readonly projectUid: ProjectUid;
  readonly mayAct: boolean;
  readonly onRunChange?: (run: StageChainRun) => void;
  readonly onOpenRun?: (runId: string, pairId: string) => void;
}

/** What a row can open: the result of its latest run (`onRunChange` selects it and shows the changes). */
function OpenButton({ pairId, inView, onRunChange }: { readonly pairId: string; readonly inView: boolean; readonly onRunChange: ((run: StageChainRun) => void) | undefined }) {
  const { run } = useLatestPairRun(pairId, inView);
  if (run === undefined || onRunChange === undefined) return null;
  return <button type="button" className="am-button" data-pair-open={pairId} onClick={() => onRunChange(run)}>Открыть</button>;
}

/** The row's way into the expert's tools: «Запустить сравнение» for a pair that has no run yet (the original's button), «Управление» after it. */
function ManageButton({ pairId, inView, open, onToggle }: { readonly pairId: string; readonly inView: boolean; readonly open: boolean; readonly onToggle: () => void }) {
  const { run } = useLatestPairRun(pairId, inView);
  return <button type="button" className="am-button am-button--quiet" aria-expanded={open} data-pair-manage={pairId} onClick={onToggle}>
    {run === undefined ? 'Запустить сравнение' : 'Управление'}
  </button>;
}

/**
 * The catalog of the project's stage pairs (`UI-B-85`, plan §1.2 tab 1): one table as the original's «Проект / раздел, Метод и
 * модель, Дата, Изменения, Требуют проверки, Статус, Открыть», with the documents by their titles. What an expert does with a
 * pair — the completeness of the set, the assembly's members, the start of a run — is the panel «Управление парой» under the table,
 * opened by the row's button (the original's row menu «⋯»); with one pair it is open from the start. A suggestion is displayed as
 * a proposal; only the expert's button creates a pair.
 */
export function StagePairCatalog({ projectUid, mayAct, onRunChange, onOpenRun }: StagePairCatalogProps) {
  const [pairPages, setPairPages] = useState<string[]>([]);
  const [suggestionPages, setSuggestionPages] = useState<string[]>([]);
  const pairs = useStagePairs(projectUid, pairPages.at(-1));
  const suggestions = useStagePairSuggestions(projectUid, suggestionPages.at(-1));
  const documents = useStageDocumentNames(projectUid);
  const names = documents.data;
  const confirm = useConfirmStagePair();
  const completeness = useSetStagePairCompleteness();
  const [selected, setSelected] = useState<StagePairSuggestion | null>(null);
  const [batchSelection, setBatchSelection] = useState<Record<string, StagePair>>({});
  const [batchId, setBatchId] = useState<string | undefined>();
  // `undefined`: not chosen yet (a single pair opens by itself); `null`: the reader closed the panel.
  const [managed, setManaged] = useState<string | null | undefined>(undefined);
  // The rows on the screen: only they read and poll their run (`useLatestPairRun`); the open pair is polled by its controls.
  const [rowsInView, setRowsInView] = useState<ReadonlySet<string>>(() => new Set());
  const setRowInView = useCallback((pairId: string, visible: boolean) => setRowsInView((prior) => withRowVisibility(prior, pairId, visible)), []);

  const pairFailure = pairs.error === null ? null : failureMessage(pairs.error);
  const suggestionFailure = suggestions.error === null ? null : failureMessage(suggestions.error);
  const commandError = confirm.error ?? completeness.error;
  const commandFailure = commandError === null ? null : failureMessage(commandError);
  const busy = confirm.isPending || completeness.isPending;
  const items = pairs.data?.items ?? [];
  const managedId = managed === undefined ? (items.length === 1 ? items[0]!.pair_id : null) : managed;
  const managedPair = items.find((pair) => pair.pair_id === managedId);
  const selectable = items.filter((pair) => pair.state === 'confirmed');
  const nameOfPair = (pair: StagePair): string => `${documentCaption(names, pair.left_document_uid)} → ${pair.right_document_uid === undefined ? 'сборка Р' : documentCaption(names, pair.right_document_uid)}`;

  const columns: TableColumn<StagePair>[] = [
    ...(mayAct ? [{
      key: 'select', header: 'В очередь',
      cell: (pair: StagePair) => pair.state === 'confirmed'
        ? <input type="checkbox" aria-label={`Выбрать для очереди: ${nameOfPair(pair)}`} checked={batchSelection[pair.pair_id] !== undefined}
            onChange={(event) => setBatchSelection((prior) => {
              const next = { ...prior };
              if (event.target.checked) next[pair.pair_id] = pair; else delete next[pair.pair_id];
              return next;
            })} />
        : null,
    }] : []),
    {
      key: 'pair', header: 'Проект / раздел',
      cell: (pair) => <RowInView pairId={pair.pair_id} onVisibility={setRowInView} className={styles.documents}>
        <span>П: <DocumentLink projectUid={projectUid} uid={pair.left_document_uid} names={names} /></span>
        <span>Р: {pair.right_document_uid === undefined
          ? <span title={pair.assembly_id}>сборка документов</span>
          : <DocumentLink projectUid={projectUid} uid={pair.right_document_uid} names={names} />}</span>
      </RowInView>,
    },
    { key: 'method', header: 'Метод и модель', cell: (pair) => <PairRunCell pairId={pair.pair_id} inView={rowsInView.has(pair.pair_id)} cell="method" /> },
    { key: 'date', header: 'Дата', cell: (pair) => <PairRunCell pairId={pair.pair_id} inView={rowsInView.has(pair.pair_id)} cell="date" /> },
    { key: 'changes', header: 'Изменения', cell: (pair) => <PairRunCell pairId={pair.pair_id} inView={rowsInView.has(pair.pair_id)} cell="changes" /> },
    { key: 'review', header: 'Требуют проверки', cell: (pair) => <PairRunCell pairId={pair.pair_id} inView={rowsInView.has(pair.pair_id)} cell="review" /> },
    {
      key: 'status', header: 'Статус',
      cell: (pair) => <div className={styles.documents}>
        <PairRunCell pairId={pair.pair_id} inView={rowsInView.has(pair.pair_id)} cell="status" />
        <span>{completenessLabel(pair.completeness)}</span>
      </div>,
    },
    {
      key: 'actions', header: 'Действия',
      cell: (pair) => <div className={styles.actions}>
        <OpenButton pairId={pair.pair_id} inView={rowsInView.has(pair.pair_id)} onRunChange={onRunChange} />
        {mayAct && pair.state === 'confirmed'
          ? <ManageButton pairId={pair.pair_id} inView={rowsInView.has(pair.pair_id)} open={managedId === pair.pair_id} onToggle={() => setManaged(managedId === pair.pair_id ? null : pair.pair_id)} /> : null}
      </div>,
    },
  ];

  return (
    <div className={styles.catalog}>
      <section aria-labelledby="stage-pair-heading">
        <div className={styles.heading}>
          <h2 id="stage-pair-heading">Пары стадий</h2>
          <div className={styles.actions}>
            {mayAct && selectable.length > 0 ? <>
              <button type="button" className="am-button am-button--quiet" onClick={() => setBatchSelection(Object.fromEntries(selectable.map((pair) => [pair.pair_id, pair])))}>Выбрать все</button>
              <button type="button" className="am-button am-button--quiet" disabled={Object.keys(batchSelection).length === 0} onClick={() => setBatchSelection({})}>Снять выбор</button>
            </> : null}
            <button type="button" className="am-button" onClick={() => void pairs.refetch()}>Обновить</button>
          </div>
        </div>
        {pairs.data === undefined || suggestions.data === undefined ? null : (
          <p data-pair-counters="">
            Сопоставлено: {selectable.length}{pairs.data.page.next_cursor === null ? '' : ' на этой странице'} · Возможных пар: {suggestions.data.items.length}{suggestions.data.page.next_cursor === null ? '' : ' на этой странице'}
          </p>
        )}
        {pairs.isPending ? <LoadingState what="пары стадий" /> : null}
        {pairFailure === null ? null : <ErrorState title="Пары стадий не открылись" detail={pairFailure.detail} correlationId={pairFailure.correlationId} onRetry={pairFailure.retryable ? () => void pairs.refetch() : undefined} />}
        {pairs.data?.items.length === 0 ? <EmptyState title="Подтверждённых пар пока нет" detail="Пары появятся после решения эксперта по документам П и Р." /> : null}
        {items.length === 0 ? null : <Table columns={columns} rows={items} rowKey={(pair) => pair.pair_id} currentKey={managedId} />}
        {pairs.data === undefined ? null : (
          <nav className={styles.actions} aria-label="Страницы пар стадий">
            <button type="button" className="am-button" disabled={pairPages.length === 0} onClick={() => setPairPages((pages) => pages.slice(0, -1))}>Назад</button>
            <button type="button" className="am-button" disabled={pairs.data.page.next_cursor === null} onClick={() => {
              const next = pairs.data?.page.next_cursor;
              if (next !== null && next !== undefined) setPairPages((pages) => [...pages, next]);
            }}>Далее</button>
          </nav>
        )}
      </section>

      {managedPair === undefined || !mayAct ? null : (
        <section className={styles.decision} aria-labelledby="stage-pair-manage-heading" data-pair-panel={managedPair.pair_id}>
          <div className={styles.heading}>
            <h3 id="stage-pair-manage-heading">Управление парой: {nameOfPair(managedPair)}</h3>
            <button type="button" className="am-button am-button--quiet" onClick={() => setManaged(null)}>Закрыть</button>
          </div>
          {managedPair.state === 'confirmed' ? (
            <div className={styles.actions}>
              <span>{completenessLabel(managedPair.completeness)}</span>
              <button type="button" className="am-button" disabled={busy || managedPair.completeness === 'full'} onClick={() => completeness.mutate({ pair: managedPair, completeness: 'full' })}>Полный</button>
              <button type="button" className="am-button" disabled={busy || managedPair.completeness === 'partial'} onClick={() => completeness.mutate({ pair: managedPair, completeness: 'partial' })}>Неполный</button>
            </div>
          ) : null}
          <StageAssemblyEditor key={managedPair.assembly_id} pair={managedPair} mayAct={managedPair.state === 'confirmed'} />
          <StageRunControls key={managedPair.pair_id} pairId={managedPair.pair_id} mayAct={managedPair.state === 'confirmed'} launcher onOpenBatch={setBatchId} {...(onRunChange === undefined ? {} : { onRunChange })} />
        </section>
      )}

      <StageBatchControls projectUid={projectUid} selectedPairs={Object.values(batchSelection)} mayAct={mayAct} onBatchChange={setBatchId}
        {...(batchId === undefined ? {} : { batchId })} {...(onOpenRun === undefined ? {} : { onOpenRun })} />
      <StageAssemblyCreator projectUid={projectUid} mayAct={mayAct} />

      <section aria-labelledby="stage-suggestions-heading">
        <h2 id="stage-suggestions-heading">Возможные пары</h2>
        <p>Совпадение шифра или названия только подсказывает выбор. Документы связывает эксперт.</p>
        {suggestions.isPending ? <LoadingState what="возможные пары" /> : null}
        {suggestionFailure === null ? null : <ErrorState title="Предложения не открылись" detail={suggestionFailure.detail} correlationId={suggestionFailure.correlationId} onRetry={suggestionFailure.retryable ? () => void suggestions.refetch() : undefined} />}
        {suggestions.data?.items.length === 0 ? <EmptyState title="Подходящих предложений пока нет" /> : null}
        {suggestions.data?.items.map((hint: StagePairSuggestion) => (
          <article className={styles.row} key={`${hint.left_document_uid}|${hint.right_document_uid}`}>
            <div className={styles.documents}>
              <span>П: <DocumentLink projectUid={projectUid} uid={hint.left_document_uid} names={names} /></span>
              <span>Р: <DocumentLink projectUid={projectUid} uid={hint.right_document_uid} names={names} /></span>
            </div>
            <span>{suggestionReason(hint.reason)}</span>
            {mayAct ? <button type="button" className="am-button" disabled={busy} onClick={() => setSelected(hint)}>Проверить связь</button> : null}
          </article>
        ))}
        {suggestions.data === undefined ? null : (
          <nav className={styles.actions} aria-label="Страницы возможных пар">
            <button type="button" className="am-button" disabled={suggestionPages.length === 0} onClick={() => setSuggestionPages((pages) => pages.slice(0, -1))}>Назад</button>
            <button type="button" className="am-button" disabled={suggestions.data.page.next_cursor === null} onClick={() => {
              const next = suggestions.data?.page.next_cursor;
              if (next !== null && next !== undefined) setSuggestionPages((pages) => [...pages, next]);
            }}>Далее</button>
          </nav>
        )}
      </section>

      {selected === null ? null : (
        <section className={styles.decision} aria-labelledby="stage-confirm-heading">
          <h3 id="stage-confirm-heading">Подтвердить связь документов?</h3>
          <p>П: <DocumentLink projectUid={projectUid} uid={selected.left_document_uid} names={names} /> · Р: <DocumentLink projectUid={projectUid} uid={selected.right_document_uid} names={names} /></p>
          <p>Подтверждение создаст пару. Предложение само ничего не связывает.</p>
          <div className={styles.actions}>
            <button type="button" className="am-button" disabled={busy} onClick={() => {
              confirm.mutate({ projectUid, leftDocumentUid: selected.left_document_uid, rightDocumentUid: selected.right_document_uid }, { onSuccess: () => setSelected(null) });
            }}>Подтвердить пару</button>
            <button type="button" className="am-button" disabled={busy} onClick={() => setSelected(null)}>Отмена</button>
          </div>
        </section>
      )}
      {commandFailure === null ? null : <ErrorState title="Решение не сохранено" detail={commandFailure.detail} correlationId={commandFailure.correlationId} />}
    </div>
  );
}
