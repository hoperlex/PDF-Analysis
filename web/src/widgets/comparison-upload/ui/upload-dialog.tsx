'use client';

/**
 * The upload dialogs of «Сравнение версий» (plan §1.1, `Q-CMP-5`): «Загрузка проекта и версий» for one project with its
 * proposal, and «Загрузка нескольких проектов» for a batch of projects (`frontend/static/js/version-comparison.js:435-502`,
 * `version-comparison-batch.js:58-126`).
 *
 * Both are one flow over the same operations — declare the files, send them in parts, let the server read them into a
 * proposal of sets, confirm each set — and differ in what they put in front of the reader. The single dialog asks one
 * question after the proposal: «Подтвердить группировку и порядок». The batch dialog is a monitor of a queue: each set has its
 * own status and its own «Подтвердить состав и порядок», «Исключить» and «Повторить», the transfer can be stopped and continued,
 * the server's processing can be paused after the project in hand, and «Подтвердить порядок во всех проектах» confirms what the
 * reader proposed for every set at once. «После подготовки сравнить все соседние версии» is the batch's flag
 * (`compare_after_preparation`).
 *
 * {@link UploadDialogView} is the whole markup, driven by props, so every state can be rendered by the static harness;
 * {@link UploadDialog} reads the flow and sends the commands. Only an expert sends anything; others see the state.
 */

import { useState } from 'react';
import type { ChangeEvent } from 'react';

import type { ComparisonProposalSet, ComparisonUpload, ProjectUid } from '@/shared/api';
import { EmptyState, LoadingState } from '@/shared/ui';
import type { ComparisonFailure } from '@/entities/version-series';
import {
  FILE_STATE_LABELS,
  UPLOAD_STATE_LABELS,
  comparisonFailure,
  uploadFailureReasonSentence,
  uploadIsActive,
} from '@/entities/version-series';
import { uploadConstraintSentence } from '@/entities/document-version';

import {
  useConfirmSet,
  useExcludeSet,
  useRetrySet,
  useUnfinishedUploads,
  useUploadAct,
} from '../api/use-upload';
import { awaitingConfirmation, confirmationOf, draftOf, proposedConfirmation } from '../model/confirm';
import { needsTransfer } from '../model/transfer';
import type { SetDraft } from '../model/confirm';
import type { Group, PrecheckProblem } from '../model/files';
import { PRECHECK_SENTENCES, formatMebibytes, groupsOf } from '../model/files';

import { SetEditor } from './set-editor';
import styles from './comparison-upload.module.css';
import type { FlowPhase, Progress, UploadFlow } from './use-upload-flow';
import { useUploadFlow } from './use-upload-flow';

export type UploadMode = 'single' | 'batch';

export const SINGLE_TITLE = 'Загрузка проекта и версий';
export const BATCH_TITLE = 'Загрузка нескольких проектов';
export const BATCH_SWITCH = 'Пакетная загрузка: каждая папка — отдельный проект со своими версиями.';
export const PICK_HINT =
  'Выберите папку с PDF (вложенные папки тоже читаются) или отдельные файлы. Исходные файлы не изменяются.';
export const PROPOSAL_NOTE = 'Номер в имени файла, «Изм.» и дата выпуска — подсказки; порядок версий задаёте вы.';
export const ZIP_NOTE = 'ZIP-комплекты пока не принимаются: загрузите PDF.';
export const REPICK_NOTE = 'Чтобы продолжить, выберите те же файлы ещё раз: по ним система узнает, какие части уже приняты.';

export interface UploadDialogViewProps {
  readonly mode: UploadMode;
  readonly phase: FlowPhase;
  readonly groups: readonly Group[];
  readonly skipped: number;
  readonly problem: PrecheckProblem | null;
  readonly compare: boolean;
  readonly hashing: Progress | null;
  readonly upload: ComparisonUpload | undefined;
  readonly loading: boolean;
  readonly sets: readonly ComparisonProposalSet[];
  readonly drafts: Readonly<Record<string, SetDraft>>;
  readonly fileNames: ReadonlyMap<string, string>;
  readonly progress: ReadonlyMap<string, Progress>;
  readonly fileFailures: ReadonlyMap<string, ComparisonFailure>;
  readonly missing: readonly string[];
  readonly failure: ComparisonFailure | null;
  readonly unfinished: readonly ComparisonUpload[];
  readonly notice: string | null;
  readonly mayAct: boolean;
  readonly busy: boolean;
  readonly onPick: (files: FileList, kind: 'one' | 'many' | 'files') => void;
  readonly onRemoveGroup: (group: string) => void;
  readonly onCompare: (on: boolean) => void;
  readonly onSend: () => void;
  readonly onStop: () => void;
  readonly onContinue: (files: FileList | null) => void;
  readonly onOpenUnfinished: (upload: ComparisonUpload) => void;
  readonly onDraft: (setId: string, draft: SetDraft) => void;
  readonly onConfirm: (set: ComparisonProposalSet) => void;
  readonly onConfirmAll: () => void;
  readonly onProposedAll: () => void;
  readonly onExclude: (set: ComparisonProposalSet) => void;
  readonly onRetry: (set: ComparisonProposalSet) => void;
  readonly onPause: () => void;
  readonly onResume: () => void;
  readonly onDelete: () => void;
  readonly onSwitch: () => void;
  readonly onClose: () => void;
}

function Picker({ mode, disabled, onPick }: { readonly mode: UploadMode; readonly disabled: boolean; readonly onPick: UploadDialogViewProps['onPick'] }) {
  const choose = (kind: 'one' | 'many' | 'files') => (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files !== null && event.target.files.length > 0) onPick(event.target.files, kind);
    event.target.value = '';
  };
  const folder = { webkitdirectory: '', directory: '' } as Record<string, string>;
  return (
    <div className={styles.pickers}>
      <label className={`am-button am-button--quiet ${styles.pick}`}>
        {mode === 'batch' ? 'Добавить папку' : 'Выбрать папку'}
        <input className={styles.hiddenInput} type="file" multiple disabled={disabled} {...folder} onChange={choose('one')} />
      </label>
      {mode === 'batch' ? (
        <label className={`am-button am-button--quiet ${styles.pick}`}>
          Добавить папку с проектами
          <input className={styles.hiddenInput} type="file" multiple disabled={disabled} {...folder} onChange={choose('many')} />
        </label>
      ) : (
        <label className={`am-button am-button--quiet ${styles.pick}`}>
          Выбрать файлы
          <input className={styles.hiddenInput} type="file" multiple accept=".pdf,application/pdf" disabled={disabled} onChange={choose('files')} />
        </label>
      )}
    </div>
  );
}

function FileRows({ upload, progress, fileFailures }: Pick<UploadDialogViewProps, 'progress' | 'fileFailures'> & { readonly upload: ComparisonUpload }) {
  const files = upload.files ?? [];
  if (files.length === 0) return null;
  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Файл</th>
            <th scope="col">Размер</th>
            <th scope="col">Состояние</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => {
            const sent = progress.get(file.file_id);
            const refused = fileFailures.get(file.file_id);
            const reason = uploadFailureReasonSentence(file.failure_reason, uploadConstraintSentence);
            return (
              <tr key={file.file_id} data-file-state={file.state}>
                <td className={styles.fileName}>{file.display_name}</td>
                <td>{formatMebibytes(file.size_bytes)}</td>
                <td>
                  <span className="am-badge am-badge--inert">{FILE_STATE_LABELS[file.state]}</span>
                  {file.state === 'uploading' && sent !== undefined && sent.total > 0 ? (
                    <progress className={styles.progress} value={Math.round((100 * sent.done) / sent.total)} max={100} aria-label="Передано" />
                  ) : null}
                  {reason === '' ? null : <span className={styles.errorText}>{reason}</span>}
                  {refused === undefined ? null : <span className={styles.errorText}>{refused.detail}</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function UploadDialogView(props: UploadDialogViewProps) {
  const { mode, phase, upload, sets, mayAct, busy } = props;
  const batch = mode === 'batch';
  const awaiting = awaitingConfirmation(sets);
  const title = batch ? BATCH_TITLE : SINGLE_TITLE;
  const picking = upload === undefined && phase === 'pick';
  return (
    <section className={styles.dialog} role="group" aria-label={title} data-upload-dialog={mode} data-upload-phase={phase}>
      <header className={styles.header}>
        <h2 className={styles.title}>{title}</h2>
        <button type="button" className="am-button am-button--small am-button--quiet" onClick={props.onClose}>
          Закрыть
        </button>
      </header>

      {!mayAct ? (
        <p className="am-note" data-upload-readonly="">
          Загружать файлы для сравнения может эксперт. Здесь показано состояние загрузок.
        </p>
      ) : null}

      {picking ? (
        <>
          <p>{PICK_HINT}</p>
          <p className="am-note">{ZIP_NOTE}</p>
          <Picker mode={mode} disabled={!mayAct} onPick={props.onPick} />
          {props.groups.length === 0 ? null : (
            <div className={styles.scroller}>
              <table className={styles.table} data-picked-groups={props.groups.length}>
                <thead>
                  <tr>
                    <th scope="col">{batch ? 'Проект (папка)' : 'Папка'}</th>
                    <th scope="col">Файлов</th>
                    <th scope="col">Размер</th>
                    <th scope="col">
                      <span className={styles.visuallyHidden}>Убрать</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {props.groups.map((group) => (
                    <tr key={group.group}>
                      <td className={styles.fileName}>{group.group === '' ? 'отдельные файлы' : group.group}</td>
                      <td>{group.files.length}</td>
                      <td>{formatMebibytes(group.bytes)}</td>
                      <td>
                        <button type="button" className="am-button am-button--small am-button--quiet" onClick={() => props.onRemoveGroup(group.group)}>
                          Убрать
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {props.groups.length > 0 ? (
            <p className="am-note" data-picked-total="">
              Выбрано файлов: {props.groups.reduce((sum, group) => sum + group.files.length, 0)} ·{' '}
              {formatMebibytes(props.groups.reduce((sum, group) => sum + group.bytes, 0))}
            </p>
          ) : null}
          {props.skipped > 0 ? <p className="am-note">Пропущено файлов не в формате PDF: {props.skipped}.</p> : null}
          {props.problem === null ? null : (
            <p className="am-decision__refusal" role="alert" data-precheck={props.problem}>
              {PRECHECK_SENTENCES[props.problem]}
            </p>
          )}
          {batch ? (
            <label className={styles.inline}>
              <input type="checkbox" checked={props.compare} disabled={!mayAct} onChange={(event) => props.onCompare(event.target.checked)} />{' '}
              После подготовки сравнить все соседние версии
            </label>
          ) : null}
          {props.unfinished.length === 0 ? null : (
            <div className={styles.unfinished} data-unfinished-uploads={props.unfinished.length}>
              <strong>Незавершённые загрузки</strong>
              <ul className={styles.list}>
                {props.unfinished.map((item) => (
                  <li key={item.upload_id} data-upload-state={item.state}>
                    {UPLOAD_STATE_LABELS[item.state]} · файлов {item.declared_files}{' '}
                    <button type="button" className="am-button am-button--small am-button--quiet" onClick={() => props.onOpenUnfinished(item)}>
                      Открыть
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className={styles.actions}>
            <button type="button" className="am-button" disabled={!mayAct || busy || props.groups.length === 0} onClick={props.onSend}>
              {batch ? 'Загрузить пакет' : 'Загрузить и разобрать'}
            </button>
            {batch ? null : (
              <button type="button" className="am-button am-button--quiet" onClick={props.onSwitch}>
                {BATCH_SWITCH}
              </button>
            )}
          </p>
        </>
      ) : null}

      {phase === 'hashing' && props.hashing !== null ? (
        <p role="status" data-hashing="">
          Считаем контрольные суммы: файл {props.hashing.done + 1} из {props.hashing.total}…
        </p>
      ) : null}

      {props.loading ? <LoadingState what="загрузку" /> : null}

      {upload === undefined ? null : (
        <div data-upload-state={upload.state}>
          <p className={styles.status}>
            <strong>Загрузка: {UPLOAD_STATE_LABELS[upload.state]}</strong>
            <span className={styles.note}>
              файлов {upload.declared_files} · {formatMebibytes(upload.declared_bytes)}
            </span>
            {upload.compare_after_preparation === true ? (
              <span className={styles.note}>После подготовки будут сравнены все соседние версии.</span>
            ) : null}
          </p>
          <FileRows upload={upload} progress={props.progress} fileFailures={props.fileFailures} />
          {props.missing.length > 0 ? (
            <div className="am-note" role="status" data-missing-files={props.missing.length}>
              <p>
                {REPICK_NOTE} Не хватает файлов: {props.missing.length}.
              </p>
            </div>
          ) : null}
          {mayAct ? (
            <p className={styles.actions}>
              {phase === 'sending' ? (
                <button type="button" className="am-button am-button--quiet" onClick={props.onStop}>
                  Остановить загрузку
                </button>
              ) : null}
              {phase === 'stopped' ? (
                <>
                  <button type="button" className="am-button" disabled={busy} onClick={() => props.onContinue(null)}>
                    Продолжить загрузку
                  </button>
                  <label className={`am-button am-button--quiet ${styles.pick}`}>
                    Выбрать те же файлы
                    <input
                      className={styles.hiddenInput}
                      type="file"
                      multiple
                      accept=".pdf,application/pdf"
                      onChange={(event) => {
                        props.onContinue(event.target.files);
                        event.target.value = '';
                      }}
                    />
                  </label>
                </>
              ) : null}
              {batch && upload.state === 'processing' ? (
                <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={props.onPause}>
                  Пауза после текущего проекта
                </button>
              ) : null}
              {batch && upload.state === 'paused' ? (
                <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={props.onResume}>
                  Продолжить обработку
                </button>
              ) : null}
              {uploadIsActive(upload.state) ? (
                <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={props.onDelete}>
                  {batch ? 'Удалить пакет' : 'Отмена'}
                </button>
              ) : null}
            </p>
          ) : null}
        </div>
      )}

      {upload !== undefined && sets.length === 0 && uploadIsActive(upload.state) && phase === 'watching' ? (
        <p role="status" className="am-note" data-reading="">
          Система читает штампы файлов и собирает предложение…
        </p>
      ) : null}

      {sets.length === 0 ? null : (
        <div className={styles.sets} data-proposal-sets={sets.length}>
          <p className="am-note">{PROPOSAL_NOTE}</p>
          {sets.map((set) => (
            <SetEditor
              key={set.set_id}
              set={set}
              draft={props.drafts[set.set_id] ?? draftOf(set)}
              fileNames={props.fileNames}
              perSet={batch}
              mayAct={mayAct}
              busy={busy}
              onDraft={(draft) => props.onDraft(set.set_id, draft)}
              onConfirm={() => props.onConfirm(set)}
              onExclude={() => props.onExclude(set)}
              onRetry={() => props.onRetry(set)}
            />
          ))}
          {mayAct && awaiting.length > 0 ? (
            <p className={styles.actions}>
              {batch ? (
                <button type="button" className="am-button" disabled={busy} onClick={props.onProposedAll}>
                  Подтвердить порядок во всех проектах
                </button>
              ) : (
                <button type="button" className="am-button" disabled={busy} onClick={props.onConfirmAll}>
                  Подтвердить группировку и порядок
                </button>
              )}
            </p>
          ) : null}
        </div>
      )}

      {upload !== undefined && upload.state === 'completed' ? (
        <EmptyState title="Загрузка завершена." detail="Версии приняты. Состояние подготовки видно на вкладке «Проекты и этапы»." />
      ) : null}

      {props.notice === null ? null : (
        <p className="am-note" role="status" data-upload-notice="">
          {props.notice}
        </p>
      )}
      {props.failure === null ? null : (
        <p className="am-decision__refusal" role="alert" data-comparison-failure={props.failure.kind}>
          {props.failure.detail}
          {props.failure.correlationId === null ? null : <> Код обращения: <code>{props.failure.correlationId}</code>.</>}
        </p>
      )}
    </section>
  );
}

export interface UploadDialogProps {
  readonly projectUid: ProjectUid;
  readonly mode: UploadMode;
  readonly mayAct: boolean;
  readonly onSwitch: () => void;
  readonly onClose: () => void;
}

export function UploadDialog({ projectUid, mode, mayAct, onSwitch, onClose }: UploadDialogProps) {
  const flow: UploadFlow = useUploadFlow(projectUid);
  const unfinished = useUnfinishedUploads(projectUid);
  const confirm = useConfirmSet();
  const exclude = useExcludeSet();
  const retry = useRetrySet();
  const act = useUploadAct();
  const [drafts, setDrafts] = useState<Readonly<Record<string, SetDraft>>>({});
  const [notice, setNotice] = useState<string | null>(null);
  const [commandFailure, setCommandFailure] = useState<ComparisonFailure | null>(null);

  const upload = flow.upload.data;
  const sets = flow.proposal.data?.sets ?? [];
  const fileNames = new Map((upload?.files ?? []).map((file) => [file.file_id, file.display_name] as const));
  // A reopened upload starts as «stopped»; it is only stopped if some file still lacks parts.
  const lacking = (upload?.files ?? []).some((file) => needsTransfer({ state: file.state, failureReason: file.failure_reason }));
  const phase = flow.phase === 'stopped' && upload !== undefined && !lacking ? 'watching' : flow.phase;
  const busy = confirm.isPending || exclude.isPending || retry.isPending || act.isPending || flow.creating || flow.phase === 'hashing';
  const uploadId = flow.uploadId;

  const wrap = async (run: () => Promise<unknown>, done?: string): Promise<boolean> => {
    setCommandFailure(null);
    try {
      await run();
      if (done !== undefined) setNotice(done);
      return true;
    } catch (error) {
      setCommandFailure(comparisonFailure(error));
      return false;
    }
  };

  const confirmSets = async (todo: readonly ComparisonProposalSet[], bodyOf: (set: ComparisonProposalSet) => ReturnType<typeof proposedConfirmation>): Promise<void> => {
    if (uploadId === null) return;
    let confirmed = 0;
    for (const set of todo) {
      const ok = await wrap(() => confirm.mutateAsync({ uploadId, setId: set.set_id, request: bodyOf(set) }));
      if (!ok) break;
      confirmed += 1;
    }
    if (confirmed > 0) setNotice(`Подтверждено комплектов: ${confirmed} из ${todo.length}.`);
  };

  return (
    <UploadDialogView
      mode={mode}
      phase={phase}
      groups={groupsOf(flow.picked)}
      skipped={flow.skipped}
      problem={flow.problem}
      compare={flow.compare}
      hashing={flow.hashing}
      upload={upload}
      loading={uploadId !== null && flow.upload.isPending}
      sets={sets}
      drafts={drafts}
      fileNames={fileNames}
      progress={flow.progress}
      fileFailures={flow.fileFailures}
      missing={flow.missing}
      failure={commandFailure ?? flow.failure}
      unfinished={unfinished.data ?? []}
      notice={notice}
      mayAct={mayAct}
      busy={busy}
      onPick={(files, kind) => flow.add(Array.from(files), kind)}
      onRemoveGroup={flow.removeGroup}
      onCompare={flow.setCompare}
      onSend={() => void flow.send()}
      onStop={flow.stop}
      onContinue={(files) => {
        const again = files === null ? [] : Array.from(files).map((file) => ({ file, path: file.name, group: '' }));
        void flow.continueSending(again);
      }}
      onOpenUnfinished={(item) => {
        setNotice(null);
        flow.attach(item.upload_id);
      }}
      onDraft={(setId, draft) => setDrafts((held) => ({ ...held, [setId]: draft }))}
      onConfirm={(set) =>
        void confirmSets([set], (current) => confirmationOf(current, drafts[current.set_id] ?? draftOf(current)))
      }
      onConfirmAll={() =>
        void confirmSets(awaitingConfirmation(sets), (current) => confirmationOf(current, drafts[current.set_id] ?? draftOf(current)))
      }
      onProposedAll={() => void confirmSets(awaitingConfirmation(sets), proposedConfirmation)}
      onExclude={(set) => {
        if (uploadId !== null) void wrap(() => exclude.mutateAsync({ uploadId, setId: set.set_id }), 'Комплект исключён.');
      }}
      onRetry={(set) => {
        if (uploadId !== null) void wrap(() => retry.mutateAsync({ uploadId, setId: set.set_id }), 'Комплект поставлен на повтор.');
      }}
      onPause={() => {
        if (uploadId !== null) void wrap(() => act.mutateAsync({ uploadId, act: 'pause' }), 'Обработка встанет на паузу после текущего проекта.');
      }}
      onResume={() => {
        if (uploadId !== null) void wrap(() => act.mutateAsync({ uploadId, act: 'resume' }), 'Обработка продолжается.');
      }}
      onDelete={() => {
        if (uploadId === null) return;
        void wrap(() => act.mutateAsync({ uploadId, act: 'cancel' }), 'Загрузка удалена.').then((ok) => {
          if (ok) flow.forget();
        });
      }}
      onSwitch={onSwitch}
      onClose={onClose}
    />
  );
}
