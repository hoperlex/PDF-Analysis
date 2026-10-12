'use client';

/**
 * `/norms/document?id=…&page=…` — one norm document (`W55A-WEB-NORMS`, plan §A3.7).
 *
 * Reached from a search result: «Открыть» names the result's PDF page, and the screen opens
 * the document's PDF there beside its text. The text is the snapshot's canonical paragraphs
 * in order, the unreliable ones marked (F-4). A document whose PDF has no confirmed binding
 * shows its text and says the PDF is unavailable; the PDF is read only when a page is asked
 * for, so opening a document costs two reads, not the whole file.
 *
 * With no `id` the address names no document, and the screen says so — it is the state a
 * cold walk of the application reaches, since only a search hands out a document.
 */

import Link from 'next/link';
import { useState } from 'react';

import type { NormDocument, NormDocumentId } from '@/shared/api';
import { routes } from '@/shared/lib';
import {
  normFailure, useNormContent, useNormDocument, useNormParagraphs, wantsNormPdf,
} from '@/entities/norms';
import { NormDocumentFacts, NormParagraphList, NormPdf } from '@/widgets/norm-document';
import { ErrorState, LoadingState, PageShell, UnsupportedState } from '@/shared/ui';

export interface NormDocumentPageProps {
  /** The `ndoc_` identity from the address, already shape-checked by the route; `null` for none. */
  readonly normDocumentId: string | null;
  /** The PDF page the address asks for, or `null`. */
  readonly page: number | null;
}

function BackToSearch() {
  return <Link className="am-button am-button--quiet" href={routes.norms()}>К поиску по нормам</Link>;
}

function Paragraphs({ normDocumentId }: { readonly normDocumentId: NormDocumentId }) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const paragraphs = useNormParagraphs(normDocumentId, cursor);
  if (paragraphs.isPending) return <LoadingState what="абзацы документа" />;
  if (paragraphs.error !== null) {
    const failure = normFailure(paragraphs.error);
    return (
      <div data-norm-paragraphs-failure={failure.kind}>
        <ErrorState
          title="Абзацы документа не прочитаны"
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={failure.retryable ? () => void paragraphs.refetch() : undefined}
        />
      </div>
    );
  }
  const next = paragraphs.data.page.next_cursor;
  return (
    <NormParagraphList
      normDocumentId={normDocumentId}
      items={paragraphs.data.items}
      onFirst={cursor === undefined ? null : () => setCursor(undefined)}
      onNext={next === null ? null : () => setCursor(next)}
    />
  );
}

/** The PDF at one page, read only here — mounted only when `wantsNormPdf` says so. */
function OpenPdf({ document, page }: { readonly document: NormDocument; readonly page: number }) {
  const content = useNormContent(document.norm_document_id);
  const failure = content.error === null ? null : normFailure(content.error);
  return (
    <NormPdf
      document={document}
      page={page}
      documentUrl={content.objectUrl}
      isLoading={content.isLoading}
      error={failure === null ? null : {
        title: 'PDF документа не прочитан',
        detail: failure.detail,
        correlationId: failure.correlationId,
        onRetry: failure.retryable ? content.refetch : undefined,
      }}
    />
  );
}

function DocumentView({ normDocumentId, page }: { readonly normDocumentId: NormDocumentId; readonly page: number | null }) {
  const document = useNormDocument(normDocumentId);
  const documentFailure = document.error === null ? null : normFailure(document.error);

  return (
    <PageShell
      title={document.data?.designation ?? 'Нормативный документ'}
      subtitle="Текст документа по абзацам текущего снимка; абзацы с ненадёжно распознанным текстом отмечены."
      actions={<BackToSearch />}
    >
      {document.isPending ? <LoadingState what="нормативный документ" /> : null}
      {documentFailure !== null ? (
        <div data-norm-document-failure={documentFailure.kind}>
          <ErrorState
            title="Нормативный документ не прочитан"
            detail={documentFailure.detail}
            correlationId={documentFailure.correlationId}
            onRetry={documentFailure.retryable ? () => void document.refetch() : undefined}
          />
        </div>
      ) : null}
      {document.data !== undefined ? (
        <>
          <NormDocumentFacts document={document.data} />
          <section aria-label="PDF документа" data-norm-pdf-page={page ?? undefined}>
            {wantsNormPdf(document.data, page)
              ? <OpenPdf document={document.data} page={page} />
              : <NormPdf document={document.data} page={page} documentUrl={null} isLoading={false} error={null} />}
          </section>
        </>
      ) : null}
      <Paragraphs normDocumentId={normDocumentId} />
    </PageShell>
  );
}

export function NormDocumentPage({ normDocumentId, page }: NormDocumentPageProps) {
  if (normDocumentId === null) {
    return (
      <PageShell title="Нормативный документ" actions={<BackToSearch />}>
        <UnsupportedState
          title="Документ не выбран"
          detail="Адрес не называет нормативный документ. Найдите его поиском по нормам и откройте из результатов."
        />
      </PageShell>
    );
  }
  return <DocumentView normDocumentId={normDocumentId} page={page} />;
}
