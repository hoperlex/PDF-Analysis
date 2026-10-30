'use client';

import { useState } from 'react';

import type { DocumentUid, ProjectUid, StageChainRun, StagePair, StagePairSuggestion } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import {
  completenessLabel, suggestionReason, useConfirmStagePair, useSetStagePairCompleteness,
  useStagePairSuggestions, useStagePairs,
} from '@/entities/stage-pair';
import { StageBatchControls, StageRunControls } from '@/widgets/stage-run-controls';

import { StageAssemblyCreator, StageAssemblyEditor } from './stage-assembly-editor';
import styles from './stage-pair-catalog.module.css';

function DocumentLink({ projectUid, uid }: { readonly projectUid: ProjectUid; readonly uid: DocumentUid }) {
  return <a href={routes.document(projectUid, uid)}><code>{uid}</code></a>;
}

export interface StagePairCatalogProps {
  readonly projectUid: ProjectUid;
  readonly mayAct: boolean;
  readonly onRunChange?: (run: StageChainRun) => void;
  readonly onOpenRun?: (runId: string, pairId: string) => void;
}

/** A suggestion is displayed as a proposal; only the expert's button creates a pair. */
export function StagePairCatalog({ projectUid, mayAct, onRunChange, onOpenRun }: StagePairCatalogProps) {
  const [pairPages, setPairPages] = useState<string[]>([]);
  const [suggestionPages, setSuggestionPages] = useState<string[]>([]);
  const pairs = useStagePairs(projectUid, pairPages.at(-1));
  const suggestions = useStagePairSuggestions(projectUid, suggestionPages.at(-1));
  const confirm = useConfirmStagePair();
  const completeness = useSetStagePairCompleteness();
  const [selected, setSelected] = useState<StagePairSuggestion | null>(null);
  const [batchSelection, setBatchSelection] = useState<Record<string, StagePair>>({});
  const [batchId, setBatchId] = useState<string | undefined>();

  const pairFailure = pairs.error === null ? null : failureMessage(pairs.error);
  const suggestionFailure = suggestions.error === null ? null : failureMessage(suggestions.error);
  const commandError = confirm.error ?? completeness.error;
  const commandFailure = commandError === null ? null : failureMessage(commandError);
  const busy = confirm.isPending || completeness.isPending;

  return (
    <div className={styles.catalog}>
      <section aria-labelledby="stage-pair-heading">
        <div className={styles.heading}>
          <h2 id="stage-pair-heading">Пары стадий</h2>
          <button type="button" className="am-button" onClick={() => void pairs.refetch()}>Обновить</button>
        </div>
        {pairs.isPending ? <LoadingState what="пары стадий" /> : null}
        {pairFailure === null ? null : <ErrorState title="Пары стадий не открылись" detail={pairFailure.detail} correlationId={pairFailure.correlationId} onRetry={pairFailure.retryable ? () => void pairs.refetch() : undefined} />}
        {pairs.data?.items.length === 0 ? <EmptyState title="Подтверждённых пар пока нет" detail="Пары появятся после решения эксперта по документам П и Р." /> : null}
        {pairs.data?.items.map((pair: StagePair) => (
          <article className={styles.row} key={pair.pair_id}>
            {mayAct && pair.state === 'confirmed' ? <label><input type="checkbox" checked={batchSelection[pair.pair_id] !== undefined}
              onChange={(event) => setBatchSelection((prior) => {
                const next = { ...prior };
                if (event.target.checked) next[pair.pair_id] = pair; else delete next[pair.pair_id];
                return next;
              })} />Выбрать для очереди</label> : null}
            <div className={styles.documents}>
              <span>П: <DocumentLink projectUid={projectUid} uid={pair.left_document_uid} /></span>
              <span>Р: {pair.right_document_uid === undefined ? <code>{pair.assembly_id}</code> : <DocumentLink projectUid={projectUid} uid={pair.right_document_uid} />}</span>
            </div>
            <span>{completenessLabel(pair.completeness)}</span>
            {mayAct && pair.state === 'confirmed' ? (
              <div className={styles.actions}>
                <button type="button" className="am-button" disabled={busy || pair.completeness === 'full'} onClick={() => completeness.mutate({ pair, completeness: 'full' })}>Полный</button>
                <button type="button" className="am-button" disabled={busy || pair.completeness === 'partial'} onClick={() => completeness.mutate({ pair, completeness: 'partial' })}>Неполный</button>
              </div>
            ) : null}
            <StageAssemblyEditor key={pair.assembly_id} pair={pair} mayAct={mayAct && pair.state === 'confirmed'} />
            <StageRunControls pairId={pair.pair_id} mayAct={mayAct && pair.state === 'confirmed'} compact onOpenBatch={setBatchId} {...(onRunChange === undefined ? {} : { onRunChange })} />
          </article>
        ))}
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
              <span>П: <DocumentLink projectUid={projectUid} uid={hint.left_document_uid} /></span>
              <span>Р: <DocumentLink projectUid={projectUid} uid={hint.right_document_uid} /></span>
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
          <p>П: <DocumentLink projectUid={projectUid} uid={selected.left_document_uid} /> · Р: <DocumentLink projectUid={projectUid} uid={selected.right_document_uid} /></p>
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
