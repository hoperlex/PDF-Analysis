'use client';

/** Whole specifications use the existing, source-bound spec API. No hidden paid queue step. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { ComparisonAiEstimate, ComparisonPageRef, ComparisonSeriesId, ComparisonSpecification, ComparisonTransitionId, Cursor } from '@/shared/api';
import {
  cancelComparisonSpecification, estimateComparisonSpecification, listComparisonSpecificationChanges,
  listComparisonSpecifications, newIdempotencyKey, startComparisonSpecification,
} from '@/shared/api';
import { COMPARISON_KEYS, EstimatePanel, SPEC_METHOD_LABELS, SPEC_PHASE_LABELS, comparisonFailure, consentOf, specFieldLabel } from '@/entities/version-series';
import { browserDownloadSink, deliverDownload } from '@/features/export-run';
import { pdfPageUrl, useEvidenceDocument } from '@/features/open-evidence';
import { readSpecificationReport, SpecificationReportError } from '../api/read-specification-report';
import { formatSpecificationReport } from '../model/specification-report';
import type { SpecificationReportFormat } from '../model/specification-report';

const STATE: Readonly<Record<string, string>> = {
  not_started: 'Не запускалось', not_applicable: 'Полные СО не определены', running: 'Выполняется',
  queued: 'В очереди', paused: 'Приостановлено', completed: 'Готово', incomplete: 'Неполный результат',
  failed: 'Ошибка', cancelled: 'Отменено',
};
const KINDS: Readonly<Record<string, string>> = {
  changed: 'Изменено', added: 'Добавлено', removed: 'Удалено', unclear: 'Неясно', renumbered: 'Перенумеровано', moved: 'Перемещено',
};
const REASON: Readonly<Record<string, string>> = {
  SPEC_NOT_PARSED: 'Полный читаемый источник СО не подтверждён. Дождитесь готовности профилей страниц и проверьте таблицы или сканы. Выводов об удалённых позициях нет.',
  SPEC_SOURCE_INCOMPLETE: 'Исходный текст или структура СО неполны. Полное сравнение, добавления и удаления не подтверждены.',
  SPEC_ANSWER_UNCONFIRMED: 'Извлечённые позиции не прошли программную сверку с источником. Подтверждённого полного результата нет.',
  SPEC_STORED_ANSWER_UNCONFIRMED: 'Сохранённое извлечение неполно или не подтверждено. Его нельзя считать полной спецификацией.',
  SPEC_NOT_READ: 'Полное извлечение позиций ещё не выполнено. Отсутствие готового результата не означает отсутствие изменений.',
};

function SpecificationSource({ page, side, onClose }: { readonly page: ComparisonPageRef; readonly side: string; readonly onClose: () => void }) {
  const valid = Number.isSafeInteger(page.page_number) && page.page_number > 0 && page.version_uid !== '';
  const document = useEvidenceDocument(valid ? page.version_uid : null);
  const url = document.objectUrl !== null && valid ? pdfPageUrl(document.objectUrl, page.page_number) : null;
  return <section aria-label="Исходная страница спецификации"><p>Сторона {side} · физическая страница PDF {page.page_number}. Версия: <code>{page.version_uid}</code>.</p><button type="button" className="am-button am-button--quiet" onClick={onClose}>Закрыть исходную страницу</button>
    {!valid ? <p>Точный переход недоступен: исходная страница или версия не подтверждены.</p> : null}
    {document.isLoading ? <p role="status">Загружается исходный PDF…</p> : null}
    {document.error ? <p role="status">Исходный PDF не открылся. <button type="button" onClick={document.refetch}>Повторить</button></p> : null}
    {url === null ? null : <><p><a href={url} target="_blank" rel="noopener noreferrer">Открыть PDF отдельно на странице {page.page_number}</a></p><object key={`${page.version_uid}:${page.page_number}`} data={url} type="application/pdf" aria-label={`Спецификация ${side}, физическая страница ${page.page_number}`} style={{ width: '100%', minHeight: 520 }}><p>Встроенный просмотр недоступен; откройте PDF по ссылке.</p></object><p>Переход по физической странице, без подсветки координат. Сверяйте номер страницы в PDF-просмотрщике.</p></>}
  </section>;
}

function SpecificationExports({ item }: { readonly item: ComparisonSpecification }) {
  const active = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  useEffect(() => () => { active.current?.abort(); active.current = null; }, []);
  const download = async (format: SpecificationReportFormat) => {
    if (active.current !== null) return;
    const controller = new AbortController(); active.current = controller;
    setBusy(true); setFailure(null); setStatus('Читаем все страницы сохранённых изменений…');
    try {
      const report = await readSpecificationReport(item.transition_id, { signal: controller.signal,
        onProgress: (progress) => { if (active.current === controller) setStatus(`Получено позиций API: ${progress.received}; страниц API: ${progress.pages}. Это чтение выгрузки, не пакеты модели.`); } });
      const file = formatSpecificationReport(report, format);
      if (active.current !== controller || controller.signal.aborted) return;
      deliverDownload(browserDownloadSink(), new Blob([file.content], { type: file.mediaType }), file.fileName);
      setStatus(`Выгрузка полученной API-проекции подготовлена: ${report.changes.length} изменений позиций.`);
    } catch (error) {
      if (active.current !== controller) return;
      if (controller.signal.aborted || error instanceof Error && error.name === 'AbortError') setStatus('Чтение выгрузки отменено. Файл не скачан.');
      else { setStatus(null); setFailure(error instanceof SpecificationReportError || error instanceof Error && error.message.startsWith('Выгрузка API-проекции') ? error.message : comparisonFailure(error).detail); }
    } finally { if (active.current === controller) { active.current = null; setBusy(false); } }
  };
  return <section aria-label="Выгрузки полученной спецификации"><h5>Сохранённые изменения позиций</h5><p>Выгрузка читает все страницы сохранённых изменений текущей API-проекции. Поля, сокращённые контрактом и отмеченные многоточием, не восстанавливаются; полный исходный PDF проверяется отдельно. Это не полный raw-источник и не заключение инженера.</p>
    {(['json', 'csv', 'html'] as const).map((format) => <button type="button" className="am-button am-button--quiet am-button--small" key={format} disabled={busy} onClick={() => void download(format)}>{format.toUpperCase()} · все полученные изменения</button>)}
    {busy ? <button type="button" className="am-button am-button--quiet" onClick={() => active.current?.abort()}>Отменить выгрузку</button> : null}
    {status === null ? null : <p role="status">{status}</p>}{failure === null ? null : <p role="alert">{failure}</p>}
  </section>;
}

function ChangeList({ transitionId, complete }: { readonly transitionId: ComparisonTransitionId; readonly complete: boolean }) {
  const [cursor, setCursor] = useState<Cursor | undefined>();
  const [source, setSource] = useState<{ readonly page: ComparisonPageRef; readonly side: string } | null>(null);
  const query = useQuery({
    queryKey: [...COMPARISON_KEYS.all, 'specification-changes', transitionId, cursor],
    queryFn: async () => (await listComparisonSpecificationChanges({ path: { comparison_transition_id: transitionId }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data,
  });
  const nextCursor = query.data?.page.next_cursor;
  return <div aria-label="Изменения спецификации">
    {source === null ? null : <SpecificationSource key={`${source.page.version_uid}:${source.page.page_number}`} page={source.page} side={source.side} onClose={() => setSource(null)} />}
    {query.isPending ? <p role="status">Читаем позиции…</p> : null}
    {query.error === null ? null : <p role="alert">{comparisonFailure(query.error).detail}</p>}
    <ul>{query.data?.items.map((change) => <li key={change.change_id} data-spec-change={change.change_id}>
      <strong>{KINDS[change.kind] ?? change.kind}</strong>{change.text === undefined ? '' : ` · ${change.text}`}
      {change.fields.length === 0 ? null : <ul>{change.fields.map((field, index) => <li key={`${field.field}-${index}`}>
        {specFieldLabel(field.field)}: {field.was ?? '—'} → {field.now ?? '—'}
      </li>)}</ul>}
      <details><summary>Сохранённые позиции и исходные страницы</summary>{([['A · было', change.old], ['B · стало', change.new]] as const).map(([side, position]) => <section key={side}><h6>{side}</h6>{position === undefined ? <p>Позиция этой стороны не передана.</p> : <><p>{position.pos ? `Поз. ${position.pos} · ` : ''}{position.name}</p><p>Марка: {position.mark ?? '—'} · количество: {position.quantity ?? '—'} {position.unit ?? ''}.</p>{position.ambiguous ? <p>Тип строки неоднозначен; требуется проверка исходного документа.</p> : null}{position.page === undefined ? <p>Привязка к исходной странице отсутствует.</p> : <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setSource({ page: position.page!, side })}>Открыть PDF {side}, стр. {position.page.page_number}</button>}</>}</section>)}</details>
    </li>)}</ul>
    {query.data?.items.length === 0 ? <p>{complete ? 'В сохранённом полном сравнении изменения позиций не выявлены.' : 'Подтверждённый полный результат не получен. Пустой список не означает отсутствие изменений позиций.'}</p> : null}
    {cursor === undefined ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(undefined)}>К началу</button>}
    {nextCursor === null || nextCursor === undefined ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(nextCursor)}>Следующие позиции</button>}
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
      {item.phase === undefined ? '' : ` · этап: ${SPEC_PHASE_LABELS[item.phase]}`}</p>
    <p>Метод сохранённого результата: {SPEC_METHOD_LABELS[item.method]}.</p>
    {[['A', item.coverage_a], ['B', item.coverage_b]].map(([side, value]) => {
      if (typeof value !== 'object' || value === null) return null;
      return <p key={String(side)} className="am-note">Охват {String(side)}: блоков {value.blocks_covered}/{value.blocks_total}, строк {value.rows_total}, не разобрано {value.rows_unresolved}.</p>;
    })}
    <p className="am-note">Охват показывает сохранённые блоки и строки. Большой источник свежего плана разбирается по частям; отдельные счётчики пакетов этим API не передаются. Незавершённые блоки и строки не объявляются отсутствующими.</p>
    {item.state === 'not_applicable' ? <p className="am-note">В текущих профилях не определены читаемые страницы полной СО. Это не подтверждает отсутствие спецификации в сканах или ещё не подготовленных страницах.</p> : null}
    {item.reason === undefined ? null : <><p className="am-note">{REASON[item.reason] ?? 'Сохранено ограничение обработки. Полнота результата не подтверждена.'}</p><details><summary>Техническая причина</summary><code>{item.reason}</code></details></>}
    {item.state === 'incomplete' && item.comparison_id === undefined ? <p>Новое задание не создавалось. Показана готовность сохранённых источников и извлечений; при этом чтении новых обращений к модели не выполнялось. <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => { void client.invalidateQueries({ queryKey: COMPARISON_KEYS.all }); }}>Обновить готовность источников</button></p> : null}
    {item.totals === undefined ? null : <p>{Object.entries(item.totals).map(([kind, count]) => `${KINDS[kind] ?? kind}: ${count}`).join(' · ')}</p>}
    <p className="am-note">ИИ-результат не подтверждён инженером. В сравнение входят распознанные позиции; неполные стороны не объявляются отсутствующими.</p>
    {mayAct && !active && item.state !== 'not_applicable' ? <button type="button" className="am-button am-button--small" onClick={() => void readEstimate()} disabled={estimateCall.isPending}>Оценить сравнение СО</button> : null}
    {mayAct && active && item.job_id !== undefined ? <button type="button" className="am-button am-button--quiet am-button--small" disabled={cancel.isPending} onClick={() => cancel.mutate()}>Отменить сравнение СО</button> : null}
    {item.state === 'completed' || item.state === 'incomplete' ? <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setChanges(!changes)}>{changes ? 'Скрыть позиции' : 'Показать изменения позиций'}</button> : null}
    {cancel.error === null ? null : <p role="alert">{comparisonFailure(cancel.error).detail}</p>}
    {dialog ? <EstimatePanel title="Полные спецификации (СО)" consentKind="spec" confirmLabel="Запустить сравнение СО"
      estimate={estimate} loading={estimateCall.isPending} failure={failure === null ? null : comparisonFailure(failure)}
      allowLocalAssembly={estimate?.method === 'spec' && estimate.calls === 0 && estimate.units > 0}
      agreedDigest={agreed} busy={start.isPending} onAgree={(on) => setAgreed(on ? estimate?.estimate_digest ?? null : null)}
      onConfirm={() => start.mutate()} onCancel={() => { setDialog(false); setAgreed(null); }}
      intro={<p>Отдельное задание сравнит целые спецификации этого перехода. Сохранённые совместимые ответы используются повторно.</p>} /> : null}
    {item.state === 'completed' || item.state === 'incomplete' ? <SpecificationExports item={item} /> : null}
    {changes ? <ChangeList key={item.comparison_id ?? item.transition_id} transitionId={item.transition_id} complete={item.state === 'completed'} /> : null}
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
  const nextCursor = query.data?.page.next_cursor;
  return <div data-whole-specifications="" onClick={(event) => event.stopPropagation()}>
    <button type="button" className="am-button am-button--quiet am-button--small" aria-expanded={open} onClick={() => setOpen(!open)}>Полные спецификации (СО)</button>
    {open ? <section role="group" aria-label="Полные спецификации серии">
      <p className="am-note">Проверка СО запускается отдельно с оценкой и согласием. Готовый результат входит в новую сводку MD.</p>
      {query.isPending ? <p role="status">Читаем спецификации…</p> : null}
      {query.error === null ? null : <p role="alert">{comparisonFailure(query.error).detail}</p>}
      {query.data?.items.map((item) => <SpecificationRow key={item.transition_id} item={item} mayAct={mayAct} />)}
      {query.data?.items.length === 0 ? <p>В серии нет листов спецификации.</p> : null}
      {cursor === undefined ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(undefined)}>К началу переходов</button>}
      {nextCursor === null || nextCursor === undefined ? null : <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(nextCursor)}>Следующие переходы</button>}
      <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => { void client.invalidateQueries({ queryKey: COMPARISON_KEYS.all }); }}>Обновить результат и сводку</button>
    </section> : null}
  </div>;
}
