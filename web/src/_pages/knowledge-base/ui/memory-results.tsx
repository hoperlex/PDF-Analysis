'use client';

/**
 * The body of «Память решений» (`D-495`): the administrator's status line, then the list of cases with its pager, or -- once a
 * case is opened -- the case. Composition only: the reads and the address are `useMemoryTab`'s, the drawing is the widget's.
 */

import type { ReactNode } from 'react';

import type { MemoryAccess } from '@/entities/decision-memory';
import { memoryFiltersNarrow } from '@/entities/decision-memory';
import { DecisionMemoryCaseView, DecisionMemoryList, DecisionMemoryStatusLine } from '@/widgets/decision-memory';

import { memoryFailure } from '../model/memory-failure';
import type { MemoryTab } from '../model/use-memory-tab';
import styles from './knowledge-base-page.module.css';

export interface MemoryResultsProps {
  readonly memory: MemoryTab;
  readonly access: MemoryAccess;
  /** The project the list is read over, as the screen states it: «Все проекты» or the project's name. */
  readonly scope: ReactNode;
  readonly narrowedByProject: boolean;
}

export function MemoryResults({ memory, access, scope, narrowedByProject }: MemoryResultsProps) {
  const { list, detail, status, cursors, setCursors, caseId } = memory;
  const next = list.data?.page.next_cursor ?? null;
  return (
    <div className={styles.results} data-memory-results="">
      {access.manage ? (
        <DecisionMemoryStatusLine
          status={status.data}
          error={status.error === null ? null : memoryFailure(status.error, () => void status.refetch(), 'Сводка памяти не получена')}
        />
      ) : null}
      {caseId !== null ? (
        <DecisionMemoryCaseView
          data={detail.data}
          isLoading={detail.isPending}
          error={detail.error === null ? null : memoryFailure(detail.error, () => void detail.refetch(), 'Дело не открылось')}
          manage={access.manage}
          onBack={memory.closeCase}
        />
      ) : (
        <>
          <p className={styles.scope} data-memory-scope={narrowedByProject ? 'project' : 'all'}>
            <span className={styles.scopeKey}>Охват</span>
            <strong className={styles.scopeValue}>{scope}</strong>
          </p>
          <DecisionMemoryList
            cases={list.data?.items ?? []}
            isLoading={list.isPending}
            error={list.error === null ? null : memoryFailure(list.error, () => void list.refetch(), 'Память решений не открылась')}
            narrowed={narrowedByProject || memoryFiltersNarrow(memory.filters)}
            onOpen={memory.openCase}
            onResetFilters={memoryFiltersNarrow(memory.filters) ? memory.resetFilters : undefined}
          />
          {cursors.length === 0 && next === null ? null : (
            <nav className="am-pager" aria-label="Страницы дел памяти">
              <button
                type="button"
                className="am-button am-button--quiet"
                disabled={cursors.length === 0}
                onClick={() => setCursors(cursors.slice(0, -1))}
              >
                Назад
              </button>
              <button
                type="button"
                className="am-button am-button--quiet"
                disabled={next === null}
                onClick={() => {
                  if (next !== null) setCursors([...cursors, next]);
                }}
              >
                Далее
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
