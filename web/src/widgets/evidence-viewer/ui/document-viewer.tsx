'use client';

/** @jsxRuntime automatic */

/**
 * «Просмотр PDF» on the version page (`UI-A-27`): the version's own document, drawn page by page, without leaving the page.
 *
 * The original opens the version's PDF in a drawer that rises from the bottom (`.version-pdf-drawer`, 85vh, an `<iframe>` of the
 * browser's reader, created only when the button is pressed). Here the drawer holds the same `PageViewer` the review screen draws
 * its cited pages with (`features/open-evidence`): pdf.js, the page as an image the reader can move and zoom, no toolbar of the
 * browser's. There is nothing to frame — no finding is being cited — so it is the page alone, with ‹ стр. [N] / M › to walk the
 * document (`UIP-S10-01`: the number is a field, as the browser's reader has one) and «Открыть PDF ↗», the whole document in the
 * browser's reader, in a new tab, on this page, as the original's ↗.
 *
 * **It is fetched only when it is opened.** The version page mounts this widget through a `next/dynamic` boundary
 * (`_pages/version-detail/ui/version-pdf-chunk.tsx`) only after the button is pressed, so the chunk, pdf.js and the bytes
 * (`streamDocumentVersionContent`, via `useEvidenceDocument`) are all asked for on that press and never before. The bytes live as long as
 * the drawer: the hook drops them when it unmounts.
 *
 * Two parts, as the other viewers here: `DocumentViewerView` is markup from plain data (the styling census renders it open), and
 * `DocumentViewer` adds the reads and the page the reader is on.
 */

import { useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

import type { VersionUid } from '@/shared/api';
import { ErrorState, LoadingState } from '@/shared/ui';
import { PageViewer, pdfPageUrl, useEvidenceDocument } from '@/features/open-evidence';

import styles from './document-viewer.module.css';

export interface DocumentViewerViewProps {
  /** What the drawer is about, one line in the bar: the document and the version. */
  readonly title: string;
  /** The page shown, from 1. */
  readonly page: number;
  /** How many pages the document has. */
  readonly pageCount: number;
  readonly onPage: (page: number) => void;
  /** The whole document in the browser's own reader on this page, or null while the bytes are not here. */
  readonly externalHref: string | null;
  readonly onClose: () => void;
  /** The page, or the state that stands in its place. */
  readonly children: ReactNode;
}

/** What the page field does with what was typed: the page to be on, and the text the field shows after. */
export interface PageEntry {
  readonly page: number;
  readonly text: string;
}

/**
 * `UIP-S10-01`: the number typed into «стр. [N] / M» when Enter is pressed. A whole number from 1 to `pageCount` is the page to go
 * to; anything else -- nothing, text, 0, a fraction, a sign, a number past the end -- leaves the reader on `current`, and the field
 * says that page again rather than keeping a number the document does not have. The page is never clamped to the nearest one: a
 * typed 99 in a 12-page document is a slip, and turning it into page 12 would show a page nobody asked for.
 */
export function enteredPage(entry: string, current: number, pageCount: number): PageEntry {
  const trimmed = entry.trim();
  if (/^[0-9]{1,7}$/.test(trimmed)) {
    const asked = Number(trimmed);
    if (asked >= 1 && asked <= pageCount) return { page: asked, text: String(asked) };
  }
  return { page: current, text: String(current) };
}

/**
 * The page number as a field. The draft lives here and is thrown away when the page changes (the caller keys it by the page), so a
 * step with ‹ › or a page taken from the field always shows the page the reader is on; leaving the field unsent puts the page back.
 */
function PageField({ page, pageCount, onPage }: { readonly page: number; readonly pageCount: number; readonly onPage: (page: number) => void }) {
  const [draft, setDraft] = useState(String(page));
  return (
    <input
      type="text"
      inputMode="numeric"
      autoComplete="off"
      className={styles.pageField}
      size={Math.max(2, String(pageCount).length)}
      value={draft}
      aria-label={`Номер страницы, из ${pageCount}`}
      title={`Номер страницы: число от 1 до ${pageCount}; переход — клавишей ввода`}
      data-version-pdf-page-field=""
      onChange={(event) => {
        setDraft(event.target.value);
      }}
      onKeyDown={(event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        const next = enteredPage(draft, page, pageCount);
        setDraft(next.text);
        if (next.page !== page) onPage(next.page);
      }}
      onBlur={() => {
        setDraft(String(page));
      }}
    />
  );
}

export function DocumentViewerView({ title, page, pageCount, onPage, externalHref, onClose, children }: DocumentViewerViewProps) {
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    // Esc closes, as it does the dialogs; the pdf.js viewport keeps the arrows and the +/− keys for itself.
    if (event.key === 'Escape') onClose();
  };
  return (
    <section className={styles.drawer} aria-label="Просмотр PDF" data-version-pdf="" onKeyDown={onKeyDown}>
      <header className={styles.bar}>
        <span className={styles.title}>PDF — {title}</span>
        <div className={styles.steps} role="group" aria-label="Страницы документа">
          <button
            type="button"
            className={styles.step}
            onClick={() => onPage(page - 1)}
            disabled={page <= 1}
            aria-label="Предыдущая страница"
            title="Предыдущая страница"
          >
            ‹
          </button>
          <span className={styles.position} data-version-pdf-page={page}>
            {'стр.'}
            <PageField key={page} page={page} pageCount={pageCount} onPage={onPage} />
            {`/ ${pageCount}`}
          </span>
          <button
            type="button"
            className={styles.step}
            onClick={() => onPage(page + 1)}
            disabled={page >= pageCount}
            aria-label="Следующая страница"
            title="Следующая страница"
          >
            ›
          </button>
        </div>
        {externalHref === null ? null : (
          <a className="am-button am-button--quiet am-button--small" href={externalHref} target="_blank" rel="noopener noreferrer" title={`Открыть исходный файл в новой вкладке, в просмотрщике браузера, на странице ${page}`}>
            Открыть PDF ↗
          </a>
        )}
        <button type="button" className={styles.close} onClick={onClose} aria-label="Закрыть просмотр PDF" title="Закрыть">
          ✕
        </button>
      </header>
      <div className={styles.body}>{children}</div>
    </section>
  );
}

export interface DocumentViewerProps {
  readonly versionUid: VersionUid;
  /** The document and the version, as the page names them. */
  readonly title: string;
  /** `DocumentVersion.page_count`: the pages the ‹ › walk. */
  readonly pageCount: number;
  readonly onClose: () => void;
}

export function DocumentViewer({ versionUid, title, pageCount, onClose }: DocumentViewerProps) {
  const document_ = useEvidenceDocument(versionUid);
  const last = Math.max(1, pageCount);
  const [asked, setAsked] = useState(1);
  const page = Math.min(Math.max(1, asked), last);

  return (
    <DocumentViewerView
      title={title}
      page={page}
      pageCount={last}
      onPage={(next) => setAsked(Math.min(Math.max(1, next), last))}
      externalHref={document_.objectUrl === null ? null : pdfPageUrl(document_.objectUrl, page)}
      onClose={onClose}
    >
      {document_.isLoading ? <LoadingState what="PDF версии" /> : null}
      {!document_.isLoading && document_.error !== null && document_.error !== undefined ? (
        <ErrorState
          title="PDF не удалось открыть"
          detail={<p>Байты документа не пришли. Страница версии и её данные от этого не зависят.</p>}
          onRetry={document_.refetch}
        />
      ) : null}
      {document_.objectUrl === null ? null : (
        <PageViewer
          documentUrl={document_.objectUrl}
          pageNumber={page}
          targets={[]}
          activeTargetId={null}
          label={`Страница ${page} документа`}
          fill
        />
      )}
    </DocumentViewerView>
  );
}
