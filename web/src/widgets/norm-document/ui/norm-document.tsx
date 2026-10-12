/**
 * One norm document (`W55A-WEB-NORMS`, plan §A3.7): what it is, its canonical paragraphs in
 * order with the unreliable ones MARKED (F-4), and its source PDF at one page.
 *
 * An unreliable paragraph's recognised text did not survive repair. It is shown — the reader
 * should know the clause exists — but marked, with the page to check it against, and it never
 * appears as a search result. The PDF is the browser's own viewer addressed by `#page=N`,
 * the evidence viewer's approach (`OD-09` untaken), and only a document with a confirmed
 * source binding serves one.
 */

import Link from 'next/link';

import type { NormDocument, NormParagraph } from '@/shared/api';
import { routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState, NotApplicableState, UnsupportedState } from '@/shared/ui';
import type { ErrorStateProps } from '@/shared/ui';
import { attributionLabel, clauseLabel, isUnreliable } from '@/entities/norms';
import { pdfPageUrl } from '@/features/open-evidence';

import styles from './norm-document.module.css';

export function NormDocumentFacts({ document }: { readonly document: NormDocument }) {
  return (
    <div className={styles.facts} data-norm-document={document.norm_document_id} data-norm-attribution={document.source_attribution}>
      <p>{document.title}</p>
      <p>Вид документа: {document.doc_type}</p>
      {document.drawn_on === null ? null : <p>Редакция от <time dateTime={document.drawn_on}>{document.drawn_on}</time></p>}
      <p>Страниц в PDF: {document.pdf_page_count}. Абзацев: {document.paragraph_count}.</p>
      {document.unreliable_paragraph_count > 0 ? (
        <p role="note" className="am-note" data-norm-unreliable-count={document.unreliable_paragraph_count}>
          Абзацев с ненадёжно распознанным текстом: {document.unreliable_paragraph_count}. Они отмечены
          ниже; сверяйте их с PDF.
        </p>
      ) : null}
      <p className="am-form__hint">{attributionLabel(document.source_attribution)}</p>
      <p className="am-form__hint">Снимок <code>{document.norms_snapshot_id}</code></p>
    </div>
  );
}

function ParagraphRow({ paragraph, normDocumentId }: { readonly paragraph: NormParagraph; readonly normDocumentId: string }) {
  const unreliable = isUnreliable(paragraph.text_reliability);
  const clause = clauseLabel(paragraph.clause_number);
  return (
    <li
      className={unreliable ? `${styles.paragraph} ${styles.unreliable}` : styles.paragraph}
      data-norm-paragraph={paragraph.norm_paragraph_id}
      data-norm-reliability={paragraph.text_reliability}
      data-norm-kind={paragraph.kind}
    >
      {unreliable ? (
        <p data-norm-unreliable>
          <strong>Текст распознан ненадёжно</strong> — сверьте его с PDF на странице {paragraph.page_label}.
        </p>
      ) : null}
      <p className={styles.text}>
        {clause === null ? null : <strong>{clause} </strong>}
        {paragraph.kind === 'heading' ? <strong>{paragraph.text}</strong> : paragraph.text}
      </p>
      <Link className="am-button am-button--quiet am-button--small" href={routes.normDocument(normDocumentId, paragraph.page_label)}>
        стр. {paragraph.page_label}
      </Link>
    </li>
  );
}

export interface NormParagraphListProps {
  readonly normDocumentId: string;
  readonly items: readonly NormParagraph[];
  readonly onFirst: (() => void) | null;
  readonly onNext: (() => void) | null;
}

export function NormParagraphList({ normDocumentId, items, onFirst, onNext }: NormParagraphListProps) {
  if (items.length === 0 && onFirst === null) {
    return <EmptyState title="В документе нет абзацев" detail="Снимок не содержит ни одного абзаца этого документа." />;
  }
  return (
    <section aria-label="Абзацы документа" className={styles.paragraphs} data-norm-paragraphs={items.length}>
      {items.length === 0 ? (
        <EmptyState title="На этой странице абзацев нет" detail="Вернитесь к началу документа." />
      ) : (
        <ol>{items.map((paragraph) => <ParagraphRow key={paragraph.norm_paragraph_id} paragraph={paragraph} normDocumentId={normDocumentId} />)}</ol>
      )}
      <div className="am-pager">
        {onFirst === null ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onFirst}>
            В начало
          </button>
        )}
        {onNext === null ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={onNext}>
            Дальше
          </button>
        )}
      </div>
    </section>
  );
}

export interface NormPdfProps {
  readonly document: NormDocument;
  /** The page asked for, or `null` when none was. */
  readonly page: number | null;
  /** `blob:` URL of the fetched PDF, or null while it is unavailable. */
  readonly documentUrl: string | null;
  readonly isLoading: boolean;
  readonly error: ErrorStateProps | null;
}

export function NormPdf({ document, page, documentUrl, isLoading, error }: NormPdfProps) {
  if (!document.content_available) {
    return (
      <NotApplicableState
        title="PDF этого документа недоступен"
        detail="У документа нет подтверждённой привязки к исходному файлу, поэтому показан только его текст."
      />
    );
  }
  if (page === null) {
    return (
      <p className="am-note" data-norm-pdf="closed">
        <Link href={routes.normDocument(document.norm_document_id, 1)}>Открыть PDF</Link> — или страницу
        нужного абзаца по ссылке рядом с ним.
      </p>
    );
  }
  if (page > document.pdf_page_count) {
    return (
      <UnsupportedState
        title="Такой страницы в документе нет"
        detail={`В PDF этого документа ${document.pdf_page_count} стр.; запрошена стр. ${page}.`}
      />
    );
  }
  if (error !== null) return <ErrorState {...error} />;
  // Until the bytes are read and their object URL exists, the panel says it is loading;
  // it never draws an empty viewer as if the page were blank.
  if (isLoading || documentUrl === null) return <LoadingState what="PDF документа" />;
  return (
    <object
      className="am-evidence__object"
      data={pdfPageUrl(documentUrl, page)}
      type="application/pdf"
      aria-label={`Страница ${page} документа ${document.designation}`}
      data-viewer-src={pdfPageUrl(documentUrl, page)}
    >
      <p>Этот браузер не умеет показывать PDF внутри страницы.</p>
    </object>
  );
}
