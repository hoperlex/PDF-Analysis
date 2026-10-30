'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { ProjectUid, StageUpload, StageUploadCandidate, StageUploadFile } from '@/shared/api';
import {
  cancelStageUpload, completeStageUploadFile, confirmStageUploadCandidate,
  createStageUpload, failureMessage, getStageUpload, listStageUploads, newIdempotencyKey,
  rejectStageUploadCandidate, resumeStageUpload, uploadStageUploadPart,
} from '@/shared/api';
import { PROJECT_SECTIONS } from '@/entities/project';
import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';
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

function CandidateDecision({ candidate, mayAct, refresh }: {
  readonly candidate: StageUploadCandidate;
  readonly mayAct: boolean;
  readonly refresh: () => Promise<void>;
}) {
  const [stage, setStage] = useState<'' | 'P' | 'R'>('');
  const [section, setSection] = useState('');
  const [designation, setDesignation] = useState('');
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
      <span>Кандидат {candidate.member_number} · {candidate.state === 'published' ? 'версия сохранена' : candidate.state === 'proposed' ? 'ожидает решения' : candidate.state}</span>
      {candidate.document_uid === undefined ? null : <code>{candidate.document_uid}</code>}
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

function FileRow({ file }: { readonly file: StageUploadFile }) {
  return <div className={styles.file}><span>{file.declaration.display_name}</span><span>{file.state} · {file.received_bytes} / {file.declaration.size_bytes} байт</span></div>;
}

export function StageUploadPanel({ projectUid, mayAct }: {
  readonly projectUid: ProjectUid;
  readonly mayAct: boolean;
}) {
  const cache = useQueryClient();
  const [cursor, setCursor] = useState('');
  const [pages, setPages] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
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
  const transfer = async (upload: StageUpload, chosen: File, digest: string) => {
    const declared = upload.files[0];
    if (declared === undefined || upload.files.length !== 1
        || declared.declaration.sha256 !== digest || declared.declaration.size_bytes !== chosen.size) {
      throw new LocalProblem('Выбранный файл не совпадает с объявленным набором.');
    }
    if (upload.state === 'paused') {
      await resumeStageUpload({
        path: { stage_upload_id: upload.upload_id },
        idempotencyKey: keyFor(`resume:${upload.upload_id}`),
      });
    }
    if (upload.state !== 'uploading' && upload.state !== 'paused') {
      throw new LocalProblem('Этот набор уже завершён или отменён.');
    }
    const count = Math.ceil(chosen.size / PART_BYTES);
    for (let number = 1; number <= count; number += 1) {
      const start = (number - 1) * PART_BYTES;
      setProgress(`Передача части ${number} из ${count}`);
      await uploadStageUploadPart({
        path: { stage_upload_id: upload.upload_id, stage_upload_file_id: declared.file_id },
        query: { part_number: number }, body: chosen.slice(start, Math.min(start + PART_BYTES, chosen.size)),
        idempotencyKey: keyFor(`part:${upload.upload_id}:${number}`),
      });
    }
    setProgress('Проверка PDF и состава ZIP');
    await completeStageUploadFile({
      path: { stage_upload_id: upload.upload_id, stage_upload_file_id: declared.file_id },
      idempotencyKey: keyFor(`complete:${upload.upload_id}`),
    });
    setActiveUploadId(null);
    setProgress('Набор принят. Подтвердите документы ниже.');
    setPages([]);
    setCursor('');
    await refresh();
  };

  const send = async (resume: StageUpload | null) => {
    if (file === null) return;
    setError(null);
    setProblem(null);
    setBusy(true);
    let createdAction: string | null = null;
    try {
      const kind = kindOf(file);
      if (kind === null || file.size < 1) {
        throw new LocalProblem('Выберите непустой PDF или ZIP.');
      }
      setProgress('Расчёт SHA-256');
      const digest = await hashStageFile(file, (read) => setProgress(`Хэширование: ${read} / ${file.size} байт`));
      let upload = resume;
      if (upload === null) {
        const signature = `${projectUid}|${file.name}|${digest}|${file.size}|${kind}`;
        createdAction = `create:${signature}`;
        upload = (await createStageUpload({
          path: { project_uid: projectUid },
          body: { files: [{
            display_name: file.name, media_kind: kind, size_bytes: file.size, sha256: digest,
          }] },
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
      await transfer(upload, file, digest);
      forgetCreateKeys();
    } catch (failure) {
      if (failure instanceof LocalProblem) setProblem(failure.message);
      else setError(failure);
      setProgress('Передача остановлена. Выберите тот же файл и продолжите набор.');
      await refresh();
    } finally {
      setBusy(false);
    }
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
    <section aria-labelledby="stage-upload-heading" className={styles.panel}>
      <h2 id="stage-upload-heading">Наборы PDF и ZIP</h2>
      <p>Файлы ZIP проверяются целиком. Каждый PDF становится кандидатом; эксперт отдельно подтверждает стадию, раздел и документ.</p>
      {mayAct ? (
        <div className={styles.form}>
          <label>PDF или ZIP
            <input type="file" accept=".pdf,.zip,application/pdf,application/zip" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
          <div className={styles.actions}>
            <button type="button" className="am-button" disabled={busy || file === null || activeUploadId !== null} onClick={() => void send(null)}>Загрузить новый набор</button>
            {activeUploadId === null ? null : <button type="button" className="am-button" disabled={busy || file === null} onClick={() => {
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
          <div className={styles.heading}><strong>Набор <code>{upload.upload_id}</code></strong><span>{upload.state}</span></div>
          {upload.files.map((item) => <FileRow key={item.file_id} file={item} />)}
          {mayAct && (upload.state === 'uploading' || upload.state === 'paused') ? (
            <div className={styles.actions}>
              <button type="button" className="am-button" disabled={busy || file === null} onClick={() => void send(upload)}>Продолжить с выбранным файлом</button>
              <button type="button" className="am-button" disabled={busy} onClick={() => void cancel(upload.upload_id)}>Отменить набор</button>
            </div>
          ) : null}
          {upload.candidates.map((candidate) => <CandidateDecision key={candidate.candidate_id} candidate={candidate} mayAct={mayAct} refresh={refresh} />)}
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
