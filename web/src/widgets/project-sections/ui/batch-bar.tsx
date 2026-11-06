'use client';

/**
 * The row under a section's cards that starts the chosen documents together (`R-151c`) and the panel that opens from
 * it, as the original's bottom bar «Выбрано: N · Запустить все (N)». One consent per run stays on the server; this
 * draws the choice and the existing batch panel, nothing more.
 */

import type { ReactNode } from 'react';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { documentCardTitle } from '@/entities/document-version';
import { BatchStartPanel } from '@/features/start-run';

import type { BatchSelection, CardSelection } from '../model/use-batch-selection';
import { startable } from '../model/use-batch-selection';
import styles from './project-sections.module.css';

export interface BatchBarProps {
  readonly projectUid: ProjectUid;
  readonly selection: BatchSelection;
  /** The cards in front of the reader, for «Выбрать все» and «Выбрать не запускавшиеся». */
  readonly documents: readonly DocumentVersion[];
}

export function BatchBar({ projectUid, selection, documents }: BatchBarProps) {
  const choices = documents.filter(startable);
  const notRun = choices.filter((version) => version.audit?.state === 'not_run');
  return (
    <>
      {selection.selection === undefined || choices.length === 0 ? null : (
        <p className={styles.batchBar} data-batch-controls="" data-batch-selection={selection.chosenCount}>
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => selection.choose(choices)}>
            Выбрать все ({choices.length})
          </button>
          {notRun.length === 0 ? null : (
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => selection.choose(notRun)}>
              Выбрать не запускавшиеся ({notRun.length})
            </button>
          )}
          {selection.chosenCount === 0 ? null : (
            <>
              <button type="button" className="am-button am-button--small" onClick={selection.openBatch}>
                Запустить аудит ({selection.chosenCount})
              </button>
              <button type="button" className="am-button am-button--quiet am-button--small" onClick={selection.clear}>
                Снять выбор
              </button>
            </>
          )}
        </p>
      )}
      {selection.batch === null ? null : (
        <BatchStartPanel projectUid={projectUid} entries={selection.batch} onClose={selection.closeBatch} />
      )}
    </>
  );
}

/**
 * The selection box of one card, for the card grid's `select` slot: drawn only on a card that can be started
 * ({@link startable}) and only while the session may choose; `undefined` draws no box on any card.
 */
export function selectionSlot(selection: CardSelection | undefined): ((version: DocumentVersion) => ReactNode) | undefined {
  if (selection === undefined) return undefined;
  return (version) => startable(version) ? (
    <input
      type="checkbox"
      aria-label={`Выбрать «${documentCardTitle(version)}» для запуска аудита`}
      checked={selection.selected.has(version.version_uid)}
      onChange={() => selection.onToggle(version)}
    />
  ) : null;
}
