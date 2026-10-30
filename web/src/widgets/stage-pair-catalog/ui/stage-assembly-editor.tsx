'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { StageAssembly, StagePair } from '@/shared/api';
import { confirmStagePair, createStageAssembly, failureMessage, getStageAssembly,
  newIdempotencyKey, reviseStageAssembly } from '@/shared/api';
import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';
import { ErrorState } from '@/shared/ui';

import { documentLabel, readDocuments, revisedMemberCount } from '../model/assemblies';
import styles from './stage-pair-catalog.module.css';

/** The key belongs to the full immutable request, including its server-provided revision. */
function useIntent() {
  const held = useRef<{ signature: string; key: string } | null>(null);
  return {
    key: (body: unknown) => {
      const signature = JSON.stringify(body);
      if (held.current?.signature !== signature) held.current = { signature, key: newIdempotencyKey() };
      return held.current.key;
    }, clear: () => { held.current = null; },
  };
}

function Failure({ error }: { readonly error: unknown }) {
  if (error === null) return null;
  const message = failureMessage(error);
  return <ErrorState title="Сборка не открылась или решение не сохранено" detail={message.detail} correlationId={message.correlationId} />;
}

export function StageAssemblyCreator({ projectUid, mayAct }: { readonly projectUid: string; readonly mayAct: boolean }) {
  const cache = useQueryClient();
  const [open, setOpen] = useState(false);
  const documents = useQuery({ queryKey: ['stage-assembly-documents', projectUid], queryFn: () => readDocuments(projectUid), enabled: open, retry: false });
  const [label, setLabel] = useState('');
  const [leftUid, setLeftUid] = useState('');
  const [rightUids, setRightUids] = useState<string[]>([]);
  const [created, setCreated] = useState<StageAssembly | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [confirmed, setConfirmed] = useState(false);
  const intent = useIntent();
  const left = documents.data?.find((document) => document.document_uid === leftUid);
  const rightDocuments = documents.data?.filter((document) => document.classification?.project_stage === 'R' &&
    (left === undefined || document.classification.section_code === left.classification?.section_code)) ?? [];
  const create = async () => {
    if (!mayAct || busy || leftUid === '' || rightUids.length < 2 || rightUids.length > 100 || label.trim() === '') return;
    const body = { label: label.trim(), document_uids: rightUids };
    setBusy(true); setError(null);
    try {
      const answer = await createStageAssembly({ path: { project_uid: projectUid }, body, idempotencyKey: intent.key(['create', projectUid, body]) });
      intent.clear(); setCreated(answer.data);
    } catch (failure) { setError(failure); }
    finally { setBusy(false); }
  };
  const confirm = async () => {
    if (!mayAct || busy || created === null || leftUid === '') return;
    const body = { left_document_uid: leftUid, assembly_id: created.assembly_id };
    setBusy(true); setError(null);
    try {
      await confirmStagePair({ path: { project_uid: projectUid }, body, idempotencyKey: intent.key(['confirm', projectUid, body]) });
      intent.clear(); setConfirmed(true);
      await cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectPairs(projectUid) });
    } catch (failure) { setError(failure); }
    finally { setBusy(false); }
  };
  if (!mayAct) return null;
  return <details className={styles.decision} onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>Создать сборку Р и связать со стадией П</summary>
    {documents.isFetching ? <p role="status">Открываем документы проекта…</p> : null}
    <div className={styles.form}>
      <label>Документ П<select value={leftUid} disabled={busy || created !== null} onChange={(event) => { setLeftUid(event.target.value); setRightUids([]); }}>
        <option value="">Выберите документ</option>
        {documents.data?.filter((document) => document.classification?.project_stage === 'P').map((document) =>
          <option key={document.document_uid} value={document.document_uid}>{documentLabel(document)}</option>)}
      </select></label>
      <label>Название сборки<input value={label} maxLength={200} disabled={busy || created !== null} onChange={(event) => setLabel(event.target.value)} /></label>
      {created === null ? <fieldset disabled={busy}><legend>Документы Р · от 2 до 100</legend>
        {rightDocuments.map((document) => <label key={document.document_uid}><input type="checkbox" checked={rightUids.includes(document.document_uid)}
          onChange={(event) => setRightUids((prior) => event.target.checked ? [...prior, document.document_uid] : prior.filter((uid) => uid !== document.document_uid))} />{documentLabel(document)}</label>)}
        {rightDocuments.length === 0 ? <p>Подходящих документов Р с подтверждённым разделом пока нет.</p> : null}
      </fieldset> : <p>Создана сборка <strong>{created.label}</strong> · документов: {created.members.length} · <code>{created.assembly_id}</code></p>}
      {created === null ? <button type="button" className="am-button" disabled={busy || leftUid === '' || label.trim() === '' || rightUids.length < 2 || rightUids.length > 100}
        onClick={() => void create()}>Создать сборку</button> : <div className={styles.actions}>
        <button type="button" className="am-button" disabled={busy || leftUid === '' || confirmed} onClick={() => void confirm()}>Подтвердить пару П ↔ сборка Р</button>
        <button type="button" className="am-button" disabled={busy} onClick={() => { setCreated(null); setRightUids([]); setConfirmed(false); intent.clear(); }}>Создать другую сборку</button>
      </div>}
      {confirmed ? <p role="status">Пара подтверждена.</p> : null}
      <Failure error={error ?? documents.error} />
    </div>
  </details>;
}

export function StageAssemblyEditor({ pair, mayAct }: { readonly pair: StagePair; readonly mayAct: boolean }) {
  const [open, setOpen] = useState(false);
  const cache = useQueryClient();
  const assembly = useQuery({ queryKey: ['stage-assembly', pair.assembly_id],
    queryFn: async () => (await getStageAssembly({ path: { stage_assembly_id: pair.assembly_id! } })).data,
    enabled: open && pair.assembly_id !== undefined, retry: false });
  const documents = useQuery({ queryKey: ['stage-assembly-documents', pair.project_uid], queryFn: () => readDocuments(pair.project_uid), enabled: open && mayAct, retry: false });
  const [adds, setAdds] = useState<string[]>([]);
  const [removes, setRemoves] = useState<string[]>([]);
  const [basePin, setBasePin] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const intent = useIntent();
  const snapshot = assembly.data;
  const activeUids = new Set(snapshot?.members.map((member) => member.document_uid));
  const section = documents.data?.find((document) => document.document_uid === pair.left_document_uid)?.classification?.section_code;
  const additions = documents.data?.filter((document) => document.classification?.project_stage === 'R' && !activeUids.has(document.document_uid)
    && (section === undefined || document.classification.section_code === section)) ?? [];
  const beginEdit = () => { if (basePin === null && snapshot !== undefined) setBasePin(snapshot.member_revision_no); setSaved(false); };
  const save = async () => {
    if (!mayAct || busy || snapshot === undefined || basePin === null || (adds.length === 0 && removes.length === 0) || revisedMemberCount(snapshot, adds, removes) < 2 || revisedMemberCount(snapshot, adds, removes) > 100) return;
    const body = { base_member_no: basePin, add_document_uids: adds, remove_document_uids: removes };
    setBusy(true); setError(null);
    try {
      const answer = await reviseStageAssembly({ path: { stage_assembly_id: snapshot.assembly_id }, body,
        idempotencyKey: intent.key([snapshot.assembly_id, body]) });
      intent.clear(); setAdds([]); setRemoves([]); setBasePin(null); setSaved(true);
      cache.setQueryData(['stage-assembly', snapshot.assembly_id], answer.data);
      await Promise.all([
        cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectPairs(pair.project_uid) }),
        cache.invalidateQueries({ queryKey: ['stage-sheet-map', pair.pair_id] }),
        cache.invalidateQueries({ queryKey: ['stage-run-map', pair.pair_id] }),
        cache.invalidateQueries({ queryKey: ['stage-full-runs', pair.pair_id] }),
      ]);
    } catch (failure) { setError(failure); }
    finally { setBusy(false); }
  };
  if (pair.assembly_id === undefined) return null;
  return <details className={styles.assembly} onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>Состав сборки Р</summary>
    {assembly.isFetching ? <p role="status">Открываем состав…</p> : null}
    {snapshot === undefined ? null : <div className={styles.form}>
      <h4>{snapshot.label}</h4>
      <p>Документов: {snapshot.members.length}</p>
      <ul>{snapshot.members.map((member) => <li key={member.document_uid}>
        <code>{member.document_uid}</code>
        {mayAct ? <label><input type="checkbox" checked={removes.includes(member.document_uid)} disabled={busy}
          onChange={(event) => { beginEdit(); setRemoves((prior) => event.target.checked ? [...prior, member.document_uid] : prior.filter((uid) => uid !== member.document_uid)); }} />Убрать из сборки</label> : null}
      </li>)}</ul>
      {mayAct ? <fieldset disabled={busy}><legend>Добавить документы Р</legend>
        {additions.map((document) => <label key={document.document_uid}><input type="checkbox" checked={adds.includes(document.document_uid)}
          onChange={(event) => { beginEdit(); setAdds((prior) => event.target.checked ? [...prior, document.document_uid] : prior.filter((uid) => uid !== document.document_uid)); }} />{documentLabel(document)}</label>)}
      </fieldset> : null}
      {mayAct ? <div className={styles.actions}><button type="button" className="am-button" disabled={busy || (adds.length === 0 && removes.length === 0) || revisedMemberCount(snapshot, adds, removes) < 2 || revisedMemberCount(snapshot, adds, removes) > 100}
        onClick={() => void save()}>Сохранить состав</button>
        <button type="button" className="am-button" disabled={busy} onClick={() => { setAdds([]); setRemoves([]); setBasePin(null); intent.clear(); void assembly.refetch(); }}>Обновить состав и сбросить правки</button></div> : null}
      {saved ? <p role="status">Состав сохранён. Карта связей и сравнение требуют обновления.</p> : null}
    </div>}
    <Failure error={error ?? assembly.error ?? documents.error} />
  </details>;
}
