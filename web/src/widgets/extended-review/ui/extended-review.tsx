'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { getExtendedRunReview, portalBlockCropUrl } from '@/shared/api';
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
  running: 'Выполняется', completed: 'Завершён', partial: 'Частичное покрытие',
  failed: 'Не завершён', unavailable: 'Недоступен для этих входных данных',
};
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

export function ExtendedReview({ runId, active }: { runId: string; active: boolean }) {
  const query = useQuery({
    queryKey: ['extended-run-review', runId],
    queryFn: async () => (await getExtendedRunReview({ path: { run_id: runId } })).data,
    refetchInterval: (reading) => active && (!reading.state.data || ['running', 'not_started'].includes(reading.state.data.status)) ? 2500 : false,
    retry: false,
  });
  if (query.isPending) return <LoadingState what="предварительный обзор блоков" />;
  if (query.isError) return <section aria-label="Предварительный обзор блоков"><h2>Предварительный обзор блоков</h2><p role="status">Не удалось прочитать обзор. <button type="button" onClick={() => void query.refetch()}>Повторить</button></p></section>;
  const reading = query.data;
  if (reading.status === 'not_started') return null;
  const result = object(reading.result);
  const coverage = object(result?.coverage);
  const sources = objects(result?.sources);
  const observations = objects(result?.observations);
  return <section aria-label="Предварительный обзор блоков" data-extended-review={reading.status}>
    <h2>Предварительный обзор блоков</h2>
    <p><strong>{labels[reading.status] ?? 'Состояние неизвестно'}</strong>. Изображения и текст исследованы в ограниченном окне. Это наблюдения для экспертной сверки, а не подтверждённые нарушения или решения эксперта.</p>
    {coverage && <p>Исследовано блоков: <strong>{count(coverage.blocks_processed)}</strong> из {count(coverage.blocks_total)}. В одобренном окне: {count(coverage.blocks_selected)}. Ещё не исследовано или недоступно: <strong>{count(coverage.blocks_remaining)}</strong>.</p>}
    {Array.isArray(result?.warnings) && result.warnings.length > 0 && <ul>{result.warnings.map((warning, i) => <li key={i}>{warningLabels[text(warning)] ?? 'Обзор имеет ограничение или ошибку; проверьте источники и состояние прогона.'}</li>)}</ul>}
    {observations.length === 0 ? <p>Предварительные наблюдения не получены. Это не подтверждение отсутствия проблем в документе.</p> : <ol>{observations.map((item, index) => <li key={text(item.observation_id) || index}>
      <h3>{text(item.title)}</h3><p>{text(item.description)}</p>
      {object(item.norm_assessment) && <aside data-norm-model-review="provisional"><strong>Модельная сверка по цитате; нужна проверка эксперта</strong><p>{assessmentLabels[text(object(item.norm_assessment)?.relation)] ?? 'Результат требует проверки'}</p><p>{text(object(item.norm_assessment)?.explanation)}</p><ul>{objects(object(item.norm_assessment)?.citations).map((citation, n) => <li key={text(citation.paragraph_id) || n}><code>{text(citation.paragraph_id)}</code><blockquote>{text(citation.quote)}</blockquote></li>)}</ul><small>Действующая редакция и применимость нормы не подтверждены.</small></aside>}
      <p>{normLabels[text(item.norm_status)] ?? 'Нормативные основания требуют проверки'}</p>
      {objects(item.norm_candidates).length > 0 && <ul>{objects(item.norm_candidates).map((norm, n) => <li key={text(norm.paragraph_id) || n}><strong>{text(norm.designation)}</strong>{text(norm.document_id) && <>{' — '}<Link href={routes.normDocument(text(norm.document_id))}>Открыть документ нормы</Link></>}{text(norm.clause_number) && `, п. ${text(norm.clause_number)}`} — стр. {text(norm.page_label) || count(norm.page_label)}<blockquote>{text(norm.quote)}</blockquote><small>Кандидат из корпуса, актуальность и применимость не подтверждены.</small></li>)}</ul>}
      <details><summary>Источники наблюдения</summary><ul>{(Array.isArray(item.source_ids) ? item.source_ids : []).map((sourceId, n) => {
        const source = sources.find((s) => s.source_id === sourceId);
        return <li key={text(sourceId) || n}>Страница {count(source?.page_number)}; {source?.kind === 'image' ? 'изображение блока' : 'текстовое наблюдение'} <code>{text(sourceId)}</code>{source?.quote ? <blockquote>{text(source.quote)}</blockquote> : null}{source?.kind === 'image' && text(result?.version_uid) && text(sourceId) ? <SourceCrop versionUid={text(result?.version_uid)} blockId={text(sourceId)} page={count(source.page_number)} /> : null}{source?.crop_sha256 ? <small> SHA256: <code>{text(source.crop_sha256)}</code></small> : null}</li>;
      })}</ul></details>
    </li>)}</ol>}
    {coverage && objects(coverage.skipped).length > 0 && <details><summary>Непроверенные блоки ({objects(coverage.skipped).length})</summary><ul>{objects(coverage.skipped).map((item, i) => <li key={text(item.block_id) || i}>Стр. {count(item.page_number)}, <code>{text(item.block_id)}</code> — {item.reason === 'outside_approved_window' ? 'за пределами одобренного окна' : 'изображение или геометрия недоступны'}</li>)}</ul></details>}
  </section>;
}
