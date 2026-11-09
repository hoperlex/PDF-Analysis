'use client';

/**
 * The cards a reader chose to start together (`R-151c`), shared by the project page and the section page.
 *
 * Only a version confirmed for a section can be run, and a version admitted for comparison only cannot
 * ({@link startable}); the selection holds nothing else. The boxes are drawn only for a session that may act as an
 * expert, and not while a batch panel is open (its entries are fixed for its life). «Выбрать все» chooses the
 * startable cards of the page in front of the reader; the batch is the chosen cards as they stood when the panel
 * opened.
 */

import { useState } from 'react';

import type { DocumentVersion, VersionUid } from '@/shared/api';
import { documentCardTitle, isComparisonOnly } from '@/entities/document-version';
import type { BatchEntry } from '@/features/start-run';

export interface CardSelection {
  readonly selected: ReadonlySet<string>;
  readonly onToggle: (version: DocumentVersion) => void;
}

export function startable(version: DocumentVersion): boolean {
  return version.classification !== undefined && !isComparisonOnly(version);
}

function entryOf(version: DocumentVersion): BatchEntry {
  return { versionUid: version.version_uid as VersionUid, title: documentCardTitle(version) };
}

export interface BatchSelection {
  /** The boxes' state for the cards, or `undefined` while no box is drawn. */
  readonly selection: CardSelection | undefined;
  readonly chosenCount: number;
  /** The batch the panel was opened with, or `null` while it is closed. */
  readonly batch: readonly BatchEntry[] | null;
  /** Choose every startable card of `versions` (replacing the choice), e.g. the whole page. */
  readonly choose: (versions: readonly DocumentVersion[]) => void;
  readonly clear: () => void;
  readonly openBatch: () => void;
  readonly closeBatch: () => void;
}

export function useBatchSelection(mayAct: boolean): BatchSelection {
  const [chosen, setChosen] = useState<ReadonlyMap<string, BatchEntry>>(new Map());
  const [batch, setBatch] = useState<readonly BatchEntry[] | null>(null);
  const selection: CardSelection | undefined = mayAct && batch === null ? {
    selected: new Set(chosen.keys()),
    onToggle: (version) => setChosen((map) => {
      const next = new Map(map);
      if (next.has(version.version_uid)) next.delete(version.version_uid);
      else next.set(version.version_uid, entryOf(version));
      return next;
    }),
  } : undefined;
  return {
    selection,
    chosenCount: chosen.size,
    batch,
    choose: (versions) => setChosen(new Map(versions.filter(startable).map((version) => [version.version_uid, entryOf(version)]))),
    clear: () => setChosen(new Map()),
    openBatch: () => setBatch([...chosen.values()]),
    closeBatch: () => {
      setBatch(null);
      setChosen(new Map());
    },
  };
}
