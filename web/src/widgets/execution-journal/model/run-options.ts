/**
 * What each step of the journal's run picker offers (`UI-B-40`).
 *
 * Pure: a page of one of the four existing list reads goes in, `{ value, label }` pairs come out.
 * The value is always the record's own identity (`project_uid`, `document_uid`, `version_uid`,
 * `run_id`); the label is only for reading. A version's ordinal, a document's title and a run's
 * time say which row is which, and none of them is sent anywhere.
 */

import type { DocumentVersion, Project, RunStatus } from '@/shared/api';
import { RUN_STATE_VALUES } from '@/shared/api';
import type { RunState } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { STATE_LABELS } from '@/shared/ui';

export interface PickerOption {
  readonly value: string;
  readonly label: string;
}

/** Said for a run whose state this client has no word for: the contract grew past it. */
export const UNRECOGNISED_RUN_STATE = 'состояние не распознано';

export function projectOptions(projects: readonly Project[]): readonly PickerOption[] {
  return projects.map((project) => ({ value: project.project_uid, label: project.name }));
}

/** One option per document; the item is the version the document currently points at. */
export function documentOptions(documents: readonly DocumentVersion[]): readonly PickerOption[] {
  return documents.map((document) => ({
    value: document.document_uid,
    label: document.display_title ?? document.source_filename ?? document.document_uid,
  }));
}

/** A document's versions in the order the server gave them (newest ordinal first). */
export function versionOptions(versions: readonly DocumentVersion[]): readonly PickerOption[] {
  return versions.map((version) => ({
    value: version.version_uid,
    label: `Версия ${version.version_ordinal} · ${formatInstant(version.published_at)} · страниц ${version.page_count}`,
  }));
}

export function runStateWord(state: RunState): string {
  return (RUN_STATE_VALUES as readonly string[]).includes(state) ? STATE_LABELS[state] : UNRECOGNISED_RUN_STATE;
}

/** A run is named by when it began, its state and, when the reading carries it, who started it. */
export function runOptions(runs: readonly RunStatus[]): readonly PickerOption[] {
  return runs.map((run) => {
    const startedBy = run.started_by_label?.trim();
    return {
      value: run.run_id,
      label: [
        formatInstant(run.created_at),
        runStateWord(run.state),
        ...(startedBy === undefined || startedBy === '' ? [] : [startedBy]),
      ].join(' · '),
    };
  });
}
