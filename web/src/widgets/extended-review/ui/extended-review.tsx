'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { getExtendedRunReview, portalBlockCropUrl } from '@/shared/api';
import type { ExtendedRunReview } from '@/shared/api';
import { LoadingState } from '@/shared/ui';
import { routes } from '@/shared/lib';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null;
}
function objects(value: unknown): RecordValue[] {
  return Array.isArray(value) ? value.flatMap((v) => { const item = object(v); return item === null ? [] : [item]; }) : [];
}
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
const labels: Record<string, string> = {
  not_started: 'Ожидает начала', queued: 'Запланирован', skipped: 'Пропущен',
  running: 'Выполняется', completed: 'Завершён', partial: 'Частичное покрытие',
  failed: 'Не завершён', unavailable: 'Недоступен для этих входных данных',
};
const procedureLabels: Record<string, string> = { queued: 'Запланировано', running: 'Выполняется', completed: 'Завершено',
  partial: 'Частично', failed: 'Ошибка', unavailable: 'Недоступно', skipped: 'Пропущено' };
const reasonLabels: Record<string, string> = {
  not_in_accepted_policy: 'В принятом согласии этого прогона полная цепочка не была предусмотрена. Для неё нужен новый прогон со свежей оценкой и согласием.',
  legacy_policy_no_v2_workflow: 'Этот прогон использует прежнюю политику обзора. Полная цепочка не добавляется к уже принятому согласию; для неё нужен новый прогон.',
  legacy_consent: 'Прогон принят по прежнему согласию. Полная цепочка в нём не планировалась.',
  source_preparation_failed: 'Подготовка исходных материалов не завершилась; расширенные процедуры не могли выполниться.',
  text_analysis_failed: 'Базовый текстовый анализ не завершился; расширенные процедуры не могли выполниться.',
  provider_binding_unavailable: 'Исполнитель для принятого задания недоступен.',
  provider_outcome_unknown: 'Результат обращения к исполнителю неизвестен. Повторная оплата автоматически не выполняется.',
  missing_artifact: 'Финальная запись результата ещё не получена.',
};
const FINAL_STATES = new Set(['completed', 'partial', 'failed', 'unavailable', 'skipped']);
export const MAX_TERMINAL_REVIEW_READS = 8;

/** A planned receipt is visible immediately, but cannot end terminal polling. */
export function extendedReviewDefinitive(reading: ExtendedRunReview | undefined): boolean {
  if (reading === undefined) return false;
  const result = object(reading.result);
  const procedures = objects(result?.procedures);
  if (procedures.some((item) => !FINAL_STATES.has(text(item.status)))) return false;
  return FINAL_STATES.has(reading.status);
}

export function extendedReviewPollInterval(active: boolean, terminalReads: number, reading: ExtendedRunReview | undefined): number | false {
  return !extendedReviewDefinitive(reading) && (active || terminalReads < MAX_TERMINAL_REVIEW_READS) ? 2500 : false;
}
const normLabels: Record<string, string> = {
  candidates: 'Найдены кандидаты нормативных ссылок — требуется проверка эксперта',
  not_found: 'Подходящие нормативные ссылки не найдены', unavailable: 'Нормативные основания ещё не проверены или недоступны',
};
const assessmentLabels: Record<string, string> = { supports: 'Цитата предварительно поддерживает замечание', contradicts: 'Цитата предварительно противоречит замечанию', insufficient: 'Цитаты недостаточно для вывода' };
const warningLabels: Record<string, string> = {
  remaining_blocks_not_reviewed: 'Часть блоков находится за пределами одобренного окна и не исследована.',
  geometry_blocks_not_available: 'Для части блоков нет подтверждённого изображения.',
  no_image_blocks_available: 'Нет доступных изображений блоков для визуального обзора.',
  merge_omitted_sources_retained: 'Не включённые в модельный свод исходные наблюдения сохранены отдельно.',
  text_observations_outside_merge_window: 'Часть текстовых наблюдений находится за пределами окна свода.',
  page_context_truncated: 'Текстовый контекст страниц ограничен по размеру; обзор не охватывает весь текст страницы.',
  norm_lookup_window_exhausted: 'Исчерпано окно поиска по корпусу; часть нормативных оснований не проверялась.',
  merge_context_truncated: 'Для свода использованы сокращённые описания; подробные источники требуют экспертной сверки.',
};

function SourceCrop({ versionUid, blockId, page }: { versionUid: string; blockId: string; page: string }) {
  const [failed, setFailed] = useState(false);
  const src = portalBlockCropUrl(versionUid, blockId);
  return <figure>{failed ? <p role="status">Изображение блока недоступно.</p> : <img src={src} alt={`Исходный блок на странице ${page}`} loading="lazy" decoding="async" style={{ maxWidth: '100%', maxHeight: 400, objectFit: 'contain' }} onError={() => setFailed(true)} />}<figcaption><a href={src} target="_blank" rel="noopener noreferrer">Открыть исходный фрагмент целиком</a></figcaption></figure>;
}

export function ExtendedReview({ runId, active, projectUid }: { runId: string; active: boolean; projectUid?: string }) {
  const activeRef = useRef(active);
  activeRef.current = active;
  const wasActive = useRef(active);
  const [terminalReads, setTerminalReads] = useState(0);
  const query = useQuery({
    queryKey: ['extended-run-review', runId],
    queryFn: async () => {
      try { return (await getExtendedRunReview({ path: { run_id: runId } })).data; }
      finally { if (!activeRef.current) setTerminalReads((value) => value + 1); }
    },
    refetchInterval: (reading) => extendedReviewPollInterval(active, terminalReads, reading.state.data),
    retry: false,
  });
  useEffect(() => {
    if (wasActive.current && !active) { setTerminalReads(0); void query.refetch(); }
    wasActive.current = active;
  }, [active, query.refetch]);
  if (query.isPending) return <LoadingState what="предварительный обзор блоков" />;
  if (query.isError && query.data === undefined) return <section aria-label="Полная цепочка анализа"><h2>Полная цепочка анализа</h2><p role="status">Не удалось прочитать состояние процедур. <button type="button" onClick={() => { setTerminalReads(0); void query.refetch(); }}>Повторить</button></p></section>;
  if (query.data === undefined) return null;
  return <>
    {query.isError ? <p role="status">Не удалось обновить состояние. Ниже последняя полученная запись.</p> : null}
    <ExtendedReviewView reading={query.data} {...(projectUid === undefined ? {} : { projectUid })} />
    {!active && terminalReads >= MAX_TERMINAL_REVIEW_READS && !extendedReviewDefinitive(query.data) ? <p role="status">Финальная запись процедур пока не получена. Завершение расширенного анализа не подтверждено.</p> : null}
    <button type="button" className="am-button am-button--quiet" disabled={query.isFetching} onClick={() => { setTerminalReads(0); void query.refetch(); }}>Обновить полный анализ</button>
  </>;
}

export function ExtendedReviewView({ reading, projectUid }: { reading: ExtendedRunReview; projectUid?: string }) {
  const result = object(reading.result);
  const procedures = objects(result?.procedures);
  const v2 = result?.workflow_version === 'extended-review-v2';
  const coverage = object(result?.coverage);
  const sources = objects(result?.sources);
  const observations = objects(result?.observations);
  return <section aria-label={v2 ? 'Полная цепочка анализа' : 'Предварительный обзор блоков'} data-extended-review={reading.status} data-workflow-version={text(result?.workflow_version)}>
    <h2>{v2 ? 'Полная цепочка анализа · расширенные процедуры' : 'Предварительный обзор блоков'}</h2>
    <p><strong>{labels[reading.status] ?? 'Состояние неизвестно'}</strong>. Изображения и текст проверяются в ограниченном одобренном окне. Это наблюдения для экспертной сверки, а не подтверждённые нарушения или решения эксперта.</p>
    {typeof result?.reason === 'string' ? <p role="status">{reasonLabels[result.reason] ?? 'Сервер сообщил ограничение выполнения; полное завершение не подтверждено.'}</p> : null}
    {v2 ? <>
      <p>Продолжение базовых этапов. Ход расширенных процедур показан ниже.</p>
      {procedures.length === 0 ? <p>План расширенных процедур ещё не получен.</p> : <ol aria-label="План полного анализа" data-extended-procedure-plan="">
        {procedures.map((procedure, index) => <li key={text(procedure.id) || index} data-extended-procedure={text(procedure.id)} data-procedure-status={text(procedure.status)}>
          <strong>{text(procedure.title) || 'Название процедуры не передано'}</strong> · {procedureLabels[text(procedure.status)] ?? 'Состояние не передано'}
          {text(procedure.reason) ? <p>{reasonLabels[text(procedure.reason)] ?? 'Есть ограничение выполнения; проверьте источники и состояние прогона.'}</p> : null}
        </li>)}
      </ol>}
    </> : procedures.length === 0 && result?.reason === undefined ? <p>Полная цепочка для этого прогона не подтверждена сервером. Историческим прогонам новые процедуры не приписываются.</p> : null}
    {coverage && <p>Исследовано блоков: <strong>{count(coverage.blocks_processed)}</strong> из {count(coverage.blocks_total)}. В одобренном окне: {count(coverage.blocks_selected)}. Ещё не исследовано или недоступно: <strong>{count(coverage.blocks_remaining)}</strong>.</p>}
    {Array.isArray(result?.warnings) && result.warnings.length > 0 && <ul>{result.warnings.map((warning, i) => <li key={i}>{warningLabels[text(warning)] ?? 'Обзор имеет ограничение или ошибку; проверьте источники и состояние прогона.'}</li>)}</ul>}
    {observations.length === 0 ? <p>Предварительные наблюдения не получены. Это не подтверждение отсутствия проблем в документе.</p> : <ol>{observations.map((item, index) => <li key={text(item.observation_id) || index}>
      <h3>{text(item.title)}</h3><p>{text(item.description)}</p>
      {object(item.norm_assessment) && <aside data-norm-model-review="provisional"><strong>Модельная сверка по цитате; нужна проверка эксперта</strong><p>{assessmentLabels[text(object(item.norm_assessment)?.relation)] ?? 'Результат требует проверки'}</p><p>{text(object(item.norm_assessment)?.explanation)}</p><ul>{objects(object(item.norm_assessment)?.citations).map((citation, n) => <li key={text(citation.paragraph_id) || n}><code>{text(citation.paragraph_id)}</code><blockquote>{text(citation.quote)}</blockquote></li>)}</ul><small>Действующая редакция и применимость нормы не подтверждены.</small></aside>}
      <p>{normLabels[text(item.norm_status)] ?? 'Нормативные основания требуют проверки'}</p>
      {objects(item.norm_candidates).length > 0 && <ul>{objects(item.norm_candidates).map((norm, n) => <li key={text(norm.paragraph_id) || n}><strong>{text(norm.designation)}</strong>{text(norm.document_id) && <>{' — '}<Link href={routes.normDocument(text(norm.document_id))}>Открыть документ нормы</Link></>}{text(norm.clause_number) && `, п. ${text(norm.clause_number)}`} — стр. {text(norm.page_label) || count(norm.page_label)}<blockquote>{text(norm.quote)}</blockquote><small>Кандидат из корпуса, актуальность и применимость не подтверждены.</small></li>)}</ul>}
      <details><summary>Источники наблюдения</summary><ul>{(Array.isArray(item.source_ids) ? item.source_ids : []).map((sourceId, n) => {
        const source = sources.find((s) => s.source_id === sourceId);
        const native = source?.source_type === 'native_page' || source?.source_kind === 'native_page';
        const version = text(source?.version_uid) || text(result?.version_uid);
        const portal = source?.kind === 'image' && !native && (source?.source_type === undefined || source.source_type === 'portal_block');
        return <li key={text(sourceId) || n}>Страница {count(source?.page_number)}; {native ? 'страница PDF' : source?.kind === 'image' ? 'изображение блока' : 'текстовое наблюдение'} <code>{text(sourceId)}</code>
          {source?.quote ? <blockquote>{text(source.quote)}</blockquote> : null}
          {native ? <p data-native-page-source="">Исходная версия PDF: <code>{version || 'Не передана'}</code>. {projectUid && version ? <Link href={routes.version(projectUid, version)}>Открыть исходную версию PDF</Link> : 'Для просмотра откройте PDF указанной версии.'}</p> : null}
          {portal && version && text(sourceId) ? <SourceCrop versionUid={version} blockId={text(sourceId)} page={count(source?.page_number)} /> : null}
          {source?.crop_sha256 ? <small> SHA256: <code>{text(source.crop_sha256)}</code></small> : null}
        </li>;
      })}</ul></details>
    </li>)}</ol>}
    {coverage && objects(coverage.skipped).length > 0 && <details><summary>Непроверенные блоки ({objects(coverage.skipped).length})</summary><ul>{objects(coverage.skipped).map((item, i) => <li key={text(item.block_id) || i}>Стр. {count(item.page_number)}, <code>{text(item.block_id)}</code> — {item.reason === 'outside_approved_window' ? 'за пределами одобренного окна' : 'изображение или геометрия недоступны'}</li>)}</ul></details>}
  </section>;
}
