'use client';
import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getExtendedRunReview } from '@/shared/api';
import type { ExtendedRunReview } from '@/shared/api';
import { LoadingState } from '@/shared/ui';
import { formatExtendedRunReport } from '@/entities/audit-run';
import type { ExtendedReportFormat } from '@/entities/audit-run';
import { WindowProgress } from './window-progress';
import { BatchProgress } from './batch-progress';
import { ObservationList } from './observation-list';
import { ReadableReport } from './readable-report';
import { ReportPackage } from './report-package';
import { ConsolidatedObservations } from './consolidated-observations';
import { CoverageBudget } from './coverage-budget';
import { CrossWindowReview } from './cross-window-review';
import { ProjectParameters } from './project-parameters';
import { NormativeContext } from './normative-context';
import { NormativeSearches } from './normative-searches';
import { extendedCandidateCounts } from './extended-review-summary';
import styles from './extended-review.module.css';

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
  corpus_unavailable: 'В этом прогоне нет доступного нормативного корпуса. Проверка ссылок не выполнена.',
  candidate_context_unavailable: 'Для наблюдений не найдены цитаты нормативного корпуса, пригодные для модельной сверки.',
  norm_paragraph_context_changed_requires_consent: 'Реализация нормативного контекста изменилась после согласия. Для новых обращений нужен новый прогон со свежей оценкой.',
  norm_paragraph_context_incomplete: 'Часть исходного нормативного контекста не передана или поисковая цитата не совпала с непрерывным текстом абзаца. Ограничения сохранены в квитанциях; актуальность и применимость требуют сверки.',
};
const FINAL_STATES = new Set(['completed', 'partial', 'failed', 'unavailable', 'skipped']);
export const MAX_TERMINAL_REVIEW_READS = 8;

/** A planned receipt is visible immediately, but cannot end terminal polling. */
export function extendedReviewDefinitive(reading: ExtendedRunReview | undefined): boolean {
  if (reading === undefined) return false;
  const result = object(reading.result);
  const procedures = objects(result?.procedures);
  const global = object(result?.global_cross_window);
  const parameters = object(result?.project_parameters);
  if (parameters !== null && !FINAL_STATES.has(text(parameters.status))) return false;
  if (global !== null && (!FINAL_STATES.has(text(global.status)) || objects(global.procedures).some((item) => !FINAL_STATES.has(text(item.status))))) return false;
  if (procedures.some((item) => !FINAL_STATES.has(text(item.status)))) return false;
  if (objects(result?.windows).some((window) => !FINAL_STATES.has(text(window.status))
    || objects(window.procedures).some((item) => !FINAL_STATES.has(text(item.status))))) return false;
  return FINAL_STATES.has(reading.status);
}

export function extendedReviewPollInterval(active: boolean, terminalReads: number, reading: ExtendedRunReview | undefined): number | false {
  return !extendedReviewDefinitive(reading) && (active || terminalReads < MAX_TERMINAL_REVIEW_READS) ? 2500 : false;
}
const warningLabels: Record<string, string> = {
  native_pdf_page_render_no_ocr: 'Для визуального анализа созданы изображения страниц исходного PDF. Отдельное распознавание текста сканов не выполнялось.',
  portal_text_only_native_page_visuals: 'Portal-набор содержит только текстовые блоки. Для визуального анализа использованы настоящие изображения страниц PDF; это не сегментация портала.',
  remaining_blocks_not_reviewed: 'Часть блоков находится за пределами одобренного окна и не исследована.',
  geometry_blocks_not_available: 'Для части блоков нет подтверждённого изображения.',
  no_image_blocks_available: 'Нет доступных изображений блоков для визуального обзора.',
  merge_omitted_sources_retained: 'Не включённые в модельный свод исходные наблюдения сохранены отдельно.',
  text_observations_outside_merge_window: 'Часть текстовых наблюдений находится за пределами окна свода.',
  page_context_truncated: 'Текстовый контекст страниц ограничен по размеру; обзор не охватывает весь текст страницы.',
  visual_context_bounded_full_text_reviewed: 'Контекст отдельных изображений сокращён; полный текст страниц передан в комплексную сверку по частям.',
  norm_lookup_window_exhausted: 'Исчерпано окно поиска по корпусу; часть нормативных оснований не проверялась.',
  merge_context_truncated: 'Для свода использованы сокращённые описания; подробные источники требуют экспертной сверки.',
};

function ReportDownloads({ reading }: { readonly reading: ExtendedRunReview }) {
  const [failure, setFailure] = useState<string | null>(null);
  const download = (format: ExtendedReportFormat) => {
    setFailure(null);
    try {
      const report = formatExtendedRunReport(reading, format);
      const url = URL.createObjectURL(new Blob([report.content], { type: report.mediaType }));
      try {
        const anchor = document.createElement('a');
        anchor.href = url; anchor.download = report.fileName; anchor.rel = 'noopener';
        document.body.appendChild(anchor); anchor.click(); anchor.remove();
      } finally { URL.revokeObjectURL(url); }
    } catch (error) { setFailure(error instanceof Error && error.message.startsWith('Технический XLSX:') ? error.message : 'Не удалось сформировать выгрузку текущей записи. Обновите данные и повторите; полные данные доступны в JSON.'); }
  };
  return <section id="extended-downloads" aria-label="Скачать отчёт анализа раздела">
    <h3>Отчёт по текущей записи</h3>
    <p>Выгрузка содержит все переданные наблюдения, исходные и исправленные кандидаты, рекомендации, источники и покрытие. Фильтр по модельному принятию или отклонению не применяется. Новые обращения к модели не запускаются.</p>
    <div className={styles.downloads}>
      <button type="button" className="am-button am-button--quiet" onClick={() => download('md')}>Скачать отчёт MD</button>
      <button type="button" className="am-button am-button--quiet" onClick={() => download('html')}>Скачать отчёт HTML</button>
      <button type="button" className="am-button am-button--quiet" onClick={() => download('json')}>Скачать все данные JSON</button>
      <button type="button" className="am-button am-button--quiet" onClick={() => download('xlsx')}>Технический XLSX</button>
    </div>
    <p>Технический XLSX содержит предварительные данные и происхождение, включая исходные и предложенные формулировки. Он не заменяет экспертный экспорт из «Разбора».</p>
    {failure === null ? null : <p role="alert">{failure}</p>}
    <ReportPackage key={reading.run_id} reading={reading} />
  </section>;
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
  if (query.isPending) return <section id="extended-analysis"><LoadingState what="предварительный обзор блоков" /></section>;
  if (query.isError && query.data === undefined) return <section id="extended-analysis" aria-label="Полная цепочка анализа"><h2>Полная цепочка анализа</h2><p role="status">Не удалось прочитать состояние процедур. <button type="button" onClick={() => { setTerminalReads(0); void query.refetch(); }}>Повторить</button></p></section>;
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
  const v3 = result?.workflow_version === 'extended-review-v3';
  const full = v2 || v3;
  const report = object(result?.report);
  const reportStatus = text(report?.status) || text(procedures.find((procedure) => procedure.id === 'report_generation')?.status);
  const coverage = object(result?.coverage);
  const textCoverage = object(result?.text_coverage);
  const fullWindow = result?.review_scope === 'full_document';
  const sources = objects(result?.sources);
  const observations = objects(result?.observations);
  const consolidation = object(result?.consolidation);
  const showGroups = consolidation?.version === 'strict-cross-window-v1' && consolidation.complete === true && Array.isArray(result?.consolidated_observations);
  const counts = extendedCandidateCounts(result);
  return <section id="extended-analysis" className={styles.panel} aria-label={full ? 'Полная цепочка анализа' : 'Предварительный обзор блоков'} data-extended-review={reading.status} data-workflow-version={text(result?.workflow_version)}>
    <h2>{v3 ? 'Анализ раздела · полный расширенный план' : v2 && fullWindow ? 'Полная цепочка анализа · расширенные процедуры' : v2 ? 'Расширенный анализ · предыдущий план' : 'Предварительный обзор блоков'}</h2>
    <p><strong>{labels[reading.status] ?? 'Состояние неизвестно'}</strong>. {fullWindow ? 'План включает все доступные блоки; текст страниц обрабатывается по частям.' : 'Изображения и текст проверяются в ограниченном одобренном окне.'} Это наблюдения для экспертной сверки, а не подтверждённые нарушения или решения эксперта.</p>
    {Array.isArray(result?.observations) ? <dl className={styles.digest} data-extended-analysis-counts=""><div><dt>Предварительные кандидаты</dt><dd>{counts.candidates}</dd></div><div><dt>Рекомендации машинного критика</dt><dd>{counts.criticRecommendations}</dd></div><div><dt>Предложенные исправленные кандидаты</dt><dd>{counts.correctionProposals}</dd></div><div><dt>Источники в текущем своде</dt><dd>{sources.length}</dd></div></dl> : <p>Записи кандидатов и рекомендаций ещё не переданы. Их отсутствие в ответе не подтверждает пустой результат анализа.</p>}
    <p>Эти счётчики относятся к расширенному машинному анализу. Канонические находки и сохранённые решения эксперта рассматриваются отдельно в «Разборе».</p>
    <nav className={styles.toolbar} aria-label="Разделы предварительного отчёта"><a href="#extended-observations">Наблюдения и источники</a>{v3 ? <a href="#extended-window-progress">Прогресс обработки</a> : null}{object(result?.global_cross_window) === null ? null : <a href="#extended-global-cross-window">Сверка между окнами</a>}{object(result?.project_parameters) === null ? null : <a href="#extended-project-parameters">Параметры проекта</a>}{report === null ? null : <a href="#extended-saved-report">Сохранённый отчёт</a>}<a href="#extended-downloads">Полные выгрузки</a></nav>
    {text(result?.section) ? <p>Раздел: <strong>{text(result?.section)}</strong>.</p> : null}
    {v2 ? <p>{fullWindow ? 'Этот прогон принят по плану V2 с обработкой полного документа по частям.' : 'Этот прогон принят по прежнему плану расширенного анализа.'} Новые критика, исправление и подготовка отчёта V3 ему не приписываются; для нового плана нужна свежая оценка и согласие в новом прогоне.</p> : null}
    {v3 ? <p>Рубрики учитывают специфику раздела. Числовые пороги и ссылки из исторических материалов — контекст, а не подтверждённые действующие нормы. Критика и исправление — рекомендации модели, решение остаётся за экспертом.</p> : null}
    {text(result?.rules_sha256) ? <details><summary>Происхождение рубрик раздела</summary><p>Отпечаток набора: <code>{text(result?.rules_sha256)}</code>.</p>{object(result?.source_provenance) ? <pre>{JSON.stringify(result?.source_provenance, null, 2)}</pre> : null}</details> : null}
    {typeof result?.reason === 'string' ? <p role="status">{reasonLabels[result.reason] ?? 'Сервер сообщил ограничение выполнения; полное завершение не подтверждено.'}</p> : null}
    {full ? <>
      <p>Продолжение базовых этапов. Ход расширенных процедур показан ниже.</p>
      {procedures.length === 0 ? <p>План расширенных процедур ещё не получен.</p> : <ol className={styles.procedures} aria-label="План полного анализа" data-extended-procedure-plan="">
        {procedures.map((procedure, index) => <li key={text(procedure.id) || index} data-extended-procedure={text(procedure.id)} data-procedure-status={text(procedure.status)}>
          <strong>{text(procedure.title) || 'Название процедуры не передано'}</strong> · {procedureLabels[text(procedure.status)] ?? 'Состояние не передано'}
          {text(procedure.reason) ? <p>{reasonLabels[text(procedure.reason)] ?? 'Есть ограничение выполнения; проверьте источники и состояние прогона.'}</p> : null}
        </li>)}
      </ol>}
    </> : procedures.length === 0 && result?.reason === undefined ? <p>Полная цепочка для этого прогона не подтверждена сервером. Историческим прогонам новые процедуры не приписываются.</p> : null}
    {v3 ? <WindowProgress windows={result?.windows} progress={result?.window_progress} fallbackVersion={text(result?.version_uid)} {...(projectUid === undefined ? {} : { projectUid })} /> : null}
    {result?.coverage_version === 'batched-v1' ? <BatchProgress batches={result?.batches} coverage={result?.phase_coverage} /> : null}
    {result?.coverage_version === 'batched-v1' ? <CoverageBudget mode={result?.coverage_budget_mode} limits={result?.phase_call_limits} estimatedText={result?.estimated_text_characters} pieceCharacters={result?.comprehensive_piece_characters} /> : null}
    <CrossWindowReview key={reading.run_id} value={result?.global_cross_window} observations={observations} sources={sources} fallbackVersion={text(result?.version_uid)} {...(projectUid === undefined ? {} : { projectUid })} />
    <ProjectParameters key={`parameters:${reading.run_id}`} value={result?.project_parameters} fallbackVersion={text(result?.version_uid)} {...(projectUid === undefined ? {} : { projectUid })} />
    <NormativeContext key={`norm-context:${reading.run_id}`} policy={result?.norm_paragraph_context_policy} receipts={result?.normative_context_receipts} />
    <NormativeSearches key={`norm-searches:${reading.run_id}`} value={result?.norm_lookup_receipts} />
    {v3 && result?.primary_text_status === 'pending' ? <p>Базовый текстовый анализ ещё выполняется. {result.visual_phase_complete === true ? 'Визуальный проход сохранён; свод и последующие проверки ожидают текстовый результат.' : 'Сохранённые визуальные результаты ещё не означают завершения анализа раздела.'}</p> : null}
    {coverage && <p>Исследовано блоков: <strong>{count(coverage.blocks_processed)}</strong> из {count(coverage.blocks_total)}. {fullWindow ? 'В плане' : 'В одобренном окне'}: {count(coverage.blocks_selected)}. Ещё не исследовано или недоступно: <strong>{count(coverage.blocks_remaining)}</strong>.</p>}
    {textCoverage === null ? null : <section data-extended-text-coverage=""><p>Комплексная сверка текста: успешно обработано страниц <strong>{count(textCoverage.pages_processed)}</strong> из {count(textCoverage.pages_total)}. В плане: {count(textCoverage.pages_selected)}. Ещё не обработано или недоступно: <strong>{count(textCoverage.pages_remaining)}</strong>.</p>{typeof textCoverage.characters_total === 'number' ? <p>Известный текстовый объём: {count(textCoverage.characters_processed)} из {count(textCoverage.characters_total)} символов обработано; осталось {count(textCoverage.characters_remaining)}. План может уточняться после подготовки следующих окон.</p> : null}<p>Эти счётчики не подтверждают отсутствие ошибок или экспертную проверку.</p></section>}
    {Array.isArray(result?.warnings) && result.warnings.length > 0 && <ul>{result.warnings.map((warning, i) => <li key={i}>{warningLabels[text(warning)] ?? 'Обзор имеет ограничение или ошибку; проверьте источники и состояние прогона.'}</li>)}</ul>}
    {consolidation !== null && !showGroups ? <p role="status">Группировка повторов в этой записи не подтверждена или не завершена. Ниже показаны исходные наблюдения; все данные сохранены в полных выгрузках.</p> : null}
    {showGroups ? <ConsolidatedObservations key={reading.run_id} groups={result?.consolidated_observations} consolidation={consolidation} observations={observations} rawRecords={result?.observations} sources={sources} fallbackVersion={text(result?.version_uid)} {...(projectUid === undefined ? {} : { projectUid })} />
      : <ObservationList key={reading.run_id} observations={observations} sources={sources} fallbackVersion={text(result?.version_uid)} {...(projectUid === undefined ? {} : { projectUid })} />}
    {coverage && objects(coverage.skipped).length > 0 && <details><summary>Непроверенные блоки ({objects(coverage.skipped).length})</summary><ul>{objects(coverage.skipped).map((item, i) => <li key={text(item.block_id) || i}>Стр. {count(item.page_number)}, <code>{text(item.block_id)}</code> — {item.reason === 'outside_approved_window' ? 'за пределами одобренного окна' : 'изображение или геометрия недоступны'}</li>)}</ul></details>}
    {report === null ? null : <section id="extended-saved-report" aria-label="Состояние отчёта раздела"><h3>Сохранённый отчёт раздела</h3><p>{procedureLabels[reportStatus] ?? 'Состояние не передано'} · записей: {count(report.observation_count)}.</p>
      {text(report.markdown) ? <ReadableReport markdown={text(report.markdown)} /> : null}
      <p>Это предварительный отчёт с ограничениями покрытия и непроверенными нормативными основаниями, не экспертное заключение.</p>
    </section>}
    <ReportDownloads reading={reading} />
  </section>;
}
