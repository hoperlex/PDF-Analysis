'use client';

/**
 * The journal's run picker: «проект → документ → версия → прогон» (`UI-B-40`).
 *
 * The journal is read by `run_id`, an opaque identity nobody remembers. The original keeps its log
 * inside the project; here the path to a run is the one every other screen already walks, and each
 * step reads the list the screen for that level reads: `listProjects`, `listDocuments` of the project,
 * `listVersions` of the document, `listRuns` of the version. Nothing is added to the contract and the
 * journal still filters only by `run_id` (`listExecutionJournal`).
 *
 * Controlled. The page holds the three upper choices and the run in view; this component draws the
 * steps and says what changed. A choice clears the ones below it, because a document that is not the
 * project's is not a choice. The run in view is independent of them: it can come from the address or
 * from the pasted identity, and then the lower steps simply do not list it.
 *
 * Every list is the first page the existing hook reads. When the server says there is more, the step
 * says so instead of looking complete.
 */

import { useId } from 'react';

import { useDocumentList, useVersionList } from '@/entities/document-version';
import { useProjectList } from '@/entities/project';
import { useRunList } from '@/entities/audit-run';

import type { PickerOption } from '../model/run-options';
import { documentOptions, projectOptions, runOptions, versionOptions } from '../model/run-options';
import styles from './run-picker.module.css';

/** The three upper choices; `null` is «not chosen yet». */
export interface RunPickerSelection {
  readonly projectUid: string | null;
  readonly documentUid: string | null;
  readonly versionUid: string | null;
}

export const EMPTY_PICKER_SELECTION: RunPickerSelection = { projectUid: null, documentUid: null, versionUid: null };

export interface RunPickerProps {
  readonly selection: RunPickerSelection;
  /** The run the journal is narrowed to; `null` while it shows every run. */
  readonly runId: string | null;
  readonly onSelection: (selection: RunPickerSelection) => void;
  /** A run was chosen, or `null` for «Все прогоны». */
  readonly onChooseRun: (runId: string | null) => void;
}

type StepStatus = 'idle' | 'loading' | 'failed' | 'ready';
type StepName = 'project' | 'document' | 'version' | 'run';

interface StepSelectProps {
  readonly label: string;
  /** The first option: what an empty choice is called when the step is open. */
  readonly placeholder: string;
  /** Said when the step opened and has nothing to offer. */
  readonly nothing: string;
  /** Said when the list could not be read. */
  readonly failure: string;
  readonly status: Exclude<StepStatus, 'idle'>;
  readonly options: readonly PickerOption[];
  readonly truncated: boolean;
  readonly value: string;
  /** `data-journal-step` on the field, so a test finds the step among its neighbours. */
  readonly step: StepName;
  readonly onChange: (value: string) => void;
  readonly onRetry?: (() => void) | undefined;
}

/** A step whose parent has not been chosen: a disabled select that says what it waits for. */
function IdleStep({ step, label, waiting }: { readonly step: StepName; readonly label: string; readonly waiting: string }) {
  const id = useId();
  return (
    <div className={styles.step} data-journal-step={step} data-journal-step-status="idle">
      <label htmlFor={id}>{label}</label>
      <select id={id} value="" disabled>
        <option value="">{waiting}</option>
      </select>
    </div>
  );
}

function StepSelect({
  label, placeholder, nothing, failure, status, options, truncated, value, step, onChange, onRetry,
}: StepSelectProps) {
  const id = useId();
  const open = status === 'ready' && options.length > 0;
  const closedWord = status === 'loading' ? 'Загрузка…' : status === 'ready' ? nothing : 'Список не прочитан';
  return (
    <div className={styles.step} data-journal-step={step} data-journal-step-status={status}>
      <label htmlFor={id}>{label}</label>
      <select id={id} value={open ? value : ''} disabled={!open} onChange={(event) => onChange(event.target.value)}>
        <option value="">{open ? placeholder : closedWord}</option>
        {open ? options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>) : null}
      </select>
      {status === 'failed' ? (
        <p className="am-form__problem" role="alert" data-journal-step-failure={step}>
          {failure}
          {onRetry === undefined ? null : (
            <>
              {' '}
              <button type="button" className="am-button am-button--quiet am-button--small" onClick={onRetry}>Повторить</button>
            </>
          )}
        </p>
      ) : null}
      {open && truncated ? (
        <p className="am-form__hint" data-journal-step-truncated={step}>
          Показана первая страница списка. Остальное найдите по идентификатору прогона ниже.
        </p>
      ) : null}
    </div>
  );
}

interface ListRead<T> {
  readonly data: { readonly items: readonly T[]; readonly page: { readonly next_cursor: string | null } } | undefined;
  readonly isError: boolean;
  readonly refetch: () => unknown;
}

function statusOf<T>(read: ListRead<T>): Exclude<StepStatus, 'idle'> {
  return read.data !== undefined ? 'ready' : read.isError ? 'failed' : 'loading';
}

/** The identity among the listed records that equals what the select reported; `null` for the placeholder. */
function chosen(options: readonly PickerOption[], value: string): string | null {
  return options.find((option) => option.value === value)?.value ?? null;
}

function ProjectStep({ selection, onSelection }: Pick<RunPickerProps, 'selection' | 'onSelection'>) {
  const read = useProjectList();
  const options = read.data === undefined ? [] : projectOptions(read.data.items);
  return (
    <StepSelect
      step="project"
      label="Проект"
      placeholder="Выберите проект"
      nothing="Проектов пока нет"
      failure="Не удалось прочитать список проектов."
      status={statusOf(read)}
      options={options}
      truncated={(read.data?.page.next_cursor ?? null) !== null}
      value={selection.projectUid ?? ''}
      onChange={(value) => onSelection({ projectUid: chosen(options, value), documentUid: null, versionUid: null })}
      onRetry={() => void read.refetch()}
    />
  );
}

function DocumentStep({ projectUid, selection, onSelection }: Pick<RunPickerProps, 'selection' | 'onSelection'> & { readonly projectUid: string }) {
  const read = useDocumentList(projectUid);
  const options = read.data === undefined ? [] : documentOptions(read.data.items);
  return (
    <StepSelect
      step="document"
      label="Документ"
      placeholder="Выберите документ"
      nothing="В проекте нет документов"
      failure="Не удалось прочитать список документов."
      status={statusOf(read)}
      options={options}
      truncated={(read.data?.page.next_cursor ?? null) !== null}
      value={selection.documentUid ?? ''}
      onChange={(value) => onSelection({ projectUid, documentUid: chosen(options, value), versionUid: null })}
      onRetry={() => void read.refetch()}
    />
  );
}

function VersionStep({ documentUid, selection, onSelection }: Pick<RunPickerProps, 'selection' | 'onSelection'> & { readonly documentUid: string }) {
  const read = useVersionList(documentUid);
  const options = read.data === undefined ? [] : versionOptions(read.data.items);
  return (
    <StepSelect
      step="version"
      label="Версия"
      placeholder="Выберите версию"
      nothing="У документа нет версий"
      failure="Не удалось прочитать список версий."
      status={statusOf(read)}
      options={options}
      truncated={(read.data?.page.next_cursor ?? null) !== null}
      value={selection.versionUid ?? ''}
      onChange={(value) => onSelection({ ...selection, versionUid: chosen(options, value) })}
      onRetry={() => void read.refetch()}
    />
  );
}

function RunStep({ versionUid, runId, onChooseRun }: Pick<RunPickerProps, 'runId' | 'onChooseRun'> & { readonly versionUid: string }) {
  const read = useRunList(versionUid);
  const options = read.data === undefined ? [] : runOptions(read.data.items);
  return (
    <StepSelect
      step="run"
      label="Прогон"
      placeholder="Все прогоны"
      nothing="У версии нет прогонов"
      failure="Не удалось прочитать список прогонов."
      status={statusOf(read)}
      options={options}
      truncated={(read.data?.page.next_cursor ?? null) !== null}
      value={runId ?? ''}
      onChange={(value) => onChooseRun(chosen(options, value))}
      onRetry={() => void read.refetch()}
    />
  );
}

export function RunPicker({ selection, runId, onSelection, onChooseRun }: RunPickerProps) {
  const { projectUid, documentUid, versionUid } = selection;
  return (
    <fieldset className={styles.picker} data-journal-picker>
      <legend className="am-form__hint">Выберите прогон по проекту, документу и версии</legend>
      <div className={styles.steps}>
        <ProjectStep selection={selection} onSelection={onSelection} />
        {projectUid === null
          ? <IdleStep step="document" label="Документ" waiting="Сначала выберите проект" />
          : <DocumentStep projectUid={projectUid} selection={selection} onSelection={onSelection} />}
        {documentUid === null
          ? <IdleStep step="version" label="Версия" waiting="Сначала выберите документ" />
          : <VersionStep documentUid={documentUid} selection={selection} onSelection={onSelection} />}
        {versionUid === null
          ? <IdleStep step="run" label="Прогон" waiting="Сначала выберите версию" />
          : <RunStep versionUid={versionUid} runId={runId} onChooseRun={onChooseRun} />}
      </div>
      <div className={`am-form__chosen ${styles.scope}`} data-journal-scope={runId === null ? 'all' : 'run'}>
        {runId === null ? (
          <span>Показаны события всех прогонов.</span>
        ) : (
          <>
            <span>Показан прогон <code>{runId}</code>.</span>
            <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => onChooseRun(null)}>
              Показать все прогоны
            </button>
          </>
        )}
      </div>
    </fieldset>
  );
}
