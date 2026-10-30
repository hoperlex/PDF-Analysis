'use client';

import { useState } from 'react';
import Link from 'next/link';
import { portalBlockCropUrl } from '@/shared/api';
import type { VersionUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import { pdfPageUrl, useEvidenceDocument } from '@/features/open-evidence';
import styles from './extended-review.module.css';

type Source = Record<string, unknown>;
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
export function sourcePage(source: Source | undefined): number | null {
  const page = source?.page_number;
  return typeof page === 'number' && Number.isSafeInteger(page) && page > 0 ? page : null;
}
export function sourceKind(source: Source | undefined): string {
  if (source?.source_type === 'native_page' || source?.source_kind === 'native_page') return 'страница PDF';
  if (source?.source_type === 'recognised_text' || source?.quote_source === 'recognised') return 'распознанный текст';
  return source?.kind === 'image' ? 'изображение блока' : 'текстовый источник';
}

export function SourceInspector({ source, fallbackVersion, projectUid, onClose }: {
  readonly source: Source; readonly fallbackVersion: string; readonly projectUid?: string; readonly onClose: () => void;
}) {
  const version = text(source.version_uid) || fallbackVersion;
  const page = sourcePage(source);
  const kind = sourceKind(source);
  const native = source.source_type === 'native_page' || source.source_kind === 'native_page';
  const recognised = source.source_type === 'recognised_text' || source.quote_source === 'recognised';
  const portal = source.kind === 'image' && !native && (source.source_type === undefined || source.source_type === 'portal_block');
  const [showPdf, setShowPdf] = useState(false);
  const [cropFailed, setCropFailed] = useState(false);
  const document = useEvidenceDocument(showPdf && version && page !== null ? version as VersionUid : null);
  const crop = portal && version && text(source.source_id) ? portalBlockCropUrl(version, text(source.source_id)) : null;
  const pageUrl = document.objectUrl !== null && page !== null ? pdfPageUrl(document.objectUrl, page) : null;
  return <section className={styles.sourceInspector} aria-label="Исходная страница и цитата" data-extended-source={text(source.source_id)}>
    <div className={styles.toolbar}><h3>{page === null ? 'Страница не указана' : `Физическая страница PDF ${page}`} · {kind}</h3><button type="button" className="am-button am-button--quiet" onClick={onClose}>Закрыть источник</button></div>
    <p>Источник: <code>{text(source.source_id)}</code>. {version ? <>Версия PDF: <code>{version}</code>.</> : 'Версия PDF не передана.'}</p>
    {text(source.quote) ? <blockquote>{text(source.quote)}</blockquote> : <p>Текстовая цитата этого источника не передана.</p>}
    {recognised ? <p>Это сохранённый распознанный слой. Он показан отдельно от native-текста; точные native-координаты по нему не утверждаются.</p> : null}
    {text(source.crop_sha256) || text(source.artifact_sha256) ? <p>Отпечаток источника SHA256: <code>{text(source.crop_sha256) || text(source.artifact_sha256)}</code>.</p> : null}
    {projectUid && version ? <p><Link href={routes.version(projectUid, version)}>Открыть сведения об исходной версии</Link></p> : null}
    {crop === null ? null : <figure>{cropFailed ? <p role="status">Изображение исходного блока не удалось прочитать.</p> : <img className={styles.crop} src={crop} alt={`Исходное изображение блока${page === null ? '' : ` на физической странице ${page}`}`} onError={() => setCropFailed(true)} />}<figcaption><a href={crop} target="_blank" rel="noopener noreferrer">Открыть изображение блока отдельно</a></figcaption></figure>}
    {page === null || !version ? <p>Для перехода к странице недостаточно номера страницы или идентификатора версии. Адрес источника не выдумывается.</p> : <>
      {!showPdf ? <button type="button" className="am-button" onClick={() => setShowPdf(true)}>Показать физическую страницу PDF {page}</button> : null}
      {document.isLoading ? <p role="status">Загружается исходный PDF…</p> : null}
      {document.error ? <p role="status">Не удалось загрузить исходный PDF. <button type="button" onClick={document.refetch}>Повторить</button></p> : null}
      {pageUrl === null ? null : <><p><a href={pageUrl} target="_blank" rel="noopener noreferrer">Открыть PDF на странице {page} отдельно</a></p><object key={`${version}:${page}`} className={styles.pdfPage} data={pageUrl} type="application/pdf" aria-label={`Исходный PDF, физическая страница ${page}`}><p>Встроенный просмотр PDF недоступен; откройте страницу по ссылке выше.</p></object><p>Навигация по физической странице PDF, без подсветки или утверждения координат. Браузер может показать документ с первой страницы; сверяйте номер в его панели.</p></>}
    </>}
  </section>;
}
