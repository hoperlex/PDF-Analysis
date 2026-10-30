'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { StageCardEvidence, StageChangeCard } from '@/shared/api';
import { applyStageCardVerdicts, failureMessage, getStageChainRun, newIdempotencyKey } from '@/shared/api';
import { AiLabel } from '@/entities/version-series';
import { formatInstant } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import { readCards, readVerdicts, STAGE_REVIEW_KEYS } from '../api/reads';
import { CARRYOVER_WORDS, CLASS_WORDS, CATEGORY_WORDS, SYSTEM_WORDS,
  editVerdict, groupedCards, rejectionReasonsMissing, verdictUpdates } from '../model/cards';
import type { VerdictDraft } from '../model/cards';
import { StageRawDifferences } from './stage-raw-differences';
import type { OpenStageRawDifference } from './stage-raw-differences';
import { StageHighLevelChanges } from './stage-high-level-changes';
import styles from './stage-changes.module.css';

export type OpenStageEvidence = (evidence: StageCardEvidence, card: StageChangeCard) => void;
export interface StageReviewProps {
  readonly runId: string | null | undefined;
  readonly mayAct: boolean;
  readonly onOpenEvidence: OpenStageEvidence;
}

export interface StageChangesProps extends StageReviewProps {
  readonly onOpenRawDifference?: OpenStageRawDifference;
}

function CardSide({ side, card, onOpenEvidence }: { readonly side: 'left' | 'right'; readonly card: StageChangeCard;
  readonly onOpenEvidence: OpenStageEvidence }) {
  const text = side === 'left' ? card.before : card.after;
  const evidence = (card.evidence ?? []).filter((item) => item.side === side || item.side === 'both');
  return <section aria-label={side === 'left' ? 'Было' : 'Стало'}>
    <h5>{side === 'left' ? 'Было · П' : 'Стало · Р'}</h5><p>{text || 'Не указано'}</p>
    {text === '' && !evidence.some((item) => item.absence_proven) ? <p className={styles.note}>Отсутствие объекта не доказано.</p> : null}
    <div className={styles.evidence}>{evidence.map((item) => <div key={item.evidence_id}>
      <span>{item.kind}</span><button type="button" className="am-button" disabled={item.profile_id === undefined}
        onClick={() => onOpenEvidence(item, card)}>Открыть в PDF ↗</button>
    </div>)}</div>
  </section>;
}

function VerdictHistory({ card }: { readonly card: StageChangeCard }) {
  const [open, setOpen] = useState(false);
  const history = useQuery({ queryKey: ['stage-card-verdicts', card.card_id],
    queryFn: () => readVerdicts(card.card_id), enabled: open, retry: false });
  const failure = history.error === null ? null : failureMessage(history.error);
  return <details onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>История решений</summary>
    {history.isFetching ? <p role="status">Открываем историю…</p> : null}
    {failure === null ? null : <ErrorState title="История не открылась" detail={failure.detail} correlationId={failure.correlationId} />}
    {history.data?.length === 0 ? <p>Решений пока нет.</p> : null}
    <ol>{history.data?.map((verdict) => <li key={verdict.verdict_id}>
      {verdict.decision === 'accepted' ? 'Принято' : 'Не принято'} · {formatInstant(verdict.created_at)} · ревизия {verdict.revision_no}
      {verdict.reason === '' ? null : <p>{verdict.reason}</p>}
    </li>)}</ol>
  </details>;
}

export function StageCardView({ card, draft, mayAct, onDraft, onOpenEvidence }: {
  readonly card: StageChangeCard; readonly draft: VerdictDraft | undefined; readonly mayAct: boolean;
  readonly onDraft: (decision: 'accepted' | 'rejected', reason?: string) => void;
  readonly onOpenEvidence: OpenStageEvidence;
}) {
  const decision = draft?.decision ?? card.verdict?.decision;
  const reason = draft?.reason ?? card.verdict?.reason ?? '';
  const editable = mayAct && !card.stale && card.class_name !== 'SERVICE_STRUCTURE';
  return <article className={styles.card} aria-labelledby={`stage-card-${card.card_id}`}>
    <header className={styles.cardHeader}>
      <div><span className="am-badge">{CLASS_WORDS[card.class_name]}</span> <span>{CATEGORY_WORDS[card.category]}</span></div>
      <code>{card.card_id}</code>
    </header>
    <h4 id={`stage-card-${card.card_id}`}>{card.title}</h4>
    {card.verdict?.decision === 'accepted' ? <p>Принято экспертом.</p> : <p><AiLabel /></p>}
    <p>Система: {SYSTEM_WORDS[card.system]}</p>
    <div className={styles.sides}>
      <CardSide side="left" card={card} onOpenEvidence={onOpenEvidence} />
      <CardSide side="right" card={card} onOpenEvidence={onOpenEvidence} />
    </div>
    {(card.evidence ?? []).length === 0 ? <p>Места на чертежах ещё не привязаны.</p> : null}
    <p>{CARRYOVER_WORDS[card.carryover ?? 'none']}</p>
    {card.stale ? <p className={styles.warning} role="status">Свидетельства устарели — обновите сравнение перед решением.</p> : null}
    {editable ? <fieldset className={styles.verdict}><legend>Экспертная оценка</legend>
      <label><input type="radio" name={`verdict-${card.card_id}`} checked={decision === 'accepted'}
        onChange={() => onDraft('accepted', '')} />Принято</label>
      <label><input type="radio" name={`verdict-${card.card_id}`} checked={decision === 'rejected'}
        onChange={() => onDraft('rejected')} />Не принято</label>
      {decision === 'rejected' ? <label>Причина отказа
        <textarea value={reason} required maxLength={2000} aria-invalid={reason.trim() === ''}
          onChange={(event) => onDraft('rejected', event.target.value)} />
      </label> : null}
    </fieldset> : card.class_name === 'SERVICE_STRUCTURE' ? <p>Служебная карточка. Экспертная оценка не требуется.</p>
      : <p>Решение: {decision === undefined ? 'не сохранено' : decision === 'accepted' ? 'Принято' : 'Не принято'}{reason === '' ? '' : ` · ${reason}`}</p>}
    {card.class_name === 'SERVICE_STRUCTURE' ? null : <VerdictHistory card={card} />}
  </article>;
}

export function StageChanges(props: StageChangesProps) {
  return <StageChangesBody key={props.runId ?? ''} {...props} />;
}

function StageChangesBody({ runId, mayAct, onOpenEvidence, onOpenRawDifference }: StageChangesProps) {
  const cache = useQueryClient();
  const run = useQuery({ queryKey: ['stage-review-run', runId ?? ''],
    queryFn: async () => (await getStageChainRun({ path: { stage_chain_run_id: runId! } })).data,
    enabled: Boolean(runId), retry: false,
    refetchInterval: (query) => query.state.data !== undefined && ['queued', 'running'].includes(query.state.data.state) ? 1500 : false });
  const cards = useQuery({ queryKey: STAGE_REVIEW_KEYS.cards(runId ?? ''),
    queryFn: () => readCards(runId!), enabled: Boolean(runId), retry: false,
    refetchInterval: run.data !== undefined && ['queued', 'running'].includes(run.data.state) ? 3000 : false });
  useEffect(() => {
    if (run.data?.state === 'completed') void cards.refetch();
  }, [run.data?.state, run.data?.run_id, cards.refetch]);
  const [drafts, setDrafts] = useState<Record<string, VerdictDraft>>({});
  const [expertMode, setExpertMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [commandError, setCommandError] = useState<unknown>(null);
  const held = useRef(new Map<string, string>());
  useEffect(() => { setDrafts({}); setSaved(false); setCommandError(null); held.current.clear(); }, [runId]);
  const updates = verdictUpdates(cards.data?.cards ?? [], drafts);
  const missingReasons = rejectionReasonsMissing(updates);
  const save = async () => {
    if (!runId || !mayAct || run.data?.stale || updates.length === 0 || missingReasons) return;
    setSaving(true); setCommandError(null);
    try {
      // Each bounded server transaction has its own retry key. A later failure retains only unsaved drafts.
      for (let offset = 0; offset < updates.length; offset += 500) {
        const batch = updates.slice(offset, offset + 500);
        const signature = JSON.stringify([runId, batch]);
        const key = held.current.get(signature) ?? newIdempotencyKey();
        held.current.set(signature, key);
        await applyStageCardVerdicts({ path: { stage_chain_run_id: runId }, body: { updates: batch }, idempotencyKey: key });
        held.current.delete(signature);
        setDrafts((prior) => {
          const remaining = { ...prior };
          for (const update of batch) delete remaining[update.card_id];
          return remaining;
        });
      }
      setSaved(true);
    } catch (failure) { setCommandError(failure); }
    finally {
      await Promise.all([
        cache.invalidateQueries({ queryKey: STAGE_REVIEW_KEYS.cards(runId) }),
        cache.invalidateQueries({ queryKey: STAGE_REVIEW_KEYS.journal(runId) }),
        cache.invalidateQueries({ queryKey: ['stage-card-verdicts'] }),
      ]);
      setSaving(false);
    }
  };
  const failure = commandError ?? cards.error ?? run.error;
  const message = failure === null ? null : failureMessage(failure);
  if (!runId) return <EmptyState title="Выберите сравнение" detail="Карточки появятся после полного сравнения стадий." />;
  const counts = cards.data?.counts;
  return <section className={styles.changes} aria-labelledby="stage-changes-heading">
    <h2 id="stage-changes-heading">Изменения проекта</h2>
    {run.data !== undefined && ['queued', 'running'].includes(run.data.state) ? <p role="status">Сравнение выполняется. Карточки будут обновляться по мере готовности.</p> : null}
    {run.data?.stale ? <p role="status">Есть новые документы или изменены связи — сравнение не обновлено.</p> : null}
    {counts === undefined ? null : <dl className={styles.counts}>
      <div><dt>Всего</dt><dd>{counts.total ?? '—'}</dd></div>
      <div><dt>Нужно проверить</dt><dd>{counts.review ?? '—'}</dd></div>
      <div><dt>Конфликты</dt><dd>{counts.conflicts ?? '—'}</dd></div>
      <div><dt>Высокая важность</dt><dd>{counts.high_importance ?? '—'}</dd></div>
    </dl>}
    {cards.isPending ? <LoadingState what="изменения проекта" /> : null}
    {message === null ? null : <ErrorState title="Изменения не открылись или решение не сохранено" detail={message.detail} correlationId={message.correlationId} />}
    {mayAct ? <label><input type="checkbox" checked={expertMode} onChange={(event) => setExpertMode(event.target.checked)} />Экспертная оценка</label> : null}
    {cards.data?.cards.length === 0 ? <EmptyState title="Карточек изменений пока нет" /> : null}
    <StageHighLevelChanges runId={runId} cards={cards.data?.cards ?? []}
      running={run.data !== undefined && ['queued', 'running'].includes(run.data.state)} completed={run.data?.state === 'completed'} onOpenEvidence={onOpenEvidence} />
    {groupedCards(cards.data?.cards ?? []).map((section) => <details key={section.key} open={!section.collapsed}>
      <summary>{section.title} · {section.cards.length}</summary>
      <div className={styles.cards}>{section.cards.map((card) => <StageCardView key={card.card_id} card={card}
        draft={drafts[card.card_id]} mayAct={mayAct && expertMode && !saving && !run.data?.stale} onOpenEvidence={onOpenEvidence}
        onDraft={(decision, reason) => {
          setDrafts((heldDrafts) => ({ ...heldDrafts,
            [card.card_id]: editVerdict(card, heldDrafts[card.card_id], decision, reason) }));
          setSaved(false);
        }} />)}</div>
    </details>)}
    {mayAct ? <div className={styles.save}><span>Не сохранено: {updates.length}</span>
      {missingReasons ? <p role="alert">Укажите причину каждого отказа.</p> : null}
      <button type="button" className="am-button" disabled={saving || run.data?.stale || updates.length === 0 || missingReasons}
        onClick={() => void save()}>Сохранить решения</button>
      {saved ? <p role="status">Решения сохранены.</p> : null}
    </div> : null}
    <StageRawDifferences runId={runId} {...(onOpenRawDifference === undefined ? {} : { onOpen: onOpenRawDifference })} />
  </section>;
}
