'use client';

/** Whole specifications use the existing, source-bound spec API. No hidden paid queue step. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import type { ComparisonAiEstimate, ComparisonSeriesId, ComparisonSpecification, ComparisonTransitionId, Cursor } from '@/shared/api';
import {
  cancelComparisonSpecification, estimateComparisonSpecification, listComparisonSpecificationChanges,
  listComparisonSpecifications, newIdempotencyKey, startComparisonSpecification,
} from '@/shared/api';
import { COMPARISON_KEYS, EstimatePanel, comparisonFailure, consentOf } from '@/entities/version-series';

const STATE: Readonly<Record<string, string>> = {
  not_started: 'Не запускалось', not_applicable: 'Спецификаций нет', running: 'Выполняется',
  queued: 'В очереди', paused: 'Приостановлено', completed: 'Готово', incomplete: 'Неполный результат',
  failed: 'Ошибка', cancelled: 'Отменено',
};
const KINDS: Readonly<Record<string, string>> = {
  changed: 'Изменено', added: 'Добавлено', removed: 'Удалено', unclear: 'Неясно', renumbered: 'Перенумеровано', moved: 'Перемещено',
};

function ChangeList({ transitionId }: { readonly transitionId: ComparisonTransitionId }) {
  const [cursor, setCursor] = useState<Cursor | undefined>();
  const query = useQuery({
    queryKey: [...COMPARISON_KEYS.all, 'specification-changes', transitionId, cursor],
    queryFn: async () => (await listComparisonSpecificationChanges({ path: { comparison_transition_id: transitionId }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data,
  });
  return <div aria-label="Изменения спецификации">
    {query.isPending ? <p role="status">Читаем позиции…</p> : null}
    {query.error === null ? null : <p role="alert">{comparisonFailure(query.error).detail}</p>}
    <ul>{query.data?.items.map((change) => <li key={change.change_id} data-spec-change={change.change_id}>
      <strong>{KINDS[change.kind] ?? change.kind}</strong>{change.text === undefined ? '' : ` · ${change.text}`}
      {change.fields.length === 0 ? null : <ul>{change.fields.map((field, index) => <li key={`${field.field}-${index}`}>
        {field.field}: {field.was ?? '—'} → {field.now ?? '—'}
      </li>)}</ul>}
    </li>)}</ul>
    {query.data?.items.length === 0 ? <p>В сохранённом результате нет изменений позиций.</p> : null}
    {cursor === undefined ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(undefined)}>К началу</button>}
    {query.data?.page.next_cursor == null ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(query.data?.page.next_cursor ?? undefined)}>Следующие позиции</button>}
  </div>;
}

function SpecificationRow({ item, mayAct }: { readonly item: ComparisonSpecification; readonly mayAct: boolean }) {
  const client = useQueryClient();
  const [estimate, setEstimate] = useState<ComparisonAiEstimate | undefined>();
  const [agreed, setAgreed] = useState<string | null>(null);
  const [dialog, setDialog] = useState(false);
  const [key, setKey] = useState(() => newIdempotencyKey());
  const [changes, setChanges] = useState(false);
  const estimateCall = useMutation({ mutationFn: async () => (await estimateComparisonSpecification({ path: { comparison_transition_id: item.transition_id } })).data });
  const start = useMutation({ mutationFn: async () => {
    if (estimate === undefined || agreed !== estimate.estimate_digest) return;
    return startComparisonSpecification({ path: { comparison_transition_id: item.transition_id }, body: { consent: consentOf(estimate) }, idempotencyKey: key });
  }, onSuccess: () => {
    setDialog(false); setAgreed(null); setEstimate(undefined);
    void client.invalidateQueries({ queryKey: COMPARISON_KEYS.all });
  }, onError: (error) => {
    if (comparisonFailure(error).estimateStale) { setEstimate(undefined); setAgreed(null); setKey(newIdempotencyKey()); }
  } });
  const cancel = useMutation({ mutationFn: () => {
    if (item.job_id === undefined) throw new Error('У задания нет идентификатора');
    return cancelComparisonSpecification({ path: { comparison_ai_job_id: item.job_id }, idempotencyKey: newIdempotencyKey() });
  }, onSuccess: () => { void client.invalidateQueries({ queryKey: COMPARISON_KEYS.all }); } });
  const readEstimate = async () => {
    setDialog(true); setEstimate(undefined); setAgreed(null); setKey(newIdempotencyKey()); start.reset();
    try { setEstimate(await estimateCall.mutateAsync()); } catch { /* displayed below */ }
  };
  const active = item.state === 'running' || item.state === 'paused';
  const failure = start.error ?? estimateCall.error;
  return <section aria-label="Переход спецификаций" data-spec-transition={item.transition_id}>
    <p><strong>{STATE[item.state] ?? item.state}</strong> · листов A: {item.sheets_a}, B: {item.sheets_b}
      {item.phase === undefined ? '' : ` · этап: ${item.phase}`}</p>
    {[['A', item.coverage_a], ['B', item.coverage_b]].map(([side, value]) => {
      if (typeof value !== 'object' || value === null) return null;
      return <p key={String(side)} className="am-note">Охват {String(side)}: блоков {value.blocks_covered}/{value.blocks_total}, строк {value.rows_total}, не разобрано {value.rows_unresolved}.</p>;
    })}
    {item.reason === undefined ? null : <p className="am-note">Ограничение: <code>{item.reason}</code>. Полнота результата не подтверждена.</p>}
    {item.totals === undefined ? null : <p>{Object.entries(item.totals).map(([kind, count]) => `${KINDS[kind] ?? kind}: ${count}`).join(' · ')}</p>}
    <p className="am-note">ИИ-результат не подтверждён инженером. В сравнение входят распознанные позиции; неполные стороны не объявляются отсутствующими.</p>
    {mayAct && !active && item.state !== 'not_applicable' ? <button type="button" className="am-button am-button--small" onClick={() => void readEstimate()} disabled={estimateCall.isPending}>Оценить сравнение СО</button> : null}
    {mayAct && active && item.job_id !== undefined ? <button type="button" className="am-button am-button--quiet am-button--small" disabled={cancel.isPending} onClick={() => cancel.mutate()}>Отменить сравнение СО</button> : null}
    {item.state === 'completed' || item.state === 'incomplete' ? <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setChanges(!changes)}>{changes ? 'Скрыть позиции' : 'Показать изменения позиций'}</button> : null}
    {cancel.error === null ? null : <p role="alert">{comparisonFailure(cancel.error).detail}</p>}
    {dialog ? <EstimatePanel title="Полные спецификации (СО)" consentKind="spec" confirmLabel="Запустить сравнение СО"
      estimate={estimate} loading={estimateCall.isPending} failure={failure === null ? null : comparisonFailure(failure)}
      agreedDigest={agreed} busy={start.isPending} onAgree={(on) => setAgreed(on ? estimate?.estimate_digest ?? null : null)}
      onConfirm={() => start.mutate()} onCancel={() => { setDialog(false); setAgreed(null); }}
      intro={<p>Отдельное задание сравнит целые спецификации этого перехода. Сохранённые совместимые ответы используются повторно.</p>} /> : null}
    {changes ? <ChangeList transitionId={item.transition_id} /> : null}
  </section>;
}

export function SpecificationPanel({ seriesId, mayAct }: { readonly seriesId: ComparisonSeriesId; readonly mayAct: boolean }) {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState<Cursor | undefined>();
  const query = useQuery({ queryKey: [...COMPARISON_KEYS.all, 'specifications', seriesId, cursor], enabled: open,
    queryFn: async () => (await listComparisonSpecifications({ path: { comparison_series_id: seriesId }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data,
    refetchInterval: open ? 3000 : false,
  });
  return <div data-whole-specifications="" onClick={(event) => event.stopPropagation()}>
    <button type="button" className="am-button am-button--quiet am-button--small" aria-expanded={open} onClick={() => setOpen(!open)}>Полные спецификации (СО)</button>
    {open ? <section role="group" aria-label="Полные спецификации серии">
      <p className="am-note">Проверка СО запускается отдельно с оценкой и согласием. Готовый результат входит в новую сводку MD.</p>
      {query.isPending ? <p role="status">Читаем спецификации…</p> : null}
      {query.error === null ? null : <p role="alert">{comparisonFailure(query.error).detail}</p>}
      {query.data?.items.map((item) => <SpecificationRow key={item.transition_id} item={item} mayAct={mayAct} />)}
      {query.data?.items.length === 0 ? <p>В серии нет листов спецификации.</p> : null}
      {cursor === undefined ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(undefined)}>К началу переходов</button>}
      {query.data?.page.next_cursor == null ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(query.data?.page.next_cursor ?? undefined)}>Следующие переходы</button>}
      <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => { void client.invalidateQueries({ queryKey: COMPARISON_KEYS.all }); }}>Обновить результат и сводку</button>
    </section> : null}
  </div>;
}
