'use client';

import { useEffect, useRef, useState } from 'react';
import type { ExtendedRunReview, VersionUid } from '@/shared/api';
import { formatExtendedRunReport } from '@/entities/audit-run';
import type { ExtendedReportFormat } from '@/entities/audit-run';
import { buildEvidencePackage, EvidencePackageError } from '@/features/export-evidence-package';
import { browserDownloadSink, deliverDownload } from '@/features/export-run';
import styles from './extended-review.module.css';

const PHASE: Readonly<Record<string, string>> = { preparing: 'Подготовка пакета', sources: 'Получение исходного PDF', packaging: 'Сборка ZIP' };
const FORMATS: readonly ExtendedReportFormat[] = ['md', 'html', 'json', 'xlsx'];
function versionOf(reading: ExtendedRunReview): string {
  const result = reading.result;
  if (typeof result !== 'object' || result === null || Array.isArray(result)) return '';
  const version = (result as Record<string, unknown>).version_uid;
  return typeof version === 'string' ? version : '';
}

export function ReportPackage({ reading }: { readonly reading: ExtendedRunReview }) {
  const active = useRef<AbortController | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const version = versionOf(reading);
  useEffect(() => () => { active.current?.abort(); active.current = null; }, []);
  const download = async () => {
    if (active.current !== null || !version) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true); setFailure(null); setProgress('Подготовка четырёх полных форматов отчёта…');
    try {
      // Snapshot this complete reading; view filters and later polling cannot change it.
      const reports = FORMATS.map((format) => {
        if (controller.signal.aborted) throw new DOMException('Отменено', 'AbortError');
        const report = formatExtendedRunReport(reading, format);
        return { name: report.fileName, content: report.content, mediaType: report.mediaType };
      });
      const result = await buildEvidencePackage({
        fileName: `analysis-${reading.run_id}-with-source.zip`, kind: 'section-analysis', runId: reading.run_id,
        reports, sources: [{ versionUid: version as VersionUid, side: 'SOURCE' }], signal: controller.signal,
        onProgress: (next) => { if (active.current === controller) setProgress(`${PHASE[next.phase] ?? 'Подготовка пакета'} · ${next.completed} из ${next.total}`); },
      });
      if (controller.signal.aborted) throw new DOMException('Отменено', 'AbortError');
      if (active.current !== controller) return;
      deliverDownload(browserDownloadSink(), result.blob, result.fileName);
      setProgress('ZIP подготовлен; загрузка передана браузеру.');
    } catch (error) {
      if (active.current !== controller) return;
      if (controller.signal.aborted || error instanceof Error && error.name === 'AbortError') setProgress('Подготовка ZIP отменена. Пакет не скачивался.');
      else {
        setProgress(null);
        setFailure(error instanceof EvidencePackageError || error instanceof Error && error.message.startsWith('Технический XLSX:')
          ? error.message : 'Не удалось подготовить полный пакет. Неполный ZIP не скачивается; отдельные форматы отчёта доступны выше.');
      }
    } finally {
      if (active.current === controller) { active.current = null; setBusy(false); }
    }
  };
  return <section aria-label="Пакет отчётов с исходным PDF" className={styles.packagePanel}>
    <h4>Отчёты вместе с исходным документом</h4>
    <p>ZIP включает полные MD, HTML, JSON и технический XLSX текущей записи, исходный PDF и манифест происхождения. Содержимое не зависит от фильтров списка; новые обращения к модели не выполняются.</p>
    <div className={styles.downloads}><button type="button" className="am-button" disabled={busy || !version} onClick={() => void download()}>Скачать ZIP с отчётами и PDF</button>{busy ? <button type="button" className="am-button am-button--quiet" onClick={() => { active.current?.abort(); }}>Отменить подготовку ZIP</button> : null}</div>
    {!version ? <p>В этой записи не указан идентификатор исходной версии PDF. Пакет с документом недоступен; версия не выбирается по имени или первому источнику.</p> : null}
    {progress === null ? null : <p role="status" aria-live="polite">{progress}</p>}
    {failure === null ? null : <p role="alert">{failure}</p>}
  </section>;
}
