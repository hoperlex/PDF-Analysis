'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { ProjectUid, StageUpload, StageUploadCandidate, StageUploadFile } from '@/shared/api';
import {
  cancelStageUpload, completeStageUploadFile, confirmStageUploadCandidate,
  createStageUpload, failureMessage, getStageUpload, listStageUploads, newIdempotencyKey,
  rejectStageUploadCandidate, resumeStageUpload, uploadStageUploadPart,
} from '@/shared/api';
import { PROJECT_SECTIONS } from '@/entities/project';
import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';
import { formatInstant, routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import { hashStageFile } from '../model/hash';
import styles from './stage-upload-panel.module.css';

const PART_BYTES = 16 * 1024 * 1024;
const queryKey = (projectUid: string, cursor: string) => ['comparison', 'stage-uploads', projectUid, cursor] as const;
class LocalProblem extends Error {}

function kindOf(file: File): 'pdf' | 'zip' | null {
  const name = file.name.toLocaleLowerCase();
  if (name.endsWith('.pdf')) return 'pdf';
  if (name.endsWith('.zip')) return 'zip';
  return null;
}

/** A chosen file with the digest its declaration carries; the name is the path the browser reports (a folder keeps its structure). */
interface Entry {
  readonly file: File;
  readonly kind: 'pdf' | 'zip';
  readonly name: string;
  readonly digest: string;
}

const MAX_NAME = 255;
function declaredName(file: File): string {
  const relative = (file as File & { readonly webkitRelativePath?: string }).webkitRelativePath;
  const path = relative !== undefined && relative !== '' ? relative : file.name;
  return path.length <= MAX_NAME ? path : path.slice(path.length - MAX_NAME);
}

const CANDIDATE_STATES: Readonly<Record<StageUploadCandidate['state'], string>> = {
  proposed: 'ожидает решения', confirmed: 'подтверждён', admitting: 'проверяется', published: 'версия сохранена', rejected: 'отклонён', failed: 'ошибка',
};

function CandidateDecision({ projectUid, candidate, mayAct, refresh }: {
  readonly projectUid: ProjectUid;
  readonly candidate: StageUploadCandidate;
  readonly mayAct: boolean;
  readonly refresh: () => Promise<void>;
}) {
  // The stamp's proposal is where the expert starts, not what is saved: nothing is stored until «Подтвердить документ».
  const [stage, setStage] = useState<'' | 'P' | 'R'>(candidate.proposed_stage ?? '');
  const [section, setSection] = useState(PROJECT_SECTIONS.some((item) => item.code === candidate.proposed_section) ? (candidate.proposed_section ?? '') : '');
  const [designation, setDesignation] = useState(candidate.designation ?? '');
  const [existing, setExisting] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const intent = useRef<{ signature: string; key: string } | null>(null);

  const decision = async (reject: boolean) => {
    const signature = reject ? `${candidate.candidate_id}|reject` : [
      candidate.candidate_id, stage, section, designation, existing,
    ].join('|');
    if (intent.current?.signature !== signature) {
      intent.current = { signature, key: newIdempotencyKey() };
    }
    setBusy(true);
    setError(null);
    setProblem(null);
    try {
      if (reject) {
        await rejectStageUploadCandidate({
          path: { stage_upload_candidate_id: candidate.candidate_id },
          idempotencyKey: intent.current.key,
        });
      } else {
        if (stage === '' || section === '' || designation.trim() === '') {
          throw new LocalProblem('Выберите стадию и раздел, затем введите шифр документа.');
        }
        await confirmStageUploadCandidate({
          path: { stage_upload_candidate_id: candidate.candidate_id },
          body: {
            stage, section_code: section, designation: designation.trim(),
            ...(existing.trim() === '' ? {} : { existing_document_uid: existing.trim() }),
          },
          idempotencyKey: intent.current.key,
        });
      }
      intent.current = null;
      await refresh();
    } catch (failure) {
      if (failure instanceof LocalProblem) setProblem(failure.message);
      else setError(failure);
    } finally {
      setBusy(false);
    }
  };

  const failure = error === null ? null : failureMessage(error);
  return (
    <article className={styles.card}>
      <strong>{candidate.display_name}</strong>
      <span>Кандидат {candidate.member_number} · {CANDIDATE_STATES[candidate.state]}</span>
      {candidate.state === 'proposed' && (candidate.proposed_stage !== undefined || candidate.proposed_section !== undefined || candidate.designation !== undefined)
        ? <span>По штампу предложено: {[candidate.proposed_stage === undefined ? null : `стадия ${candidate.proposed_stage === 'P' ? 'П' : 'Р'}`,
          candidate.proposed_section === undefined ? null : `раздел ${candidate.proposed_section}`,
          candidate.designation === undefined ? null : `шифр ${candidate.designation}`].filter((part) => part !== null).join(', ')}. Решение за вами.</span> : null}
      {candidate.document_uid === undefined ? null : <a href={routes.document(projectUid, candidate.document_uid)}>Открыть документ</a>}
      {candidate.state === 'proposed' && mayAct ? (
        <div className={styles.form}>
          <label>Стадия
            <select value={stage} onChange={(event) => setStage(event.target.value as '' | 'P' | 'R')}>
              <option value="">— выберите —</option>
              <option value="P">П</option><option value="R">Р</option>
            </select>
          </label>
          <label>Раздел
            <select value={section} onChange={(event) => setSection(event.target.value)}>
              <option value="">— выберите —</option>
              {PROJECT_SECTIONS.map((item) => <option key={item.code} value={item.code}>{item.code} · {item.name}</option>)}
            </select>
          </label>
          <label>Шифр документа
            <input value={designation} maxLength={200} onChange={(event) => setDesignation(event.target.value)} />
          </label>
          <label>ID существующего документа (необязательно)
            <input value={existing} onChange={(event) => setExisting(event.target.value)} placeholder="doc_…" />
          </label>
          <p>Стадия, раздел и документ сохраняются только после вашего подтверждения.</p>
          <div className={styles.actions}>
            <button type="button" className="am-button" disabled={busy} onClick={() => void decision(false)}>Подтвердить документ</button>
            <button type="button" className="am-button" disabled={busy} onClick={() => void decision(true)}>Отклонить</button>
          </div>
        </div>
      ) : null}
      {failure === null ? null : <ErrorState title="Решение не сохранено" detail={failure.detail} correlationId={failure.correlationId} />}
      {problem === null ? null : <p role="alert">{problem}</p>}
    </article>
  );
}

const FILE_STATES: Readonly<Record<StageUploadFile['state'], string>> = {
  declared: 'объявлен', receiving: 'принимается', received: 'получен', admitting: 'проверяется', ready: 'готов', failed: 'ошибка', cancelled: 'отменён',
};
const UPLOAD_STATES: Readonly<Record<StageUpload['state'], string>> = {
  uploading: 'передача', paused: 'приостановлен', admitting: 'проверка', completed: 'принят', failed: 'ошибка', cancelled: 'отменён',
};

function FileRow({ file }: { readonly file: StageUploadFile }) {
  return <div className={styles.file}><span>{file.declaration.display_name}</span><span>{FILE_STATES[file.state]} · {file.received_bytes} / {file.declaration.size_bytes} байт</span></div>;
}

/**
 * The sets of PDF and ZIP files of the project and the form that adds one. The original opens its upload in a dialog from the button
 * «Загрузить проекты» at the right of the steps bar; here the same button opens this panel, which stays closed until it is asked for
 * — except that a set with documents waiting for the expert's word opens it once, since those decisions would otherwise hide.
 */
export function StageUploadPanel({ projectUid, mayAct, open = true, onOpenChange = () => undefined }: {
  readonly projectUid: ProjectUid;
  readonly mayAct: boolean;
  /** Drawn when true (the default, for a panel mounted alone); the workspace closes it until «Загрузить проекты» asks. */
  readonly open?: boolean;
  readonly onOpenChange?: (open: boolean) => void;
}) {
  const cache = useQueryClient();
  const [cursor, setCursor] = useState('');
  const [pages, setPages] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [skipped, setSkipped] = useState(0);
  const [activeUploadId, setActiveUploadId] = useState<string | null>(null);
  const [progress, setProgress] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const keys = useRef(new Map<string, string>());
  const uploads = useQuery({
    queryKey: queryKey(projectUid, cursor),
    queryFn: async () => (await listStageUploads({
      path: { project_uid: projectUid },
      query: { limit: 50, ...(cursor === '' ? {} : { cursor }) },
    })).data,
    retry: false,
  });

  const waiting = mayAct && (uploads.data?.items.some((upload) => upload.candidates.some((candidate) => candidate.state === 'proposed')) ?? false);
  const announced = useRef(false);
  useEffect(() => {
    if (waiting && !announced.current) {
      announced.current = true;
      onOpenChange(true);
    }
  }, [waiting, onOpenChange]);

  const keyFor = (action: string) => {
    const existing = keys.current.get(action);
    if (existing !== undefined) return existing;
    const created = newIdempotencyKey();
    keys.current.set(action, created);
    return created;
  };
  const forgetCreateKeys = () => {
    for (const action of keys.current.keys()) {
      if (action.startsWith('create:')) keys.current.delete(action);
    }
  };
  const refresh = async () => {
    await cache.invalidateQueries({ queryKey: ['comparison', 'stage-uploads', projectUid] });
    await cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectSuggestions(projectUid) });
    await Promise.all([
      cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectPairs(projectUid) }),
      cache.invalidateQueries({ queryKey: ['stage-full-runs'] }),
      cache.invalidateQueries({ queryKey: ['stage-full-run'] }),
      cache.invalidateQueries({ queryKey: ['stage-sheet-map'] }),
      cache.invalidateQueries({ queryKey: ['stage-text-evidence'] }),
    ]);
  };
  const transfer = async (upload: StageUpload, entries: readonly Entry[]) => {
    if (upload.state !== 'uploading' && upload.state !== 'paused') {
      throw new LocalProblem('Этот набор уже завершён или отменён.');
    }
    // The files still to send; a file already received or admitted is not sent again. Each is found among the chosen ones by its
    // digest and size — the declaration, not the name, is what ties a chosen file to the set.
    const waiting = upload.files.filter((declared) => declared.state === 'declared' || declared.state === 'receiving');
    const matched = waiting.map((declared) => ({
      declared,
      entry: entries.find((item) => item.digest === declared.declaration.sha256 && item.file.size === declared.declaration.size_bytes),
    }));
    const missing = matched.find((item) => item.entry === undefined);
    if (missing !== undefined) {
      throw new LocalProblem(`Среди выбранных нет файла «${missing.declared.declaration.display_name}». Выберите те же файлы и продолжите набор.`);
    }
    if (upload.state === 'paused') {
      await resumeStageUpload({
        path: { stage_upload_id: upload.upload_id },
        idempotencyKey: keyFor(`resume:${upload.upload_id}`),
      });
    }
    for (const [index, { declared, entry }] of matched.entries()) {
      const chosen = entry!.file;
      const count = Math.ceil(chosen.size / PART_BYTES);
      for (let number = 1; number <= count; number += 1) {
        const start = (number - 1) * PART_BYTES;
        setProgress(`Файл ${index + 1} из ${matched.length}: передача части ${number} из ${count}`);
        await uploadStageUploadPart({
          path: { stage_upload_id: upload.upload_id, stage_upload_file_id: declared.file_id },
          query: { part_number: number }, body: chosen.slice(start, Math.min(start + PART_BYTES, chosen.size)),
          idempotencyKey: keyFor(`part:${upload.upload_id}:${declared.file_id}:${number}`),
        });
      }
      setProgress(`Файл ${index + 1} из ${matched.length}: проверка PDF и состава ZIP`);
      await completeStageUploadFile({
        path: { stage_upload_id: upload.upload_id, stage_upload_file_id: declared.file_id },
        idempotencyKey: keyFor(`complete:${upload.upload_id}:${declared.file_id}`),
      });
    }
    setActiveUploadId(null);
    setProgress('Набор принят. Подтвердите документы ниже.');
    setPages([]);
    setCursor('');
    await refresh();
  };

  const send = async (resume: StageUpload | null) => {
    if (files.length === 0) return;
    setError(null);
    setProblem(null);
    setBusy(true);
    let createdAction: string | null = null;
    try {
      const kinds = files.map(kindOf);
      if (kinds.some((kind) => kind === null) || files.some((item) => item.size < 1)) {
        throw new LocalProblem('Выберите непустые PDF или ZIP.');
      }
      const entries: Entry[] = [];
      for (const [index, item] of files.entries()) {
        const digest = await hashStageFile(item, (read) => setProgress(`Файл ${index + 1} из ${files.length}: хэширование, ${read} / ${item.size} байт`));
        entries.push({ file: item, kind: kindOf(item)!, name: declaredName(item), digest });
      }
      let upload = resume;
      if (upload === null) {
        const signature = `${projectUid}|${entries.map((item) => `${item.name}|${item.digest}|${item.file.size}|${item.kind}`).join(';')}`;
        createdAction = `create:${signature}`;
        upload = (await createStageUpload({
          path: { project_uid: projectUid },
          body: { files: entries.map((item) => ({
            display_name: item.name, media_kind: item.kind, size_bytes: item.file.size, sha256: item.digest,
          })) },
          idempotencyKey: keyFor(createdAction),
        })).data;
      }
      setActiveUploadId(upload.upload_id);
      if (upload.state === 'completed') {
        setActiveUploadId(null);
        forgetCreateKeys();
        await refresh();
        return;
      }
      await transfer(upload, entries);
      forgetCreateKeys();
    } catch (failure) {
      if (failure instanceof LocalProblem) setProblem(failure.message);
      else setError(failure);
      setProgress('Передача остановлена. Выберите те же файлы и продолжите набор.');
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const pick = (list: FileList | null) => {
    const all = Array.from(list ?? []);
    const wanted = all.filter((item) => kindOf(item) !== null);
    setFiles(wanted);
    setSkipped(all.length - wanted.length);
  };

  const cancel = async (uploadId: string) => {
    setBusy(true);
    setError(null);
    try {
      await cancelStageUpload({
        path: { stage_upload_id: uploadId },
        idempotencyKey: keyFor(`cancel:${uploadId}`),
      });
      if (activeUploadId === uploadId) setActiveUploadId(null);
      forgetCreateKeys();
      await refresh();
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  };

  const failure = error === null ? null : failureMessage(error);
  const readFailure = uploads.error === null ? null : failureMessage(uploads.error);
  return (
    <section aria-labelledby="stage-upload-heading" className={styles.panel} id="stage-upload-panel" hidden={!open}>
      <div className={styles.heading}>
        <h2 id="stage-upload-heading">Наборы PDF и ZIP</h2>
        <button type="button" className="am-button am-button--quiet" onClick={() => onOpenChange(false)}>Свернуть</button>
      </div>
      <p>Файлы ZIP проверяются целиком. Каждый PDF, в том числе из выбранной папки, становится кандидатом; эксперт отдельно подтверждает стадию, раздел и документ.</p>
      {mayAct ? (
        <div className={styles.form}>
          <label>PDF или ZIP (можно несколько)
            <input type="file" multiple accept=".pdf,.zip,application/pdf,application/zip" onChange={(event) => pick(event.target.files)} />
          </label>
          <label>Папка с проектами
            <input type="file" multiple {...({ webkitdirectory: '', directory: '' } as Record<string, string>)} onChange={(event) => pick(event.target.files)} />
          </label>
          {files.length === 0 && skipped === 0 ? null : <p role="status">Выбрано файлов: {files.length}{skipped === 0 ? '' : ` · пропущено не PDF и не ZIP: ${skipped}`}</p>}
          <div className={styles.actions}>
            <button type="button" className="am-button" disabled={busy || files.length === 0 || activeUploadId !== null} onClick={() => void send(null)}>Загрузить новый набор</button>
            {activeUploadId === null ? null : <button type="button" className="am-button" disabled={busy || files.length === 0} onClick={() => {
              void getStageUpload({ path: { stage_upload_id: activeUploadId } })
                .then((answer) => send(answer.data)).catch(setError);
            }}>Продолжить передачу</button>}
          </div>
          {progress === '' ? null : <p role="status">{progress}</p>}
        </div>
      ) : null}
      {failure === null ? null : <ErrorState title="Набор не обработан" detail={failure.detail} correlationId={failure.correlationId} />}
      {problem === null ? null : <p role="alert">{problem}</p>}
      {uploads.isPending ? <LoadingState what="наборы проекта" /> : null}
      {readFailure === null ? null : <ErrorState title="Наборы не открылись" detail={readFailure.detail} correlationId={readFailure.correlationId} onRetry={readFailure.retryable ? () => void uploads.refetch() : undefined} />}
      {uploads.data?.items.length === 0 ? <EmptyState title="Наборов пока нет" detail="Загрузите PDF или ZIP, затем подтвердите кандидатов." /> : null}
      {uploads.data?.items.map((upload) => (
        <article className={styles.batch} key={upload.upload_id}>
          <div className={styles.heading}><strong title={upload.upload_id}>Набор от {formatInstant(upload.created_at)} · файлов {upload.files.length}</strong><span>{UPLOAD_STATES[upload.state]}</span></div>
          {upload.files.map((item) => <FileRow key={item.file_id} file={item} />)}
          {mayAct && (upload.state === 'uploading' || upload.state === 'paused') ? (
            <div className={styles.actions}>
              <button type="button" className="am-button" disabled={busy || files.length === 0} onClick={() => void send(upload)}>Продолжить с выбранными файлами</button>
              <button type="button" className="am-button" disabled={busy} onClick={() => void cancel(upload.upload_id)}>Отменить набор</button>
            </div>
          ) : null}
          {upload.candidates.map((candidate) => <CandidateDecision key={candidate.candidate_id} projectUid={projectUid} candidate={candidate} mayAct={mayAct} refresh={refresh} />)}
        </article>
      ))}
      {uploads.data === undefined ? null : <nav className={styles.actions} aria-label="Страницы наборов стадий">
        <button type="button" className="am-button" disabled={pages.length === 0} onClick={() => {
          const previous = pages.slice(0, -1);
          setPages(previous);
          setCursor(previous.at(-1) ?? '');
        }}>Назад</button>
        <button type="button" className="am-button" disabled={uploads.data.page.next_cursor === null} onClick={() => {
          const next = uploads.data?.page.next_cursor;
          if (next !== null && next !== undefined) {
            setPages((held) => [...held, next]);
            setCursor(next);
          }
        }}>Далее</button>
      </nav>}
    </section>
  );
}
